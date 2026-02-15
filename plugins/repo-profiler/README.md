# repo-profiler

Analyzes a remote GitHub repository and generates Claude Code configuration
files (CLAUDE.md, hooks, review skill) tailored to the codebase's patterns,
tooling, and bug history.

## Install

```
/plugin install trailofbits/skills-curated/plugins/repo-profiler
```

## Prerequisites

- GitHub CLI (`gh`) authenticated with access to the target repo
- Git on your PATH
- Python 3 on your PATH

## Usage

```
/profile-repo https://github.com/owner/repo
```

Or ask conversationally:

> Profile this repository for Claude Code: https://github.com/owner/repo

## What It Generates

Files are written into `.claude/` inside a local clone:

- **CLAUDE.md** — Project instructions: stack, conventions, commands,
  known problem areas, anti-patterns
- **hooks/hooks.json** — Hookify rules matching the repo's tooling and
  preventing known anti-patterns
- **skills/repo-review/SKILL.md** — Review checklist weighted by actual
  bug frequency, with directory-specific guidance

## How It Works

1. **Fetch & Inventory** — Clones the repo, builds file tree and language
   distribution
2. **Tooling Detection** — Reads config files to detect linters, formatters,
   test frameworks, CI pipelines
3. **History Analysis** — Analyzes 90 days of merged PRs and commits to find
   bug hotspots and recurring patterns
4. **Code Sampling** — Reads representative source files to understand
   architecture, conventions, and error handling
5. **Generation** — Synthesizes findings into the three output files
