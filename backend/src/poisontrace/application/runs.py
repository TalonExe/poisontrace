"""Run orchestration and recorded evidence behind an application interface."""

from poisontrace.application.contracts import RunDetailResponse, RunRequest, RunResponse
from poisontrace.application.errors import ScenarioNotFound
from poisontrace.application.ports import ModelFactory, RunStore, SecretsAdapter, UsableScenarioLookup
from poisontrace.domain import ExperimentMode, ExperimentResult, Scenario
from poisontrace.application.gateway import ToolGateway
from poisontrace.application.execution import ScenarioRunner


class RunApplicationService:
    def __init__(
        self,
        store: RunStore,
        scenarios: UsableScenarioLookup,
        model_factory: ModelFactory,
        secrets: SecretsAdapter | None = None,
    ) -> None:
        self.store = store
        self.scenarios = scenarios
        self._model_factory = model_factory
        self.secrets = secrets

    def _scenario(self, scenario_id: str) -> Scenario:
        try:
            return self.scenarios.load_usable(scenario_id)
        except KeyError as exc:
            raise ScenarioNotFound(str(scenario_id)) from exc

    def list(self) -> list[RunResponse]:
        return [self.summary(run_id) for run_id in self.store.run_ids()]

    def get(self, run_id: int) -> RunDetailResponse:
        result = self.store.result_for(run_id)
        events = self.store.events_for(run_id)
        return {
            **self.summary(run_id, result),
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

    def create(self, payload: RunRequest) -> RunResponse:
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
        model = self._model_factory(provider, model_name, api_key)
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
        return self.summary(self.store.latest_run_id(), result)

    def summary(self, run_id: int, result: ExperimentResult | None = None) -> RunResponse:
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
