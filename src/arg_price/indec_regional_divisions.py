"""Governed INDEC IPC region × expenditure-division price surface.

This module intentionally does not participate in the repository's curated
multi-source consensus.  It packages exact INDEC observations from the
historical regional-division series as a separate public-data product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

PRODUCT_ID = "publicdata.indec-ipc-regional-divisions/v1"
SOURCE_ID = "indec_ipc_regional_divisions"
PARSER_ID = "indec_ipc_regional_divisions/csv-v1"
INDEX_BASE = "2016-12=100"
SOURCE_URL = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_divisiones.csv"
METADATA_URL = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_metadatos.txt"
LANDING_PAGE = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31"

REGIONS = {
    "gba": "gran_buenos_aires",
    "gran buenos aires": "gran_buenos_aires",
    "pampeana": "pampeana",
    "noreste": "noreste",
    "nea": "noreste",
    "noroeste": "noroeste",
    "noa": "noroeste",
    "cuyo": "cuyo",
    "patagonia": "patagonia",
}
EXPECTED_REGIONS = tuple(sorted(set(REGIONS.values())))

# INDEC publishes divisions under COICOP. These stable IDs preserve the
# official 01–12 division order without pretending the repository owns the
# classification itself.
DIVISIONS = {
    "alimentos y bebidas no alcoholicas": ("coicop01", "Alimentos y bebidas no alcohólicas"),
    "bebidas alcoholicas y tabaco": ("coicop02", "Bebidas alcohólicas y tabaco"),
    "prendas de vestir y calzado": ("coicop03", "Prendas de vestir y calzado"),
    "vivienda agua electricidad gas y otros combustibles": ("coicop04", "Vivienda, agua, electricidad, gas y otros combustibles"),
    "equipamiento y mantenimiento del hogar": ("coicop05", "Equipamiento y mantenimiento del hogar"),
    "salud": ("coicop06", "Salud"),
    "transporte": ("coicop07", "Transporte"),
    "comunicacion": ("coicop08", "Comunicación"),
    "recreacion y cultura": ("coicop09", "Recreación y cultura"),
    "educacion": ("coicop10", "Educación"),
    "restaurantes y hoteles": ("coicop11", "Restaurantes y hoteles"),
    "bienes y servicios varios": ("coicop12", "Bienes y servicios varios"),
}
EXPECTED_DIVISIONS = tuple(f"coicop{i:02d}" for i in range(1, 13))

OUTPUT_FIELDS = (
    "period",
    "region_id",
    "division_id",
    "division_label",
    "index_value",
    "index_base",
    "source_id",
    "source_snapshot_sha256",
    "source_cell_identity",
    "value_status",
)


def _plain(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _column_map(fieldnames: Iterable[str]) -> dict[str, str]:
    return {_plain(name): name for name in fieldnames if name is not None}


def _find_column(columns: dict[str, str], *aliases: str, required: bool = True) -> str | None:
    for alias in aliases:
        hit = columns.get(_plain(alias))
        if hit:
            return hit
    if required:
        raise ValueError("missing_required_column:" + "/".join(aliases))
    return None


def _parse_period(value: object) -> str:
    raw = str(value or "").strip()
    for pattern in (r"^(\d{4})[-/](\d{1,2})(?:[-/]\d{1,2})?$", r"^(\d{1,2})[-/](\d{4})$"):
        match = re.match(pattern, raw)
        if match:
            if pattern.startswith("^(\\d{4})"):
                year, month = int(match.group(1)), int(match.group(2))
            else:
                month, year = int(match.group(1)), int(match.group(2))
            if 1 <= month <= 12:
                return f"{year:04d}-{month:02d}-01"
    raise ValueError(f"invalid_period:{raw}")


def _parse_number(value: object) -> str:
    raw = str(value or "").strip().replace("\u00a0", "")
    if not raw or _plain(raw) in {"na", "n a", "no aplica", "s d", "sd"}:
        raise ValueError("missing_index_value")
    if "," in raw and "." in raw:
        # Source is Spanish; when both separators occur, dots are thousands and
        # comma is decimal for the published CSV representation.
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    number = float(raw)
    if not (number > 0 and number < float("inf")):
        raise ValueError(f"invalid_index_value:{value}")
    return format(number, ".15g")


def _division_from_row(label: object, code: object = "", classifier: object = "") -> tuple[str, str] | None:
    label_plain = _plain(label)
    if label_plain in {"nivel general", "general"}:
        return None
    if label_plain in DIVISIONS:
        return DIVISIONS[label_plain]

    # Be tolerant of a source code such as 01, 1, 01.0 or COICOP 01, but only
    # after confirming the row is classified as a division rather than a group.
    class_plain = _plain(classifier)
    if class_plain and "division" not in class_plain and "coicop" not in class_plain:
        raise ValueError(f"unsupported_classifier:{classifier}")
    digits = re.findall(r"\d+", str(code or ""))
    if digits:
        candidate = int(digits[0])
        if 1 <= candidate <= 12:
            division_id = f"coicop{candidate:02d}"
            known = {v[0]: v[1] for v in DIVISIONS.values()}
            return division_id, known[division_id]
    raise ValueError(f"unknown_division:{label}")


def normalize_csv(raw: bytes, source_snapshot_sha256: str | None = None) -> list[dict[str, str]]:
    digest = source_snapshot_sha256 or hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8-sig")
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("missing_csv_header")
    columns = _column_map(reader.fieldnames)
    period_col = _find_column(columns, "periodo", "period", "fecha", "indice_tiempo", "periodo_referencia")
    region_col = _find_column(columns, "region", "region geografica", "descripcion_region", "region_geografica")
    label_col = _find_column(columns, "descripcion_divisiones", "division", "descripcion division", "descripcion")
    index_col = _find_column(columns, "indice_ipc", "indice ipc", "indice", "index_value", "valor")
    code_col = _find_column(columns, "codigo", "code", "codigo coicop", required=False)
    classifier_col = _find_column(columns, "clasificador", "classifier", required=False)
    base_col = _find_column(columns, "base", "indice_base", "index_base", required=False)

    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for source_row_number, source in enumerate(reader, start=2):
        region_raw = source.get(region_col, "")
        region_plain = _plain(region_raw)
        region_id = REGIONS.get(region_plain)
        if region_id is None:
            for label, candidate in sorted(REGIONS.items(), key=lambda item: -len(item[0])):
                if label in region_plain:
                    region_id = candidate
                    break
        if region_id is None:
            # The same file may contain Total nacional. The product contract is
            # strictly the six official regions, so non-regional rows are skipped.
            if region_plain in {"nacional", "total nacional", "total pais", "total del pais"}:
                continue
            raise ValueError(f"unknown_region:{region_raw}")
        division = _division_from_row(
            source.get(label_col, ""),
            source.get(code_col, "") if code_col else "",
            source.get(classifier_col, "") if classifier_col else "",
        )
        if division is None:
            continue
        division_id, division_label = division
        period = _parse_period(source.get(period_col, ""))
        index_value = _parse_number(source.get(index_col, ""))
        index_base = str(source.get(base_col, "")).strip() if base_col else INDEX_BASE
        if base_col and _plain(index_base) not in {_plain(INDEX_BASE), "diciembre 2016 100", "dic 2016 100"}:
            raise ValueError(f"base_period_inconsistent:{index_base}")
        index_base = INDEX_BASE
        key = (period, region_id, division_id)
        if key in seen:
            raise ValueError("duplicate_cell:" + "|".join(key))
        seen.add(key)
        cell = (
            f"serie_ipc_divisiones.csv#row={source_row_number};column={index_col};"
            f"period={period};region={region_id};division={division_id}"
        )
        rows.append(
            {
                "period": period,
                "region_id": region_id,
                "division_id": division_id,
                "division_label": division_label,
                "index_value": index_value,
                "index_base": index_base,
                "source_id": SOURCE_ID,
                "source_snapshot_sha256": digest,
                "source_cell_identity": cell,
                "value_status": "direct_official_observation",
            }
        )
    rows.sort(key=lambda r: (r["period"], r["region_id"], r["division_id"]))
    if not rows:
        raise ValueError("no_regional_division_rows")
    return rows


def _month_sequence(start: str, end: str) -> list[str]:
    """Return first-of-month ISO dates from start through end, inclusive."""
    year, month = map(int, start[:7].split("-"))
    end_year, end_month = map(int, end[:7].split("-"))
    out: list[str] = []
    while (year, month) <= (end_year, end_month):
        out.append(f"{year:04d}-{month:02d}-01")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return out


def coverage(rows: Iterable[dict[str, str]]) -> dict:
    rows = list(rows)
    periods = sorted({r["period"] for r in rows})
    expected_periods = _month_sequence(periods[0], periods[-1]) if periods else []
    missing_months = sorted(set(expected_periods) - set(periods))
    regions = sorted({r["region_id"] for r in rows})
    divisions = sorted({r["division_id"] for r in rows})
    keys = {(r["period"], r["region_id"], r["division_id"]) for r in rows}
    duplicate_count = len(rows) - len(keys)
    missing = [
        {"period": p, "region_id": region, "division_id": division}
        for p in expected_periods
        for region in EXPECTED_REGIONS
        for division in EXPECTED_DIVISIONS
        if (p, region, division) not in keys
    ]
    bases = sorted({r["index_base"] for r in rows})
    required_window = set(_month_sequence("2018-05-01", "2025-12-01"))
    covered_periods = set(periods)
    return {
        "schema": "indec-ipc-regional-divisions-coverage/v1",
        "product_id": PRODUCT_ID,
        "first_month": periods[0] if periods else None,
        "last_month": periods[-1] if periods else None,
        "number_of_months": len(periods),
        "expected_months_in_span": len(expected_periods),
        "missing_months": missing_months,
        "region_inventory": regions,
        "division_inventory": divisions,
        "missing_region_ids": sorted(set(EXPECTED_REGIONS) - set(regions)),
        "missing_division_ids": sorted(set(EXPECTED_DIVISIONS) - set(divisions)),
        "missing_cells_count": len(missing),
        "duplicate_cells_count": duplicate_count,
        "index_bases": bases,
        "base_period_consistent": bases == [INDEX_BASE],
        "structural_breaks": [] if bases == [INDEX_BASE] else [{"kind": "index_base_change", "index_bases": bases}],
        "covers_may_2018_through_2025": required_window.issubset(covered_periods),
        "expected_regions": list(EXPECTED_REGIONS),
        "expected_divisions": list(EXPECTED_DIVISIONS),
        "missing_cells": missing,
    }


def validate_rows(rows: Iterable[dict[str, str]], require_engel_window: bool = False) -> list[str]:
    rows = list(rows)
    errors: list[str] = []
    keys = [(r["period"], r["region_id"], r["division_id"]) for r in rows]
    if len(keys) != len(set(keys)):
        errors.append("duplicate_cells")
    if any(r.get("value_status") != "direct_official_observation" for r in rows):
        errors.append("non_official_or_imputed_value_status")
    if any(r.get("index_base") != INDEX_BASE for r in rows):
        errors.append("base_period_inconsistent")
    if any(r.get("region_id") not in EXPECTED_REGIONS for r in rows):
        errors.append("unexpected_region")
    if any(r.get("division_id") not in EXPECTED_DIVISIONS for r in rows):
        errors.append("unexpected_division")
    cov = coverage(rows)
    if require_engel_window and not cov["covers_may_2018_through_2025"]:
        errors.append("required_2018_05_through_2025_coverage_missing")
    return errors


def _write_csv(path: Path, rows: Iterable[dict[str, str]], fields: Iterable[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def source_lock(
    raw: bytes,
    retrieved_at_utc: str,
    resolved_url: str = SOURCE_URL,
    metadata_raw: bytes | None = None,
    metadata_resolved_url: str = METADATA_URL,
) -> dict:
    result = {
        "schema": "indec-ipc-regional-divisions-source-lock/v1",
        "source_id": SOURCE_ID,
        "authority": "Instituto Nacional de Estadística y Censos (INDEC)",
        "landing_page": LANDING_PAGE,
        "resolved_url": resolved_url,
        "metadata_url": METADATA_URL,
        "metadata_resolved_url": metadata_resolved_url,
        "retrieved_at_utc": retrieved_at_utc,
        "byte_size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "parser_id": PARSER_ID,
        "index_base": INDEX_BASE,
    }
    if metadata_raw is not None:
        result["metadata_byte_size"] = len(metadata_raw)
        result["metadata_sha256"] = hashlib.sha256(metadata_raw).hexdigest()
    return result


def lock_source(output_root: Path, timeout: int = 60) -> Path:
    request = Request(SOURCE_URL, headers={"User-Agent": "IPC-Argentina/indec-regional-divisions-v1"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        resolved_url = response.geturl()
    metadata_request = Request(METADATA_URL, headers={"User-Agent": "IPC-Argentina/indec-regional-divisions-v1"})
    with urlopen(metadata_request, timeout=timeout) as response:
        metadata_raw = response.read()
        metadata_resolved_url = response.geturl()
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    lock = source_lock(raw, stamp, resolved_url, metadata_raw, metadata_resolved_url)
    digest = lock["sha256"]
    root = Path(output_root).resolve()
    snapshot = root / "snapshots" / f"serie_ipc_divisiones-{digest}.csv"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if snapshot.exists() and snapshot.read_bytes() != raw:
        raise ValueError("immutable_snapshot_collision")
    snapshot.write_bytes(raw)
    lock["snapshot_path"] = os.path.relpath(snapshot, root)
    metadata_digest = lock["metadata_sha256"]
    metadata_snapshot = root / "snapshots" / f"serie_ipc_metadatos-{metadata_digest}.txt"
    if metadata_snapshot.exists() and metadata_snapshot.read_bytes() != metadata_raw:
        raise ValueError("immutable_metadata_snapshot_collision")
    metadata_snapshot.write_bytes(metadata_raw)
    lock["metadata_snapshot_path"] = os.path.relpath(metadata_snapshot, root)
    lock_path = root / "source_lock.json"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_bytes(_json_bytes(lock))
    return lock_path


def load_locked_source(lock_path: Path) -> tuple[dict, bytes]:
    lock_path = Path(lock_path).resolve()
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("schema") != "indec-ipc-regional-divisions-source-lock/v1":
        raise ValueError("wrong_source_lock_schema")
    snapshot = (lock_path.parent / lock["snapshot_path"]).resolve()
    if lock_path.parent not in snapshot.parents:
        raise ValueError("unsafe_snapshot_path")
    raw = snapshot.read_bytes()
    if len(raw) != lock.get("byte_size") or hashlib.sha256(raw).hexdigest() != lock.get("sha256"):
        raise ValueError("source_lock_checksum_mismatch")
    if lock.get("metadata_snapshot_path"):
        metadata_snapshot = (lock_path.parent / lock["metadata_snapshot_path"]).resolve()
        if lock_path.parent not in metadata_snapshot.parents:
            raise ValueError("unsafe_metadata_snapshot_path")
        metadata_raw = metadata_snapshot.read_bytes()
        if (
            len(metadata_raw) != lock.get("metadata_byte_size")
            or hashlib.sha256(metadata_raw).hexdigest() != lock.get("metadata_sha256")
        ):
            raise ValueError("metadata_source_lock_checksum_mismatch")
    return lock, raw


def build_release(lock_path: Path, output_root: Path) -> Path:
    lock, raw = load_locked_source(lock_path)
    rows = normalize_csv(raw, lock["sha256"])
    errors = validate_rows(rows)
    if errors:
        raise ValueError("invalid_normalized_rows:" + ",".join(errors))
    cov = coverage(rows)
    normalized_bytes = io.StringIO()
    writer = csv.DictWriter(normalized_bytes, fieldnames=list(OUTPUT_FIELDS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    normalized_payload = normalized_bytes.getvalue().encode("utf-8")
    normalized_sha = hashlib.sha256(normalized_payload).hexdigest()
    release_id = f"indec-ipc-regional-divisions-v1-{lock['sha256'][:12]}-{normalized_sha[:12]}"
    output_root = Path(output_root).resolve()
    target = output_root / release_id

    if target.exists():
        manifest_path = target / "manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("release_id") == release_id and not validate_release(target):
                return target
        raise ValueError("immutable_release_collision")

    output_root.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=release_id + ".", dir=output_root))
    try:
        (temp / "regional_division_indices.csv").write_bytes(normalized_payload)
        (temp / "coverage.json").write_bytes(_json_bytes({k: v for k, v in cov.items() if k != "missing_cells"}))
        _write_csv(temp / "missing_cells.csv", cov["missing_cells"], ("period", "region_id", "division_id"))
        release_lock = dict(lock)
        release_lock.pop("snapshot_path", None)
        release_lock.pop("metadata_snapshot_path", None)
        (temp / "source_lock.json").write_bytes(_json_bytes(release_lock))
        contract = {
            "product_id": PRODUCT_ID,
            "source_id": SOURCE_ID,
            "parser_id": PARSER_ID,
            "grain": ["period", "region_id", "division_id"],
            "index_base": INDEX_BASE,
            "regions": list(EXPECTED_REGIONS),
            "divisions": list(EXPECTED_DIVISIONS),
            "value_status": "direct_official_observation",
            "imputation": "forbidden",
            "consensus_membership": "none",
        }
        (temp / "contract.json").write_bytes(_json_bytes(contract))
        payloads = ["regional_division_indices.csv", "coverage.json", "missing_cells.csv", "source_lock.json", "contract.json"]
        manifest = {
            "schema": "research-artifact-manifest/v1",
            "artifact_type": PRODUCT_ID,
            "release_id": release_id,
            "status": "direct_official_evidence",
            "source_id": SOURCE_ID,
            "source_snapshot_sha256": lock["sha256"],
            "source_retrieved_at_utc": lock["retrieved_at_utc"],
            "coverage": {
                "first_month": cov["first_month"],
                "last_month": cov["last_month"],
                "number_of_months": cov["number_of_months"],
                "missing_cells_count": cov["missing_cells_count"],
            },
            "files": [
                {"path": name, "sha256": _sha256(temp / name), "size": (temp / name).stat().st_size}
                for name in payloads
            ],
        }
        (temp / "manifest.json").write_bytes(_json_bytes(manifest))
        checksum_names = ["manifest.json", *payloads]
        (temp / "checksums.sha256").write_text(
            "".join(f"{_sha256(temp / name)}  {name}\n" for name in checksum_names),
            encoding="utf-8",
        )
        temp.rename(target)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    return target


def validate_release(release: Path, require_engel_window: bool = False) -> list[str]:
    release = Path(release).resolve()
    errors: list[str] = []
    try:
        manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"manifest_unreadable:{type(exc).__name__}"]
    if manifest.get("artifact_type") != PRODUCT_ID:
        errors.append("wrong_product_id")
    for item in manifest.get("files", []):
        path = (release / item["path"]).resolve()
        if release not in path.parents or not path.is_file():
            errors.append("missing_or_unsafe_file:" + item["path"])
            continue
        if path.stat().st_size != item["size"] or _sha256(path) != item["sha256"]:
            errors.append("checksum_mismatch:" + item["path"])
    with (release / "regional_division_indices.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    errors.extend(validate_rows(rows, require_engel_window=require_engel_window))
    cov = coverage(rows)
    declared = json.loads((release / "coverage.json").read_text(encoding="utf-8"))
    for key in (
        "first_month",
        "last_month",
        "number_of_months",
        "expected_months_in_span",
        "missing_months",
        "missing_cells_count",
        "duplicate_cells_count",
        "index_bases",
    ):
        if declared.get(key) != cov.get(key):
            errors.append("coverage_manifest_mismatch:" + key)
    return sorted(set(errors))


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    lock_p = sub.add_parser("lock", help="download and pin the exact official INDEC CSV")
    lock_p.add_argument("--output-root", default="build/indec_ipc_regional_divisions")
    build_p = sub.add_parser("build", help="materialize an immutable normalized release from a source lock")
    build_p.add_argument("--lock", default="build/indec_ipc_regional_divisions/source_lock.json")
    build_p.add_argument("--output-root", default="artifacts/indec_ipc_regional_divisions")
    validate_p = sub.add_parser("validate", help="validate a materialized release")
    validate_p.add_argument("release")
    validate_p.add_argument("--require-engel-window", action="store_true")
    coverage_p = sub.add_parser("coverage", help="print release coverage diagnostics")
    coverage_p.add_argument("release")
    args = parser.parse_args()
    if args.command == "lock":
        print(lock_source(Path(args.output_root)))
    elif args.command == "build":
        print(build_release(Path(args.lock), Path(args.output_root)))
    elif args.command == "validate":
        errors = validate_release(Path(args.release), require_engel_window=args.require_engel_window)
        if errors:
            raise SystemExit("ERROR: " + ", ".join(errors))
        print("valid INDEC regional-division release")
    elif args.command == "coverage":
        with (Path(args.release) / "regional_division_indices.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        print(json.dumps(coverage(rows), indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    _main()
