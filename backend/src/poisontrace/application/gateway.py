from dataclasses import dataclass
from copy import deepcopy

from poisontrace.domain import ToolCall, ToolDefinition
from poisontrace.domain import InvestigationCall, EvidenceTool, EvidenceObservation
from poisontrace.application.ports import EvidenceSession


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

    def evidence_call_policy(self, call, definitions, manifest=None):
        matches = [t for t in definitions if (t.server_id, t.name) == (call.server_id, call.name)]
        if len(matches) != 1:
            return ToolOutcome(False, "unknown_or_colliding_identity")
        if manifest is not None:
            reason = manifest.reason(matches[0], definitions)
            if reason != "approved_definition":
                return ToolOutcome(False, reason)
        if not matches[0].read_only:
            return ToolOutcome(False, "tool_not_read_only")
        return ToolOutcome(True, "approved_definition" if manifest is not None else "discovered_read_only_tool")

    async def invoke_evidence(self, call: InvestigationCall, definitions: tuple[EvidenceTool, ...],
                              session: EvidenceSession, *, manifest=None) -> EvidenceObservation:
        outcome = self.evidence_call_policy(call, definitions, manifest)
        if not outcome.allowed:
            raise PermissionError(outcome.reason)
        return await session.invoke(call)


class EvidenceManifest:
    """Exact qualified definition comparison, with no metadata fallback."""

    def __init__(self, approved):
        self.approved = deepcopy(tuple(approved))
        identities = [(t.server_id, t.name) for t in self.approved]
        if len(set(identities)) != len(identities):
            raise ValueError("colliding approved identity")
        for tool in self.approved:
            definition = tool.definition
            if (not tool.server_id or not tool.name or not tool.description or not tool.read_only
                or definition.get("name") != tool.name or definition.get("description") != tool.description
                or definition.get("inputSchema") != tool.input_schema
                or definition.get("annotations", {}).get("readOnlyHint") is not True
                or tool.input_schema.get("type") != "object"):
                raise ValueError("invalid approved definition")

    def reason(self, tool, discovered):
        identity = (tool.server_id, tool.name)
        if sum((t.server_id, t.name) == identity for t in discovered) != 1:
            return "colliding_identity"
        approved = next((t for t in self.approved if (t.server_id, t.name) == identity), None)
        if approved is None:
            return "unapproved_identity"
        return "approved_definition" if tool == approved else "definition_mismatch"
