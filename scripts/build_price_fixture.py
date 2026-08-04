#!/usr/bin/env python3
"""Build tiny synthetic price-lineage fixtures; never reads live sources."""
import csv, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'fixtures'/'price-lineage'; OUT.mkdir(parents=True,exist_ok=True)
rows={
'observed.csv': [('period','series','value','class'),('2020-01','A','100','observed'),('2020-02','A','102','observed'),('2020-03','A','104','observed'),('2020-01','B','200','observed'),('2020-03','B','208','observed')],
'composite.csv': [('period','value','primary_class','flags'),('2020-01','100','derived','synthetic;rebased'),('2020-02','102','interpolated','synthetic;imputed'),('2020-03','104','derived','synthetic;spliced'),('2020-04','106','projected','synthetic')],
'conversion.csv': [('period','from_reference','to_reference','factor','class'),('2020-01','fixture_ref_A','fixture_ref_B','2','synthetic'),('2020-02','fixture_ref_A','fixture_ref_B','2','synthetic'),('2020-03','fixture_ref_A','fixture_ref_B','2','synthetic')]
}
for name,data in rows.items():
 with (OUT/name).open('w',newline='',encoding='utf-8') as f: csv.writer(f).writerows(data)
types={'observed.csv':'publicdata.argentina-price-observed/v1','composite.csv':'research.argentina-price-composite/v1','conversion.csv':'research.argentina-monetary-conversion/v1'}
for name,atype in types.items():
 digest=hashlib.sha256((OUT/name).read_bytes()).hexdigest()
 manifest={'schema':'research-artifact-manifest/v1','artifact_id':'fixture.price-lineage.'+name[:-4]+'.v1','artifact_type':atype,'status':'synthetic','frequency':'monthly','coverage':{'first':'2020-01','last':'2020-04' if name=='composite.csv' else '2020-03'},'base_or_reference':'fixture only; see columns' if name=='conversion.csv' else ('series-specific source base' if name=='observed.csv' else 'fixture 2020-01=100'),'files':[{'path':name,'sha256':digest}],'value_class_column':'class' if name!='composite.csv' else 'primary_class','method':{'observed.csv':'two invented inputs; B intentionally misses 2020-02','composite.csv':'A rebased; B divided by 2; missing 2020-02 linearly interpolated; declared splice at 2020-03; 2020-04 projected +2','conversion.csv':'invented constant conversion; no real currency'}[name]}
 (OUT/(name[:-4]+'.manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('built 3 synthetic fixture artifacts in',OUT.relative_to(ROOT))
