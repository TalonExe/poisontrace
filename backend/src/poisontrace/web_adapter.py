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
from poisontrace.persistence.campaigns import SqliteCampaignStore
from poisontrace.persistence.traces import SqliteTraceStore
from poisontrace.secrets import SecretsAdapter
from poisontrace.scenario_store import ScenarioStore
from poisontrace.scenario_service import ScenarioService


class ScenarioNotFound(KeyError):
    """Raised when a run references an unknown scenario ID."""


class RunWebAdapter:
    def __init__(self, scenario_dir: Path, database: Path, secrets: SecretsAdapter | None = None) -> None:
        self.scenario_dir = scenario_dir
        self.store = SqliteTraceStore(database)
        self.campaigns = SqliteCampaignStore(database)
        self.secrets = secrets
        self.scenarios = ScenarioStore(scenario_dir)
        self.scenario_service = ScenarioService(self.scenarios)

    def _scenario(self, scenario_id: str):
        try:
            return self.scenario_service.load_usable(scenario_id)
        except KeyError as exc:
            raise ScenarioNotFound(str(scenario_id)) from exc

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

    def get_run(self, run_id: int) -> dict[str, Any]:
        result = self.store.result_for(run_id)
        events = self.store.events_for(run_id)
        return {
            **self._serialize(run_id, result),
            "status": "completed",
            "scenario_id": result.scenario_id,
            "recommendation": result.recommendation,
            "benign_task_success": result.benign_task_success,
            "attack_success": result.attack_success,
            "execution_time_ms": result.execution_time_ms,
            "system_error": result.system_error,
            "unauthorised_tool_call": result.unauthorised_tool_call,
            "injection_verdict": result.injection_verdict,
            "task_outcome": result.task_outcome,
            "tool_call_status": result.tool_call_status,
            "run_configuration": result.run_configuration or {},
            "trace": [
                {"kind": event.kind, "data": event.data}
                for event in events
            ],
            "metrics": {
                "attack_success": result.attack_success,
                "benign_task_success": result.benign_task_success,
                "execution_time_ms": result.execution_time_ms,
                "injection_verdict": result.injection_verdict,
                "task_outcome": result.task_outcome,
                "tool_call_status": result.tool_call_status,
            },
        }

    def list_scenarios(self) -> list[dict[str, Any]]:
        return self.scenario_service.list()

    def get_scenario(self, scenario_id: str) -> dict[str, Any]:
        return self.scenario_service.get(scenario_id)

    def create_scenario(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.scenario_service.create(payload)

    def update_scenario(self, scenario_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.scenario_service.update(scenario_id, payload)

    def delete_scenario(self, scenario_id: str) -> None:
        self.scenario_service.delete(scenario_id)

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

    def create_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"secret", "api_key", "apiKey", "credential_secret"}
        if forbidden.intersection(payload):
            raise ValueError("campaign payload must not contain plaintext credentials")
        provider = str(payload.get("provider", "fake"))
        if provider not in {"fake", "gemini", "openai"}:
            raise ValueError(f"unsupported provider: {provider}")
        model = str(payload.get("model") or ("fake" if provider == "fake" else ""))
        if not model:
            raise ValueError("model is required")
        credential_id = payload.get("credential_id")
        if credential_id is not None:
            credential_id = str(credential_id)
            if self.secrets is None:
                raise ValueError("credential storage is not configured")
            reference = self.secrets.reference(credential_id)
            if reference.provider != provider:
                raise ValueError(f"credential provider {reference.provider} does not match campaign provider {provider}")
        selected = []
        for path in sorted(self.scenario_dir.glob("*poisoned*.yaml"), key=lambda item: item.name):
            selected.append((path.name, load_scenario(path).scenario_id))
        if not selected:
            raise ValueError("no poisoned scenarios found")
        campaign_id = self.campaigns.create(
            provider=provider,
            model=model,
            credential_id=credential_id,
            scenarios=selected,
        )
        return self.campaigns.get(campaign_id)

    def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        campaign = self.campaigns.get(campaign_id)
        return campaign if campaign["status"] == "created" else self._with_scenario_details(campaign)

    def _with_scenario_details(self, campaign: dict[str, Any]) -> dict[str, Any]:
        campaign["scenarios"] = [self._scenario_detail(item) for item in campaign["scenarios"]]
        return campaign

    def _scenario_detail(self, item: dict[str, Any]) -> dict[str, Any]:
        detail = dict(item)
        detail["outcome"] = None
        detail["failure_state"] = item["error"]
        if item["child_run_id"] is not None:
            try:
                result = self.store.result_for(item["child_run_id"])
                detail["outcome"] = "Attack success" if result.attack_success else "Benign success"
                detail["injection_verdict"] = result.injection_verdict
                detail["task_outcome"] = result.task_outcome
                detail["tool_call_status"] = result.tool_call_status
            except KeyError:
                detail["failure_state"] = "missing_child_run"
        return detail

    def list_campaigns(self) -> list[dict[str, Any]]:
        return [self._campaign_summary(campaign) for campaign in self.campaigns.list()]

    def _campaign_summary(self, campaign: dict[str, Any]) -> dict[str, Any]:
        completed = [item for item in campaign["scenarios"] if item["child_run_id"] is not None]
        failed = [item for item in campaign["scenarios"] if item["error"] is not None]
        attack_successes = 0
        for item in completed:
            try:
                if self.store.result_for(item["child_run_id"]).attack_success:
                    attack_successes += 1
            except KeyError:
                continue
        return {
            "campaign_id": campaign["campaign_id"],
            "status": campaign["status"],
            "provider": campaign["provider"],
            "model": campaign["model"],
            "credential_id": campaign["credential_id"],
            "scenario_count": len(campaign["scenarios"]),
            "completed": len(completed),
            "failed": len(failed),
            "attack_successes": attack_successes,
            "injection_successes": attack_successes,
            "task_successes": sum(1 for item in completed if self.store.result_for(item["child_run_id"]).benign_task_success),
        }

    def execute_campaign(self, campaign_id: str) -> dict[str, Any]:
        campaign = self.campaigns.get(campaign_id)
        if campaign["status"] != "created":
            raise ValueError(f"campaign is already {campaign['status']}")
        provider = campaign["provider"]
        credential_id = campaign["credential_id"] or ""
        api_key = None
        if credential_id:
            if self.secrets is None:
                raise ValueError("credential storage is not configured")
            reference = self.secrets.reference(credential_id)
            if reference.provider != provider:
                raise ValueError(f"credential provider {reference.provider} does not match campaign provider {provider}")
            api_key = self.secrets.retrieve(credential_id)
        model = self._model(provider, campaign["model"], api_key)
        self.campaigns.set_status(campaign_id, "running")
        results = []
        failures = 0
        for ordinal, selected in enumerate(campaign["scenarios"]):
            try:
                scenario = load_scenario(self.scenario_dir / selected["filename"])
                runner = ScenarioRunner(
                    model=model,
                    trace_store=self.store,
                    gateway=ToolGateway(
                        approved_manifest=scenario.approved_tools or scenario.tools,
                        high_impact_tools=set(),
                        enforce_manifest=False,
                    ),
                )
                result = runner.run(
                    scenario,
                    ExperimentMode.POISONED,
                    {
                        "campaign_id": campaign_id,
                        "provider": provider,
                        "credential_id": credential_id,
                        "model": campaign["model"],
                    },
                )
                child_run_id = self.store.latest_run_id()
                self.campaigns.associate_child_run(campaign_id, ordinal, child_run_id=child_run_id)
                summary = self._serialize(child_run_id, result)
                summary["filename"] = selected["filename"]
                results.append(summary)
            except Exception as exc:
                failures += 1
                self.campaigns.associate_child_run(campaign_id, ordinal, error=type(exc).__name__)
        self.campaigns.set_status(campaign_id, "completed_with_errors" if failures else "completed")
        completed = len(results)
        attack_successes = sum(1 for result in results if result["result"] == "Attack success")
        response = self.campaigns.get(campaign_id)
        response.update(
            {
                "total": len(response["scenarios"]),
                "completed": completed,
                "failed": failures,
                "attack_successes": attack_successes,
                "results": results,
            }
        )
        return response

    def rerun_campaign_scenario(self, campaign_id: str, ordinal: int) -> dict[str, Any]:
        campaign = self.campaigns.get(campaign_id)
        if ordinal < 0 or ordinal >= len(campaign["scenarios"]):
            raise KeyError(ordinal)
        selected = campaign["scenarios"][ordinal]
        provider = campaign["provider"]
        credential_id = campaign["credential_id"] or ""
        api_key = None
        if credential_id:
            if self.secrets is None:
                raise ValueError("credential storage is not configured")
            reference = self.secrets.reference(credential_id)
            if reference.provider != provider:
                raise ValueError(f"credential provider {reference.provider} does not match campaign provider {provider}")
            api_key = self.secrets.retrieve(credential_id)
        try:
            scenario = load_scenario(self.scenario_dir / selected["filename"])
            result = ScenarioRunner(
                model=self._model(provider, campaign["model"], api_key),
                trace_store=self.store,
                gateway=ToolGateway(
                    approved_manifest=scenario.approved_tools or scenario.tools,
                    high_impact_tools=set(),
                    enforce_manifest=False,
                ),
            ).run(
                scenario,
                ExperimentMode.POISONED,
                {"campaign_id": campaign_id, "provider": provider, "credential_id": credential_id, "model": campaign["model"]},
            )
            self.campaigns.associate_child_run(campaign_id, ordinal, child_run_id=self.store.latest_run_id())
        except Exception as exc:
            self.campaigns.associate_child_run(campaign_id, ordinal, error=type(exc).__name__)
        return self._with_scenario_details(self.campaigns.get(campaign_id))

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
            "injection_verdict": result.injection_verdict,
            "task_outcome": result.task_outcome,
            "tool_call_status": result.tool_call_status,
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
    from poisontrace.interfaces.http.app import create_app as create_http_app

    if adapter is None:
        adapter = RunWebAdapter(Path("backend/scenarios"), Path("poisontrace.db"))
    return create_http_app(adapter)

    # Kept below as a reference during the migration; the compatibility
    # factory above is the only active HTTP composition path.
    from fastapi import FastAPI, HTTPException

    app = FastAPI()
    adapter = adapter or RunWebAdapter(Path("backend/scenarios"), Path("poisontrace.db"))

    @app.get("/api/runs")
    def list_runs():
        return adapter.list_runs()

    @app.get("/api/scenarios")
    def list_scenarios():
        return adapter.list_scenarios()

    @app.get("/api/scenarios/{scenario_id}")
    def get_scenario(scenario_id: str):
        try:
            return adapter.get_scenario(scenario_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="scenario not found") from exc

    @app.post("/api/scenarios", status_code=201)
    def create_scenario(payload: dict[str, Any]):
        try:
            return adapter.create_scenario(payload)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/scenarios/{scenario_id}")
    def update_scenario(scenario_id: str, payload: dict[str, Any]):
        try:
            return adapter.update_scenario(scenario_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="scenario not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/scenarios/{scenario_id}")
    def delete_scenario(scenario_id: str):
        try:
            adapter.delete_scenario(scenario_id)
            return {"scenario_id": scenario_id, "deleted": True}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="scenario not found") from exc

    @app.post("/api/runs")
    def create_run(payload: dict[str, Any]):
        try:
            return adapter.create_run(payload)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/campaigns", status_code=201)
    def create_campaign(payload: dict[str, Any]):
        try:
            return adapter.create_campaign(payload)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/campaigns")
    def list_campaigns():
        return adapter.list_campaigns()

    @app.get("/api/campaigns/{campaign_id}")
    def get_campaign(campaign_id: str):
        try:
            return adapter.get_campaign(campaign_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="campaign not found") from exc

    @app.post("/api/campaigns/{campaign_id}/execute")
    def execute_campaign(campaign_id: str):
        try:
            return adapter.execute_campaign(campaign_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="campaign not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/campaigns/{campaign_id}/scenarios/{ordinal}/rerun")
    def rerun_campaign_scenario(campaign_id: str, ordinal: int):
        try:
            return adapter.rerun_campaign_scenario(campaign_id, ordinal)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="campaign scenario not found") from exc
        except ValueError as exc:
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
