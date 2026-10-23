# PoisonTrace context

PoisonTrace evaluates how malicious MCP tool metadata can influence an AI-assisted SOC investigation. The shared domain vocabulary is maintained in [DOMAIN_GLOSSARY.md](DOMAIN_GLOSSARY.md). Implementation decisions and build order are maintained in [IMPLEMENTATION_BRIEF.md](IMPLEMENTATION_BRIEF.md). Module interfaces and test seams are maintained in [ARCHITECTURE.md](ARCHITECTURE.md).

## Domain boundary

The first investigation is a synthetic authentication-alert triage case. The agent gathers evidence and produces a recommendation. Protected actions require explicit approval. All attack outcomes are judged against observable security-policy violations, and every experiment has an ordered trace.
