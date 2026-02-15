# repo-profiler Design

## Problem

Engineers using Claude Code need project-specific guidance to work autonomously
in a codebase. Today this requires manually writing CLAUDE.md, configuring
hooks, and building review skills. This skill automates that by analyzing a
repository and generating the configuration files.

## What It Does

Analyzes a remote GitHub repository and generates a complete set of Claude Code
configuration files that teach an agent how to work in that codebase.

**Input:** GitHub URL via `/profile-repo <github-url>`

**Output:** Files written into `.claude/` inside a local clone of the repo:

```
.claude/
├── CLAUDE.md              # Project-specific instructions and coding standards
├── hooks/
│   └── hooks.json         # Hookify rules preventing known anti-patterns
└── skills/
    └── repo-review/
        └── SKILL.md       # Custom review skill weighted by bug history
```

**Consumers:** Other engineers on the team and automated agent pipelines.

## Approach

Agent-driven with structured prompts. The SKILL.md orchestrates the agent
through a multi-phase workflow. Two helper scripts handle mechanical collection
(cloning, PR/commit fetching). The agent does all synthesis and file generation.

Builds on `claude-automation-recommender`'s reference files for tooling
detection patterns rather than re-cataloging hooks and plugins.

## Plugin Structure

```
plugins/repo-profiler/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── repo-profiler/
│       ├── SKILL.md
│       ├── references/
│       │   ├── analysis-guide.md
│       │   └── output-templates.md
│       └── scripts/
│           ├── fetch_repo.sh
│           └── collect_history.sh
├── commands/
│   └── profile-repo.md
└── README.md
```

Replaces `coderabbit-config-generator` in the marketplace.

## Analysis Phases

### Phase 1 — Fetch & Inventory

- Clone via `gh repo clone` to a local directory
- Build file tree, language distribution, directory layout
- Repo age, size, contributor count

### Phase 2 — Tooling & Standards Detection

- Read config files: pyproject.toml, package.json, Cargo.toml, Makefile,
  Dockerfile, CI configs
- Detect linters, formatters, test frameworks from configs
- Read existing CLAUDE.md, CONTRIBUTING.md, .editorconfig
- Reference `claude-automation-recommender` patterns for detection heuristics

### Phase 3 — History & Pattern Analysis

- Merged PRs from last 90 days via `gh pr list`
- Commit messages via `git log`, categorized by type
- Bug-fix concentration by directory
- Reverted commits
- Issue labels and recurring themes

### Phase 4 — Code Sampling

- Entry points (main files, route definitions, CLI entry points)
- Module boundaries and import patterns
- Error handling patterns
- Test patterns (what does a typical test look like?)
- Sample representative files across major directories

After each phase the agent writes findings to `analysis-notes.md` in the
output directory for visibility.

## Output Files

### CLAUDE.md

- Language/framework stack and versions
- Directory structure explanation
- Coding conventions detected from the codebase
- Build/test/lint commands from CI and config files
- Known problem areas with bug-fix frequency data
- Anti-patterns specific to this repo from bug history

### hooks/hooks.json

- Formatter/linter hooks matching detected tooling
- Protection hooks for sensitive files and lock files
- Repo-specific guards from bug patterns

### skills/repo-review/SKILL.md

- Review checklist weighted by actual bug frequency
- Directory-specific review guidance
- Architecture enforcement rules (import direction, layer boundaries)
- "Rationalizations to reject" section from historical failure patterns

## Script Responsibilities

| Task | Owner | Reason |
|------|-------|--------|
| Clone repo | fetch_repo.sh | Mechanical, deterministic |
| Collect PRs + commits | collect_history.sh | Mechanical, uses gh CLI |
| Read configs | Agent | Needs judgment on relevance |
| Detect tooling | Agent | Pattern recognition |
| Analyze bugs | Agent | Interprets PR context |
| Sample code | Agent | Architectural inference |
| Generate all output | Agent | Synthesis is the core value |

## Non-Goals

- Does not push or commit — leaves files for user review
- Does not run generated hooks/skills to verify they work
- Does not analyze repos the user lacks `gh` access to
- Does not generate MCP server configs (references claude-automation-recommender)
- Does not do incremental re-profiling — each run is fresh

## Prerequisites

- `gh` CLI authenticated with access to the target repo
- Git available on PATH
