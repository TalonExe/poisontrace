from pathlib import Path
import pytest
from poisontrace.domain import ExperimentMode, Scenario
from poisontrace.application.execution import ScenarioRunner
from poisontrace.application.gateway import ToolGateway
from poisontrace.adapters.persistence.traces import SqliteTraceStore
from poisontrace.adapters.models.fake import FakeModel
from poisontrace.application.runs import RunApplicationService
from poisontrace.application.scenarios import ScenarioService
from poisontrace.adapters.scenarios.repository import YamlScenarioRepository

@pytest.mark.parametrize('error', [RuntimeError('api_key=synthetic-secret provider body'), ValueError('synthetic-secret malformed response')])
def test_failed_attempt_is_saved_safe_timed_and_unscored(tmp_path, error):
    class Failing:
        def respond(self, scenario, tools): raise error
    scenario = Scenario.authentication_alert()
    store = SqliteTraceStore(tmp_path / 'runs.db')
    result = ScenarioRunner(Failing(), store, ToolGateway(scenario.approved_tools, set())).run(scenario, ExperimentMode.DEFENDED)
    assert result.run_id is not None
    saved = store.result_for(result.run_id)
    assert saved.status == 'failed'
    assert saved.system_error is True
    assert saved.execution_time_ms > 0
    assert saved.marker_influence is None
    assert saved.attacker_goal_achievement is None
    assert saved.recommendation_correctness is None
    assert saved.attack_success is None
    assert saved.benign_task_success is None
    assert saved.error_category in {'response_validation_error', 'experiment_execution_error'}
    assert store.events_for(result.run_id)[-1].kind == 'experiment_failed'
    assert 'synthetic-secret' not in repr(saved) + repr(store.events_for(result.run_id))


def test_returned_id_cannot_be_replaced_by_a_later_saved_run(tmp_path):
    class InterleavingStore(SqliteTraceStore):
        def save_result(self, result, run_key=None):
            saved_id = super().save_result(result, run_key)
            super().save_result(__import__('dataclasses').replace(result, scenario_id='another-incident'), 'other')
            return saved_id
        def latest_run_id(self): raise AssertionError('global latest lookup is forbidden')
    directory = tmp_path / 'scenarios'
    directory.mkdir()
    source = Path('backend/tests/fixtures/scenarios/authentication-alert-001.yaml')
    (directory / source.name).write_bytes(source.read_bytes())
    store = InterleavingStore(tmp_path / 'runs.db')
    runs = RunApplicationService(store, ScenarioService(YamlScenarioRepository(directory)), lambda *args: FakeModel())
    created = runs.create({'scenario_id':'001', 'mode':'clean'})
    assert created['run_id'] == 1
    assert runs.get(created['run_id'])['scenario_id'] == '001'
    assert store.result_for(2).scenario_id == 'another-incident'


def test_model_construction_failure_is_a_saved_attempt(tmp_path):
    directory = tmp_path / 'scenarios'
    directory.mkdir()
    source = Path('backend/tests/fixtures/scenarios/authentication-alert-001.yaml')
    (directory / source.name).write_bytes(source.read_bytes())
    store = SqliteTraceStore(tmp_path / 'runs.db')
    def failed_factory(*args): raise RuntimeError('synthetic-secret')
    runs = RunApplicationService(store, ScenarioService(YamlScenarioRepository(directory)), failed_factory)
    created = runs.create({'scenario_id': '001', 'mode': 'clean'})
    assert runs.get(created['run_id'])['status'] == 'failed'
    assert 'synthetic-secret' not in repr(runs.get(created['run_id']))

def test_http_failed_attempt_is_reopenable_and_safe(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig
    directory = tmp_path / 'scenarios'
    directory.mkdir()
    source = Path('backend/tests/fixtures/scenarios/authentication-alert-001.yaml')
    (directory / source.name).write_bytes(source.read_bytes())
    class Malformed:
        def respond(self, scenario, tools):
            import json
            return json.loads('synthetic-secret invalid JSON')
    backend = build_backend(WebConfig(scenario_dir=directory, database=tmp_path / 'runs.db'), model_factory=lambda *args: Malformed())
    client = analyst_client(create_app(backend))
    created = client.post('/api/runs', json={'scenario_id':'001', 'mode':'defended'}).json()
    detail = client.get(f"/api/runs/{created['run_id']}").json()
    assert detail['status'] == 'failed'
    assert detail['error_category'] == 'response_validation_error'
    assert detail['attack_success'] is None
    assert detail['execution_time_ms'] > 0
    assert client.get('/api/runs').json()[0]['status'] == 'failed'
    assert 'synthetic-secret' not in str(detail)
    invalid = client.post('/api/runs', json={'scenario_id':'001', 'mode':'unknown'})
    assert invalid.status_code == 400
    assert len(client.get('/api/runs').json()) == 1


def test_campaign_children_keep_their_returned_ids_during_overlapping_saves(tmp_path):
    from dataclasses import replace
    from poisontrace.adapters.persistence.campaigns import InMemoryCampaignStore
    from poisontrace.adapters.scenarios.loader import CampaignScenarioFiles
    from poisontrace.application.campaigns import CampaignApplicationService
    class InterleavingStore(SqliteTraceStore):
        def save_result(self, result, run_key=None):
            saved_id = super().save_result(result, run_key)
            super().save_result(replace(result, scenario_id='unrelated'), 'other')
            return saved_id
        def latest_run_id(self): raise AssertionError('global latest lookup is forbidden')
    directory = tmp_path / 'scenarios'
    directory.mkdir()
    source = Path('backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml')
    (directory / source.name).write_bytes(source.read_bytes())
    store = InterleavingStore(tmp_path / 'runs.db')
    service = CampaignApplicationService(InMemoryCampaignStore(), store, CampaignScenarioFiles(directory), lambda *args: FakeModel(), RunApplicationService(store, None, None).summary)
    cid = service.create({})['campaign_id']
    service.execute(cid)
    assert service.get(cid)['scenarios'][0]['child_run_id'] == 1
    rerun = service.rerun(cid, 0)
    assert rerun['scenarios'][0]['child_run_id'] == 3
    assert store.result_for(3).scenario_id == '002'

def test_additive_migration_preserves_pre_slice_records(tmp_path):
    import sqlite3
    database = tmp_path / 'historical.db'
    # Historical schema is test setup, not a query used to verify current behavior.
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE runs (id INTEGER PRIMARY KEY AUTOINCREMENT, scenario_id TEXT NOT NULL, mode TEXT NOT NULL, recommendation TEXT NOT NULL, benign_task_success INTEGER NOT NULL, attack_success INTEGER NOT NULL, execution_time_ms REAL NOT NULL, system_error INTEGER NOT NULL, unauthorised_tool_call INTEGER NOT NULL)')
        connection.execute("INSERT INTO runs VALUES (9, 'historic-incident', 'defended', 'escalate', 0, 1, 12.5, 0, 0)")
        connection.execute('CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, kind TEXT NOT NULL, data TEXT NOT NULL)')
        connection.execute('INSERT INTO events (run_id,kind,data) VALUES (9,?,?)', ('tool_returned', '{"name":"historical-tool"}'))
    store = SqliteTraceStore(database)
    saved = store.result_for(9)
    assert saved.scoring_version == 'legacy'
    assert saved.attack_success is True
    assert saved.benign_task_success is False
    assert saved.execution_time_ms == 12.5
    assert saved.attacker_goal_achievement is None
    assert saved.call_rejected is None
    assert store.events_for(9)[0].kind == 'tool_returned'
    scenario = Scenario.authentication_alert()
    result = ScenarioRunner(FakeModel(), store, ToolGateway(scenario.approved_tools, set())).run(scenario, ExperimentMode.CLEAN)
    assert result.run_id == 10
    assert SqliteTraceStore(database).result_for(9) == saved
