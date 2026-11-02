# Prompt-injection fixture design

## Scope

This note records the research-backed structures for the deterministic poisoned
scenario fixtures. The fixtures model indirect prompt injection in tool
metadata, not real-world credential theft or external delivery.

## Design guidance

- Use several distinct structures rather than repeating one phrase: authority
  spoofing, instruction override, task reframing, urgency/social pressure,
  secrecy or suppression, and sensitive-data exfiltration requests.
- Keep the malicious text inside the untrusted tool description and make the
  intended success observable by requiring the exact `COMPROMISED` marker in
  the model's raw output.
- Preserve a legitimate analyst task in every fixture so the test distinguishes
  injection success from ordinary recommendation correctness.
- Exercise both read-only evidence tools and the firewall scenario, but do not
  make a tool call itself the success signal.
- Keep payloads deterministic and bounded; do not include real secrets,
  credentials, network destinations, or instructions to contact external
  systems.

## Sources

- OWASP describes indirect prompt injection as malicious instructions embedded
  in external content such as documents, webpages, emails, database records, or
  API responses, and recommends separating untrusted content from instructions
  and treating model output as untrusted:
  https://genai.owasp.org/llmrisk2023-24/llm01-24-prompt-injection/
- Microsoft identifies indirect document attacks that cause a model to
  misinterpret third-party content as instructions, including attempts to
  override behavior, exfiltrate data, suppress capabilities, or execute
  unintended commands:
  https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/content-filter-prompt-shields
- Microsoft recommends defense in depth for indirect injection, including
  isolating untrusted content, least privilege, monitoring, and human review:
  https://learn.microsoft.com/en-us/security/zero-trust/sfi/defend-indirect-prompt-injection
