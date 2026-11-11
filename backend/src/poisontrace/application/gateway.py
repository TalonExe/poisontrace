from dataclasses import dataclass

from poisontrace.domain import ToolCall, ToolDefinition


@dataclass(frozen=True)
class ToolOutcome:
    allowed: bool
    reason: str
    approval_actor: str | None = None


class ToolGateway:
    def __init__(
        self,
        approved_manifest: tuple[ToolDefinition, ...],
        high_impact_tools: set[str],
        enforce_manifest: bool = True,
    ) -> None:
        self.approved_manifest = {tool.name: tool for tool in approved_manifest}
        self.high_impact_tools = high_impact_tools
        self.enforce_manifest = enforce_manifest

    def invoke(
        self,
        call: ToolCall,
        discovered_tools: tuple[ToolDefinition, ...],
        approval_actor: str | None = None,
    ) -> ToolOutcome:
        approved = self.approved_manifest.get(call.name)
        discovered = next((tool for tool in discovered_tools if tool.name == call.name), None)
        if self.enforce_manifest and (approved is None or discovered != approved):
            return ToolOutcome(False, "tool_definition_mismatch")
        if call.name in self.high_impact_tools:
            if approval_actor is None:
                return ToolOutcome(False, "approval_required")
            return ToolOutcome(True, "approved", approval_actor)
        return ToolOutcome(True, "allowed")
