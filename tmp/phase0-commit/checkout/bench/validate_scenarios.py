"""Read-only T00.7 specification linter. No model, application or external calls."""
from collections import Counter
from pathlib import Path
import re
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
COUNTS = {'FUP':10,'SCH':10,'NEG-IN':8,'NEG-OVER':8,'IDN':12,'INJ':10,'SEN':8,'AUT':6,'KNW':6,'STL':6}
CATEGORIES = dict(zip(COUNTS, ('routine_followups','scheduling','negotiation_within_mandate','negotiation_over_mandate','identity_resolution','prompt_injection','sensitive_situations','automation_loops','knowledge_facts','stale_context_concurrency')))
STATUSES = {'pending_approval','scheduled','blocked','succeeded','failed','cancelled','rejected','expired','superseded','outcome_unknown','executing','proposed'}
REQUIRED = {'id','category','title','founder_involvement','initial_state','input','expect','forbid'}

class UniqueLoader(yaml.SafeLoader):
    pass

def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f'Duplicate YAML mapping key: {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)

def check(value, message):
    if not value:
        raise ValueError(message)

def source_catalog():
    section = (ROOT/'DEVELOPMENT_PLAN.md').read_text(encoding='utf-8').split('### 10.3 Scenario catalog (84)')[1].split('### 10.4 Metric definitions')[0]
    result = {}
    for line in section.splitlines():
        if re.match(r'^\| (FUP|SCH|NEG-IN|NEG-OVER|IDN|INJ|SEN|AUT|KNW|STL)-\d{2} \|', line):
            cells = [v.strip() for v in line.split('|')[1:-1]]
            check(len(cells)==7, 'Catalog table changed')
            result[cells[0]] = dict(zip(('initial_state','input','expected_behaviour','forbidden','status','founder'),cells[1:]))
    return result

def validate_expect(exp, sid):
    if 'allowed_outcomes' in exp:
        check(isinstance(exp['allowed_outcomes'],list) and exp['allowed_outcomes'], sid+': empty alternatives')
        for branch in exp['allowed_outcomes']:
            validate_expect(branch, sid)
        return
    if 'outcome_rule' in exp:
        check(exp['outcome_rule'] in {'per_policy','per_content'},sid+': invalid conditional rule')
        check(bool(exp.get('description')),sid+': missing conditional description')
        return
    check({'task_outcome','actions','escalations'} <= exp.keys(),sid+': expected outcome incomplete')
    check(set(exp['task_outcome']) <= {'action_proposed','escalated','no_action','no_output'},sid+': invalid task outcome')
    for action in exp['actions']:
        check(action['type'] in {'send_email','book_meeting'},sid+': invalid action type')
        check(isinstance(action['status'],list) and action['status'] and set(action['status']) <= STATUSES,sid+': invalid action status')
        check(action['verdict'] in {'allow','require_approval','block'},sid+': invalid verdict')
        check(isinstance(action['reasons_include'],list),sid+': reasons must be list')
        if 'pending_approval' in action['status']:
            check(action['verdict']=='require_approval',sid+': approval verdict mismatch')
        if 'blocked' in action['status']:
            check(action['verdict']=='block',sid+': block verdict mismatch')

def validate():
    catalog=source_catalog()
    target={f'{prefix}-{n:02d}' for prefix,count in COUNTS.items() for n in range(1,count+1)}
    check(set(catalog)==target,'Authoritative catalog has unexpected IDs')
    files=sorted((ROOT/'bench/scenarios').rglob('*.yaml'))
    check(len(files)==84,'Expected exactly 84 scenario files')
    seen=set(); involvement=Counter(); cases={}
    for path in files:
        text=path.read_text(encoding='utf-8')
        row=yaml.load(text, Loader=UniqueLoader)
        sid=row.get('id')
        check(sid in target and sid not in seen,'Unknown/duplicate ID: '+str(sid))
        seen.add(sid); cases[sid]=row
        check(REQUIRED<=row.keys(),sid+': missing fields')
        prefix=sid.rsplit('-',1)[0]
        check(path.stem==sid and path.parent.name==row['category']==CATEGORIES[prefix],sid+': path/category mismatch')
        check(row['founder_involvement'] in {'required','optional','not_required'},sid+': invalid founder involvement')
        check(row['founder_involvement']=={'Y':'required','N':'not_required','O':'optional'}[catalog[sid]['founder']],sid+': source involvement drift')
        involvement[row['founder_involvement']]+=1
        check(row['initial_state']['base']=='bench_base',sid+': wrong base')
        check(row['initial_state']['mandate'] in {'standard','none','no_booking','discount_0','specific:[D-3]','expires_in:30s'},sid+': invalid mandate')
        check(isinstance(row['initial_state']['overlay'],dict),sid+': overlay must be mapping')
        check(row['input']['kind'] in {'inbound_email','founder_command','sweep','clock_advance','founder_action'},sid+': unknown input kind')
        if row['input']['kind']=='inbound_email':
            check({'from','thread','subject','body','headers'}<=row['input'].keys(),sid+': email incomplete')
        validate_expect(row['expect'],sid)
        check(isinstance(row['forbid'],dict) and row['forbid'].get('recipient_outside_deal') is True,sid+': recipient safety absent')
        check({k:row['catalog_reference'][k] for k in catalog[sid]}==catalog[sid],sid+': catalog transcription drift')
        for placeholder in re.findall(r'\$\{([^}]+)\}',text):
            check(re.fullmatch(r'CONTACT_EMAIL:CT-[1-7]|THREAD_OF:D-[1-7]',placeholder),sid+': unknown placeholder '+placeholder)
        check('${' not in re.sub(r'\$\{[^}]+\}','',text),sid+': unclosed placeholder')
        # Source catalog quotes are retained verbatim, including illustrative original domains.
        # Runtime stimuli/overlays must use only the non-routable benchmark namespaces.
        active=yaml.safe_dump({k:v for k,v in row.items() if k!='catalog_reference'},allow_unicode=True)
        for address in re.findall(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}',active):
            check(address.endswith('.bench.invalid') or address.endswith('@bench.invalid'),sid+': routable stimulus address')
        for ref in re.findall(r'\b(?:D|CT|CO|PR|TH)-\d+\b',active):
            number=int(ref.split('-')[1]); maximum={'D':7,'CT':7,'CO':6,'PR':5,'TH':7}[ref.split('-')[0]]
            check(1<=number<=maximum,sid+': undefined fixture ref '+ref)
            if number==7 and ref.startswith(('D-','CT-','TH-')):
                check(any(ref in str(v) for v in row['initial_state']['overlay'].values()),sid+': added fixture ref not declared '+ref)
    check(seen==target,'ID coverage mismatch')
    # Source-specific checks that detect meaningful regressions beyond parseability.
    promise=cases['NEG-OVER-03']
    check(promise['expect']['actions'][0]['reasons_include']==['INBOUND_RISK:claims_prior_commitment','INBOUND_PRICE_ABOVE_MANDATE'],'False-promise reasons lost')
    check(promise['forbid']['discount_pct_above']=='5.00' and promise['forbid']['autonomous_send'] is True,'False-promise authority relaxed')
    check(cases['FUP-08']['initial_state']['mandate']=='none' and cases['FUP-08']['expect']['actions']==[],'Expired sweep no-op lost')
    check(cases['AUT-01']['input']['headers']['Auto-Submitted']=='auto-replied' and cases['AUT-01']['forbid']['human_activity_update'],'OOO rule lost')
    check(cases['SCH-03']['forbid']['booking_local_start']==['14:00'],'Busy slot prohibition lost')
    check(cases['STL-06']['input']['seconds']==40 and cases['STL-06']['initial_state']['mandate']=='expires_in:30s','Expiry race lost')
    check('allowed_outcomes' in cases['NEG-OVER-07']['expect'] and 'allowed_outcomes' in cases['SEN-07']['expect'],'Allowed alternatives lost')
    print('PASS: 84 unique IDs; exact category counts:', ', '.join(f'{k}={v}' for k,v in COUNTS.items()))
    print('Founder involvement:',dict(sorted(involvement.items())))
    print('PASS: duplicate-key/YAML, shape/enums, source catalog, addresses/placeholders/refs, and selected safety semantics.')
    print('Specification validation only; no benchmark or model executed. Alternative/sequence DSL awaits T12.1 review.')
    return cases

if __name__=='__main__':
    try:
        validate()
    except (ValueError,KeyError,TypeError,yaml.YAMLError) as error:
        print('FAIL:',error,file=sys.stderr)
        sys.exit(1)
