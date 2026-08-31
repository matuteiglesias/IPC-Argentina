import hashlib, math, tempfile, unittest
from pathlib import Path
from arg_price.composite import build
from arg_price.sources import check_lock

ORDER=["a","b"]
def row(s,p,v): return {"source_id":s,"period":p,"source_index":v}
class CompositeTests(unittest.TestCase):
 def data(self):
  return [row("a","2015-12-01",50),row("a","2016-01-01",55),row("a","2016-02-01",60),row("b","2016-01-01",110),row("b","2016-02-01",120),row("b","2016-03-01",130)]
 def test_overlap_partial_and_one_source(self):
  out, offsets=build(self.data(),ORDER)
  self.assertAlmostEqual(offsets[1],-math.log10(2)); self.assertEqual(out[-1]["contributing_source_count"],1); self.assertAlmostEqual(out[1]["index"],100)
 def test_scale_invariance(self):
  a,_=build(self.data(),ORDER); b,_=build([{**r,"source_index":r["source_index"]*7 if r["source_id"]=="b" else r["source_index"]} for r in self.data()],ORDER)
  self.assertEqual([round(x["index"],10) for x in a],[round(x["index"],10) for x in b])
 def test_invalid_and_conflict(self):
  with self.assertRaisesRegex(ValueError,"nonfinite"): build(self.data()+[row("a","2017-01-01",0)],ORDER)
  with self.assertRaisesRegex(ValueError,"conflicting"): build(self.data()+[row("a","2016-01-01",56)],ORDER)
  with self.assertRaisesRegex(ValueError,"no_source"): build([row("a","2016-01-01",1),row("a","2016-03-01",2)],ORDER)
 def test_source_order_identity(self): self.assertEqual(build(self.data(),ORDER)[0][0]["method_id"],"research.argentina-price-composite/legacy-compatible-v1")
 def test_stable(self): self.assertEqual(build(self.data(),ORDER),build(self.data(),ORDER))

class SourceLockTests(unittest.TestCase):
 def test_relative_snapshot_is_portable(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp); snap=root/"snapshots/source.csv"; snap.parent.mkdir(); raw=b"period,value\n2026-07,1\n"; snap.write_bytes(raw)
   lock={"entries":[{"source_id":"source","status":"pinned","snapshot_path":"snapshots/source.csv","byte_size":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}]}
   self.assertEqual(check_lock(lock,root),[])
   snap.write_bytes(raw+b"tampered")
   self.assertEqual(check_lock(lock,root),["checksum_mismatch:source"])
 def test_relative_snapshot_cannot_escape_lock_root(self):
  lock={"entries":[{"source_id":"source","status":"pinned","snapshot_path":"../source.csv","byte_size":1,"sha256":"x"}]}
  with tempfile.TemporaryDirectory() as tmp:
   self.assertEqual(check_lock(lock,Path(tmp)),["unsafe_snapshot_path:source"])

if __name__=="__main__": unittest.main()
