"""Web-facing adapter for the domain runner.

The service uses plain dictionaries at its boundary so the domain remains
independent of any HTTP framework.
"""

from pathlib import Path
from typing import Any

from poisontrace.agent import FakeModel
from poisontrace.domain import ExperimentMode
from poisontrace.gateway import ToolGateway
from poisontrace.gemini_model import GeminiModel
from poisontrace.openai_model import OpenAIModel
from poisontrace.runner import ScenarioRunner
from poisontrace.scenario_loader import load_scenario
from poisontrace.trace import SqliteTraceStore
from poisontrace.secrets import SecretsAdapter


class RunWebAdapter:
    def __init__(self, scenario_dir: Path, database: Path, secrets: SecretsAdapter | None = None) -> None:
        self.scenario_dir = scenario_dir
        self.store = SqliteTraceStore(database)
        self.secrets = secrets

    def _scenario(self, scenario_id: str):
        candidates = [
            self.scenario_dir / f"{scenario_id}.yaml",
            self.scenario_dir / "authentication-alert.yaml"
            if scenario_id == "authentication-alert"
            else None,
        ]
        for candidate in candidates:
            if candidate is not None and candidate.exists():
                return load_scenario(candidate)
        raise ValueError(f"unknown scenario: {scenario_id}")

    @staticmethod
    def _model(provider: str, model: str | None, api_key: str | None = None):
        if provider == "fake":
            return FakeModel()
        if provider == "gemini":
            return GeminiModel(model_name=model or "gemini-3.5-flash-lite", api_key=api_key)
        if provider == "openai":
            return OpenAIModel(model_name=model or "gpt-5-mini", api_key=api_key)
        raise ValueError(f"unsupported provider: {provider}")

    def list_runs(self) -> list[dict[str, Any]]:
        return [self._serialize(run_id) for run_id in self.store.run_ids()]

    def create_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        scenario_id = payload.get("scenario_id", "authentication-alert")
        mode = ExperimentMode(payload.get("mode", "clean").lower())
        provider = payload.get("provider", payload.get("model", "fake"))
        if provider not in {"fake", "gemini", "openai"}:
            raise ValueError(f"unsupported provider: {provider}")
        model_name = payload.get("model") if provider in {"gemini", "openai"} else None
        credential_id = str(payload.get("credential_id", ""))
        api_key = None
        if credential_id:
            if self.secrets is None:
                raise ValueError("credential storage is not configured")
            reference = self.secrets.reference(credential_id)
            if reference.provider != provider:
                raise ValueError(f"credential provider {reference.provider} does not match run provider {provider}")
            api_key = self.secrets.retrieve(credential_id)
        scenario = self._scenario(scenario_id)
        model = self._model(provider, model_name, api_key)
        runner = ScenarioRunner(
            model=model,
            trace_store=self.store,
            gateway=ToolGateway(
                approved_manifest=scenario.approved_tools or scenario.tools,
                high_impact_tools=set(),
                enforce_manifest=mode != ExperimentMode.POISONED,
            ),
        )
        result = runner.run(
            scenario,
            mode,
            {
                "session_id": str(payload.get("session_id", "")),
                "provider": provider,
                "credential_id": credential_id,
            },
        )
        return self._serialize(self.store.latest_run_id(), result)

    def _serialize(self, run_id: int, result=None) -> dict[str, Any]:
        result = result or self.store.result_for(run_id)
        return {
            "id": f"EXP-{run_id:03d}",
            "run_id": run_id,
            "scenario_id": result.scenario_id,
            "mode": result.mode.value.title(),
            "model": result.model_name,
            "result": "Attack success" if result.attack_success else "Benign success",
            "time": "just now",
            "tone": "red" if result.attack_success else "green",
            "mark": "!" if result.attack_success else "✓",
        }

    def save_credential(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.secrets is None:
            raise ValueError("credential storage is not configured")
        return self._credential_dict(self.secrets.save(payload["provider"], payload["secret"], payload.get("label", "")))

    def replace_credential(self, credential_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.secrets is None:
            raise ValueError("credential storage is not configured")
        return self._credential_dict(self.secrets.replace(credential_id, payload["provider"], payload["secret"], payload.get("label", "")))

    def _credential_dict(self, reference):
        return {"credential_id": reference.credential_id, "provider": reference.provider, "label": reference.label, "masked": reference.masked}


def create_app(adapter: RunWebAdapter | None = None):
    """Create the HTTP app without importing FastAPI for domain-only users."""
    from fastapi import FastAPI, HTTPException

    app = FastAPI()
    adapter = adapter or RunWebAdapter(Path("scenarios"), Path("poisontrace.db"))

    @app.get("/api/runs")
    def list_runs():
        return adapter.list_runs()

    @app.post("/api/runs")
    def create_run(payload: dict[str, Any]):
        try:
            return adapter.create_run(payload)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/credentials")
    def list_credentials():
        if adapter.secrets is None:
            raise HTTPException(status_code=503, detail="credential storage is not configured")
        return [adapter._credential_dict(item) for item in adapter.secrets.list()]

    @app.post("/api/credentials")
    def save_credential(payload: dict[str, Any]):
        try:
            return adapter.save_credential(payload)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/credentials/{credential_id}")
    def replace_credential(credential_id: str, payload: dict[str, Any]):
        try:
            return adapter.replace_credential(credential_id, payload)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/credentials/{credential_id}/test")
    def test_credential(credential_id: str):
        try:
            adapter.secrets.retrieve(credential_id)
            return {"credential_id": credential_id, "ok": True}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="credential not found") from exc

    @app.delete("/api/credentials/{credential_id}")
    def revoke_credential(credential_id: str):
        try:
            adapter.secrets.revoke(credential_id)
            return {"credential_id": credential_id, "revoked": True}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="credential not found") from exc

    return app
