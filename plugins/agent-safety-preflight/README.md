# Agent Safety Preflight

Preflight AI coding-agent runs before granting repository, shell, package-script, MCP, deployment, or credential-adjacent scope.

## Installation

```text
/plugin install trailofbits/skills-curated/plugins/agent-safety-preflight
```

## Usage

Use this skill before approving Claude Code, Codex, Cursor, OpenCode, Roo Code, Cline, or other coding-agent work in a real repository. It asks the agent to produce a short preflight receipt that names the planned scope, repo surfaces inspected, Green/Yellow/Red risk level, allowed commands, rollback path, and what still needs human approval.

The plugin has no hooks, no scripts, and no network calls. It is guidance-only so reviewers can audit it quickly and teams can adapt it to their existing approval flow.

## Example receipt

```markdown
Agent/tool: Claude Code
Planned run: update CI workflow and package scripts
Repo surfaces inspected: package.json, .github/workflows/*, .env.example, .mcp.json
Risk level: Yellow
Allowed commands: npm test, npm run lint
Blocked without human approval: deploy, secrets, token creation, external service changes
Rollback: revert branch commit before merge
```

## Credits

Original free source package: [el-zachariah/ai-agent-safety-starter-pack](https://github.com/el-zachariah/ai-agent-safety-starter-pack). This curated plugin keeps the core guidance self-contained and omits paid-product links, hooks, and scripts.
