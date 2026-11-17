"""Offline workflow substitute. It is not a model-effectiveness experiment."""
from poisontrace.domain import InvestigationCall, InvestigationDecision, InvestigationStep


class ScriptedInvestigationModel:
    model_name = "scripted-soc-v2"
    prompt_version = "evidence-loop-v2"
    settings = {"deterministic": True}
    prompt_snapshot = {"workflow": "evidence-loop-v2", "provider_prompt": None}

    async def next_step(self, case, tools, observations):
        for name in ("get_alert", "get_evidence", "get_context"):
            if not any(observation.tool_name == name for observation in observations):
                tool = next(tool for tool in tools if tool.name == name)
                return InvestigationStep(call=InvestigationCall(tool.server_id, tool.name, {"case_id": case.case_id}))
        records = [record for observation in observations for record in observation.result["records"]]
        auth = next(record for record in records if "unauthorized_access" in record)
        context = next(record for record in records if "authorized_maintenance" in record)
        malicious = auth["unauthorized_access"] is True and context["authorized_maintenance"] is False
        critical = context.get("critical_impact", context.get("privileged_account", False))
        priority = ("P1" if critical else "P2") if malicious else ("P3" if context.get("telemetry_followup_required", False) else "P4")
        refs = tuple(record["evidence_id"] for record in records)
        return InvestigationStep(decision=InvestigationDecision(
            "malicious" if malicious else "benign", priority,
            "escalate" if malicious else "close",
            "Returned event and context records establish unapproved activity. Escalate for incident response review."
            if malicious else "Returned event and context records establish no unapproved activity. Close the incident alert; retain any noted telemetry follow-up.", refs))
