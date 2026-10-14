"""Stage only an explicitly enumerated Phase 0 ticket; refuse an occupied index."""
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
ticket=sys.argv[1]
sections={}
manifest=(ROOT/'docs/phase0/ARTIFACT_MANIFEST.md').read_text(encoding='utf-8')
group=None
for line in manifest.splitlines():
    if line.startswith('## '):group=line.split(' (')[0][3:];sections[group]=[]
    elif group and re.fullmatch(r'- (?:NEW|MODIFIED): `[^`]+`',line):
        sections[group].append(line.split('`')[1])
if ticket not in {'T00.2','T00.6','T00.7','T00.8','Shared safety/context/report'}:raise ValueError('Unknown ticket')
paths=sections[ticket]
if ticket=='T00.6':
    paths+=['.gitattributes']
    # Include the existing source dataset so the handoff is complete on a fresh checkout.
    paths+=sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'t00.6-portable').rglob('*') if p.is_file() and p.suffix in {'.md','.yaml','.pdf'})
if ticket=='T00.8':
    # These are the supplied Phase 0 source documents required by links/hash validators.
    paths+=['DEVELOPMENT_PLAN.md','AI-Chief-of-Staff-Workbook.pdf','AI_Chief_of_Staff_Daily_Workload_Plan_Jayraj_Corrected.pdf']
paths=sorted(set(paths))
for path in paths:
    resolved=(ROOT/path).resolve()
    if ROOT not in resolved.parents or not resolved.is_file():raise ValueError('Invalid path '+path)
    if path in {'SAFETY_HARNESS_SUMMARY.md','T09.1_SUMMARY.md'} or path.startswith(('backend/','frontend/','tests/','tmp/')):raise ValueError('Protected teammate/temporary path '+path)
staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
if staged and set(staged)!=set(paths):raise ValueError('Preserve occupied index; unexpected staged paths: '+str(staged))
subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
actual=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
if set(actual)!=set(paths):raise ValueError('Staged path mismatch: '+str(actual))
subprocess.run(['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check'],cwd=ROOT,check=True)
print(f'{ticket}: {len(actual)} exact files staged; CRLF-aware staged whitespace check passed.')
subprocess.run(['git','diff','--cached','--stat'],cwd=ROOT,check=True)
