from pathlib import Path
import re
import tempfile
from typing import Any

import yaml

from poisontrace.adapters.scenarios.loader import load_scenario


class YamlScenarioRepository:
    def __init__(self, directory: Path):
        self.directory = directory

    def _read(self, path: Path) -> dict[str, Any]:
        document: Any = None
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("scenario must be a mapping")
            load_scenario(path)
            if not document.get("name"):
                raise ValueError("scenario is missing name")
            return {"filename": path.name, "valid": True, "error": None, "raw": path.read_text(encoding="utf-8"), "document": document}
        except Exception as exc:
            return {"filename": path.name, "valid": False, "error": str(exc), "raw": path.read_text(encoding="utf-8"), "document": document if isinstance(document, dict) else None}

    def write_document(self, filename: str, document: dict[str, Any]) -> None:
        self.write_raw(filename, yaml.safe_dump(document, sort_keys=False, allow_unicode=False))

    def load(self, filename: str):
        return load_scenario(self.directory / filename)

    def read_raw(self, filename: str) -> str:
        return self._path(filename).read_text(encoding="utf-8")

    def write_raw(self, filename: str, raw: str) -> None:
        path = self._path(filename)
        self.directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.directory, delete=False) as handle:
            handle.write(raw)
            temporary = Path(handle.name)
        temporary.replace(path)

    def _path(self, filename: str) -> Path:
        candidate = Path(filename)
        if candidate.name != filename or candidate.suffix != ".yaml":
            raise ValueError("invalid scenario filename")
        path = (self.directory / candidate).resolve()
        if path.parent != self.directory.resolve():
            raise ValueError("invalid scenario filename")
        return path

    def list(self) -> list[dict[str, Any]]:
        items = []
        for path in sorted(self.directory.glob("*.yaml"), key=lambda item: item.name):
            item = self._read(path)
            document = item["document"] or {}
            items.append({"filename": item["filename"], "scenario_id": document.get("scenario_id"), "name": document.get("name") or path.stem, "valid": item["valid"], "error": item["error"]})
        return items

    def get(self, scenario_id: str) -> dict[str, Any]:
        for path in self.directory.glob("*.yaml"):
            item = self._read(path)
            document = item["document"] or {}
            if document.get("scenario_id") == scenario_id or item["filename"] == scenario_id or item["filename"] == f"{scenario_id}.yaml":
                return {**item, "name": document.get("name") or path.stem, "scenario_id": document.get("scenario_id") or scenario_id}
        raise KeyError(scenario_id)

    def _validate(self, document: dict[str, Any]) -> None:
        if not document.get("name", "").strip(): raise ValueError("name is required")
        if not re.fullmatch(r"\d{3}", str(document.get("scenario_id", ""))): raise ValueError("scenario_id must be a three-digit identifier")
        if not isinstance(document.get("tools"), list) or not document["tools"]: raise ValueError("scenario must contain at least one tool")
        if any(not isinstance(tool, dict) or not str(tool.get("name", "")).strip() for tool in document["tools"]): raise ValueError("tools must have names")
        names = [tool.get("name") for tool in document["tools"]]
        if len(set(names)) != len(names): raise ValueError("tool names must be unique")
        for tool in document.get("approved_tools", document["tools"]):
            if not isinstance(tool, dict) or not str(tool.get("name", "")).strip(): raise ValueError("approved tools must have names")
            if tool.get("name") not in names: raise ValueError("approved tools must be declared in tools")

    def _write(self, path: Path, document: dict[str, Any]) -> None:
        self._validate(document)
        self.directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.directory, delete=False) as handle:
            yaml.safe_dump(document, handle, sort_keys=False, allow_unicode=False)
            temporary = Path(handle.name)
        temporary.replace(path)

    def save(self, document: dict[str, Any], filename: str | None = None) -> dict[str, Any]:
        self._validate(document)
        current_filename = Path(filename).name if filename else None
        for item in self.list():
            if item["filename"] == current_filename:
                continue
            if item["scenario_id"] == str(document["scenario_id"]):
                raise ValueError("scenario_id already exists")
            if item["name"].strip().casefold() == document["name"].strip().casefold():
                raise ValueError("scenario name already exists")
        if filename is None:
            slug = re.sub(r"[^a-z0-9]+", "-", document["name"].lower()).strip("-") or "scenario"
            filename = f"{slug}-{document['scenario_id']}.yaml"
        path = self.directory / Path(filename).name
        if path.parent != self.directory:
            raise ValueError("invalid scenario filename")
        self._write(path, document)
        return self.get(str(document["scenario_id"]))

    def delete_filename(self, filename: str) -> None:
        self._path(filename).unlink()
