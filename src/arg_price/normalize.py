"""Source-specific snapshot parsers producing the canonical source table."""
from __future__ import annotations
import csv, io
from pathlib import Path

COLUMNS=("source_id","period","source_index","source_base_or_vintage","value_status","source_snapshot_sha256","parser_id")

def national_csv(raw, meta):
    rows=[]
    for r in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        if r.get("indice_tiempo") and r.get("ipc_ng_nacional"):
            rows.append(_row(meta,r["indice_tiempo"][:7]+"-01",r["ipc_ng_nacional"],"December 2016=100"))
    return validate(rows)

def workbook(path, meta):
    """Parse known workbook variants without executing macros."""
    if Path(path).suffix.lower() not in (".xls",".xlsx"): raise ValueError("unparseable_pinned_source")
    import pandas as pd
    sid=meta["source_id"]
    if sid=="indec_ipc_gba_historical":
        frame=pd.read_excel(path,sheet_name="Serie Histórica",skiprows=4).dropna(subset=["Nivel general"])
        rows=[_row(meta,f"{int(r.iloc[0]):04d}-{int(r.iloc[1]):02d}-01",r["Nivel general"],"source-declared") for _,r in frame.iterrows() if int(r.iloc[0])>=2000 and (int(r.iloc[0]),int(r.iloc[1])) <= (2007,2)]
    elif sid=="san_luis_ipc_provincial":
        f=pd.read_excel(path,sheet_name="Serie",skiprows=3).dropna(subset=["Nivel General"]); rows=[_row(meta,str(pd.to_datetime(r["Periodo"]).date())[:7]+"-01",r["Nivel General"],"source-declared") for _,r in f.iterrows()]
    else:
        # Empalmed CABA/Córdoba workbooks vary; find date-like columns and a
        # general-level numeric neighbor explicitly rather than guessing bases.
        f=pd.read_excel(path,sheet_name=None)
        rows=[]
        for sheet in f.values():
            for c in sheet.columns:
                dates=pd.to_datetime(sheet[c],errors="coerce")
                if dates.notna().sum()<12: continue
                for vcol in sheet.columns:
                    vals=pd.to_numeric(sheet[vcol],errors="coerce")
                    if vals.notna().sum()>=dates.notna().sum()*.8:
                        rows=[_row(meta,str(d.date())[:7]+"-01",v,"official empalmed series") for d,v in zip(dates,vals) if pd.notna(d) and pd.notna(v)]; break
                if rows: break
            if rows: break
    return validate(rows)

def _row(meta,period,value,base):
    return dict(zip(COLUMNS,(meta["source_id"],period,float(str(value).replace(",",".")),base,"observed",meta["sha256"],meta["parser_id"])))

def validate(rows):
    seen={}
    for r in rows:
        import math
        v=float(r["source_index"]); key=(r["source_id"],r["period"])
        if not math.isfinite(v) or v<=0: raise ValueError("nonfinite_or_nonpositive_index")
        if key in seen and seen[key]!=v: raise ValueError("conflicting_duplicate")
        seen[key]=v
    if not rows: raise ValueError("unparseable_pinned_source")
    return sorted(rows,key=lambda r:(r["period"],r["source_id"]))
