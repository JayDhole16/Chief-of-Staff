from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
plan=(ROOT/'DEVELOPMENT_PLAN.md').read_text(encoding='utf-8')
titles=['Executor-only external writes','Founder-confirmed authority','Deterministic policy and fail-safe guards','Server rendering and hash-bound approval','Sealed credential isolation','Untrusted customer text and task scope','Three Evolus agents on AMD-hosted inference','PostgreSQL as the only stateful dependency','Idempotent effects and handlers','State machines, audit and receipts','Module boundaries and external ports','Controlled contracts and migration changes']
rows=[line for line in plan.split('## 15. ARCHITECTURE DECISIONS')[1].splitlines() if line.startswith('| ADR-')]
assert len(rows)==12
directory=ROOT/'docs/adr'; directory.mkdir(parents=True,exist_ok=True)
for index,line in enumerate(rows):
    adr,decision,consequence=[c.strip() for c in line.split('|')[1:-1]]
    path=directory/(adr+'.md')
    if path.exists():raise ValueError('Existing ADR must be preserved: '+str(path))
    source='DEVELOPMENT_PLAN.md §15, '+adr+'; workbook PROJECT_CONTEXT §4 (PDF p.3).'
    text=(f'# {adr}: {titles[index]}\n\nStatus: **Proposed / pending team review**. Prepared: 2026-10-14 IST.\n\n'
          'Context: Capture the existing workbook decision for the three-person implementation; this record does not certify current code.\n\n'
          f'Decision: {decision}\n\nConsequences: Preserve {consequence}. Any departure follows the reviewed ADR/schema/snapshot process; this session changes no implementation contract.\n\n'
          f'Source: {source}\n\nReview: Jairaj architecture/safety and Rehan platform/runtime sign-off pending; YOU reviews product and end-to-end acceptance. No approval recorded.\n')
    path.write_text(text,encoding='utf-8')
directory=ROOT/'docs/workbook';directory.mkdir(parents=True,exist_ok=True)
dest=directory/'DEVELOPMENT_PLAN.md'
if dest.exists():raise ValueError('Preserve existing canonical development plan')
shutil.copyfile(ROOT/'DEVELOPMENT_PLAN.md',dest)
sources=[]
for filename,role in [('AI-Chief-of-Staff-Workbook.pdf','Combined official workbook v1.0, 238 pages'),('AI_Chief_of_Staff_Daily_Workload_Plan_Jayraj_Corrected.pdf','Three-person ownership plan, 12 pages'),('DEVELOPMENT_PLAN.md','Supplied standalone plan; byte-identical copy under docs/workbook')]:
    p=ROOT/filename
    sources.append({'path':filename,'role':role,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size_bytes':p.stat().st_size})
canonical=[]
for name,start,end in [('PROJECT_CONTEXT',2,10),('PRD',11,16),('SRS',17,30),('FRD',31,39),('TRD',40,73),('ARCHITECTURE',74,94),('DATABASE_SCHEMA',95,130),('BACKEND_SCHEMA',131,167),('FEATURE_TICKETS',168,202),('DEVELOPMENT_PLAN',203,238)]:
    p=directory/(name+'.md')
    row={'path':str(p.relative_to(ROOT)).replace('\\','/'),'present':p.exists(),'pdf_pages':[start,end],'status':'supplied standalone source copied exactly' if p.exists() else 'missing original Markdown; PDF reference only'}
    if p.exists():row['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    canonical.append(row)
(directory/'source-manifest.json').write_text(json.dumps({'checked_date_ist':'2026-10-14','sources':sources,'canonical_documents':canonical,'team_signoff':'pending','pdf_extractions_are_authoritative_markdown':False},indent=2)+'\n',encoding='utf-8')
print('Prepared 12 proposed ADRs, one exact standalone plan copy and a source manifest; 9 canonical originals missing.')
