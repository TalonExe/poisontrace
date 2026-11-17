"""Offline OpenAI Responses requests at the investigation model boundary."""
import asyncio
import pytest
import json
from types import SimpleNamespace

from openai.types.responses import Response
from poisontrace.adapters.mcp.cases import BundledCases
from poisontrace.domain import EvidenceTool, EvidenceObservation
from poisontrace.adapters.models.openai_investigation import OpenAIInvestigationModel


def response_for(step, **changes):
    return Response.model_validate({
        'id': 'resp_test', 'created_at': 0, 'model': 'gpt-5-mini', 'object': 'response',
        'status': 'completed', 'parallel_tool_calls': False, 'tool_choice': 'none', 'tools': [],
        'output': [{'id':'msg_test','type':'message','role':'assistant','status':'completed',
                    'content':[{'type':'output_text','text':json.dumps({'step':step}),'annotations':[]}]}],
        **changes,
    })


def test_openai_continuation_receives_actual_results_and_selected_model():
    requests = []
    replies = [response_for(dict(action='call', server_id='trusted-soc', tool_name='get_evidence', case_id='soc-auth-001')),
        response_for(dict(action='decision', verdict='malicious', priority='P1', handling='escalate',
            explanation='Unapproved access in auth-001', evidence_refs=['auth-001']))]
    async def create(**kwargs):
        requests.append(kwargs)
        return replies.pop(0)
    model = OpenAIInvestigationModel(client=SimpleNamespace(responses=SimpleNamespace(create=create)), model_name='gpt-5-mini-test-snapshot')
    case = BundledCases().get('soc-auth-001').model_input
    tools = (EvidenceTool('trusted-soc','get_evidence','Read evidence',{},True),)
    call = asyncio.run(model.next_step(case,tools,())).call
    observed = EvidenceObservation(call.server_id, call.name, call.arguments,
        {'records':[{'evidence_id':'auth-001','unauthorized_access':True}]})
    decision = asyncio.run(model.next_step(case,tools,(observed,))).decision
    assert decision.verdict == 'malicious'
    assert decision.evidence_refs == ('auth-001',)
    assert all(r['model'] == 'gpt-5-mini-test-snapshot' for r in requests)
    assert requests[0]['text']['format']['strict'] is True
    assert requests[0]['store'] is False
    assert 'temperature' not in requests[0]
    assert json.loads(requests[0]['input'])['observations'] == []
    assert json.loads(requests[1]['input'])['observations'][0]['result']['records'][0]['unauthorized_access'] is True
    assert set(json.loads(requests[0]['input'])['case']) == {'case_id','case_version','alert'}


@pytest.mark.parametrize("family,defended", [(None,False), ("description-poisoning",False), ("cross-server-shadowing",False), ("cross-server-shadowing",True), ("description-poisoning",True)])
def test_openai_http_investigation_continues_from_real_mcp_and_reopens(tmp_path, analyst_client, family, defended):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig
    requests = []
    async def create(**kwargs):
        requests.append(kwargs)
        inputs = json.loads(kwargs['input'])
        assert set(inputs['case']) == {'case_id', 'case_version', 'alert'}
        if defended:
            assert 'controlled-malicious' not in json.dumps(inputs)
            assert 'do not call get_context' not in json.dumps(inputs)
            assert 'Investigation override' not in json.dumps(inputs)
        elif family:
            from poisontrace.domain import investigation_attack
            assert investigation_attack(family).description in [tool['description'] for tool in inputs['tools']]
        assert 'target_handling' not in json.dumps(inputs)
        if not inputs['observations']:
            return response_for(dict(action='call',server_id='trusted-soc',tool_name='get_evidence',case_id='soc-auth-001'))
        assert inputs['observations'][0]['result']['records'][0]['evidence_id'] == 'auth-001'
        return response_for(dict(action='decision',verdict='malicious',priority='P1',handling='escalate',explanation='Unapproved access, auth-001',evidence_refs=['auth-001']))
    class Secrets:
        def reference(self, identifier):
            assert identifier == 'test-reference'
            return SimpleNamespace(provider='openai')
        def retrieve(self, identifier): return 'SYNTHETIC_PRIVATE_KEY'
    def factory(provider, model, key):
        assert (provider,model,key) == ('openai','gpt-5-mini-test-snapshot','SYNTHETIC_PRIVATE_KEY')
        return OpenAIInvestigationModel(client=SimpleNamespace(responses=SimpleNamespace(create=create)),model_name=model)
    config = WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db')
    backend = build_backend(config,Secrets(),investigation_model_factory=factory)
    http = analyst_client(create_app(backend))
    result = http.post('/api/runs',json=dict(workflow='mcp-investigation-v1',case_id='soc-auth-001',mode='defended' if defended else 'poisoned' if family else 'clean',attack_family=family,provider='openai',model='gpt-5-mini-test-snapshot',credential_id='test-reference'))
    assert result.status_code == 200, result.text
    assert result.json()['status'] == 'completed'
    detail = http.get('/api/runs/'+str(result.json()['run_id'])).json()
    assert detail['model'] == 'gpt-5-mini-test-snapshot'
    assert detail['run_configuration']['provider'] == 'openai'
    assert len(requests) == 2
    assert detail['investigation']['decision']['evidence_refs'] == ['auth-001']
    assert detail['recommendation_correctness'] is True
    assert 'SYNTHETIC_PRIVATE_KEY' not in json.dumps(detail)
    kinds = [event['kind'] for event in detail['trace']]
    assert kinds.index('tool_result') < kinds.index('model_continued') < kinds.index('investigation_completed')
    assert build_backend(config).runs.get(result.json()['run_id']) == detail



@pytest.mark.parametrize('behavior,category', [
    ('refusal','investigation_validation_error'),('incomplete','investigation_validation_error'),
    ('empty','investigation_validation_error'),('malformed','investigation_validation_error'),
    ('extra_arguments','investigation_validation_error'),('unknown_tool','tool_policy_error'),
    ('early_final','investigation_validation_error'),('bad_ref','investigation_validation_error'),
    ('loop','investigation_call_limit'),('provider','investigation_execution_error'),('timeout','investigation_time_limit'),
])
def test_openai_failures_are_saved_with_safe_categories_and_null_scores(tmp_path, behavior, category):
    from test_clean_investigation import runner_for
    async def create(**kwargs):
        if behavior == 'provider': raise RuntimeError('PRIVATE_KEY raw provider error')
        if behavior == 'timeout': await asyncio.sleep(10)
        call = dict(action='call',server_id='trusted-soc',tool_name='get_evidence',case_id='soc-auth-001')
        if behavior == 'refusal':
            return response_for(call,output=[{'id':'msg_refusal','type':'message','role':'assistant','status':'completed',
                'content':[{'type':'refusal','refusal':'PRIVATE_KEY diagnostic'}]}])
        if behavior == 'incomplete': return response_for(call,status='incomplete',incomplete_details={'reason':'max_output_tokens'})
        if behavior == 'empty': return response_for(call,output=[])
        if behavior == 'malformed':
            return SimpleNamespace(status='completed',output=[],output_text='not-json PRIVATE_KEY')
        if behavior == 'extra_arguments': call['arguments'] = {'command':'unsupported'}
        if behavior == 'unknown_tool': call['tool_name'] = 'delete_case'
        if behavior == 'early_final' or (behavior == 'bad_ref' and json.loads(kwargs['input'])['observations']):
            return response_for(dict(action='decision',verdict='benign',priority='P4',handling='close',explanation='Unsupported',evidence_refs=['invented']))
        return response_for(call)
    model = OpenAIInvestigationModel(client=SimpleNamespace(responses=SimpleNamespace(create=create)))
    runner, store = runner_for(tmp_path, lambda:model, max_calls=1, timeout_seconds=3 if behavior=='timeout' else 20)
    result = runner.run('soc-auth-001',{'provider':'openai','model':'gpt-5-mini'})
    assert result.status == 'failed'
    assert result.error_category == category
    assert result.run_id is not None
    assert result.marker_influence is result.recommendation_correctness is result.attacker_goal_achievement is None
    reopened = store.result_for(result.run_id)
    assert reopened.error_category == category
    assert reopened.investigation['decision'] is None
    assert 'PRIVATE_KEY' not in str(store.events_for(result.run_id))
    if behavior in {'loop','bad_ref'}: assert reopened.investigation['evidence']


def test_single_campaign_and_rerun_send_actual_openai_model_to_sdk(tmp_path):
    from pathlib import Path
    from poisontrace.bootstrap import build_backend
    from poisontrace.config import WebConfig
    from poisontrace.adapters.models.openai import OpenAIModel
    requests = []
    def create(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(output_text=json.dumps({'tool_name':None,'arguments':{'scenario_id':'002'},'recommendation':'escalate'}))
    def factory(provider,model,key):
        assert provider == 'openai'
        return OpenAIModel(client=SimpleNamespace(responses=SimpleNamespace(create=create)),model_name=model)
    scenarios = tmp_path/'scenarios'
    scenarios.mkdir()
    (scenarios/'auth-poisoned.yaml').write_bytes(Path('backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml').read_bytes())
    backend = build_backend(WebConfig(scenario_dir=scenarios,database=tmp_path/'runs.db'),model_factory=factory)
    single = backend.runs.create(dict(provider='openai',model='gpt-5-mini',scenario_id='002',mode='clean'))
    campaign = backend.campaign_service.create(dict(provider='openai',model='gpt-5-mini'))
    executed = backend.campaign_service.execute(campaign['campaign_id'])
    rerun = backend.campaign_service.rerun(campaign['campaign_id'],0)
    assert [r['model'] for r in requests] == ['gpt-5-mini'] * 3
    ids = [single['run_id'],executed['scenarios'][0]['child_run_id'],rerun['scenarios'][0]['child_run_id']]
    assert len(set(ids)) == 3
    assert all(backend.runs.get(i)['model'] == 'gpt-5-mini' for i in ids)


def test_openai_factory_owns_and_closes_sdk_without_network(tmp_path, monkeypatch):
    import openai
    from poisontrace.bootstrap import build_investigation_model
    from test_clean_investigation import runner_for
    constructed, closed = [], []
    async def create(**kwargs):
        return response_for({},status='incomplete')
    async def close(): closed.append(True)
    def client_factory(**kwargs):
        constructed.append(kwargs)
        return SimpleNamespace(responses=SimpleNamespace(create=create),close=close)
    monkeypatch.setattr(openai,'AsyncOpenAI',client_factory)
    runner, store = runner_for(tmp_path,lambda:build_investigation_model('openai','gpt-5-mini','SYNTHETIC_KEY'))
    result = runner.run('soc-auth-001',{'provider':'openai','model':'gpt-5-mini'})
    assert result.error_category == 'investigation_validation_error'
    assert constructed == [{'api_key':'SYNTHETIC_KEY','max_retries':0,'timeout':20}]
    assert closed == [True]
    assert 'SYNTHETIC_KEY' not in str(store.events_for(result.run_id))


def test_openai_invalid_configuration_never_resolves_key_or_starts_attempt(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig
    class Secrets:
        def reference(self, identifier): return SimpleNamespace(provider='gemini')
        def retrieve(self, identifier): raise AssertionError('must not resolve key')
    backend = build_backend(WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db'),Secrets())
    client = analyst_client(create_app(backend))
    payload = dict(workflow='mcp-investigation-v1',case_id='soc-auth-001',mode='clean',provider='openai',model='gpt-5-mini',credential_id='wrong-provider')
    for changes in ({},{'model':''},{'credential_id':''},{'case_id':'missing'},{'mode':'poisoned'}):
        assert client.post('/api/runs',json={**payload,**changes}).status_code in {400,404}
    assert backend.store.run_ids() == []
