from pathlib import Path
import hashlib
import json
import subprocess
import yaml

ROOT=Path(__file__).resolve().parents[2]
count=0
manifest=json.loads((ROOT/'docs/workbook/source-manifest.json').read_text(encoding='utf-8'))
for source in manifest['sources']:
    blob=subprocess.check_output(['git','show','HEAD:'+source['path']],cwd=ROOT)
    assert hashlib.sha256(blob).hexdigest()==source['sha256'],source['path']
    count+=1
data=yaml.safe_load((ROOT/'t00.6-portable/seed/demo/documents.yaml').read_text(encoding='utf-8'))
for source in data['documents']:
    path='t00.6-portable/'+source['source_path']
    blob=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)
    assert hashlib.sha256(blob).hexdigest()==source['sha256'],path
    count+=1
assert subprocess.check_output(['git','show','HEAD:DEVELOPMENT_PLAN.md'],cwd=ROOT)==subprocess.check_output(['git','show','HEAD:docs/workbook/DEVELOPMENT_PLAN.md'],cwd=ROOT)
print('PASS:',count,'recorded source/document hashes match committed Git bytes; standalone plan copy identical.')
