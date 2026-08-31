"""Source-specific snapshot parsers producing the canonical source table."""
from __future__ import annotations
import csv, io, json, re, unicodedata
from pathlib import Path

COLUMNS=("source_id","period","source_index","source_base_or_vintage","value_status","source_snapshot_sha256","parser_id")
SPANISH_MONTHS={"ene":1,"feb":2,"mar":3,"abr":4,"may":5,"jun":6,"jul":7,"ago":8,"sep":9,"set":9,"oct":10,"nov":11,"dic":12}

def _plain(value):
    text=unicodedata.normalize("NFKD",str(value)).encode("ascii","ignore").decode("ascii").lower()
    return re.sub(r"\s+"," ",text).strip()

def _period_from_spanish_column(value):
    text=_plain(value).replace("_","-").replace("/","-")
    match=re.fullmatch(r"([a-z]{3})-(\d{2}|\d{4})",text)
    if not match or match.group(1) not in SPANISH_MONTHS: return None
    year=int(match.group(2)); year=2000+year if year<100 else year
    return f"{year:04d}-{SPANISH_MONTHS[match.group(1)]:02d}-01"

def national_csv(raw, meta):
    rows=[]
    for r in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        if r.get("indice_tiempo") and r.get("ipc_ng_nacional"):
            rows.append(_row(meta,r["indice_tiempo"][:7]+"-01",r["ipc_ng_nacional"],"December 2016=100"))
    return validate(rows)

def _decode_cordoba_csv(raw):
    """Decode the declared Córdoba CSV without broad encoding guessing."""
    try:
        return raw.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        # The current official CKAN empalmed CSV is Windows-1252/Latin-1 text.
        # Keep this fallback source-specific rather than introducing a generic
        # best-effort decoder across publisher artifacts.
        return raw.decode("cp1252"), "cp1252"

def cordoba_csv(raw, meta):
    """Parse the official Córdoba wide CSV and its bounded publisher preamble."""
    text, encoding = _decode_cordoba_csv(raw)
    lines=text.splitlines()
    header_candidates=[]
    for index,line in enumerate(lines):
        fields=[_plain(value) for value in line.split(";")[:3]]
        if len(fields)>=2 and fields[0]=="coicop" and fields[1] in {"descripcion","description"}:
            header_candidates.append(index)
    if len(header_candidates)!=1:
        raise ValueError(f"unparseable_pinned_source:cordoba_header_count:{len(header_candidates)}")
    header_index=header_candidates[0]
    reader=csv.DictReader(io.StringIO("\n".join(lines[header_index:])),delimiter=";")
    fields=reader.fieldnames or []
    month_fields=[(name,_period_from_spanish_column(name)) for name in fields]
    month_fields=[x for x in month_fields if x[1]]
    if not month_fields: raise ValueError("unparseable_pinned_source:no_month_columns")
    selected=None
    for row in reader:
        label=_plain(row.get("Descripcion") or row.get("Descripción") or row.get("descripcion") or "")
        code=_plain(row.get("COICOP") or row.get("Codigo") or row.get("Código") or "")
        if label in {"nivel general","general"} or "nivel general" in label or code in {"00","0","general"}:
            if selected is not None:
                raise ValueError("unparseable_pinned_source:multiple_nivel_general_rows")
            selected=row
    if selected is None: raise ValueError("unparseable_pinned_source:no_nivel_general_row")
    rows=[]
    for field,period in month_fields:
        raw_value=(selected.get(field) or "").strip()
        if raw_value:
            rows.append(_row(meta,period,raw_value,f"official Córdoba empalmed/source-declared base; encoding={encoding}"))
    return validate(rows)

def neuquen_calculator_json(raw, meta):
    """Parse the official Neuquén calculator API's level-general index payload."""
    try:
        data=json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ValueError("unparseable_pinned_source:neuquen_invalid_json") from exc
    if not isinstance(data,list) or not data:
        raise ValueError("unparseable_pinned_source:neuquen_payload_not_nonempty_list")
    expected={"anio","mes","indice"}; rows=[]
    for index,item in enumerate(data):
        if not isinstance(item,dict) or set(item)!=expected:
            raise ValueError(f"unparseable_pinned_source:neuquen_schema_row:{index}")
        year=str(item["anio"]).strip(); month=str(item["mes"]).strip(); value=str(item["indice"]).strip()
        if not re.fullmatch(r"\d{4}",year):
            raise ValueError(f"unparseable_pinned_source:neuquen_year_row:{index}")
        if not re.fullmatch(r"\d{1,2}",month) or not 1<=int(month)<=12:
            raise ValueError(f"unparseable_pinned_source:neuquen_month_row:{index}")
        if not value:
            raise ValueError(f"unparseable_pinned_source:neuquen_index_row:{index}")
        rows.append(_row(meta,f"{int(year):04d}-{int(month):02d}-01",value,"official Neuquén empalmed level-general series; modern base 2022=100"))
    return validate(rows)

def generic_wide_csv(raw, meta):
    """Parse a source table with one level-general row and Spanish month columns."""
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    fields=reader.fieldnames or []
    month_fields=[(name,_period_from_spanish_column(name)) for name in fields]
    month_fields=[x for x in month_fields if x[1]]
    if not month_fields: raise ValueError("unparseable_pinned_source:no_month_columns")
    rows_in=list(reader); selected=None
    for row in rows_in:
        text=" ".join(_plain(row.get(f,"")) for f in fields[:3])
        if "nivel general" in text:
            selected=row; break
    if selected is None and len(rows_in)==1: selected=rows_in[0]
    if selected is None: raise ValueError("unparseable_pinned_source:no_nivel_general_row")
    rows=[]
    for field,period in month_fields:
        value=(selected.get(field) or "").strip()
        if value: rows.append(_row(meta,period,value,"source-declared"))
    return validate(rows)

def workbook(path, meta):
    """Parse known workbook variants without executing macros."""
    if Path(path).suffix.lower() not in (".xls",".xlsx"): raise ValueError("unparseable_pinned_source")
    import pandas as pd
    sid=meta["source_id"]
    if sid=="indec_ipc_gba_historical":
        # Old INDEC files have used both accented and unaccented sheet names.
        book=pd.read_excel(path,sheet_name=None,skiprows=4)
        name=next((n for n in book if _plain(n)=="serie historica"),None)
        if not name: raise ValueError("unparseable_pinned_source:historical_sheet")
        frame=book[name]
        value_col=next((c for c in frame.columns if _plain(c)=="nivel general"),None)
        if value_col is None: raise ValueError("unparseable_pinned_source:nivel_general")
        frame=frame.dropna(subset=[value_col])
        rows=[_row(meta,f"{int(r.iloc[0]):04d}-{int(r.iloc[1]):02d}-01",r[value_col],"source-declared") for _,r in frame.iterrows() if str(r.iloc[0]).replace('.0','').isdigit() and str(r.iloc[1]).replace('.0','').isdigit() and int(r.iloc[0])>=2000 and (int(r.iloc[0]),int(r.iloc[1])) <= (2007,2)]
    elif sid=="san_luis_ipc_provincial":
        books=pd.read_excel(path,sheet_name=None,skiprows=3)
        f=next(iter(books.values()))
        value_col=next((c for c in f.columns if "nivel general" in _plain(c)),None)
        period_col=next((c for c in f.columns if _plain(c) in {"periodo","period","fecha"}),None)
        if value_col is None or period_col is None: raise ValueError("unparseable_pinned_source:san_luis_columns")
        f=f.dropna(subset=[value_col]); rows=[_row(meta,str(pd.to_datetime(r[period_col]).date())[:7]+"-01",r[value_col],"source-declared") for _,r in f.iterrows() if pd.notna(pd.to_datetime(r[period_col],errors="coerce"))]
    else:
        # CABA/Neuquén official workbooks may change layout. Search for a date
        # axis and a level-general numeric neighbor; fail rather than guessing
        # when no unambiguous table is found.
        books=pd.read_excel(path,sheet_name=None)
        candidates=[]
        for sheet_name,sheet in books.items():
            for c in sheet.columns:
                dates=pd.to_datetime(sheet[c],errors="coerce")
                if dates.notna().sum()<12: continue
                for vcol in sheet.columns:
                    if vcol==c: continue
                    vals=pd.to_numeric(sheet[vcol],errors="coerce")
                    paired=(dates.notna() & vals.notna()).sum()
                    label=_plain(vcol)
                    if paired>=12 and ("nivel general" in label or "indice" in label or paired>=dates.notna().sum()*.9):
                        candidates.append((paired,sheet_name,c,vcol,dates,vals))
        if not candidates: raise ValueError("unparseable_pinned_source:no_date_value_table")
        candidates.sort(key=lambda x:(x[0],"nivel general" in _plain(x[3])),reverse=True)
        best=candidates[0]
        rows=[_row(meta,str(d.date())[:7]+"-01",v,"official empalmed/source-declared series") for d,v in zip(best[4],best[5]) if pd.notna(d) and pd.notna(v)]
    return validate(rows)

def parse_snapshot(path: Path, meta: dict) -> list[dict]:
    sid=meta["source_id"]; suffix=path.suffix.lower(); raw=path.read_bytes()
    if sid=="indec_ipc_national": return national_csv(raw,meta)
    if sid=="cordoba_ipc" and suffix==".csv": return cordoba_csv(raw,meta)
    if sid=="neuquen_ipc_provincial" and suffix in (".php",".json"): return neuquen_calculator_json(raw,meta)
    if suffix in (".xls",".xlsx"): return workbook(path,meta)
    raise ValueError(f"unparseable_pinned_source:unsupported_format:{sid}:{suffix}")

def _row(meta,period,value,base):
    clean=str(value).replace(".","").replace(",",".") if isinstance(value,str) and "," in value else str(value)
    return dict(zip(COLUMNS,(meta["source_id"],period,float(clean),base,"observed",meta["sha256"],meta["parser_id"])))

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
