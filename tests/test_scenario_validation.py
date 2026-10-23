import pytest

from poisontrace.scenario_loader import load_scenario


def test_loader_rejects_scenario_without_required_field(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_text(
        "schema_version: 1\nscenario_id: invalid\nexpected_recommendation: escalate\ntools: []\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="alert"):
        load_scenario(path)


def test_loader_rejects_scenario_without_tools(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_text(
        "schema_version: 1\nscenario_id: invalid\nalert: test\nexpected_recommendation: escalate\ntools: []\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="at least one tool"):
        load_scenario(path)
