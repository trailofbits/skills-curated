---
name: agent-safety-preflight
version: 1.0.0
description: |
  Preflights AI coding-agent runs before granting repository, shell,
  package-script, MCP, deployment, or credential-adjacent scope. Use when a
  Claude Code, Codex, Cursor, OpenCode, Roo Code, Cline, or similar agent is
  about to edit a real repo, run commands, wire tools, or touch secrets-adjacent
  files and the operator needs a concise Green/Yellow/Red approval receipt.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Agent Safety Preflight

Preflight an AI coding-agent run before it receives broad repo, shell, package-script, MCP, deployment, or credential-adjacent scope. The goal is not to block useful automation; it is to make the risk boundary explicit before a fast agent turns a vague task into file edits, shell commands, or external changes.

## When to Use

- Before approving an AI coding agent to edit a real repository.
- Before running package scripts, test scripts, migrations, deploy commands, or generated shell commands suggested by an agent.
- Before connecting an agent to MCP servers, browser tools, API-backed tools, or local services.
- Before letting an agent work near `.env`, secret templates, deployment config, CI credentials, package manager tokens, or cloud/provider settings.
- When reviewing a PR, issue, or task handoff and you need a short receipt explaining what was inspected and what remains out of scope.

## When NOT to Use

- Pure reading tasks where the agent cannot write files, run shell commands, or call tools.
- Throwaway local experiments with no credentials, no network side effects, and no shared repo state.
- After-the-fact incident response; use a full security review or incident process instead.
- As a substitute for code review, dependency review, secret scanning, or organization-specific approval policy.

## Quick Start

1. **State the planned agent run.** Name the agent/tool, repository, branch, task, and requested permissions.
2. **Inspect the repo surfaces that change risk.** Check package scripts, lockfiles, CI workflows, agent/plugin config, MCP config, dev containers, deploy config, `.env*` examples, migration scripts, and generated commands.
3. **Classify the run.**
   - **Green:** read-only or narrow edits, no package scripts, no credentials, no deploy or external service changes.
   - **Yellow:** package scripts, local services, MCP/tool connectors, generated shell commands, workflow changes, or broad repo edits.
   - **Red:** credentials, token creation, deploys, production data, cloud/provider mutation, payment/billing settings, destructive commands, or unclear third-party code execution.
4. **Write the receipt before acting.** Use the format below. If the level is Yellow or Red, explicitly list what requires human approval.
5. **Run only the allowed commands.** If the task expands, stop and write a new receipt instead of silently broadening scope.
6. **Leave rollback evidence.** Record the branch, commit, backup, or revert plan that restores state if the agent run goes wrong.

## Preflight Receipt Format

```markdown
Agent/tool:
Repository/branch:
Planned run:
Requested permissions:
Repo surfaces inspected:
Risk level: Green | Yellow | Red
Allowed commands/actions:
Blocked without human approval:
External services/network/deploy touched:
Secrets or credentials touched:
Rollback/recovery path:
Reasoning:
```

## Repo Surfaces to Check

- `package.json`, `pnpm-lock.yaml`, `package-lock.json`, `yarn.lock`, `pyproject.toml`, `uv.lock`, `requirements*.txt`, `Cargo.toml`, `go.mod`, `Makefile`, `justfile`, `Taskfile.yml`.
- `.github/workflows/*`, `.gitlab-ci.yml`, `Dockerfile`, `docker-compose*.yml`, `.devcontainer/*`, deployment manifests, migration directories.
- `.claude/*`, `.claude-plugin/*`, `commands/*`, `agents/*`, `.cursor/rules/*`, `.cursorrules`, Roo/Cline/OpenCode/Codex config, MCP config such as `.mcp.json`.
- `.env`, `.env.*`, `.env.example`, secret templates, cloud/provider config, payment or billing integration config.
- Generated scripts or instructions copied from an issue, chat, marketplace package, or plugin README.

## Rationalizations to Reject

- "It is just a test script." Test scripts can run package lifecycle hooks, start services, mutate fixtures, or call external systems.
- "The agent will ask before doing anything risky." Pre-approval must define risk before the agent is inside a broad tool loop.
- "The MCP server is local." Local MCP tools can still access files, browsers, credentials, shells, or networked services.
- "No real secret is committed." Secret-adjacent templates, provider config, and token-creation steps still change blast radius.
- "We can revert later." Revert does not undo leaked secrets, sent requests, deployed changes, deleted remote state, or third-party side effects.
- "The marketplace package is popular." Popularity is not review; inspect hooks, commands, scripts, and requested scopes.

## Example: Yellow Receipt

```markdown
Agent/tool: Claude Code
Repository/branch: example/app on feature/agent-ci-fix
Planned run: update CI and package scripts for lint/test reliability
Requested permissions: repo edit + local shell
Repo surfaces inspected: package.json, pnpm-lock.yaml, .github/workflows/ci.yml, .env.example, .mcp.json
Risk level: Yellow
Allowed commands/actions: pnpm install --frozen-lockfile, pnpm test, pnpm lint
Blocked without human approval: npm publish, deploy, secret creation, workflow token changes, external service mutation
External services/network/deploy touched: package registry read only during install
Secrets or credentials touched: none; .env.example only
Rollback/recovery path: revert feature branch commit before merge
Reasoning: package scripts and CI changes can execute code, but no production credentials or deploy actions are in scope.
```

## Optional Scanner Source

For teams that want a concrete starter scanner, the free source package at `https://github.com/el-zachariah/ai-agent-safety-starter-pack` includes a lightweight repo preflight scanner and examples. Treat it as optional supporting material, not as a requirement for this skill.
