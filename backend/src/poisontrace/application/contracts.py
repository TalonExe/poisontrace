"""Framework-independent contracts exchanged across application seams."""

from typing import Literal, NotRequired, TypedDict


Provider = Literal["fake", "gemini", "openai", "scripted"]
RunMode = Literal["clean", "poisoned", "defended"]


class RunRequest(TypedDict, total=False):
    attack_family: str
    workflow: str
    case_id: str
    session_id: str
    scenario_id: str
    mode: RunMode
    provider: Provider
    model: str
    credential_id: str


class RunResponse(TypedDict):
    investigation_scores: dict | None
    workflow: str
    system_error: bool
    status: str
    error_category: str | None
    defense_evidence_version: str
    manifest_check_performed: bool | None
    definition_mismatch: bool | None
    call_rejected: bool | None
    policy_reason: str | None
    proposed_tool_name: str | None
    clean_call_legitimate: bool | None
    gateway_simulated: bool | None
    scoring_version: str
    marker_influence: bool | None
    attacker_goal_achievement: bool | None
    recommendation_correctness: bool | None
    expected_recommendation: str | None
    attacker_target_recommendation: str | None
    id: str
    run_id: int
    scenario_id: str
    mode: str
    model: str
    result: str
    time: str
    tone: str
    mark: str
    injection_verdict: str
    task_outcome: str
    tool_call_status: str


class RunMetrics(TypedDict):
    attack_success: bool | None
    benign_task_success: bool | None
    execution_time_ms: float
    injection_verdict: str
    task_outcome: str
    tool_call_status: str


class RunTraceEvent(TypedDict):
    kind: str
    data: dict[str, object]


class RunDetailResponse(RunResponse):
    investigation: dict | None
    condition_version: str
    model_facing_definitions: list[dict[str, object]] | None
    recommendation: str
    benign_task_success: bool | None
    attack_success: bool | None
    execution_time_ms: float
    unauthorised_tool_call: bool
    run_configuration: dict[str, str]
    trace: list[RunTraceEvent]
    metrics: RunMetrics


class CampaignRequest(TypedDict, total=False):
    provider: Provider
    model: str
    credential_id: str


class CredentialWriteRequest(TypedDict):
    provider: str
    secret: str
    label: NotRequired[str]


class CredentialResponse(TypedDict):
    credential_id: str
    provider: str
    label: str
    masked: str


SECRET_FIELD_NAMES = frozenset({"secret", "api_key", "apiKey", "credential_secret", "plaintext"})
