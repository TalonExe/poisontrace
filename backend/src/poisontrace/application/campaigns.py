"""Campaign orchestration, child evidence and reruns behind one application interface."""

from typing import Any

from poisontrace.application.contracts import CampaignRequest
from poisontrace.application.ports import CampaignStore, CampaignScenarios, ModelFactory, RunStore, RunSummary, SecretsAdapter
from poisontrace.domain import ExperimentMode
from poisontrace.application.gateway import ToolGateway
from poisontrace.application.execution import ScenarioRunner


class CampaignApplicationService:
    def __init__(
        self,
        campaigns: CampaignStore,
        runs: RunStore,
        scenarios: CampaignScenarios,
        model_factory: ModelFactory,
        summary: RunSummary,
        secrets: SecretsAdapter | None = None,
    ) -> None:
        self._campaigns = campaigns
        self._runs = runs
        self._scenarios = scenarios
        self._model_factory = model_factory
        self._summary = summary
        self._secrets = secrets

    def create(self, payload: CampaignRequest) -> dict[str, Any]:
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
            if self._secrets is None:
                raise ValueError("credential storage is not configured")
            reference = self._secrets.reference(credential_id)
            if reference.provider != provider:
                raise ValueError(f"credential provider {reference.provider} does not match campaign provider {provider}")
        selected = self._scenarios.select_poisoned()
        if not selected:
            raise ValueError("no poisoned scenarios found")
        campaign_id = self._campaigns.create(
            provider=provider,
            model=model,
            credential_id=credential_id,
            scenarios=selected,
        )
        return self._campaigns.get(campaign_id)

    def get(self, campaign_id: str) -> dict[str, Any]:
        campaign = self._campaigns.get(campaign_id)
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
                result = self._runs.result_for(item["child_run_id"])
                detail["outcome"] = "Attack success" if result.attack_success else "Benign success"
                detail["injection_verdict"] = result.injection_verdict
                detail["task_outcome"] = result.task_outcome
                detail["tool_call_status"] = result.tool_call_status
                detail["trace"] = [
                    {"kind": event.kind, "data": event.data}
                    for event in self._runs.events_for(item["child_run_id"])
                ]
            except KeyError:
                detail["failure_state"] = "missing_child_run"
        return detail

    def list(self) -> list[dict[str, Any]]:
        return [self._campaign_summary(campaign) for campaign in self._campaigns.list()]

    def _campaign_summary(self, campaign: dict[str, Any]) -> dict[str, Any]:
        completed = [item for item in campaign["scenarios"] if item["child_run_id"] is not None]
        failed = [item for item in campaign["scenarios"] if item["error"] is not None]
        attack_successes = 0
        for item in completed:
            try:
                if self._runs.result_for(item["child_run_id"]).attack_success:
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
            "task_successes": sum(1 for item in completed if self._runs.result_for(item["child_run_id"]).benign_task_success),
        }

    def execute(self, campaign_id: str) -> dict[str, Any]:
        campaign = self._campaigns.get(campaign_id)
        if campaign["status"] != "created":
            raise ValueError(f"campaign is already {campaign['status']}")
        provider = campaign["provider"]
        credential_id = campaign["credential_id"] or ""
        api_key = None
        if credential_id:
            if self._secrets is None:
                raise ValueError("credential storage is not configured")
            reference = self._secrets.reference(credential_id)
            if reference.provider != provider:
                raise ValueError(f"credential provider {reference.provider} does not match campaign provider {provider}")
            api_key = self._secrets.retrieve(credential_id)
        model = self._model_factory(provider, campaign["model"], api_key)
        self._campaigns.set_status(campaign_id, "running")
        results = []
        failures = 0
        for ordinal, selected in enumerate(campaign["scenarios"]):
            try:
                scenario = self._scenarios.load(selected["filename"])
                runner = ScenarioRunner(
                    model=model,
                    trace_store=self._runs,
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
                child_run_id = self._runs.latest_run_id()
                self._campaigns.associate_child_run(campaign_id, ordinal, child_run_id=child_run_id)
                summary = self._summary(child_run_id, result)
                summary["filename"] = selected["filename"]
                results.append(summary)
            except Exception as exc:
                failures += 1
                self._campaigns.associate_child_run(campaign_id, ordinal, error=type(exc).__name__)
        self._campaigns.set_status(campaign_id, "completed_with_errors" if failures else "completed")
        completed = len(results)
        attack_successes = sum(1 for result in results if result["result"] == "Attack success")
        response = self._campaigns.get(campaign_id)
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

    def rerun(self, campaign_id: str, ordinal: int) -> dict[str, Any]:
        campaign = self._campaigns.get(campaign_id)
        if ordinal < 0 or ordinal >= len(campaign["scenarios"]):
            raise KeyError(ordinal)
        selected = campaign["scenarios"][ordinal]
        provider = campaign["provider"]
        credential_id = campaign["credential_id"] or ""
        api_key = None
        if credential_id:
            if self._secrets is None:
                raise ValueError("credential storage is not configured")
            reference = self._secrets.reference(credential_id)
            if reference.provider != provider:
                raise ValueError(f"credential provider {reference.provider} does not match campaign provider {provider}")
            api_key = self._secrets.retrieve(credential_id)
        try:
            scenario = self._scenarios.load(selected["filename"])
            result = ScenarioRunner(
                model=self._model_factory(provider, campaign["model"], api_key),
                trace_store=self._runs,
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
            self._campaigns.associate_child_run(campaign_id, ordinal, child_run_id=self._runs.latest_run_id())
        except Exception as exc:
            self._campaigns.associate_child_run(campaign_id, ordinal, error=type(exc).__name__)
        return self._with_scenario_details(self._campaigns.get(campaign_id))
