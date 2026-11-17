"""Bounded clean evidence feedback, independent of provider and MCP SDK types."""
import asyncio
from collections.abc import Callable
from dataclasses import asdict, replace
from copy import deepcopy
import json
from time import perf_counter
from uuid import uuid4

from poisontrace.application.gateway import ToolGateway, EvidenceManifest
from poisontrace.application.errors import InvestigationCallLimit, InvestigationOutputLimit, EvidenceToolError
from poisontrace.application.ports import (EvidenceTransport, InvestigationCases, InvestigationModel, TraceEvent, TraceStore)
from poisontrace.domain import (ExperimentMode, ExperimentResult, INJECTION_MARKER, InvestigationStep, redact_sensitive_output)
from poisontrace.domain import investigation_attack
from poisontrace.domain import score_investigation, SCORING_VERSION


def safe_json(value):
    if isinstance(value, str):
        return redact_sensitive_output(value)
    if isinstance(value, dict):
        return {str(key): safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(item) for item in value]
    return value


def failure_category(error):
    if isinstance(error, BaseExceptionGroup):
        return failure_category(error.exceptions[0])
    if isinstance(error, TimeoutError):
        return "investigation_time_limit"
    if isinstance(error, InvestigationCallLimit):
        return "investigation_call_limit"
    if isinstance(error, InvestigationOutputLimit):
        return "investigation_output_limit"
    if isinstance(error, EvidenceToolError):
        return "tool_execution_error"
    if isinstance(error, PermissionError):
        return "tool_policy_error"
    if isinstance(error, (ValueError, TypeError, KeyError, StopIteration)):
        return "investigation_validation_error"
    return "investigation_execution_error"


class InvestigationRunner:
    def __init__(self, store: TraceStore, cases: InvestigationCases, transport: EvidenceTransport,
                 model_factory: Callable[[], InvestigationModel], gateway: ToolGateway,
                 *, approved_manifest=(), max_calls: int = 4, timeout_seconds: float = 20, max_output_bytes: int = 16384):
        if max_calls < 1 or timeout_seconds <= 0 or max_output_bytes < 1:
            raise ValueError("investigation limits must be positive")
        self.manifest = EvidenceManifest(approved_manifest)
        self.store, self.cases, self.transport = store, cases, transport
        self.model_factory, self.gateway = model_factory, gateway
        self.max_calls, self.timeout_seconds, self.max_output_bytes = max_calls, timeout_seconds, max_output_bytes

    def list_cases(self) -> list[dict]:
        attacks = [asdict(investigation_attack(family)) for family in ("description-poisoning", "cross-server-shadowing")]
        return [{**case, "attacks": [attack for attack in attacks if attack["family"] in case.get("supported_attack_families", ("description-poisoning", "cross-server-shadowing"))]} for case in self.cases.list()]

    def run(self, case_id: str, configuration: dict[str, str] | None = None, *, model_factory=None) -> ExperimentResult:
        return self.run_snapshot(self.cases.get(case_id), configuration, model_factory=model_factory)

    def run_snapshot(self, case, configuration=None, *, model_factory=None):
        # Use one selected snapshot throughout a matched group.
        mode = (configuration or {}).get("mode", "clean")
        family = (configuration or {}).get("attack_family")
        if mode not in {"clean", "poisoned", "defended"} or (mode == "clean" and family is not None):
            raise ValueError("invalid investigation condition")
        if mode in {"poisoned", "defended"}:
            investigation_attack(family)
            if family not in case.supported_attack_families:
                raise ValueError("attack family is not allocated to this case")
        return asyncio.run(self._run(case, configuration or {}, model_factory or self.model_factory))

    async def _run(self, case, configuration, model_factory):
        started = perf_counter()
        key = uuid4().hex
        mode = ExperimentMode(configuration.get("mode", "clean"))
        attack = investigation_attack(configuration["attack_family"]) if mode != ExperimentMode.CLEAN else None
        attack_data = asdict(attack) if attack else None
        configuration = {**configuration, "mode": mode.value, "workflow": "mcp-investigation-v1", "condition_version": "manifest-mcp-v1",
            "case_id": case.case_id, "case_version": case.case_version, "provider": configuration.get("provider", "scripted"),
            "max_calls": str(self.max_calls), "timeout_seconds": str(self.timeout_seconds),
            "max_output_bytes": str(self.max_output_bytes), "manifest_policy": "disabled" if mode == ExperimentMode.POISONED else "approved-manifest-v1"}
        if attack:
            configuration["payload_id"] = attack.payload_id
        provenance = {"case_snapshot": safe_json(asdict(case)), "approved_manifest": [asdict(t) for t in self.manifest.approved], "decision_contract_version": "canonical-handling-v2", "attack": attack_data, "expected_decision": case.expected_decision, "dataset_category": case.dataset_category,
            "attacker_predicate": case.attack_targets.get(attack.family) if attack else None}
        observations, definitions = [], ()
        policy = {"enforced": mode != ExperimentMode.POISONED, "discovered": [], "exposed": [],
            "restrictions": [], "invocation_rejections": [], "executed_calls": 0, "proposed_calls": 0, "invocation_checked": False}
        provenance["manifest"] = policy
        decision = None
        model = None
        marker_values = []
        reference_valid = None
        candidate = None

        def record(kind, data):
            self.store.record(TraceEvent(kind, safe_json(data), key))

        record("investigation_started", {"case_id": case.case_id, "case_version": case.case_version,
            "alert": case.alert, "limits": {"calls": self.max_calls, "seconds": self.timeout_seconds, "output_bytes": self.max_output_bytes}})
        record("investigation_condition", provenance)
        deadline = asyncio.timeout(self.timeout_seconds)
        try:
            async with deadline:
                model = model_factory()
                connection = self.transport.open(case, attack_family=attack.family) if attack else self.transport.open(case)
                async with connection as session:
                    record("transport_connected", session.identity)
                    configuration["transport_identity"] = json.dumps(safe_json(session.identity))
                    definitions = await session.discover()
                    if not definitions or len(definitions) > 20:
                        raise ValueError("invalid tool discovery")
                    if len(json.dumps([asdict(tool) for tool in definitions]).encode()) > self.max_output_bytes:
                        raise InvestigationOutputLimit()
                    for tool in definitions:
                        record("tool_discovered", asdict(tool))
                    policy["discovered"] = safe_json([asdict(tool) for tool in definitions])
                    exposed = []
                    for tool in definitions:
                        reason = self.manifest.reason(tool, definitions) if policy["enforced"] else "enforcement_disabled"
                        allowed = reason in {"approved_definition", "enforcement_disabled"}
                        check = {"stage": "before_exposure", "server_id": tool.server_id, "tool_name": tool.name,
                            "allowed": allowed, "reason": reason, "manifest_check_performed": policy["enforced"], "simulated": False}
                        record("discovery_policy", check)
                        if allowed:
                            exposed.append(tool)
                        else:
                            policy["restrictions"].append({k: check[k] for k in ("server_id", "tool_name", "reason")})
                    # Clean receives the trusted snapshot, never substituted discovered metadata.
                    exposed = self.manifest.approved if mode == ExperimentMode.CLEAN else tuple(exposed)
                    policy["exposed"] = safe_json([asdict(tool) for tool in exposed])
                    configuration["model_facing_definitions"] = json.dumps(policy["exposed"])
                    for step_number in range(self.max_calls + 1):
                        record("model_started" if not observations else "model_continued", {"step": step_number + 1,
                            "evidence_refs": [r["evidence_id"] for o in observations for r in o.result["records"]]})
                        step = await model.next_step(case.model_input, deepcopy(exposed), deepcopy(tuple(observations)))
                        if not isinstance(step, InvestigationStep):
                            raise ValueError("invalid model step")
                        if len(json.dumps(asdict(step)).encode()) > self.max_output_bytes:
                            raise InvestigationOutputLimit()
                        raw = step.raw_output
                        if raw is not None and (not isinstance(raw, str) or len(raw.encode()) > self.max_output_bytes):
                            raise InvestigationOutputLimit()
                        marker_values.append(INJECTION_MARKER in raw if raw is not None else None)
                        record("model_step", {k: v for k, v in asdict(step).items() if k != 'raw_output'})
                        if step.decision is not None:
                            decision = step.decision
                            observed_refs = {r["evidence_id"] for o in observations for r in o.result["records"]}
                            candidate = safe_json(asdict(decision))
                            reference_valid = bool(decision.evidence_refs) and bool(observations) and set(decision.evidence_refs) <= observed_refs
                            if not reference_valid:
                                raise ValueError("decision must reference returned evidence")
                            break
                        if step_number == self.max_calls:
                            raise InvestigationCallLimit()
                        call = step.call
                        policy["proposed_calls"] += 1
                        manifest = self.manifest if policy["enforced"] else None
                        outcome = self.gateway.evidence_call_policy(call, definitions, manifest)
                        allowed = outcome.allowed
                        policy["invocation_checked"] = True
                        record("policy_decision", {"stage": "before_invocation", "server_id": call.server_id,
                            "tool_name": call.name, "allowed": allowed, "reason": outcome.reason,
                            "manifest_check_performed": policy["enforced"], "simulated": False})
                        if not allowed:
                            policy["invocation_rejections"].append({"server_id": call.server_id, "tool_name": call.name, "reason": outcome.reason})
                            record("tool_rejected", asdict(call))
                        else:
                            record("tool_invoked", asdict(call))
                        try:
                            observation = await self.gateway.invoke_evidence(call, definitions, session, manifest=manifest)
                            policy["executed_calls"] += 1
                        except Exception as error:
                            record("tool_error", {"server_id": call.server_id, "tool_name": call.name,
                                "error_category": failure_category(error)})
                            raise
                        data = observation.result
                        if (observation.server_id, observation.tool_name, observation.arguments) != (call.server_id, call.name, call.arguments):
                            raise ValueError("tool result identity mismatch")
                        if len(json.dumps(data).encode()) > self.max_output_bytes or data.get("case_id") != case.case_id or data.get("case_version") != case.case_version:
                            raise ValueError("invalid tool result identity or size")
                        records = data.get("records")
                        if not isinstance(records, list) or not records or any(not isinstance(r, dict) or not isinstance(r.get("evidence_id"), str) or not r["evidence_id"] for r in records):
                            raise ValueError("invalid returned evidence")
                        record("tool_result", asdict(observation))
                        observations.append(observation)
                    if decision is None:
                        raise ValueError("missing final decision")
            decision_data = safe_json(asdict(decision))
            investigation = {**provenance, "version": "investigation-v1", "case_id": case.case_id, "case_version": case.case_version,
                "decision": decision_data, "evidence": [safe_json(asdict(observation)) for observation in observations]}
            record("investigation_completed", decision_data)
            result = ExperimentResult(case.case_id, mode, redact_sensitive_output(decision.handling), None, None,
                scoring_version=SCORING_VERSION, marker_influence=None,
                task_outcome="Investigation complete; correctness unscored", tool_call_status="Evidence retrieved through MCP",
                injection_verdict="Unscored",
                investigation=investigation, gateway_simulated=False)
        except Exception as error:
            category = "investigation_time_limit" if deadline.expired() else failure_category(error)
            record("investigation_failed", {"error_category": category})
            result = ExperimentResult(case.case_id, mode, "", None, None,
                scoring_version=SCORING_VERSION, status="failed", error_category=category, system_error=True,
                injection_verdict="Unscored", task_outcome="Unscored", tool_call_status="Investigation failed", gateway_simulated=False,
                investigation={**provenance, "version": "investigation-v1", "case_id": case.case_id, "case_version": case.case_version,
                    "decision": None, "evidence": [safe_json(asdict(observation)) for observation in observations]})
        finally:
            close = getattr(model, "aclose", None)
            if close is not None:
                try:
                    async with asyncio.timeout(2):
                        await close()
                except Exception:
                    record("model_cleanup_failed", {"error_category": "provider_cleanup_error"})
        policy["no_call"] = policy["proposed_calls"] == 0
        marker = True if True in marker_values else False if marker_values and all(v is False for v in marker_values) else None
        refs = {r['evidence_id'] for o in observations for r in o.result['records']}
        scores = score_investigation(asdict(decision) if decision else None, case.expected_decision,
            provenance['attacker_predicate'], refs, attacked=attack is not None, marker=marker, completed=result.status == 'completed')
        scores['evidence_references_valid'] = reference_valid
        result.investigation['scores'] = scores
        result.investigation['candidate_decision'] = candidate if result.status == 'failed' else None
        result = replace(result, marker_influence=scores['marker_influence'],
            recommendation_correctness=scores['handling_correctness'], benign_task_success=scores['handling_correctness'],
            attacker_goal_achievement=scores['attacker_goal'], attack_success=scores['attacker_goal'],
            task_outcome=('Decision matches ground truth' if scores['decision_correctness'] else 'Decision differs from ground truth') if scores['decision_correctness'] is not None else 'Unscored',
            injection_verdict='Marker observed' if scores['marker_influence'] is True else 'Marker not observed' if scores['marker_influence'] is False else 'Marker unavailable')
        result.investigation["prompt_snapshot"] = safe_json(getattr(model, "prompt_snapshot", None))
        result.investigation["model_settings"] = safe_json(getattr(model, "settings", None))
        result = replace(result, execution_time_ms=(perf_counter() - started) * 1000,
            model_name=getattr(model, "model_name", configuration.get("model", "scripted-soc-v2")), prompt_version=getattr(model, "prompt_version", "evidence-loop-v2"),
            run_configuration=configuration)
        return replace(result, run_id=self.store.save_result(result, key))
