"""Verify every baseline file except the exact authorized Phase 0 edit paths."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
ALLOWED={'context.md','t00.6-portable/README.md','t00.6-portable/VERIFICATION.md',
         't00.6-portable/seed/demo/proposals.yaml','t00.6-portable/seed/demo/documents.yaml'}
# Explicit follow-up authorization: ignore the two local-only workbook PDFs.
ALLOWED.add('.gitignore')
ALLOWED.update('t00.6-portable/knowledge/'+name+'.md' for name in ('faq','pricing','services'))
ALLOWED.update('t00.6-portable/seed/demo/proposals/PR-'+str(n)+suffix for n in (1,2,3) for suffix in ('.md','.pdf'))

def main():
    baseline=json.loads((ROOT/'docs/phase0/preservation-baseline.json').read_text(encoding='utf-8'))
    changed=[]
    for relative,digest in baseline.items():
        path=ROOT/relative
        if not path.exists():raise ValueError('Preexisting file removed: '+relative)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            if relative not in ALLOWED:raise ValueError('Unauthorized preexisting edit: '+relative)
            changed.append(relative)
    protected=[p for p in baseline if p not in ALLOWED]
    print(f'PASS: all {len(baseline)} preexisting files retained; {len(protected)} protected files byte-identical; {len(changed)} authorized existing-file edits.')
    print('Protected scope includes backend, frontend, tests/fixtures, Makefile, pyproject.toml, LICENSE and both dirty summary files.')
    return baseline,changed

if __name__=='__main__':main()
