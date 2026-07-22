# Design: /update-skill Command

## Problem

Imported plugins diverge from their upstream sources over time. Our import
process transforms files (path substitution, frontmatter rewriting, platform
cleanup, restructuring), so upstream and downstream aren't 1:1 diffable.
We need a way to review upstream changes intelligently and selectively
downstream them.

## Input

```
/update-skill last30days
```

Plugin name only. Upstream URL resolved from marketplace.json `author.url`.

## Phases

### Phase 1 -- Resolve & Fetch

- Look up plugin in marketplace.json -> `author.url`
- Parse GitHub owner/repo from the URL
- Determine import date from `git log -- plugins/{name}/`
- Fetch current upstream tree via `fetch_github_tree.py`
- Get upstream commit log since import date via `gh api`

### Phase 2 -- Analyze & Report

- Categorize commits by conventional-commit prefix (feat/fix/docs/chore)
- Map upstream files to downstream equivalents (handle renames)
- Read both versions of modified files, summarize changes
- Present structured report: overview, bug fixes, new features, docs, file map

### Phase 3 -- Interactive Triage

Walk the user through each change group conversationally:

1. Bug fixes first (highest priority) -- show what each fix addresses, which
   files are affected, ask: apply, skip, or discuss further?
2. New features -- show what each adds, new files/deps, ask: apply, skip,
   or discuss?
3. Other modified files -- show summary, ask how to handle

For each approved change, note the upstream files and transform strategy.

### Phase 4 -- Apply & PR

For approved changes:

- Apply transforms (path substitution, platform cleanup, frontmatter
  preservation -- same pipeline as import-skill)
- Lint scripts (ruff, shellcheck)
- Run security scan
- Bump patch version in plugin.json and marketplace.json
- Create branch (update/{name}), commit, push, open PR
- PR body: what was updated, what was skipped and why, upstream commit range

## What it does NOT do

- Does not auto-apply without user approval
- Does not modify files until Phase 4 (after triage)

## Where it lives

`.claude/commands/update-skill.md`

## Tools needed

Bash, Read, Write, Edit, Grep, Glob -- same as import-skill.
