from poisontrace.application.scenarios import ScenarioService
from poisontrace.adapters.scenarios.repository import YamlScenarioRepository


def test_invalid_files_are_visible_but_not_usable(tmp_path):
    path = tmp_path / "broken-005.yaml"
    path.write_text("scenario_id: '005'\nname: Broken\n", encoding="utf-8")
    service = ScenarioService(YamlScenarioRepository(tmp_path))

    assert service.list()[0]["valid"] is False
    try:
        service.load_usable(path.name)
    except ValueError as exc:
        assert str(exc).startswith("scenario is invalid:")
    else:
        raise AssertionError("invalid scenario was accepted for execution")


def test_update_keeps_scenario_id_immutable(tmp_path):
    service = ScenarioService(YamlScenarioRepository(tmp_path))
    created = service.create({"name": "Example"})
    document = {
        "schema_version": 1,
        "scenario_id": "999",
        "name": "Example Revised",
        "alert": "test",
        "expected_recommendation": "escalate",
        "tools": [{"name": "lookup", "description": "Lookup evidence"}],
        "approved_tools": [{"name": "lookup", "description": "Lookup evidence"}],
    }

    updated = service.update(created["scenario_id"], {"document": document})

    assert updated["scenario_id"] == created["scenario_id"]
