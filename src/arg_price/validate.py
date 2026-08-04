"""Standard-library consumer preflight for a candidate release."""
import argparse,csv,hashlib,json
from pathlib import Path
from . import METHOD_ID,MONETARY_REFERENCE_ID

def validate(base, require_no_projection=False, require_period=None, require_monetary_reference=None):
    base=Path(base).resolve(); errors=[]
    try: m=json.loads((base/"manifest.json").read_text())
    except Exception as exc: return ["corrupted_declared_file:"+str(exc)]
    if m.get("schema")!="research-artifact-manifest/v1" or m.get("artifact_type")!="research.argentina-price-composite/v1": errors.append("method_identity_mismatch")
    if m.get("method_id")!=METHOD_ID: errors.append("method_identity_mismatch")
    wanted=require_monetary_reference or MONETARY_REFERENCE_ID
    if m.get("monetary_reference_id")!=wanted: errors.append("method_identity_mismatch")
    for item in m.get("files",[]):
        p=(base/item["path"]).resolve()
        if base not in p.parents or not p.is_file(): errors.append("unsafe_path:"+item["path"]); continue
        if hashlib.sha256(p.read_bytes()).hexdigest()!=item["sha256"] or p.stat().st_size!=item["size"]: errors.append("checksum_mismatch:"+item["path"])
    monthly=base/"monthly_composite.csv"
    if monthly.is_file():
        rows=list(csv.DictReader(monthly.open()))
        if require_no_projection and any(r["value_status"] in ("projected","synthetic_projection") for r in rows): errors.append("projection_present")
        if require_period and not any(r["period"]==require_period for r in rows): errors.append("required_period_missing")
        if any(not r["period"] or float(r["index"])<=0 for r in rows): errors.append("nonfinite_or_nonpositive_index")
    return errors

def main():
    p=argparse.ArgumentParser(); p.add_argument("release"); p.add_argument("--require-no-projection",action="store_true"); p.add_argument("--require-period"); p.add_argument("--require-monetary-reference"); a=p.parse_args()
    errors=validate(a.release,a.require_no_projection,a.require_period,a.require_monetary_reference)
    if errors: raise SystemExit("ERROR: "+", ".join(errors))
    qa=json.loads((Path(a.release)/"qa.json").read_text()); print(f"valid candidate; {len(qa['warnings'])} warning code(s); 0 hard failures")
if __name__=="__main__": main()
