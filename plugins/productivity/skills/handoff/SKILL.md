---
name: handoff
description: >-
  Compacts the current conversation into a handoff document so a fresh agent
  can continue the work in a new session.
disable-model-invocation: true
argument-hint: "What will the next session be used for?"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash
---

# Handoff

Write a handoff document summarising the current conversation so a fresh agent
can continue the work. Save it to the temporary directory of the user's OS —
not the current workspace.

Include a "suggested skills" section in the document, which suggests skills
that the next agent should invoke.

Do not duplicate content already captured in other artifacts (specs, plans,
ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally
identifiable information.

If the user passed arguments, treat them as a description of what the next
session will focus on and tailor the document accordingly.

## When to Use

- The conversation is long and the work needs to continue in a fresh session
- Handing the current task to another agent (or another person's agent) that
  has no access to this conversation
- Preserving hard-won context — decisions made, dead ends explored, current
  state — before it is lost to context compaction

## When NOT to Use

- The work is finished; write a commit message, PR description, or docs
  instead
- The context is already fully captured in artifacts (a plan file, an issue,
  a spec) — point the next session at those directly
