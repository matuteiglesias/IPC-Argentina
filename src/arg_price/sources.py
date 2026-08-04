"""Bounded discovery, download, and pinning of declared price sources."""
from __future__ import annotations
import hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

USER_AGENT = "IPC-Argentina-candidate-builder/1.0 (research artifact; bounded source probe)"

def _get(url: str, timeout: int = 30) -> tuple[bytes, dict, str]:
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=timeout) as r:
        return r.read(), dict(r.headers.items()), r.geturl()

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
    page = source.get("series_page") or source.get("machine_readable_mirror", {}).get("landing_page")
    raw, _, final = _get(page)
    html = raw.decode("utf-8", "replace")
    links = re.findall(r'''href=["']([^"']+)["']''', html, re.I)
    if source["source_id"].startswith("idecba"):
        matches = [x for x in links if x.lower().endswith((".xlsx", ".xls")) and "ipc" in x.lower()]
    else:
        matches = [x for x in links if "IPC-Prov-San-Luis.xlsx".lower() in x.lower()]
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

def lock(registry: dict, cache: Path, output: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True); entries=[]
    for source in registry["sources"]:
        sid=source["source_id"]
        try:
            url, evidence=discover(source); raw, headers, final=_get(url)
            digest=hashlib.sha256(raw).hexdigest(); suffix=Path(final.split("?")[0]).suffix or ".bin"
            target=cache/f"{sid}-{digest}{suffix}"; target.write_bytes(raw)
            entries.append({"source_id":sid,"status":"pinned","resolved_url":final,"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"headers":{"content-type":headers.get("Content-Type"),"last-modified":headers.get("Last-Modified"),"etag":headers.get("ETag")},"byte_size":len(raw),"sha256":digest,"snapshot_path":str(target),"parser_id":sid+"/v1","discovery_evidence":evidence,"source_base_or_vintage":"adapter-inspected"})
        except Exception as exc:
            entries.append({"source_id":sid,"status":"unavailable","warning_code":"source_unavailable","evidence":f"{type(exc).__name__}: {exc}"})
    result={"schema":"price-source-lock/v1","registry_id":registry["registry_id"],"entries":entries}
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result

def check_lock(lock_data: dict) -> list[str]:
    errors=[]; pinned=0
    for e in lock_data["entries"]:
        if e["status"] != "pinned": continue
        pinned+=1; p=Path(e["snapshot_path"])
        if not p.is_file() or len(p.read_bytes()) != e["byte_size"] or hashlib.sha256(p.read_bytes()).hexdigest()!=e["sha256"]: errors.append("checksum_mismatch:"+e["source_id"])
    if not pinned: errors.append("no_pinned_source")
    return errors
