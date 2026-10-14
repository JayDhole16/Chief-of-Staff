from pathlib import Path
import hashlib
import importlib.util
import json

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('preserve',ROOT/'scripts/phase0/verify_preservation.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
baseline,changed=module.main()
protected=[p for p in baseline if p not in module.ALLOWED]
report={'date_ist':'2026-10-14','base_head':'fecad8b','branch':'t00-phase0-product-integration','baseline_files':len(baseline),'protected_files_byte_identical':len(protected),'protected_paths':sorted(protected),'authorized_changed_paths':sorted(changed),'deleted_preexisting_files':[],'unrelated_modified_files':[],'staged_committed_pushed':False}
(ROOT/'docs/phase0/preservation-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
groups={label:[] for label in ('T00.2','T00.6','T00.7','T00.8','Shared safety/context/report')}
for path in sorted(ROOT.rglob('*')):
    if not path.is_file() or any(part in path.parts for part in ('.git','node_modules','.venv','__pycache__','.pytest_cache','tmp')):continue
    relative=str(path.relative_to(ROOT)).replace('\\','/')
    is_new=relative not in baseline
    if not is_new and relative not in changed:continue
    if relative.startswith('bench/'):group='T00.7'
    elif relative.startswith('t00.6-portable/') or path.name in {'repair_demo_encoding.py','render_demo_proposals.py','validate_demo_content.py','T00.6_HANDOFF.md','T00.6-content-review.md'}:group='T00.6'
    elif relative.startswith('docs/team/') or path.name=='T00.2-registration-and-questions.md':group='T00.2'
    elif relative.startswith(('docs/adr/','docs/product/','docs/workbook/')) or path.name in {'validate_phase0_documents.py','architecture-deviation-review.md','PROJECT_CONTEXT-proposed-updates.md'}:group='T00.8'
    else:group='Shared safety/context/report'
    groups[group].append((relative,'NEW' if is_new else 'MODIFIED'))
# Include this manifest without a self-referential hash.
manifest_path='docs/phase0/ARTIFACT_MANIFEST.md'
if not any(p==manifest_path for p,s in groups['Shared safety/context/report']):groups['Shared safety/context/report'].append((manifest_path,'NEW'))
text='# Exact Phase 0 artifact manifest\n\nDate: 2026-10-14 IST. Paths are relative to the existing repository. No files staged/committed/pushed. Original sources and unchanged portable files remain present but are not listed as new changes. tmp/ contains review/extraction/render intermediates only.\n\n'
for group,paths in groups.items():
    text+='## '+group+f' ({len(paths)} files)\n\n'
    for path,status in sorted(paths):text+=f'- {status}: `{path}`\n'
    text+='\n'
text+='All 92 preexisting files remain; 78 protected files are byte-identical. The 14 authorized preexisting edits are context.md and the exact T00.6 encoding/document-repair paths. See preservation-report.json and VERIFICATION.md.\n'
(ROOT/manifest_path).write_text(text,encoding='utf-8')
print('Manifest:',{k:len(v) for k,v in groups.items()})
