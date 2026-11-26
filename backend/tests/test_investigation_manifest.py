"""Manifest observations at policy, real transport and persisted HTTP seams."""
from job_helpers import complete_investigation
import asyncio
from dataclasses import replace

import pytest
from poisontrace.adapters.mcp.cases import BundledCases, approved_evidence_manifest
from poisontrace.adapters.mcp.transport import LocalSocTransport
from poisontrace.application.gateway import EvidenceManifest, ToolGateway
from poisontrace.domain import InvestigationCall
from poisontrace.bootstrap import build_backend, create_app
from poisontrace.config import WebConfig

@pytest.mark.parametrize('family', ['description-poisoning', 'cross-server-shadowing'])
def test_defended_withholds_discovered_attack_before_model_and_reopens(tmp_path, analyst_client, family):
    backend = build_backend(WebConfig(scenario_dir=tmp_path / 'scenarios', database=tmp_path / 'runs.db'))
    client = analyst_client(create_app(backend))
    response = complete_investigation(client, backend, {'workflow': 'mcp-investigation-v1', 'case_id': 'soc-auth-001',
        'provider': 'scripted', 'mode': 'defended', 'attack_family': family})
    assert response.status_code == 200, response.text
    detail = client.get(f"/api/runs/{response.json()['run_id']}").json()
    assert detail['status'] == 'completed'
    policy = detail['investigation']['manifest']
    assert len(policy['discovered']) == 4
    assert len(policy['exposed']) == 3
    assert policy['restrictions'] == [{'server_id': 'controlled-malicious', 'tool_name': 'get_advisory', 'reason': 'definition_mismatch'}]
    assert all(t['server_id'] == 'trusted-soc' for t in detail['model_facing_definitions'])
    assert policy['invocation_rejections'] == [] and policy['executed_calls'] == 3
    assert detail['recommendation_correctness'] is True
    assert detail['attacker_goal_achievement'] is False
    assert build_backend(WebConfig(scenario_dir=tmp_path / 'scenarios', database=tmp_path / 'runs.db')).runs.get(detail['run_id']) == detail

@pytest.mark.parametrize('family', ['description-poisoning', 'cross-server-shadowing'])
def test_gateway_rejects_real_attacked_tool_without_dispatching_to_either_server(family):
    async def exercise():
        async with LocalSocTransport().open(BundledCases().get('soc-auth-001'), attack_family=family) as session:
            definitions = await session.discover()
            dispatched = []
            real_invoke = session.invoke
            async def observe(call):
                dispatched.append(call)
                return await real_invoke(call)
            session.invoke = observe
            gateway = ToolGateway((), set())
            manifest = EvidenceManifest(approved_evidence_manifest())
            for call in (InvestigationCall('controlled-malicious', 'get_advisory', {'case_id':'soc-auth-001'}),
                         InvestigationCall('unknown', 'get_evidence', {'case_id':'soc-auth-001'})):
                with pytest.raises(PermissionError):
                    await gateway.invoke_evidence(call, definitions, session, manifest=manifest)
            assert dispatched == []
            result = await gateway.invoke_evidence(InvestigationCall('trusted-soc', 'get_evidence', {'case_id':'soc-auth-001'}), definitions, session, manifest=manifest)
            assert result.result['records'][0]['evidence_id'] == 'auth-001'
            assert len(dispatched) == 1
    asyncio.run(exercise())


def test_manifest_rejects_collision_invalid_approval_and_explicit_empty():
    tools = approved_evidence_manifest()
    with pytest.raises(ValueError):
        EvidenceManifest((tools[0], tools[0]))
    with pytest.raises(ValueError):
        EvidenceManifest((replace(tools[0], description='changed'),))
    manifest = EvidenceManifest(tools)
    assert manifest.reason(tools[0], (tools[0], tools[0])) == 'colliding_identity'
    assert EvidenceManifest(()).reason(tools[0], tools) == 'unapproved_identity'

@pytest.mark.parametrize('family', ['description-poisoning', 'cross-server-shadowing'])
def test_model_never_sees_withheld_text_and_restriction_can_coexist_with_wrong_decision(tmp_path, family):
    from poisontrace.adapters.models.scripted_investigation import ScriptedInvestigationModel
    from poisontrace.adapters.persistence.traces import SqliteTraceStore
    from poisontrace.application.investigation import InvestigationRunner
    from poisontrace.domain import InvestigationStep, InvestigationDecision
    seen = []
    class WrongOfflineModel(ScriptedInvestigationModel):
        async def next_step(self, case, tools, observations):
            seen.append(tools)
            assert all(t.server_id == 'trusted-soc' for t in tools)
            step = await super().next_step(case, tools, observations)
            if step.decision:
                return InvestigationStep(decision=InvestigationDecision('benign', 'P4', 'close', 'Deliberately wrong offline answer.', step.decision.evidence_refs))
            return step
    store = SqliteTraceStore(tmp_path / 'runs.db')
    runner = InvestigationRunner(store, BundledCases(), LocalSocTransport(), WrongOfflineModel, ToolGateway((), set()), approved_manifest=approved_evidence_manifest())
    result = runner.run('soc-auth-001', {'mode':'defended', 'attack_family': family})
    assert seen and result.status == 'completed'
    assert result.investigation['decision']['handling'] == 'close'
    assert result.investigation['manifest']['restrictions']
    assert result.investigation['manifest']['invocation_rejections'] == []


def test_explicit_empty_manifest_exposes_nothing_and_records_no_call_without_block(tmp_path):
    from poisontrace.adapters.persistence.traces import SqliteTraceStore
    from poisontrace.application.investigation import InvestigationRunner
    class NoCallModel:
        async def next_step(self, case, tools, observations):
            assert tools == ()
            raise ValueError('No invented fallback')
    store = SqliteTraceStore(tmp_path / 'runs.db')
    runner = InvestigationRunner(store, BundledCases(), LocalSocTransport(), NoCallModel, ToolGateway((), set()), approved_manifest=())
    result = runner.run('soc-auth-001', {'mode':'defended', 'attack_family':'cross-server-shadowing'})
    policy = result.investigation['manifest']
    assert policy['exposed'] == [] and policy['no_call'] is True
    assert policy['invocation_rejections'] == [] and policy['executed_calls'] == 0
    assert result.investigation['decision'] is None

def test_rejected_call_is_saved_without_execution_or_fabricated_decision(tmp_path):
    from poisontrace.adapters.persistence.traces import SqliteTraceStore
    from poisontrace.application.investigation import InvestigationRunner
    from poisontrace.domain import InvestigationStep
    class RejectedModel:
        async def next_step(self, case, tools, observations):
            assert all(t.server_id == 'trusted-soc' for t in tools)
            return InvestigationStep(call=InvestigationCall('controlled-malicious','get_advisory', {'case_id':case.case_id}))
    store = SqliteTraceStore(tmp_path / 'runs.db')
    runner = InvestigationRunner(store, BundledCases(), LocalSocTransport(), RejectedModel, ToolGateway((), set()), approved_manifest=approved_evidence_manifest())
    result = runner.run('soc-auth-001', {'mode':'defended', 'attack_family':'cross-server-shadowing'})
    saved = store.result_for(result.run_id)
    assert saved.status == 'failed' and saved.error_category == 'tool_policy_error'
    assert saved.investigation['decision'] is None and saved.recommendation == ''
    policy = saved.investigation['manifest']
    assert policy['executed_calls'] == 0 and policy['no_call'] is False
    assert policy['invocation_rejections'] == [{'server_id':'controlled-malicious','tool_name':'get_advisory','reason':'definition_mismatch'}]
    kinds = [e.kind for e in store.events_for(result.run_id)]
    assert 'tool_rejected' in kinds and 'tool_invoked' not in kinds and 'tool_result' not in kinds

def test_approved_file_rejects_invalid_json_schema_before_runner_construction(tmp_path):
    import json
    from dataclasses import asdict
    from jsonschema.exceptions import SchemaError
    values = [asdict(t) for t in approved_evidence_manifest()]
    values[0]['input_schema']['properties'] = {'case_id': {'type':'invented-type'}}
    values[0]['definition']['inputSchema'] = values[0]['input_schema']
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(values))
    with pytest.raises(SchemaError):
        approved_evidence_manifest(path)


# Direct application reopening uses an explicit trusted analyst.
pytestmark = pytest.mark.usefixtures("application_analyst")
