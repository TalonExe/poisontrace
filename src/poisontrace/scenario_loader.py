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
        safe_fallback_recommendation=document.get("safe_fallback_recommendation"),
    )
