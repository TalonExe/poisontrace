from pathlib import Path

import yaml

from poisontrace.domain import Scenario, ToolDefinition


def load_scenario(path: Path) -> Scenario:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("scenario must be a mapping")
    if document.get("schema_version") != 1:
        raise ValueError("unsupported scenario schema version")

    for field in ("scenario_id", "alert", "expected_recommendation", "tools"):
        if field not in document:
            raise ValueError(f"scenario is missing {field}")
    if not document["tools"]:
        raise ValueError("scenario must contain at least one tool")
    if not document.get("name"):
        raise ValueError("scenario is missing name")

    tools = tuple(ToolDefinition(tool["name"], tool["description"]) for tool in document["tools"])
    approved_tools = tuple(
        ToolDefinition(tool["name"], tool["description"])
        for tool in document.get("approved_tools", document["tools"])
    )
    return Scenario(
        scenario_id=document["scenario_id"],
        alert=document["alert"],
        expected_recommendation=document["expected_recommendation"],
        tools=tools,
        approved_tools=approved_tools,
        attacker_target_recommendation=document.get("attacker_target_recommendation"),
        safe_fallback_recommendation=document.get("safe_fallback_recommendation"),
    )


class CampaignScenarioFiles:
    """Load campaign inputs by filename, including the historical selection rules."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def select_poisoned(self) -> tuple[list[tuple[str, str]], list[str]]:
        selected, excluded = [], []
        for path in sorted(self._directory.glob("*poisoned*.yaml"), key=lambda item: item.name):
            try:
                selected.append((path.name, self.load(path.name).scenario_id))
            except ValueError:
                excluded.append(path.name)
        return selected, excluded

    def load(self, filename: str) -> Scenario:
        if Path(filename).name != filename:
            raise ValueError("invalid campaign filename")
        try:
            scenario = load_scenario(self._directory / filename)
            if not all(isinstance(value, str) and value.strip() for value in
                       (scenario.scenario_id, scenario.alert, scenario.expected_recommendation)):
                raise ValueError("invalid scenario fields")
            if any(not isinstance(tool.name, str) or not tool.name.strip()
                   or not isinstance(tool.description, str) or not tool.description.strip()
                   for tool in (*scenario.tools, *scenario.approved_tools)):
                raise ValueError("invalid scenario tool")
            return scenario
        except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
            raise ValueError("invalid campaign scenario file") from exc
