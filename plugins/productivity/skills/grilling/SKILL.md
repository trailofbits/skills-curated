---
name: grilling
description: >-
  Interviews the user relentlessly about a plan, decision, or idea until every
  branch of the decision tree is resolved. Use when the user wants to
  stress-test their thinking, sharpen a plan or design before acting, or uses
  any 'grill' trigger phrase (e.g. "grill me on this").
allowed-tools:
  - Read
  - Grep
  - Glob
  - AskUserQuestion
---

# Grilling

Interview the user relentlessly about every aspect of the plan, decision, or
idea until you reach a shared understanding. Walk down each branch of the
decision tree, resolving dependencies between decisions one-by-one. For each
question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before
continuing. Asking multiple questions at once is bewildering.

If a *fact* can be found by exploring the environment (filesystem, tools,
etc.), look it up rather than asking. The *decisions*, though, are the
user's — put each one to them and wait for their answer.

Do not act on the plan until the user confirms a shared understanding has been
reached.

## When to Use

- The user wants to stress-test a plan, design, or decision before committing
  to it
- A feature request or design has unresolved ambiguities that should be
  surfaced and decided before implementation
- The user explicitly asks to be grilled, interviewed, or challenged on their
  thinking

## When NOT to Use

- The user has already made their decisions and wants execution — grilling
  after the fact is friction, not rigor
- The user is brainstorming and needs divergent options generated; grilling
  converges on decisions rather than generating alternatives
- The question is a simple factual one that exploration or a direct answer
  resolves
