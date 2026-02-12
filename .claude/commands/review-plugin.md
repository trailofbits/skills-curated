---
name: review-plugin
description: >-
  Reviews a plugin for quality, correctness, and CLAUDE.md conformance.
  Fixes all issues found. Use after importing or modifying a plugin.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
---

# /review-plugin — Deep Plugin Quality Review

Review a plugin directory for quality, correctness, and conformance to
project standards. Finds issues, fixes them, and reports what changed.

**Argument:** A plugin directory path (e.g., `plugins/ghidra-headless/`).

## Process

1. Run all checks across five categories (A–E below)
2. Categorize each finding as **BLOCK** (must fix) or **WARN** (should fix)
3. Fix all BLOCK findings immediately
4. Fix WARN findings where the fix is clear and safe
5. Re-run linters after fixes to confirm clean
6. Report a summary of what was found and what was fixed

## Category A: Script Correctness

### Shell scripts (`*.sh`)

For each shell script in the plugin:

1. **`set -euo pipefail`** — must be present after the shebang. BLOCK if missing.

2. **shellcheck** — run `shellcheck -x {script}`. BLOCK on errors, WARN on warnings.

3. **Bash 3.2 array safety** — search for `"${arr[@]}"` patterns where `arr`
   might be empty. Under Bash 3.2 with `set -u`, expanding an empty array is
   an unbound variable error. The fix is `${arr[@]+"${arr[@]}"}`. BLOCK if found.

   ```bash
   # How to detect: look for array expansions that aren't guarded
   grep -n '"${[A-Z_a-z]*\[@\]}"' {script}
   ```

   Exceptions: arrays that are guaranteed non-empty by prior logic (e.g.,
   populated in a required argument parser that exits on empty).

4. **Unbound variable references** — any `${VAR}` where `VAR` might not be
   set should use `${VAR:-}` (empty default) or `${VAR:-default}`. BLOCK if
   the variable comes from the environment without a prior check.

5. **Executable bit** — `ls -la {script}` should show `x` permission.
   BLOCK if missing. Fix: `chmod +x {script}`.

6. **shfmt** — run `shfmt -i 2 -ci -d {script}`. BLOCK if formatting issues
   found. Fix: `shfmt -i 2 -ci -w {script}`.

### Python scripts (`*.py`)

For each Python script:

1. **PEP 723 inline metadata** — if the script has dependencies (imports
   beyond stdlib), it must have a `# /// script` metadata block. WARN if
   missing.

2. **ruff check** — run `ruff check {script}`. BLOCK on errors.

3. **ruff format** — run `ruff format --check {script}`. WARN on formatting
   issues. Fix: `ruff format {script}`.

### Java files (`*.java`)

1. **Duplicate utility methods** — if the same method name appears in
   multiple files, verify the implementations are identical. BLOCK if
   implementations differ (the behavior is inconsistent). Fix: unify them.

2. **Null safety** — scan for patterns like `obj.method()` where `obj`
   comes from a lookup that can return null without a prior null check.
   WARN if found.

## Category B: Documentation Accuracy

Cross-reference documentation against actual files and script behavior.

1. **Referenced paths exist** — every file path mentioned in SKILL.md and
   README.md must point to an actual file in the plugin. BLOCK if a
   referenced file doesn't exist.

   ```bash
   # Extract paths from markdown and verify
   grep -oE '\{baseDir\}/[^ )`"]+' plugins/{name}/skills/*/SKILL.md
   ```

2. **Output file names match** — if documentation says a script produces
   `output.json`, read the script and verify it actually writes that
   filename. BLOCK if names don't match.

3. **Feature descriptions match behavior** — for each capability described
   in SKILL.md, read the corresponding script and verify it actually does
   what's claimed. BLOCK if a documented feature doesn't exist in the code
   or works differently than described.

4. **Prerequisites are accurate** — tools listed as prerequisites should
   actually be invoked by the scripts. WARN if a listed prerequisite isn't
   used, or if an unlisted tool is required.

## Category C: CLAUDE.md Conformance

Check against project standards from CLAUDE.md.

1. **Frontmatter `name`** — must match the plugin directory name (kebab-case,
   ≤64 chars). BLOCK if mismatched.

2. **Frontmatter `description`** — must be third-person ("Analyzes X", not
   "I help with X") with specific trigger conditions. WARN if vague.

3. **"When to Use" section** — must exist with concrete scenarios (not
   generic phrases like "when you need help"). BLOCK if missing, WARN if
   too vague.

4. **"When NOT to Use" section** — must exist with concrete scenarios.
   BLOCK if missing, WARN if too vague.

5. **SKILL.md length** — must be under 500 lines, or overflow content must
   be split into `references/`. WARN if over 500 lines.

6. **No leftover platform references** — search for `$CODEX_HOME`,
   `$PI_HOME`, `<path-to-skill>`, and similar patterns. BLOCK if found.

   ```bash
   grep -rE '\$CODEX_HOME|\$PI_HOME|<path-to-skill>' plugins/{name}/
   ```

7. **No stubs or placeholders** — search for `TODO`, `FIXME`, `XXX`,
   `placeholder`, `TBD`. BLOCK if found in shipped content (comments in
   scripts are WARN).

8. **README.md exists** — must include install command, prerequisites (if
   any), and credits to the original source. BLOCK if README.md is missing.

9. **plugin.json `name` matches SKILL.md `name`** — BLOCK if mismatched.

## Category D: Code Consistency

1. **Duplicate functions** — if the same function name appears in multiple
   files within the plugin, verify implementations are identical. BLOCK if
   they differ.

2. **Naming conventions** — variable and function names should be consistent
   within the plugin (no mix of `snake_case` and `camelCase` in shell,
   no mix of naming styles in the same language). WARN if inconsistent.

3. **Error messages include context** — error messages should say what
   operation failed and on what input (not just "Error" or "Failed").
   WARN if context is missing.

## Category E: Security

Go beyond what the automated scanner catches.

1. **No hardcoded credentials** — search for patterns like `token=`,
   `password=`, `api_key=`, `secret=` with literal values. BLOCK if found.

   ```bash
   grep -rEi 'token=["'"'"'][^$]|password=["'"'"'][^$]|api_key=["'"'"'][^$]|secret=["'"'"'][^$]' plugins/{name}/
   ```

2. **Output directory safety** — scripts should write output to a directory
   the user controls (passed as argument or current directory), not to
   fixed system locations like `/tmp/fixed-name` or `~/.config/`. WARN if
   scripts write to hardcoded locations outside the working directory.

3. **No unguarded eval** — search for `eval`, `exec()`, `subprocess.call`
   with `shell=True`, or similar dynamic execution. WARN if found without
   a clear justification in a comment.

   ```bash
   grep -rn 'eval \|eval(|exec(|shell=True' plugins/{name}/
   ```

## Output Format

After completing all checks and fixes, report:

```
## Review Summary: {plugin name}

### Findings

| # | Category | Severity | Description | Status |
|---|----------|----------|-------------|--------|
| 1 | A: Scripts | BLOCK | Missing set -euo pipefail in run.sh | Fixed |
| 2 | B: Docs | WARN | README lists unused prerequisite | Fixed |
| ... | | | | |

### Stats
- BLOCK: {n} found, {n} fixed
- WARN: {n} found, {n} fixed
- Clean: {yes/no — all BLOCKs resolved and linters pass}
```
