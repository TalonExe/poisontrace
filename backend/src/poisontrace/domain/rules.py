import re


INJECTION_MARKER = "COMPROMISED"


_SENSITIVE_OUTPUT_FIELD = re.compile(
    r"(?i)(?:[\"']?)(api[_ -]?key|access[_ -]?token|secret|password|recovery[_ -]?code)"
    r"(?:[\"']?)(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,}\]]+)"
)


def redact_sensitive_output(raw_output: str) -> str:
    return _SENSITIVE_OUTPUT_FIELD.sub(r"\1\2[REDACTED]", raw_output)
