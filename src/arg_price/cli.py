import argparse,json
from pathlib import Path
from .sources import probe,lock,check_lock
from .release import recovered_candidate

ROOT=Path(__file__).resolve().parents[2]
def registry(): return json.loads((ROOT/"contracts/source_registry.json").read_text())
def main():
 p=argparse.ArgumentParser(); p.add_argument("command",choices=["probe","lock","lock-check","candidate"]); p.add_argument("--lock",default="build/price_sources/source_lock.json"); a=p.parse_args()
 lock_path=(ROOT/a.lock).resolve()
 if a.command=="probe": result=probe(registry()); print(json.dumps(result,indent=2)); return
 if a.command=="lock": result=lock(registry(),ROOT/"build/price_sources/snapshots",lock_path); print(json.dumps(result,indent=2)); return
 if a.command=="lock-check":
  errors=check_lock(json.loads(lock_path.read_text()),lock_path.parent); print("valid source lock" if not errors else "ERROR: "+", ".join(errors)); raise SystemExit(bool(errors))
 if a.command=="candidate": print(recovered_candidate(ROOT))
if __name__=="__main__": main()
