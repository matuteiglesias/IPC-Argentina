import argparse,json
from pathlib import Path
from .sources import probe,lock,check_lock
from .release import recovered_candidate
from .v2_release import build_all

ROOT=Path(__file__).resolve().parents[2]
def registry(): return json.loads((ROOT/"contracts/source_registry.json").read_text())
def main():
 p=argparse.ArgumentParser(); p.add_argument("command",choices=["probe","lock","lock-check","candidate","v2-build"]); p.add_argument("--lock",default="build/price_sources/source_lock.json"); p.add_argument("--output-root",default="artifacts/price_v2"); a=p.parse_args()
 if a.command=="probe": result=probe(registry()); print(json.dumps(result,indent=2)); return
 if a.command=="lock": result=lock(registry(),ROOT/"build/price_sources/snapshots",ROOT/a.lock); print(json.dumps(result,indent=2)); return
 if a.command=="lock-check":
  lock_path=(ROOT/a.lock).resolve(); errors=check_lock(json.loads(lock_path.read_text()),lock_path.parent); print("valid source lock" if not errors else "ERROR: "+", ".join(errors)); raise SystemExit(bool(errors))
 if a.command=="candidate": print(recovered_candidate(ROOT)); return
 if a.command=="v2-build":
  result=build_all((ROOT/a.lock).resolve(),(ROOT/a.output_root).resolve()); print(json.dumps({k:str(v) for k,v in result.items()},indent=2)); return
if __name__=="__main__": main()
