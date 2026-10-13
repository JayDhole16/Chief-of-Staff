"""Check prepared Phase 0 documents, source provenance and local links without mutations."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
LOCAL_ONLY_PDFS = {
    'AI-Chief-of-Staff-Workbook.pdf',
    'AI_Chief_of_Staff_Daily_Workload_Plan_Jayraj_Corrected.pdf',
}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def main():
    plan=(ROOT/'DEVELOPMENT_PLAN.md').read_text(encoding='utf-8')
    rows=[line for line in plan.split('## 15. ARCHITECTURE DECISIONS')[1].splitlines() if line.startswith('| ADR-')]
    adrs=sorted((ROOT/'docs/adr').glob('ADR-*.md'))
    require(len(adrs)==12, 'Expected 12 ADRs')
    for index,(path,row) in enumerate(zip(adrs,rows),1):
        identifier,decision,_=[c.strip() for c in row.split('|')[1:-1]]
        text=path.read_text(encoding='utf-8')
        require(path.name==f'ADR-{index:04d}.md' and identifier in text, 'ADR numbering drift')
        require('Proposed / pending team review' in text, 'ADR falsely approved')
        require('Decision: '+decision in text, 'Frozen source decision changed')
        require(all(label in text for label in ('Context:', 'Consequences:', 'Source:', 'Review:')), 'ADR field absent')
    manifest=json.loads((ROOT/'docs/workbook/source-manifest.json').read_text(encoding='utf-8'))
    local_only_missing=[]
    for source in manifest['sources']:
        path=ROOT/source['path']
        if source['path'] in LOCAL_ONLY_PDFS:
            require(source.get('distribution')=='local_only', 'Workbook PDF must remain local-only')
            if not path.exists():
                local_only_missing.append(source['path'])
                continue
        blob=path.read_bytes()
        require(hashlib.sha256(blob).hexdigest()==source['sha256'] and len(blob)==source['size_bytes'], 'Source modified')
    require(len(manifest['canonical_documents'])==10, 'Canonical inventory incomplete')
    for row in manifest['canonical_documents']:
        path=ROOT/row['path']
        require(path.exists()==row['present'], 'Canonical presence drift')
        if path.exists():require(hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'], 'Copied source hash drift')
    require((ROOT/'docs/workbook/DEVELOPMENT_PLAN.md').read_bytes()==(ROOT/'DEVELOPMENT_PLAN.md').read_bytes(), 'Standalone source copy changed')
    require(sum(r['present'] for r in manifest['canonical_documents'])==1, 'Unexpected canonical sources; review needed')
    broken=[]
    for path in list((ROOT/'docs').rglob('*.md'))+list((ROOT/'bench').glob('*.md')):
        if path.name=='DEVELOPMENT_PLAN.md':continue  # Supplied prose/source syntax is not authored here.
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if link.startswith(('http:', 'https:', '#')):continue
            target=(path.parent/link.split('#')[0]).resolve()
            if not target.exists():broken.append(f'{path.relative_to(ROOT)}: {link}')
    require(not broken,'Broken authored links: '+str(broken))
    beats=(ROOT/'docs/product/demo-beats.md').read_text(encoding='utf-8')
    require(set(re.findall(r'^\| ([0-6]) /',beats,re.MULTILINE))==set('0123456'),'Demo beat missing/duplicate')
    brief=(ROOT/'docs/product/acceptance-brief.md').read_text(encoding='utf-8')
    require(set(re.findall(r'^\| (G[0-4]) \|',brief,re.MULTILINE))=={'G0','G1','G2','G3','G4'},'Gate brief incomplete')
    require('not measured results' in brief, 'Target/result distinction absent')
    print('PASS: 12 proposed ADRs match exact frozen decision rows; source hashes/copy; 10-document inventory (9 missing); local links; beats 0-6; gates G0-G4.')
    if local_only_missing:
        print('Local-only workbook PDFs unavailable in this checkout; their hashes were not checked:', ', '.join(local_only_missing))
    print('Document preparation only; team sign-off, canonical originals, PR/merge and gate evidence remain pending.')

if __name__=='__main__':
    main()
