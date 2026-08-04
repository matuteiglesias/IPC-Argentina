"""Frozen legacy-compatible composite calculation (standard library)."""
import math
from datetime import date
from collections import defaultdict
from . import METHOD_ID

def build(rows, source_order, release_id="pending"):
    values=defaultdict(dict); seen={}
    for r in rows:
        key=(r["source_id"],r["period"]); value=float(r["source_index"])
        if not math.isfinite(value) or value<=0: raise ValueError("nonfinite_or_nonpositive_index")
        if key in seen and seen[key]!=value: raise ValueError("conflicting_duplicate")
        seen[key]=value; values[r["period"]][r["source_id"]]=value
    logs={p:{s:math.log10(v) for s,v in x.items()} for p,x in values.items()}
    offsets=[]
    for i,s in enumerate(source_order):
        if i==0: offsets.append(0.0); continue
        prev=source_order[i-1]; overlap=[x[s]-x[prev] for x in logs.values() if s in x and prev in x]
        offsets.append(offsets[-1]-(sum(overlap)/len(overlap) if overlap else 0.0))
    aligned={p:{s:v+offsets[source_order.index(s)] for s,v in x.items()} for p,x in logs.items()}
    base=sum(aligned["2016-01-01"].values())/len(aligned["2016-01-01"])
    periods=sorted(aligned)
    for left,right in zip(periods,periods[1:]):
        y,m=map(int,left[:7].split("-")); expected=f"{y+(m==12):04d}-{1 if m==12 else m+1:02d}-01"
        if right != expected: raise ValueError("no_source_for_emitted_month")
    previous={}; out=[]
    for p in periods:
        x=aligned[p]
        if not x: raise ValueError("no_source_for_emitted_month")
        log_index=sum(x.values())/len(x)-base; changes=[]
        for s,v in values[p].items():
            if s in previous:
                c=100*(v/previous[s]-1)
                if c != 0: changes.append(c)
            previous[s]=v
        out.append({"period":p,"index":100*10**log_index,"log_index":log_index,"monthly_change_pct":sum(changes)/len(changes) if changes else "","contributing_source_ids":"|".join(s for s in source_order if s in x),"contributing_source_count":len(x),"value_status":"derived_from_observed","method_id":METHOD_ID,"release_id":release_id})
    return out, offsets
