"""Bounded discovery, download, and pinning of declared price sources."""
from __future__ import annotations
import hashlib, html as html_lib, json, re, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

USER_AGENT = "IPC-Argentina-candidate-builder/1.0 (research artifact; bounded source probe)"

def _get(url: str, timeout: int = 30) -> tuple[bytes, dict, str]:
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=timeout) as r:
        return r.read(), dict(r.headers.items()), r.geturl()

def _plain(value: str) -> str:
    value = html_lib.unescape(re.sub(r"<[^>]+>", " ", value))
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value).strip().lower()

def _spreadsheet_links(raw_html: str) -> list[tuple[str, str]]:
    pairs = []
    for match in re.finditer(r'''<a\b[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>''', raw_html, re.I | re.S):
        href, body = match.group(1), match.group(2)
        clean = href.split("?", 1)[0].lower()
        if clean.endswith((".xlsx", ".xls", ".csv")):
            pairs.append((href, _plain(body)))
    return pairs

def discover(source: dict) -> tuple[str, list[str]]:
    retrieval = source.get("retrieval", {})
    kind = retrieval.get("kind")
    evidence = []
    if kind in ("direct_file", "direct_csv"):
        return retrieval["url"], evidence
    if kind == "ckan_resource_discovery":
        raw, _, _ = _get(retrieval["ckan_package_api"])
        package = json.loads(raw)["result"]
        preferred = retrieval["preferred_resource_id"]
        resources = package["resources"]
        resource = next((x for x in resources if x.get("id") == preferred), None)
        if resource is None:
            resource = next((x for x in resources if x.get("format", "").upper() == "CSV" and "empalm" in (x.get("name", "")+x.get("description", "")).lower()), None)
        if not resource: raise ValueError("no compatible empalmed CSV resource")
        evidence.append(retrieval["ckan_package_api"])
        return resource["url"], evidence
    if kind == "discover_neuquen_empalmed_download":
        page = source["series_page"]
        raw, _, final = _get(page)
        text = raw.decode("utf-8", "replace")
        anchor = _plain(retrieval.get("anchor_text", "indice de precios al consumidor nivel general serie empalmada"))
        links = _spreadsheet_links(text)
        # Prefer a direct link whose anchor/href explicitly identifies the empalmed IPC.
        explicit = []
        for href, label in links:
            signature = _plain(href + " " + label)
            if "ipc" in signature and ("empalm" in signature or "nivel general" in signature):
                explicit.append(href)
        explicit = list(dict.fromkeys(explicit))
        if len(explicit) == 1:
            evidence.append(final)
            return urljoin(final, explicit[0]), evidence
        if len(explicit) > 1:
            raise ValueError("ambiguous_neuquen_empalmed_download")
        # Some versions of the anuario render a generic `Descargar` anchor after
        # the series label. Bound the search to the first block following the
        # exact label rather than selecting an arbitrary spreadsheet on the page.
        plain_page = _plain(text)
        anchor_pos = plain_page.find(anchor)
        if anchor_pos >= 0:
            candidates = [href for href, label in links if "descargar" in label]
            if len(candidates) == 1:
                evidence.append(final)
                return urljoin(final, candidates[0]), evidence
        raise ValueError("neuquen_empalmed_download_not_unambiguously_discoverable")

    page = source.get("series_page") or source.get("machine_readable_mirror", {}).get("landing_page")
    if not page:
        raise ValueError(f"unsupported_retrieval_kind:{kind}")
    raw, _, final = _get(page)
    html = raw.decode("utf-8", "replace")
    links = re.findall(r'''href=["']([^"']+)["']''', html, re.I)
    if source["source_id"].startswith("idecba"):
        matches = [x for x in links if x.lower().split("?",1)[0].endswith((".xlsx", ".xls")) and "ipc" in x.lower()]
    elif source["source_id"] == "san_luis_ipc_provincial":
        matches = [x for x in links if "IPC-Prov-San-Luis.xlsx".lower() in x.lower()]
    else:
        raise ValueError(f"unsupported_series_page_adapter:{source['source_id']}")
    if not matches: raise ValueError("download anchor not found on series page")
    evidence.append(final)
    return urljoin(final, matches[-1]), evidence

def probe(registry: dict) -> dict:
    results=[]
    for source in registry["sources"]:
        try:
            url, evidence=discover(source); raw, headers, final=_get(url)
            if len(raw) < 20: raise ValueError("malformed short response")
            results.append({"source_id":source["source_id"],"status":"available","resolved_url":final,"byte_size":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"content_type":headers.get("Content-Type"),"discovery_evidence":evidence})
        except Exception as exc:
            results.append({"source_id":source["source_id"],"status":"unavailable","warning_code":"source_unavailable","evidence":f"{type(exc).__name__}: {exc}"})
    return {"schema":"price-source-probe/v1","results":results}

def _portable_snapshot_path(target: Path, lock_path: Path) -> str:
    """Prefer a path relative to the lock so lock + snapshots can move together."""
    target = target.resolve()
    base = lock_path.parent.resolve()
    try:
        return target.relative_to(base).as_posix()
    except ValueError:
        # Compatibility escape hatch for callers intentionally storing the cache
        # elsewhere. New scheduled releases colocate snapshots under the lock root.
        return str(target)

def _resolve_snapshot_path(value: str, base_dir: Path | None) -> tuple[Path | None, str | None]:
    path = Path(value)
    if path.is_absolute():
        return path, None
    if base_dir is None:
        return path, None
    base = Path(base_dir).resolve()
    resolved = (base / path).resolve()
    if resolved != base and base not in resolved.parents:
        return None, "unsafe_snapshot_path"
    return resolved, None

def lock(registry: dict, cache: Path, output: Path) -> dict:
    output = output.resolve(); cache = cache.resolve()
    cache.mkdir(parents=True, exist_ok=True); entries=[]
    for source in registry["sources"]:
        sid=source["source_id"]
        try:
            url, evidence=discover(source); raw, headers, final=_get(url)
            digest=hashlib.sha256(raw).hexdigest(); suffix=Path(final.split("?")[0]).suffix or ".bin"
            target=cache/f"{sid}-{digest}{suffix}"; target.write_bytes(raw)
            entries.append({"source_id":sid,"status":"pinned","resolved_url":final,"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"headers":{"content-type":headers.get("Content-Type"),"last-modified":headers.get("Last-Modified"),"etag":headers.get("ETag")},"byte_size":len(raw),"sha256":digest,"snapshot_path":_portable_snapshot_path(target, output),"parser_id":sid+"/v1","discovery_evidence":evidence,"source_base_or_vintage":"adapter-inspected"})
        except Exception as exc:
            entries.append({"source_id":sid,"status":"unavailable","warning_code":"source_unavailable","evidence":f"{type(exc).__name__}: {exc}"})
    result={"schema":"price-source-lock/v1","registry_id":registry["registry_id"],"entries":entries}
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result

def check_lock(lock_data: dict, base_dir: Path | None = None) -> list[str]:
    errors=[]; pinned=0
    for e in lock_data["entries"]:
        if e["status"] != "pinned": continue
        pinned+=1
        p, path_error = _resolve_snapshot_path(e["snapshot_path"], base_dir)
        if path_error:
            errors.append(path_error+":"+e["source_id"]); continue
        if p is None or not p.is_file():
            errors.append("checksum_mismatch:"+e["source_id"]); continue
        raw = p.read_bytes()
        if len(raw) != e["byte_size"] or hashlib.sha256(raw).hexdigest()!=e["sha256"]:
            errors.append("checksum_mismatch:"+e["source_id"])
    if not pinned: errors.append("no_pinned_source")
    return errors
