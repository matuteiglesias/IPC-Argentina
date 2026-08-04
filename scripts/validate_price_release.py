#!/usr/bin/env python3
"""Standard-library validation for price artifact manifests."""
import argparse, csv, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/'contracts/price-release-compatibility.json').read_text())
parser=argparse.ArgumentParser()
parser.add_argument('release',nargs='?',default='fixtures/price-lineage')
parser.add_argument('--consumer',choices=sorted(contract['consumers']))
parser.add_argument('--approved-mode',action='store_true')
args=parser.parse_args()
base=(ROOT/Path(args.release)).resolve()
if ROOT not in base.parents: raise SystemExit('ERROR: release path escapes repository')
manifests=sorted(base.glob('*.manifest.json'))
if not manifests: raise SystemExit('ERROR: no manifests')
for mp in manifests:
 m=json.loads(mp.read_text()); required={'schema','artifact_id','artifact_type','status','frequency','coverage','base_or_reference','files','value_class_column'}
 missing=required-set(m)
 if missing: raise SystemExit(f'ERROR: {mp}: missing {sorted(missing)}')
 if m['schema']!='research-artifact-manifest/v1' or m['artifact_type'] not in contract['allowed_artifact_types'] or m['status'] not in contract['allowed_statuses']: raise SystemExit(f'ERROR: {mp}: invalid envelope/type/status')
 for item in m['files']:
  p=(base/item['path']).resolve()
  if base not in p.parents or not p.is_file(): raise SystemExit(f'ERROR: unsafe or missing path {item["path"]}')
  if hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']: raise SystemExit(f'ERROR: hash mismatch {item["path"]}')
  with p.open(newline='',encoding='utf-8') as f: values={r[m['value_class_column']] for r in csv.DictReader(f)}
  if not values <= set(contract['allowed_value_classes']): raise SystemExit(f'ERROR: invalid value classes {values}')
  if args.consumer and args.approved_mode:
   forbidden=set(contract['consumers'][args.consumer]['approved_mode']['forbid_classes'])
   if values & forbidden: raise SystemExit(f'ERROR: {args.consumer} approved mode forbids {sorted(values & forbidden)} in {item["path"]}')
print(f'validated {len(manifests)} manifests: hashes, safe paths, types, statuses, coverage declarations, and value classes')
