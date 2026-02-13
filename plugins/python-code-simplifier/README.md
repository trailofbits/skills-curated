# Python Code Simplifier

Simplifies and refines Python code for clarity, consistency, and maintainability while preserving all functionality. Focuses on recently modified code unless instructed otherwise.

Adapted from Anthropic's [code-simplifier](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/code-simplifier) agent with Python-specific standards replacing the original TypeScript/React guidance.

## Install

```
/plugin install trailofbits/skills-curated/plugins/python-code-simplifier
```

## What It Does

After writing or modifying Python code, this skill reviews recent changes and applies refinements:

- Flattens unnecessary nesting with guard clauses and early returns
- Improves naming consistency (`snake_case` functions, `PascalCase` classes, `UPPER_SNAKE_CASE` constants)
- Adds type annotations to public function signatures
- Sorts imports (stdlib, third-party, local)
- Replaces dense comprehensions or chained expressions with clearer alternatives
- Removes redundant code and unnecessary comments
- Consolidates related logic without over-abstracting

All changes preserve exact functionality — only how the code reads changes, never what it does.

## Credits

- **Source:** [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/code-simplifier)
- **Author:** Anthropic
- **Adaptation:** TypeScript/React standards replaced with Python equivalents
- **License:** Not specified
