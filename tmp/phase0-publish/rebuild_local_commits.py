"""Rebuild only unpublished Phase 0 commits using an isolated index; preserve working files."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
EXCLUDED=['AI-Chief-of-Staff-Workbook.pdf','AI_Chief_of_Staff_Daily_Workload_Plan_Jayraj_Corrected.pdf']
TMP=ROOT/'tmp/phase0-publish'
STATE=TMP/'rebuild-state.json'

def git(*args,env=None):
    return subprocess.check_output(['git',*args],cwd=ROOT,env=env,text=True).strip()

def isolated_tree(start,add_paths,index_name):
    env=os.environ.copy()
    index=(TMP/index_name).resolve()
    assert ROOT in index.parents and index.parent==TMP.resolve()
    env['GIT_INDEX_FILE']=str(index)
    git('read-tree',start,env=env)
    git('update-index','--force-remove','--',*EXCLUDED,env=env)
    if add_paths:git('add','--',*add_paths,env=env)
    git('-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check',env=env)
    return git('write-tree',env=env)

mode=sys.argv[1]
assert git('branch','--show-current')=='t00-phase0-product-integration'
assert not git('diff','--cached','--name-only'), 'Preserve unexpected staged work'
if mode=='ticket':
    old_head=git('rev-parse','HEAD')
    assert old_head.startswith('59cdb2d'), 'Unexpected unpublished HEAD; stop instead of overwriting'
    old_ticket=git('rev-parse','eb193aa')
    parent=git('rev-parse','ab54c23')
    pdf_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in EXCLUDED}
    changed=['.gitignore','docs/workbook/README.md','docs/workbook/source-manifest.json','docs/workbook/source-manifest.md','scripts/phase0/validate_phase0_documents.py']
    tree=isolated_tree(old_ticket,changed,'ticket.index')
    new_ticket=git('commit-tree',tree,'-p',parent,'-m','T00.8: prepare architecture decisions and local-only workbook source metadata')
    state={'old_head':old_head,'old_ticket':old_ticket,'new_ticket':new_ticket,'pdf_hashes':pdf_hashes}
    STATE.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print('Prepared replacement T00.8 commit:',new_ticket)
    print('Working branch/index unchanged; both local source PDFs retained.')
elif mode=='audit':
    state=json.loads(STATE.read_text(encoding='utf-8'))
    assert git('rev-parse','HEAD')==state['old_head'], 'HEAD changed during review; stop'
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in state['pdf_hashes'].items()), 'Local PDFs changed'
    changed=['context.md','docs/phase0/PUBLICATION_STATUS.md','docs/phase0/ARTIFACT_MANIFEST.md','docs/phase0/IMPLEMENTATION_REPORT.md','docs/phase0/VERIFICATION.md','docs/phase0/preservation-report.json','scripts/phase0/verify_preservation.py']
    tree=isolated_tree(state['old_head'],changed,'audit.index')
    new_head=git('commit-tree',tree,'-p',state['new_ticket'],'-m','docs: record Phase 0 evidence and publication excluding workbook PDFs')
    # Prove the original PDF blobs are absent from every commit reachable by the branch to be pushed.
    excluded_blobs={git('rev-parse',state['old_ticket']+':'+p) for p in EXCLUDED}
    objects={line.split()[0] for line in git('rev-list','--objects',new_head).splitlines()}
    assert not excluded_blobs & objects, 'Excluded PDF content remains reachable'
    backup='refs/heads/local-backup/phase0-before-pdf-exclusion'
    existing=subprocess.run(['git','show-ref','--verify','--quiet',backup],cwd=ROOT)
    assert existing.returncode==1, 'Backup ref already exists; stop for review'
    git('update-ref',backup,state['old_head'],'0'*40)
    # Compare-and-swap the review branch; update only its index, never checkout/reset working files.
    git('update-ref','refs/heads/t00-phase0-product-integration',new_head,state['old_head'])
    git('read-tree',new_head)
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in state['pdf_hashes'].items()), 'Local PDF preservation failed'
    state['new_head']=new_head
    state['local_backup']=backup
    STATE.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print('Rebuilt unpublished review branch:',new_head)
    print('Old local history retained at',backup,'(never push this backup).')
    print('PASS: excluded PDF blobs absent from reachable history; local PDFs and unrelated working files retained.')
else:raise ValueError('Unknown mode')
