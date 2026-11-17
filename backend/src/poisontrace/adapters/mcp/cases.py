import json
from pathlib import Path
from dataclasses import asdict
import os
from tempfile import NamedTemporaryFile
from threading import RLock

from poisontrace.domain import SyntheticCase, EvidenceTool
from jsonschema import Draft202012Validator


class BundledCases:
    """Fixed case library, separate from editable schema-v1 metadata scenarios."""

    def __init__(self, directory: Path | None = None):
        self.directory = directory
        self._lock = RLock()

    def _sources(self):
        root = Path(__file__).parent
        return {"soc-auth-001": root / "authentication.json", **{
            path.stem: path for path in sorted((root / "corpus").glob("*.json"))}}

    def list(self) -> list[dict]:
        cases = [self.get(identifier) for identifier in self._sources()]
        return [{"case_id": case.case_id, "case_version": case.case_version, "name": case.name,
                 "dataset_category": case.dataset_category, "supported_attack_families": list(case.supported_attack_families)} for case in cases]

    def get(self, case_id: str) -> SyntheticCase:
        sources = self._sources()
        if case_id not in sources:
            raise KeyError(case_id)
        source = sources[case_id]
        if self.directory is not None and (self.directory / f"{case_id}.json").exists():
            source = self.directory / f"{case_id}.json"
        return SyntheticCase(**json.loads(source.read_text(encoding="utf-8")))

    def save_ground_truth(self, case, base_version):
        if self.directory is None:
            raise ValueError("case authoring is unavailable")
        with self._lock:
            if self.get(case.case_id).case_version != base_version:
                raise ValueError("case changed; reload before saving")
            self.directory.mkdir(parents=True, exist_ok=True)
            destination = self.directory / f"{case.case_id}.json"
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory, delete=False) as file:
                temporary = Path(file.name)
                json.dump(asdict(case), file, indent=2)
            try:
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
        return case


def approved_evidence_manifest(path: Path | None = None):
    """Reviewed ordinary definitions, never derived from attacked discovery at runtime."""
    source = path if path is not None else Path(__file__).with_name("approved_manifest.json")
    values = json.loads(source.read_text(encoding="utf-8"))
    tools = tuple(EvidenceTool(**value) for value in values)
    for tool in tools:
        Draft202012Validator.check_schema(tool.input_schema)
        if "outputSchema" in tool.definition:
            Draft202012Validator.check_schema(tool.definition["outputSchema"])
    return tools
