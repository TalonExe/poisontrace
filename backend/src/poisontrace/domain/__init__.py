"""Public benchmark values and rules. Calculations live in domain.metrics."""

from poisontrace.domain.values import AgentDecision, ExperimentMode, ExperimentResult, Scenario, ToolCall, ToolDefinition
from poisontrace.domain.rules import INJECTION_MARKER, redact_sensitive_output
from poisontrace.domain.values import (InvestigationInput, SyntheticCase, EvidenceTool,
    InvestigationCall, EvidenceObservation, InvestigationDecision, InvestigationStep)

__all__ = ["AgentDecision", "ExperimentMode", "ExperimentResult", "Scenario", "ToolCall", "ToolDefinition", "INJECTION_MARKER", "redact_sensitive_output",
    "InvestigationInput", "SyntheticCase", "EvidenceTool", "InvestigationCall", "EvidenceObservation", "InvestigationDecision", "InvestigationStep", "InvestigationAttack", "investigation_attack", "score_investigation", "validate_predicate", "SCORING_VERSION"]

from poisontrace.domain.investigation_attacks import InvestigationAttack, investigation_attack

from poisontrace.domain.investigation_scoring import score_investigation, validate_predicate, SCORING_VERSION
