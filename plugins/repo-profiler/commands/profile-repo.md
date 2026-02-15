---
name: profile-repo
description: "Analyze a GitHub repository and generate Claude Code configuration files"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
---

# /profile-repo -- Generate a Claude Code Profile for a Repository

Analyze a GitHub repository and generate a complete set of Claude Code
configuration files (CLAUDE.md, hooks, review skill) tailored to the
codebase.

## Argument

A GitHub URL or `owner/repo` shorthand. Examples:

- `https://github.com/owner/repo`
- `owner/repo`

## Instructions

Execute the full repo-profiler workflow described in
`{baseDir}/skills/repo-profiler/SKILL.md`, using the provided URL as
the target repository.

Follow all six phases in order:
1. Fetch & Inventory
2. Tooling & Standards Detection
3. History & Pattern Analysis
4. Code Sampling
5. Generate Output
6. Summary
