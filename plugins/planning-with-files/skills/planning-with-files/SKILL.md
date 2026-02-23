---
name: planning-with-files
description: >-
  Implements file-based planning for complex multi-step tasks. Creates
  task_plan.md, findings.md, and progress.md as persistent working memory. Use
  when starting tasks requiring >5 tool calls, multi-phase projects, research,
  or any work where losing track of goals and progress would be costly.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# Planning with Files

Use persistent markdown files as working memory on disk.

## Quick Start

1. **Create planning files** -- use `/plan` or create manually from
   [templates](references/templates.md)
2. **Create `task_plan.md`** with goal, phases, and key questions
3. **Create `findings.md`** for research and decisions
4. **Create `progress.md`** for session logging
5. **Re-read the plan before decisions** -- refreshes goals in attention
6. **Update after each phase** -- mark status, log errors

## When to Use

- Multi-step tasks (3+ phases)
- Research projects requiring many searches
- Building or creating projects with multiple files
- Tasks spanning many tool calls (>10)
- Any work where losing track of goals would be costly
- Tasks that may span multiple sessions

## When NOT to Use

- Simple questions or quick lookups
- Single-file edits with obvious scope
- Tasks completable in under 5 tool calls
- Conversational exchanges without implementation

## Core Pattern

```
Context Window = RAM (volatile, limited)
Filesystem     = Disk (persistent, unlimited)

Anything important gets written to disk.
```

After many tool calls, the original goal drifts out of the attention
window. Reading `task_plan.md` brings it back. This is the single
most important pattern in file-based planning.

## File Purposes

| File | Purpose | When to Update |
|------|---------|----------------|
| `task_plan.md` | Phases, progress, decisions | After each phase completes |
| `findings.md` | Research, discoveries, decisions | After ANY discovery |
| `progress.md` | Session log, test results | Throughout the session |

All three files go in the **project root**, not the plugin directory.

## Critical Rules

### 1. Create Plan First

Never start a complex task without `task_plan.md`. This is
non-negotiable. The plan is your persistent memory.

### 2. The 2-Action Rule

After every 2 search, browse, or read operations, immediately save
key findings to `findings.md`. Multimodal content (images, browser
results, PDF contents) does not persist in context -- capture it as
text before it is lost.

### 3. Read Before Decide

Before any major decision, re-read `task_plan.md`. This pushes
goals and context back into the recent attention window, counteracting
the "lost in the middle" effect that occurs after ~50 tool calls.

```
[Original goal -- far away in context, forgotten]
...many tool calls...
[Recently read task_plan.md -- gets ATTENTION]
→ Now make the decision with goals fresh in context
```

### 4. Update After Act

After completing any phase:

- Mark phase status: `in_progress` -> `complete`
- Log any errors encountered in the Errors table
- Note files created or modified in `progress.md`

### 5. Log ALL Errors

Every error goes in `task_plan.md`. Include the attempt number and
resolution. This builds knowledge and prevents repeating failures.

```markdown
## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| FileNotFoundError | 1 | Created default config |
| API timeout | 2 | Added retry logic |
```

### 6. Never Repeat Failures

If an action failed, the next action must be different. Track what
you tried and mutate the approach.

```
if action_failed:
    next_action != same_action
```

## 3-Strike Error Protocol

```
ATTEMPT 1: Diagnose & Fix
  -> Read error carefully
  -> Identify root cause
  -> Apply targeted fix

ATTEMPT 2: Alternative Approach
  -> Same error? Try a different method
  -> Different tool? Different library?
  -> NEVER repeat the exact same failing action

ATTEMPT 3: Broader Rethink
  -> Question assumptions
  -> Search for solutions
  -> Consider updating the plan

AFTER 3 FAILURES: Escalate to User
  -> Explain what you tried (with attempt log)
  -> Share the specific error
  -> Ask for guidance
```

## Read vs Write Decision Matrix

| Situation | Action | Reason |
|-----------|--------|--------|
| Just wrote a file | Don't read it | Content still in context |
| Viewed image/PDF | Write findings NOW | Multimodal content doesn't persist |
| Browser returned data | Write to file | Screenshots don't persist |
| Starting new phase | Read plan/findings | Re-orient if context is stale |
| Error occurred | Read relevant file | Need current state to fix |
| Resuming after gap | Read all planning files | Recover full state |

## 5-Question Reboot Test

If you can answer these from your planning files, context is solid:

| Question | Answer Source |
|----------|--------------|
| Where am I? | Current phase in `task_plan.md` |
| Where am I going? | Remaining phases |
| What's the goal? | Goal statement in plan |
| What have I learned? | `findings.md` |
| What have I done? | `progress.md` |

## Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| State goals once and forget | Re-read plan before decisions |
| Hide errors and retry silently | Log every error to plan file |
| Stuff everything in context | Store large content in files |
| Start executing immediately | Create plan file FIRST |
| Repeat failed actions | Track attempts, mutate approach |
| Create files in plugin directory | Create files in project root |

## References

- [Templates](references/templates.md) -- starter templates for all
  three planning files
- [Principles](references/principles.md) -- context engineering
  principles behind this approach
- [Examples](references/examples.md) -- concrete examples and error
  recovery patterns
