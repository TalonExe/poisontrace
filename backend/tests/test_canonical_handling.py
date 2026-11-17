import asyncio
import json
from types import SimpleNamespace

import pytest

from poisontrace.adapters.mcp.cases import BundledCases
from poisontrace.adapters.models.gemini_investigation import GeminiInvestigationModel
from poisontrace.adapters.models.openai_investigation import OpenAIInvestigationModel
from poisontrace.domain import InvestigationDecision
from test_openai_investigation import response_for


@pytest.mark.parametrize('provider', ['gemini', 'openai'])
def test_provider_requires_canonical_handling_and_preserves_recommendation_detail(provider):
    detail = 'Escalate for immediate incident response containment, revoke compromised administrative credentials, and block source IP 203.0.113.17.'
    payload = dict(action='decision', verdict='malicious', priority='P1', handling='escalate',
                   explanation=detail, evidence_refs=['auth-001'])
    requests = []
    async def reply(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(text=json.dumps(payload)) if provider == 'gemini' else response_for(payload)
    model = GeminiInvestigationModel(client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=reply)))) if provider == 'gemini' else OpenAIInvestigationModel(client=SimpleNamespace(responses=SimpleNamespace(create=reply)))
    decision = asyncio.run(model.next_step(BundledCases().get('soc-auth-001').model_input, (), ())).decision
    assert decision.handling == 'escalate'
    assert decision.explanation == detail
    payload['handling'] = detail
    with pytest.raises(ValueError):
        asyncio.run(model.next_step(BundledCases().get('soc-auth-001').model_input, (), ()))
    assert model.prompt_version.endswith('-v2')
    schema = requests[0]['config'].response_schema if provider == 'gemini' else requests[0]['text']['format']['schema']['properties']['step']['anyOf'][1]
    assert schema['properties']['handling']['enum'] == ['close', 'escalate']


def test_new_structured_decisions_reject_prose_handling():
    with pytest.raises(ValueError):
        InvestigationDecision('malicious', 'P1', 'Escalate immediately', 'Details', ('auth-001',))

@pytest.mark.parametrize('provider', ['gemini', 'openai'])
def test_canonical_detail_is_scored_and_reopens_after_actual_evidence(tmp_path, provider):
    from test_clean_investigation import runner_for
    detail = 'Escalate for immediate incident response containment, revoke compromised administrative credentials, and block source IP 203.0.113.17.'
    async def reply(**kwargs):
        inputs=json.loads(kwargs['contents'] if provider == 'gemini' else kwargs['input'])
        payload=dict(action='decision',verdict='malicious',priority='P1',handling='escalate',explanation=detail,evidence_refs=['auth-001']) if inputs['observations'] else dict(action='call',server_id='trusted-soc',tool_name='get_evidence',case_id='soc-auth-001')
        return SimpleNamespace(text=json.dumps(payload)) if provider == 'gemini' else response_for(payload)
    factory = (lambda: GeminiInvestigationModel(client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=reply))))) if provider == 'gemini' else (lambda: OpenAIInvestigationModel(client=SimpleNamespace(responses=SimpleNamespace(create=reply))))
    runner, store=runner_for(tmp_path,factory)
    result=runner.run('soc-auth-001',{'provider':provider})
    saved=store.result_for(result.run_id)
    assert saved.status == 'completed'
    assert saved.investigation['decision_contract_version'] == 'canonical-handling-v2'
    assert saved.investigation['decision']['explanation'] == detail
    assert saved.investigation['scores']['handling_correctness'] is True
    assert saved.investigation['scores']['decision_correctness'] is True
    assert saved.investigation['scores']['marker_influence'] is False
