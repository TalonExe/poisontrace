"""Application service for scenario-library use cases."""

import re
from typing import Any

from poisontrace.application.ports import ScenarioRepository


class ScenarioService:
    """Coordinates scenario CRUD and the usable-scenario execution boundary."""

    def __init__(self, store: ScenarioRepository) -> None:
        self.store = store

    def list(self) -> list[dict[str, Any]]:
        return self.store.list()

    def get(self, scenario_id: str) -> dict[str, Any]:
        return self.store.get(scenario_id)

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", ""))
        if not name.strip():
            raise ValueError("name is required")
        if any(item["name"].strip().casefold() == name.strip().casefold() for item in self.store.list()):
            raise ValueError("scenario name already exists")
        used = [int(item["scenario_id"]) for item in self.store.list() if item["scenario_id"] and str(item["scenario_id"]).isdigit()]
        scenario_id = f"{max(used, default=0) + 1:03d}"
        document = dict(payload.get("document") or {})
        document.update({"schema_version": 1, "scenario_id": scenario_id, "name": name})
        document.setdefault("alert", "")
        document.setdefault("expected_recommendation", "escalate")
        document.setdefault("tools", [])
        document.setdefault("approved_tools", [])
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "scenario"
        filename = f"{slug}-{scenario_id}.yaml"
        try:
            return self.store.save(document, filename)
        except ValueError:
            self.store.write_document(filename, document)
            return self.store.get(filename)

    def update(self, scenario_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.store.get(scenario_id)
        document = dict(payload.get("document", payload))
        document["scenario_id"] = scenario_id
        return self.store.save(document, current["filename"])

    def delete(self, scenario_id: str) -> None:
        current = self.store.get(scenario_id)
        self.store.delete_filename(current["filename"])

    def load_usable(self, scenario_id: str):
        item = self.store.get(str(scenario_id))
        if not item["valid"]:
            raise ValueError(f"scenario is invalid: {item['error']}")
        return self.store.load(item["filename"])
