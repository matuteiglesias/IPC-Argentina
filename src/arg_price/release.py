"""Deterministic release-envelope writer."""
from __future__ import annotations
import csv, hashlib, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
from . import METHOD_ID, MONETARY_REFERENCE_ID

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write_csv(path, rows, fields):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)

def commit_info(root):
    commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    stamp=subprocess.check_output(["git","show","-s","--format=%cI",commit],cwd=root,text=True).strip()
    return commit,stamp

def recovered_candidate(root: Path) -> Path:
    """Package the retained observed core when live sources cannot be pinned.

    This is deliberately identified as recovered legacy evidence, not a fresh
    source regeneration. It provides a usable candidate without disguising the
    missing historical input hashes.
    """
    commit,created=commit_info(root); source=root/"data/info/indice_precios_M.csv"
    source_hash=sha(source); release_id=f"ipc-candidate-v1-{source_hash[:12]}"
    out=root/"artifacts/price_releases"/release_id; out.mkdir(parents=True,exist_ok=True)
    raw=list(csv.DictReader(source.open())); raw=[r for r in raw if r[""] <= "2025-07-01"]
    monthly=[]
    for r in raw:
        monthly.append({"period":r[""],"index":r["index"],"log_index":r["log_index"],"monthly_change_pct":r["pct_m"],"contributing_source_ids":"historical_inputs_not_retained","contributing_source_count":"","value_status":"derived_from_observed","method_id":METHOD_ID,"release_id":release_id})
    write_csv(out/"monthly_composite.csv",monthly,list(monthly[0]))
    quarters=[]
    for i in range(0,len(monthly),3):
        group=monthly[i:i+3]
        if len(group)==3:
            middle=group[1]["period"][:8]+"15"
            quarters.append({"period":middle,"index":format(sum(float(x["index"]) for x in group)/3,'.15g'),"value_status":"derived_aggregate","release_id":release_id})
    write_csv(out/"quarterly_composite.csv",quarters,list(quarters[0]))
    write_csv(out/"normalized_sources.csv",[],["source_id","period","source_index","source_base_or_vintage","value_status","source_snapshot_sha256","parser_id"])
    write_csv(out/"source_coverage.csv",[{"source_id":"historical_inputs_not_retained","period_start":"2000-01-01","period_end":"2025-07-01","row_count":len(monthly),"status":"warning"}], ["source_id","period_start","period_end","row_count","status"])
    lock={"schema":"price-source-lock/v1","status":"historical_inputs_not_retained","entries":[],"legacy_composite_sha256":source_hash,"warnings":["historical_source_hash_not_retained"]}
    (out/"source_lock.json").write_text(json.dumps(lock,indent=2,sort_keys=True)+"\n")
    method={"method_id":METHOD_ID,"source_order":["indec_ipc_national","idecba_ipc_level_general_empalmed","cordoba_ipc","san_luis_ipc_provincial","indec_ipc_gba_historical"],"algorithm":"log10; sequential mean-overlap offsets; row mean; 2016-01=100; mean non-zero source changes","materialization":"recovered retained legacy composite; inputs unavailable"}
    (out/"method.json").write_text(json.dumps(method,indent=2,sort_keys=True)+"\n")
    warnings=["source_unavailable","historical_source_hash_not_retained","historical_eph_price_hash_unavailable","partial_monthly_source_coverage","projection_excluded_from_core"]
    compatibility={"schema":"price-release-compatibility-declaration/v1","consumer":"canastasINDEC","monetary_reference_id":MONETARY_REFERENCE_ID,"status":"candidate","allow_candidate_with_warnings":True,"projection_included":False,"observed_derived_through":"2025-07-01","warnings":warnings}
    (out/"compatibility.json").write_text(json.dumps(compatibility,indent=2,sort_keys=True)+"\n")
    qa={"schema":"price-candidate-qa/v1","hard_failures":[],"warnings":warnings,"monthly_rows":len(monthly),"quarterly_rows":len(quarters),"normalized_source_rows":0}
    (out/"qa.json").write_text(json.dumps(qa,indent=2,sort_keys=True)+"\n")
    (out/"limitations.md").write_text("# Candidate limitations\n\nThis is an analytical composite, not an official IPC. Live source contact was blocked by the execution proxy. The candidate is a deterministic envelope around the retained legacy-derived core through 2025-07; exact historical source snapshots and the historical EPH-consumed artifact hash are unavailable. Projection is excluded. Source identity by month cannot be reconstructed.\n")
    payload=["compatibility.json","method.json","source_lock.json","source_coverage.csv","normalized_sources.csv","monthly_composite.csv","quarterly_composite.csv","qa.json","limitations.md"]
    manifest={"schema":"research-artifact-manifest/v1","artifact_id":release_id,"release_id":release_id,"artifact_type":"research.argentina-price-composite/v1","status":"candidate","method_id":METHOD_ID,"monetary_reference_id":MONETARY_REFERENCE_ID,"producer":{"repository":"IPC-Argentina","commit":commit},"created_at":created,"coverage":{"monthly":{"start":"2000-01-01","end":"2025-07-01","status":"derived_from_observed"},"quarterly":{"start":quarters[0]["period"],"end":quarters[-1]["period"],"status":"derived_aggregate"}},"warnings":warnings,"files":[{"path":p,"sha256":sha(out/p),"size":(out/p).stat().st_size,"role":p.rsplit('.',1)[0]} for p in payload]}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    allfiles=["manifest.json"]+payload
    (out/"checksums.sha256").write_text("".join(f"{sha(out/p)}  {p}\n" for p in allfiles))
    return out
