"""Framework-independent contracts exchanged across application seams."""

from typing import Literal, NotRequired, TypedDict


Provider = Literal["fake", "gemini", "openai"]
RunMode = Literal["clean", "poisoned", "defended"]


class RunRequest(TypedDict, total=False):
    session_id: str
    scenario_id: str
    mode: RunMode
    provider: Provider
    model: str
    credential_id: str


class RunResponse(TypedDict):
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
    attack_success: bool
    benign_task_success: bool
    execution_time_ms: float
    injection_verdict: str
    task_outcome: str
    tool_call_status: str


class RunTraceEvent(TypedDict):
    kind: str
    data: dict[str, str]


class RunDetailResponse(RunResponse):
    status: str
    recommendation: str
    benign_task_success: bool
    attack_success: bool
    execution_time_ms: float
    system_error: bool
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
