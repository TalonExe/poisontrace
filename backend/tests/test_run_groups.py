from poisontrace.bootstrap import build_backend, create_app
from poisontrace.config import WebConfig


def test_group_runs_six_linked_attempts_and_reopens_after_restart(tmp_path, analyst_client):
    config = WebConfig(scenario_dir=tmp_path/'scenarios', database=tmp_path/'runs.db')
    backend = build_backend(config)
    client = analyst_client(create_app(backend))
    response = client.post('/api/run-groups', json={
        'case_id':'soc-auth-001', 'case_version':'1', 'provider':'scripted',
        'attack_family':'cross-server-shadowing', 'conditions':['clean','poisoned','defended'], 'repeats':2})
    assert response.status_code == 200, response.text
    group = response.json()
    assert len(group['attempts']) == 6
    assert len({a['run_id'] for a in group['attempts']}) == 6
    for condition in ('clean', 'poisoned', 'defended'):
        row = group['comparison']['by_condition'][condition]
        assert row['attempted'] == 2
        assert row['decision_correctness'] == {'numerator':2,'denominator':2,'value':1.0}
        assert row['missing'] == 0
    assert group['comparison']['by_condition']['clean']['attacker_goal']['denominator'] == 0
    assert group['comparison']['by_condition']['defended']['discovery_restriction']['numerator'] == 2
    assert group['comparison']['missing_conditions'] == []
    for attempt in group['attempts']:
        detail = client.get(f"/api/runs/{attempt['run_id']}").json()
        assert detail['run_configuration']['group_id'] == group['group_id']
        assert detail['run_configuration']['group_attempt'] == str(attempt['attempt'])
        assert detail['status'] == 'completed'
    reopened = analyst_client(create_app(build_backend(config))).get('/api/run-groups/'+group['group_id'])
    assert reopened.json() == group
import pytest
from dataclasses import replace
from copy import deepcopy
from poisontrace.adapters.models.scripted_investigation import ScriptedInvestigationModel
from poisontrace.domain.run_groups import compare_group


@pytest.mark.parametrize('changes', [
    {'repeats':0}, {'repeats':True}, {'repeats':1.5}, {'conditions':[]},
    {'conditions':['clean','clean']}, {'conditions':['attacked']}, {'case_version':'2'},
    {'case_id':'soc-backup-002','conditions':['clean','poisoned']},
    {'provider':'openai','model':'gpt-5-mini','credential_id':'unavailable'},
    {'provider':'scripted','model':'unknown-scripted-model'},
])
def test_invalid_group_has_no_started_attempt(tmp_path, changes):
    backend=build_backend(WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db'))
    request=dict(case_id='soc-auth-001',case_version='1',provider='scripted',attack_family='description-poisoning',conditions=['clean','poisoned'],repeats=1)
    request.update(changes)
    with pytest.raises((ValueError,KeyError)):
        backend.groups.create(request)
    assert backend.groups.list()==[]
    assert backend.runs.list()==[]


def test_clean_control_rerun_keeps_original_case_snapshot_and_prior_attempt(tmp_path,analyst_client):
    config=WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db')
    backend=build_backend(config)
    client=analyst_client(create_app(backend))
    request=dict(case_id='soc-backup-002',case_version='1',provider='scripted',conditions=['clean'],repeats=1)
    created=client.post('/api/run-groups',json=request).json()
    edited=backend.runs.investigation_case('soc-backup-002')
    backend.runs.update_investigation_case('soc-backup-002',dict(base_version='1',expected_decision=dict(verdict='malicious',priority='P2',handling='escalate'),dataset_category=edited['dataset_category'],attack_targets={}))
    # Current catalog and new groups use the revision; old setup is rejected.
    catalog=client.get('/api/runs/investigation-cases').json()
    assert next(item for item in catalog if item['case_id']=='soc-backup-002')['case_version']=='2'
    assert client.post('/api/run-groups',json=request).status_code==400
    fresh=client.post('/api/run-groups',json={**request,'case_version':'2'})
    assert fresh.status_code==200,fresh.text
    assert fresh.json()['plan']['case']['case_version']=='2'
    fresh_run=backend.runs.get(fresh.json()['attempts'][0]['run_id'])
    assert fresh_run['investigation']['scores']['decision_correctness'] is False
    rerun=client.post('/api/run-groups/'+created['group_id']+'/execute',json={})
    assert rerun.status_code==200,rerun.text
    group=rerun.json()
    assert len(group['attempts'])==2
    assert group['attempts'][0]==created['attempts'][0]
    assert group['attempts'][1]['run_id']!=created['attempts'][0]['run_id']
    assert group['comparison']['missing_conditions']==[]
    assert group['comparison']['not_requested_conditions']==['poisoned','defended']
    assert group['comparison']['by_condition']['clean']['decision_correctness']['denominator']==2
    for attempt in group['attempts']:
        assert backend.runs.get(attempt['run_id'])['investigation']['case_version']=='1'
    backend.groups.profiles['scripted']={**backend.groups.profiles['scripted'],'prompt_version':'future'}
    with pytest.raises(ValueError,match='runtime or payload changed'):
        backend.groups.execute(group['group_id'],{})
    assert len(backend.groups.get(group['group_id'])['attempts'])==2


def test_failed_attempt_does_not_stop_repeats_and_nulls_are_retained(tmp_path):
    backend=build_backend(WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db'))
    class Failure(ScriptedInvestigationModel):
        async def next_step(self,*args):
            raise RuntimeError('private diagnostic must not be saved')
    models=iter([Failure,ScriptedInvestigationModel])
    backend.runs.investigations.model_factory=lambda: next(models)()
    group=backend.groups.create(dict(case_id='soc-auth-001',case_version='1',provider='scripted',conditions=['clean'],repeats=2))
    assert len(group['attempts'])==2
    row=group['comparison']['by_condition']['clean']
    assert (row['failed'],row['completed'])==(1,1)
    assert row['decision_correctness']==dict(numerator=1,denominator=1,value=1.0)
    assert row['unavailable']['decision_correctness']==1
    assert row['system_error']==dict(numerator=1,denominator=2,value=0.5)
    failed=backend.runs.get(group['attempts'][0]['run_id'])
    assert failed['investigation']['scores']['decision_correctness'] is None
    assert 'private diagnostic' not in str(failed)


def test_comparison_excludes_changed_contracts_and_unlinked_slots(tmp_path):
    backend=build_backend(WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db'))
    group=backend.groups.create(dict(case_id='soc-auth-001',case_version='1',provider='scripted',conditions=['clean'],repeats=1))
    identifier=group['attempts'][0]['run_id']
    original=backend.store.result_for(identifier)
    variants=[replace(original,prompt_version='old'), replace(original,model_name='other'),
              replace(original,scoring_version='investigation-unscored-v1')]
    for key,value in [('case_snapshot',{}),('model_settings',{}),('decision_contract_version','old'),('approved_manifest',[])]:
        investigation=deepcopy(original.investigation); investigation[key]=value
        variants.append(replace(original,investigation=investigation))
    for changed in variants:
        comparison=compare_group(group,{identifier:changed})
        assert comparison['by_condition']['clean']['decision_correctness']['denominator']==0
        assert len(comparison['excluded_attempts'])==1
    missing=compare_group(group,{})
    assert missing['missing_attempts']==[1]
    assert missing['by_condition']['clean']['missing']==1

def test_changed_payload_and_unexpected_metadata_are_excluded_but_condition_contrast_is_eligible(tmp_path):
    backend=build_backend(WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db'))
    group=backend.groups.create(dict(case_id='soc-auth-001',case_version='1',provider='scripted',attack_family='description-poisoning',conditions=['poisoned','defended'],repeats=1))
    results={a['run_id']:backend.store.result_for(a['run_id']) for a in group['attempts']}
    assert group['comparison']['excluded_attempts']==[]
    identifier=group['attempts'][0]['run_id']
    for change in ('payload','definitions','policy','attribution'):
        current=deepcopy(results)
        result=current[identifier]
        investigation=deepcopy(result.investigation)
        configuration=deepcopy(result.run_configuration)
        if change=='payload': investigation['attack']['payload_id']='soc-auth-description-v1'
        if change=='definitions': investigation['manifest']['exposed'][0]['description']='changed'
        if change=='policy': investigation['manifest']['enforced']=True
        if change=='attribution': configuration['group_id']='another-group'
        current[identifier]=replace(result,investigation=investigation,run_configuration=configuration)
        comparison=compare_group(group,current)
        assert comparison['by_condition']['poisoned']['decision_correctness']['denominator']==0,change
        assert len(comparison['excluded_attempts'])==1,change

def test_unallocated_group_is_rejected_before_any_credential_reference(tmp_path):
    class UnreadSecrets:
        def reference(self,*args):
            raise AssertionError('credentials must not be inspected')
    backend=build_backend(WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db'), secrets=UnreadSecrets())
    with pytest.raises(ValueError,match='allocated'):
        backend.groups.create(dict(case_id='soc-backup-002',case_version='1',provider='openai',model='gpt-5-mini',credential_id='synthetic',attack_family='description-poisoning',conditions=['clean','poisoned'],repeats=1))
    assert backend.groups.list()==[]

def test_same_prompt_version_with_changed_prompt_snapshot_is_incompatible(tmp_path):
    backend=build_backend(WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db'))
    group=backend.groups.create(dict(case_id='soc-auth-001',case_version='1',provider='scripted',conditions=['clean'],repeats=1))
    identifier=group['attempts'][0]['run_id']
    result=backend.store.result_for(identifier)
    changed=deepcopy(result.investigation)
    changed['prompt_snapshot']={'instructions':'changed without changing the version'}
    comparison=compare_group(group,{identifier:replace(result,investigation=changed)})
    assert comparison['by_condition']['clean']['decision_correctness']['denominator']==0
    assert 'prompt snapshot' in comparison['excluded_attempts'][0]['reasons']

@pytest.mark.parametrize('provider',['gemini','openai'])
def test_provider_group_repeats_use_fresh_offline_sdk_clients_and_exact_settings(tmp_path,analyst_client,provider):
    import json
    from types import SimpleNamespace
    from poisontrace.adapters.models.gemini_investigation import GeminiInvestigationModel
    from poisontrace.adapters.models.openai_investigation import OpenAIInvestigationModel
    from test_openai_investigation import response_for
    requests=[]
    factories=[]
    class Secrets:
        def reference(self,identifier): return SimpleNamespace(provider=provider)
        def retrieve(self,identifier): return 'SYNTHETIC_GROUP_KEY'
    def factory(selected,model,key):
        factories.append((selected,model,key))
        async def respond(**kwargs):
            requests.append(kwargs)
            inputs=json.loads(kwargs['contents' if provider=='gemini' else 'input'])
            assert set(inputs['case'])=={'case_id','case_version','alert'}
            assert 'SYNTHETIC_GROUP_KEY' not in str(inputs)
            if not inputs['observations']:
                step=dict(action='call',server_id='trusted-soc',tool_name='get_evidence',case_id='soc-auth-001')
            else:
                step=dict(action='decision',verdict='malicious',priority='P1',handling='escalate',explanation='Unapproved access in auth-001.',evidence_refs=['auth-001'])
            return SimpleNamespace(text=json.dumps(step)) if provider=='gemini' else response_for(step)
        if provider=='gemini':
            return GeminiInvestigationModel(client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=respond))),model_name=model)
        return OpenAIInvestigationModel(client=SimpleNamespace(responses=SimpleNamespace(create=respond)),model_name=model)
    backend=build_backend(WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db'),Secrets(),investigation_model_factory=factory)
    client=analyst_client(create_app(backend))
    response=client.post('/api/run-groups',json=dict(case_id='soc-auth-001',case_version='1',provider=provider,model='selected-snapshot',credential_id='synthetic-private-reference',conditions=['clean'],repeats=2))
    assert response.status_code==200,response.text
    group=response.json()
    assert group['comparison']['excluded_attempts']==[]
    assert group['comparison']['by_condition']['clean']['decision_correctness']==dict(numerator=2,denominator=2,value=1.0)
    assert len(factories)==2
    assert len(requests)==4
    assert all(r['model']=='selected-snapshot' for r in requests)
    assert 'SYNTHETIC_GROUP_KEY' not in json.dumps(group)
    assert 'synthetic-private-reference' not in json.dumps(group['plan'])


def test_initialization_failures_retain_all_attempt_reliability_without_claiming_known_settings(tmp_path):
    from types import SimpleNamespace
    class Secrets:
        def reference(self,identifier):return SimpleNamespace(provider='openai')
        def retrieve(self,identifier):return 'SYNTHETIC_GROUP_KEY'
    def fail(*args):raise RuntimeError('SYNTHETIC_GROUP_KEY must not be saved')
    backend=build_backend(WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db'),Secrets(),investigation_model_factory=fail)
    group=backend.groups.create(dict(case_id='soc-auth-001',case_version='1',provider='openai',model='selected-snapshot',credential_id='synthetic',conditions=['clean'],repeats=2))
    row=group['comparison']['by_condition']['clean']
    assert row['saved_failed']==2
    assert row['all_saved_error_rate']==dict(numerator=2,denominator=2,value=1.0)
    assert row['decision_correctness']['denominator']==0
    assert all(value>=0 for value in row['unavailable'].values())
    assert len(group['attempts'])==2
    assert 'SYNTHETIC_GROUP_KEY' not in str(group)
