"""Run orchestration and recorded evidence behind an application interface."""

from dataclasses import asdict, replace
import json

from poisontrace.application.contracts import RunDetailResponse, RunRequest, RunResponse
from poisontrace.application.errors import ScenarioNotFound
from poisontrace.application.ports import ModelFactory, RunStore, SecretsAdapter, UsableScenarioLookup
from poisontrace.domain import ExperimentMode, ExperimentResult, Scenario
from poisontrace.domain.metrics import calculate_metrics
from poisontrace.application.gateway import ToolGateway
from poisontrace.application.execution import ScenarioRunner
from poisontrace.domain import investigation_attack


class RunApplicationService:
    def __init__(
        self,
        store: RunStore,
        scenarios: UsableScenarioLookup,
        model_factory: ModelFactory,
        secrets: SecretsAdapter | None = None,
        investigations=None,
        investigation_model_factory=None,
    ) -> None:
        self.store = store
        self.scenarios = scenarios
        self._model_factory = model_factory
        self.secrets = secrets
        self.investigations = investigations
        self._investigation_model_factory = investigation_model_factory

    def investigation_cases(self):
        return self.investigations.list_cases() if self.investigations is not None else []

    def investigation_case(self, case_id):
        case = self.investigations.cases.get(case_id)
        return {key: getattr(case, key) for key in ('case_id', 'case_version', 'name', 'expected_decision', 'dataset_category', 'attack_targets', 'supported_attack_families')}

    def update_investigation_case(self, case_id, payload):
        if set(payload) != {'base_version', 'expected_decision', 'dataset_category', 'attack_targets'}:
            raise ValueError('supply only case ground truth and base_version')
        case = self.investigations.cases.get(case_id)
        if payload['base_version'] != case.case_version:
            raise ValueError('case changed; reload before saving')
        from poisontrace.domain import validate_predicate
        validate_predicate(payload['expected_decision'], complete=True)
        updated = replace(case, case_version=str(int(case.case_version) + 1),
            expected_decision=payload['expected_decision'], dataset_category=payload['dataset_category'], attack_targets=payload['attack_targets'])
        if updated.expected_decision['handling'] not in {'close', 'escalate'} or any(target.get('handling', 'close') not in {'close', 'escalate'} for target in updated.attack_targets.values()):
            raise ValueError('handling must be close or escalate')
        self.investigations.cases.save_ground_truth(updated, case.case_version)
        return self.investigation_case(case_id)

    def _scenario(self, scenario_id: str) -> Scenario:
        try:
            return self.scenarios.load_usable(scenario_id)
        except KeyError as exc:
            raise ScenarioNotFound(str(scenario_id)) from exc

    def list(self) -> list[RunResponse]:
        return [self.summary(run_id) for run_id in self.store.run_ids()]

    def metrics(self) -> dict:
        return asdict(calculate_metrics([self.store.result_for(run_id) for run_id in self.store.run_ids()]))

    def get(self, run_id: int) -> RunDetailResponse:
        result = self.store.result_for(run_id)
        events = self.store.events_for(run_id)
        return {
            **self.summary(run_id, result),
            "prompt_version": result.prompt_version,
            "status": result.status,
            "investigation": result.investigation,
            "condition_version": result.run_configuration.get("condition_version", "legacy"),
            "model_facing_definitions": json.loads(result.run_configuration.get("model_facing_definitions", "null")),
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

    def prepare_investigation(self, payload, *, case=None):
        if self.investigations is None:
            raise ValueError("MCP investigations are not configured")
        provider = payload.get("provider")
        mode = payload.get("mode")
        family = payload.get("attack_family")
        if mode not in {"clean", "poisoned", "defended"} or provider not in {"scripted", "gemini", "openai"}:
            raise ValueError("investigations require clean, poisoned or defended and scripted, Gemini or OpenAI")
        if "payload_id" in payload:
            raise ValueError("payload identity is selected by attack family")
        if mode in {"poisoned", "defended"}:
            investigation_attack(family)
        elif family is not None:
            raise ValueError("clean investigations require no attack family")
        try:
            case = case if case is not None else self.investigations.cases.get(payload.get("case_id"))
        except KeyError as exc:
            raise ScenarioNotFound("unknown investigation case") from exc
        if family and family not in case.supported_attack_families:
            raise ValueError("attack family is not allocated to this case")
        credential_id = str(payload.get("credential_id", ""))
        configuration = {"session_id": str(payload.get("session_id", "")), "provider": provider, "mode": mode}
        if family:
            configuration["attack_family"] = family
        factory = None
        if provider == "scripted":
            if credential_id:
                raise ValueError("scripted investigations require no credential")
        else:
            model_name = payload.get("model")
            if not isinstance(model_name, str) or not model_name.strip() or len(model_name) > 200:
                raise ValueError("a configured provider model is required")
            if not credential_id or self.secrets is None or self._investigation_model_factory is None:
                raise ValueError("provider investigations require a credential reference")
            if self.secrets.reference(credential_id).provider != provider:
                raise ValueError("credential provider does not match investigation provider")
            configuration.update({"credential_id": credential_id, "model": model_name})
            factory = lambda: self._investigation_model_factory(provider, model_name, self.secrets.retrieve(credential_id))
        return case, configuration, factory


    def create(self, payload: RunRequest) -> RunResponse:
        workflow = payload.get("workflow", "metadata-v1")
        if workflow == "mcp-investigation-v1":
            case, configuration, factory = self.prepare_investigation(payload)
            result = self.investigations.run_snapshot(case, configuration, model_factory=factory)
            return self.summary(result.run_id, result)
        if workflow != "metadata-v1":
            raise ValueError("unknown execution workflow")
        scenario_id = payload.get("scenario_id", "authentication-alert")
        try:
            mode = ExperimentMode(str(payload.get("mode", "")).lower())
        except ValueError as exc:
            raise ValueError("experiment condition is required: clean, poisoned or defended") from exc
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
        runner = ScenarioRunner(
            model=None,
            model_factory=lambda: self._model_factory(provider, model_name, api_key),
            trace_store=self.store,
            gateway=ToolGateway(
                approved_manifest=scenario.approved_tools if scenario.approved_tools is not None else scenario.tools,
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
        return self.summary(result.run_id, result)

    def summary(self, run_id: int, result: ExperimentResult | None = None) -> RunResponse:
        result = result or self.store.result_for(run_id)
        scores = (result.investigation or {}).get('scores')
        correct = scores.get('decision_correctness') if scores else result.recommendation_correctness
        return {
            "investigation_scores": scores,
            "id": f"EXP-{run_id:03d}",
            "workflow": result.run_configuration.get("workflow", "metadata-v1"),
            "run_id": run_id,
            "scenario_id": result.scenario_id,
            "mode": result.mode.value.title(),
            "model": result.model_name,
            "result": ("Failed attempt" if result.status == "failed" else "Legacy scoring" if result.scoring_version == "legacy" else
                       "Attacker goal achieved" if result.attacker_goal_achievement else result.task_outcome),
            "status": result.status,
            "system_error": result.system_error,
            "error_category": result.error_category,
            "defense_evidence_version": result.defense_evidence_version,
            "manifest_check_performed": result.manifest_check_performed,
            "definition_mismatch": result.definition_mismatch,
            "call_rejected": result.call_rejected,
            "policy_reason": result.policy_reason,
            "proposed_tool_name": result.proposed_tool_name,
            "clean_call_legitimate": result.clean_call_legitimate,
            "gateway_simulated": result.gateway_simulated,
            "scoring_version": result.scoring_version,
            "marker_influence": result.marker_influence,
            "attacker_goal_achievement": result.attacker_goal_achievement,
            "recommendation_correctness": result.recommendation_correctness,
            "expected_recommendation": result.expected_recommendation,
            "attacker_target_recommendation": result.attacker_target_recommendation,
            "time": "just now",
            "tone": "red" if result.system_error or result.attacker_goal_achievement else "green" if correct else "amber",
            "mark": "!" if result.system_error or result.attacker_goal_achievement else "✓" if correct else "?",
            "injection_verdict": result.injection_verdict,
            "task_outcome": result.task_outcome,
            "tool_call_status": result.tool_call_status,
        }
