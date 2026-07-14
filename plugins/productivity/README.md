# Productivity

General workflow skills, not code-specific. Four skills for working with
agents day-to-day: stress-testing plans through relentless interviews, handing
work off between sessions, learning topics over multiple sessions, and writing
better skills.

## Installation

```
/plugin install productivity@skills-curated
```

## Skills

| Skill | Invocation | Description |
|-------|------------|-------------|
| `grilling` | Model-invoked | Interviews you relentlessly about a plan, decision, or idea until every branch of the decision tree is resolved. Say "grill me on this" or ask to stress-test your thinking. |
| `handoff` | `/productivity:handoff` | Compacts the current conversation into a handoff document (saved to the OS temp directory) so a fresh agent can continue the work. Takes an optional argument describing what the next session will focus on. |
| `teach` | `/productivity:teach` | Teaches you a skill or concept over multiple sessions, using the current directory as a stateful teaching workspace: a mission statement, HTML lessons, learning records, curated resources, and reference documents. |
| `writing-great-skills` | `/productivity:writing-great-skills` | Reference for writing and editing skills well — the vocabulary (leading words, context load, progressive disclosure) and failure modes (premature completion, sediment, no-ops) that make a skill predictable. |

`handoff`, `teach`, and `writing-great-skills` are user-invoked
(`disable-model-invocation: true`): they add zero context load and fire only
when you type them.

## Credits

Imported from [mattpocock/skills](https://github.com/mattpocock/skills)
(`skills/productivity`) by [Matt Pocock](https://github.com/mattpocock).
Licensed under the [MIT License](LICENSE).

Modifications from the original:

- Removed Codex-specific `agents/openai.yaml` files
- Dropped the `grill-me` alias skill (in Claude Code, `/productivity:grilling`
  invokes the grilling skill directly)
- Rewrote `grilling` from first person ("interview me") to agent-facing
  instructions
- Moved companion documents into `references/` and switched links to
  `{baseDir}` paths
- Added "When to Use" / "When NOT to Use" sections and `allowed-tools`
