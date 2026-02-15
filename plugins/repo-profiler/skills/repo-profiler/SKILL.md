---
name: repo-profiler
description: "Analyzes a remote GitHub repository and generates Claude Code configuration files (CLAUDE.md, hooks, review skill) tailored to the codebase's patterns, tooling, and bug history. Use when the user wants to profile a repo, set up Claude Code for a new project, or generate agent guidance for a codebase."
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
---

# Repository Profiler

Analyzes a GitHub repository and generates a complete Claude Code configuration:
project-specific CLAUDE.md, hookify rules, and a custom review skill — all
derived from the repo's actual code, tooling, and bug history.

## When to Use

- Setting up Claude Code for a new repository
- Generating agent guidance for autonomous workflows in a codebase
- Creating project-specific review checklists based on real bug patterns
- Onboarding engineers to a codebase with tailored Claude Code config

## When NOT to Use

- The repository is brand new with no PR history (less than 10 merged PRs)
- You only need to edit an existing CLAUDE.md (just edit it directly)
- You want MCP server recommendations (use claude-automation-recommender instead)
- The repository is private and you don't have `gh` access to it

## Prerequisites

- GitHub CLI (`gh`) authenticated with access to the target repository
- Git on your PATH
- Python 3 on your PATH

## Workflow

### Phase 1: Fetch & Inventory

Clone the repository and build a structural inventory.

**Step 1:** Run the fetch script:

```bash
{baseDir}/scripts/fetch_repo.sh --url "<GITHUB_URL>" --dest ./repo-profile-workdir
```

Parse the JSON manifest from stdout. Record `repo`, `dest`,
`default_branch`, `contributor_count`, and `file_count`.

**Step 2:** Build a language distribution. From the clone directory, count
files by extension:

```bash
find ./repo-profile-workdir -type f -not -path '*/.git/*' \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20
```

**Step 3:** List top-level directory structure:

```bash
ls -1d ./repo-profile-workdir/*/
```

**Step 4:** Write Phase 1 findings to `./repo-profile-workdir/.claude/analysis-notes.md`:

```markdown
# Analysis Notes

## Phase 1: Inventory
- **Repo:** {repo}
- **Default branch:** {branch}
- **Contributors:** {count}
- **Files:** {count}
- **Primary languages:** {top 3 by file count}
- **Directory layout:** {brief description}
```

### Phase 2: Tooling & Standards Detection

Read config files to detect existing tooling and standards.

**Step 1:** Check for these files in the clone root. Read each one that
exists. See `{baseDir}/references/analysis-guide.md` § "Config File Lookup
Table" for what each file tells you.

Priority files to check:
- `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Gemfile`
- `.github/workflows/*.yml`
- `Makefile`, `Dockerfile`, `docker-compose.yml`
- `.pre-commit-config.yaml`
- `CLAUDE.md`, `CONTRIBUTING.md`, `.editorconfig`
- Linter configs: `.eslintrc*`, `eslint.config.*`, `ruff.toml`, `.rubocop.yml`
- `tsconfig.json`

**Step 2:** For each detected tool, extract:
- Tool name and version
- Run command (from CI, Makefile, or package.json scripts)
- Key settings (strictness, enabled rules)

**Step 3:** Append Phase 2 findings to `analysis-notes.md`:

```markdown
## Phase 2: Tooling
- **Build system:** {tool}
- **Package manager:** {tool}
- **Linter:** {tool} (command: `{cmd}`)
- **Formatter:** {tool} (command: `{cmd}`)
- **Test framework:** {tool} (command: `{cmd}`)
- **CI:** {GitHub Actions / CircleCI / etc.}
- **Existing CLAUDE.md:** {yes/no — if yes, note key contents}
- **Existing CONTRIBUTING.md:** {yes/no — if yes, note key contents}
```

### Phase 3: History & Pattern Analysis

Analyze PR history and commit patterns to find bug hotspots.

**Step 1:** Derive `owner/repo` from the clone's origin URL:

```bash
git -C ./repo-profile-workdir remote get-url origin
```

**Step 2:** Run the history collection script:

```bash
{baseDir}/scripts/collect_history.sh \
  --repo "<owner/repo>" \
  --repo-path ./repo-profile-workdir \
  --days 90 \
  --out-dir ./repo-profile-workdir/.claude
```

Parse the JSON manifest. Record PR count, commit count, revert count.

**Step 3:** Read `pr-data.json` and categorize PRs. See
`{baseDir}/references/analysis-guide.md` § "PR Categorization" for the
prefix-to-category mapping.

For each PR, determine:
- Category (bug fix, feature, refactor, etc.)
- Which directories it likely affects (from title and body)
- Bug pattern keywords (shallow copy, silent failure, etc.)

**Step 4:** Identify bug hotspots — directories with 3+ bug-fix PRs.

**Step 5:** Read `reverts.txt`. For each revert, note what was reverted
and why.

**Step 6:** Append Phase 3 findings to `analysis-notes.md`:

```markdown
## Phase 3: History
- **PRs analyzed:** {count} ({bug_fix_count} bug fixes, {feature_count} features, ...)
- **Commits:** {count}
- **Reverts:** {count}
- **Bug hotspots:**
  - {directory}: {count} fixes — {pattern_summary}
  - {directory}: {count} fixes — {pattern_summary}
- **Common bug patterns:** {list of recurring keywords/themes}
```

### Phase 4: Code Sampling

Read source files to understand architecture and conventions.

**Step 1:** Identify entry points. Look for:
- `main.py`, `app.py`, `index.ts`, `main.rs`, `main.go`, `app.rb`
- `src/index.*`, `src/main.*`, `cmd/*/main.go`
- Route/API definition files

Read each entry point found.

**Step 2:** For each major directory (from Phase 1), read 2-3 representative
files. See `{baseDir}/references/analysis-guide.md` § "Code Sampling" for
what to prioritize and what to look for.

**Step 3:** Read one test file per major directory to understand test patterns.

**Step 4:** Append Phase 4 findings to `analysis-notes.md`:

```markdown
## Phase 4: Code Sampling
- **Architecture:** {layered / monolithic / microservices / etc.}
- **Import style:** {absolute / relative}
- **Layer order:** {e.g., handlers → services → models → utils}
- **Error handling:** {exceptions / Result types / error codes}
- **Logging:** {library and pattern}
- **Naming:** {function_style, FileNaming, test_naming}
- **Test pattern:** {framework, fixture approach, mock strategy}
- **Test location:** {colocated / separate tests/ directory}
```

### Phase 5: Generate Output

Synthesize all findings into the three output files using the templates
in `{baseDir}/references/output-templates.md`.

**Step 1:** Create the output directory structure:

```bash
mkdir -p ./repo-profile-workdir/.claude/hooks
mkdir -p ./repo-profile-workdir/.claude/skills/repo-review
```

**Step 2:** Generate `CLAUDE.md`. Use the template from
`{baseDir}/references/output-templates.md` § "CLAUDE.md Template".

Fill in every section from the analysis notes. Key rules:
- Only include conventions that are **consistently followed** in the codebase
- Only include problem areas with **3+ bug fixes** in the analysis window
- Only include anti-patterns that **actually caused bugs** in this repo
- Use concrete commands detected from CI/configs, not guesses
- If an existing CLAUDE.md was found, **merge** its contents — don't discard
  what the team already wrote

Write to `./repo-profile-workdir/.claude/CLAUDE.md`.

**Step 3:** Generate `hooks.json`. Use the template from
`{baseDir}/references/output-templates.md` § "hooks.json Template".

Select hooks based on detected tooling:
- If a formatter exists → add a PostToolUse reminder hook
- If `.env` or credential files exist → add a protection hook
- If lock files exist → add a lock file protection hook
- If specific bug patterns recur → consider a pattern-specific warning hook

Write to `./repo-profile-workdir/.claude/hooks/hooks.json`.

**Step 4:** Generate the review skill. Use the template from
`{baseDir}/references/output-templates.md` § "repo-review Skill Template".

Weight the checklist by bug frequency:
- Checks for the most common bug category come first
- Each check should reference the specific pattern found, not generic advice
- Include "Rationalizations to reject" derived from actual failure patterns
- Skip sections where no relevant bugs were found

Write to `./repo-profile-workdir/.claude/skills/repo-review/SKILL.md`.

### Phase 6: Summary

**Step 1:** Print a summary for the user:

```
Profile generated for {repo} at ./repo-profile-workdir/.claude/

Files created:
  .claude/CLAUDE.md          — Project instructions ({N} conventions, {N} problem areas)
  .claude/hooks/hooks.json   — {N} hooks ({list of hook types})
  .claude/skills/repo-review/SKILL.md — Review checklist ({N} checks)
  .claude/analysis-notes.md  — Raw analysis data

Based on analysis of:
  {pr_count} merged PRs, {commit_count} commits, {revert_count} reverts
  {file_count} files across {language_count} languages

The clone is at ./repo-profile-workdir — review the generated files,
then copy .claude/ to the repo or push directly.
```

**Step 2:** Clean up intermediate files. Remove the history collection
outputs but keep `analysis-notes.md` for reference:

```bash
rm -f ./repo-profile-workdir/.claude/pr-data.json
rm -f ./repo-profile-workdir/.claude/commit-log.txt
rm -f ./repo-profile-workdir/.claude/reverts.txt
```
