from pathlib import Path

import pytest

from poisontrace.adapters.scenarios.loader import CampaignScenarioFiles, load_scenario
from poisontrace.adapters.scenarios.repository import YamlScenarioRepository
from poisontrace.application.scenarios import ScenarioService




def test_draft_repair_keeps_filename_identity_and_failed_write_keeps_original(tmp_path, monkeypatch):
    repository = YamlScenarioRepository(tmp_path)
    service = ScenarioService(repository)
    draft = service.create({"name": "Draft"})
    assert not draft["valid"]
    with pytest.raises(ValueError, match="scenario is invalid"):
        service.load_usable(draft["scenario_id"])
    document = {"schema_version": 1, "name": "Repaired", "alert": "test",
                "expected_recommendation": "escalate", "tools": [{"name": "lookup", "description": "Evidence"}]}
    repaired = service.update(draft["scenario_id"], {"document": document})
    assert repaired["valid"]
    assert repaired["filename"] == draft["filename"]
    assert service.load_usable(draft["scenario_id"]).scenario_id == draft["scenario_id"]
    original = repository.read_raw(draft["filename"])
    def fail_replace(*args, **kwargs):
        raise OSError("synthetic replacement failure")
    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="replacement failure"):
        service.update(draft["scenario_id"], {"document": {**document, "name": "Changed"}})
    assert repository.read_raw(draft["filename"]) == original
    service.delete(draft["scenario_id"])
    with pytest.raises(KeyError):
        service.get(draft["scenario_id"])


def test_campaign_files_reload_and_still_reject_invalid_matching_files(tmp_path):
    source = Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml").read_text(encoding="utf-8")
    path = tmp_path / "only-poisoned.yaml"
    path.write_text(source, encoding="utf-8")
    files = CampaignScenarioFiles(tmp_path)
    assert files.select_poisoned() == [(path.name, "002")]
    path.write_text("invalid: true", encoding="utf-8")
    with pytest.raises(ValueError):
        files.load(path.name)
    with pytest.raises(ValueError):
        files.select_poisoned()
