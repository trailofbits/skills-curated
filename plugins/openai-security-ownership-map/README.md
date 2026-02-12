# Security Ownership Map

Analyze git repositories to build a security ownership topology (people-to-file), compute bus factor and sensitive-code ownership, and export CSV/JSON for graph databases and visualization. Trigger only when the user explicitly wants a security-oriented ownership or bus-factor analysis grounded in git history (for example: orphaned sensitive code, security maintainers, CODEOWNERS reality checks for risk, sensitive hotspots, or ownership clusters). Do not trigger for general maintainer lists or non-security ownership questions.

## Installation

```
/plugin install trailofbits/skills-curated/plugins/openai-security-ownership-map
```


## What It Covers

- Overview
- Requirements
- Workflow
- Quick start
- Sensitivity rules
- Output artifacts
- LLM query helper
- Basic security queries

## Credits

Originally from [OpenAI's curated skills catalog](https://github.com/openai/skills/tree/main/skills/.curated/security-ownership-map).
Converted to Claude Code plugin format for the Trail of Bits
curated skills marketplace.
