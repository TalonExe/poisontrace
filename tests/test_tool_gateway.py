from poisontrace.domain import ToolCall, ToolDefinition
from poisontrace.gateway import ToolGateway


def test_gateway_blocks_tool_definition_that_differs_from_approved_manifest():
    discovered = ToolDefinition("disable_account", "Disable an account.")
    approved = ToolDefinition("disable_account", "Disable an account only after analyst approval.")
    gateway = ToolGateway(approved_manifest=(approved,), high_impact_tools={"disable_account"})

    outcome = gateway.invoke(ToolCall("disable_account", {"account_id": "acct-001"}), (discovered,))

    assert outcome.allowed is False
    assert outcome.reason == "tool_definition_mismatch"


def test_gateway_requires_approval_for_matching_high_impact_tool():
    tool = ToolDefinition("disable_account", "Disable an account.")
    gateway = ToolGateway(approved_manifest=(tool,), high_impact_tools={"disable_account"})

    outcome = gateway.invoke(ToolCall("disable_account", {"account_id": "acct-001"}), (tool,))

    assert outcome.allowed is False
    assert outcome.reason == "approval_required"


def test_gateway_allows_high_impact_tool_after_explicit_approval():
    tool = ToolDefinition("disable_account", "Disable an account.")
    gateway = ToolGateway(approved_manifest=(tool,), high_impact_tools={"disable_account"})

    outcome = gateway.invoke(
        ToolCall("disable_account", {"account_id": "acct-001"}),
        (tool,),
        approval_actor="test-analyst",
    )

    assert outcome.allowed is True
    assert outcome.reason == "approved"
    assert outcome.approval_actor == "test-analyst"
