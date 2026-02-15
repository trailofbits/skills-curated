# repo-profiler Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the coderabbit-config-generator plugin with repo-profiler — a skill that analyzes a remote GitHub repository and generates Claude Code configuration files (CLAUDE.md, hooks, review skill).

**Architecture:** Agent-driven with structured prompts. Two shell scripts handle mechanical work (cloning repos, collecting PR/commit history). The SKILL.md orchestrates the agent through a 4-phase analysis workflow and file generation. Reference docs provide detection heuristics and output templates.

**Tech Stack:** Shell scripts (bash), Claude Code plugin system (SKILL.md, commands/, plugin.json)

---

### Task 1: Delete coderabbit-config-generator

**Files:**
- Delete: `plugins/coderabbit-config-generator/` (entire directory)

**Step 1: Remove the plugin directory**

Run: `trash plugins/coderabbit-config-generator`

**Step 2: Verify deletion**

Run: `ls plugins/ | grep coderabbit`
Expected: No output

**Step 3: Commit**

```bash
git add -u plugins/coderabbit-config-generator/
git commit -m "Remove coderabbit-config-generator plugin (replaced by repo-profiler)"
```

---

### Task 2: Create plugin skeleton

**Files:**
- Create: `plugins/repo-profiler/.claude-plugin/plugin.json`
- Create: `plugins/repo-profiler/skills/repo-profiler/scripts/` (directory)
- Create: `plugins/repo-profiler/skills/repo-profiler/references/` (directory)
- Create: `plugins/repo-profiler/commands/` (directory)

**Step 1: Create directory structure**

```bash
mkdir -p plugins/repo-profiler/.claude-plugin
mkdir -p plugins/repo-profiler/skills/repo-profiler/scripts
mkdir -p plugins/repo-profiler/skills/repo-profiler/references
mkdir -p plugins/repo-profiler/commands
```

**Step 2: Write plugin.json**

Write to `plugins/repo-profiler/.claude-plugin/plugin.json`:

```json
{
  "name": "repo-profiler",
  "version": "1.0.0",
  "description": "Analyzes a remote GitHub repository and generates Claude Code configuration files (CLAUDE.md, hooks, review skill) tailored to the codebase's patterns, tooling, and bug history.",
  "author": {
    "name": "Trail of Bits",
    "url": "https://github.com/trailofbits/skills-curated"
  }
}
```

**Step 3: Commit**

```bash
git add plugins/repo-profiler/.claude-plugin/plugin.json
git commit -m "Add repo-profiler plugin skeleton"
```

---

### Task 3: Write fetch_repo.sh

Clones a GitHub repo to a local directory and prints a JSON manifest.

**Files:**
- Create: `plugins/repo-profiler/skills/repo-profiler/scripts/fetch_repo.sh`

**Step 1: Write the script**

Write to `plugins/repo-profiler/skills/repo-profiler/scripts/fetch_repo.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

print_usage() {
  cat <<'USAGE'
Usage: fetch_repo.sh [options]

Options:
  --url URL             GitHub repository URL or owner/repo (required)
  --dest PATH           Clone destination (default: ./repo-profile-workdir)
  -h, --help            Show this help text
USAGE
}

URL=""
DEST="./repo-profile-workdir"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      URL="$2"
      shift 2
      ;;
    --dest)
      DEST="$2"
      shift 2
      ;;
    -h | --help)
      print_usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      print_usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${URL}" ]]; then
  echo "--url is required." >&2
  print_usage >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required but not installed." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "gh CLI is not authenticated. Run 'gh auth login' first." >&2
  exit 1
fi

# Strip protocol and github.com prefix to get owner/repo
REPO="${URL}"
REPO="${REPO#https://}"
REPO="${REPO#http://}"
REPO="${REPO#github.com/}"
# Remove trailing tree/blob paths
REPO="${REPO%%/tree/*}"
REPO="${REPO%%/blob/*}"
# Remove trailing .git
REPO="${REPO%.git}"
# Remove trailing slash
REPO="${REPO%/}"

if [[ ! "${REPO}" =~ ^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$ ]]; then
  echo "Could not parse repo from URL: ${URL}" >&2
  echo "Expected format: owner/repo or https://github.com/owner/repo" >&2
  exit 1
fi

if [[ -d "${DEST}" ]]; then
  echo "Destination already exists: ${DEST}" >&2
  echo "Remove it first or use --dest to specify another path." >&2
  exit 1
fi

gh repo clone "${REPO}" "${DEST}" -- --depth=1 --single-branch

# Get repo metadata
DEFAULT_BRANCH=$(git -C "${DEST}" rev-parse --abbrev-ref HEAD)
CONTRIBUTOR_COUNT=$(git -C "${DEST}" log --format="%aN" | sort -u | wc -l | tr -d ' ')
FILE_COUNT=$(find "${DEST}" -type f -not -path "${DEST}/.git/*" | wc -l | tr -d ' ')

# Print manifest as JSON
cat <<EOF
{
  "repo": "${REPO}",
  "dest": "${DEST}",
  "default_branch": "${DEFAULT_BRANCH}",
  "contributor_count": ${CONTRIBUTOR_COUNT},
  "file_count": ${FILE_COUNT}
}
EOF
```

**Step 2: Make executable**

```bash
chmod +x plugins/repo-profiler/skills/repo-profiler/scripts/fetch_repo.sh
```

**Step 3: Lint**

```bash
shellcheck plugins/repo-profiler/skills/repo-profiler/scripts/fetch_repo.sh
shfmt -i 2 -ci -d plugins/repo-profiler/skills/repo-profiler/scripts/fetch_repo.sh
```

Fix any issues reported. If shfmt finds formatting problems:

```bash
shfmt -i 2 -ci -w plugins/repo-profiler/skills/repo-profiler/scripts/fetch_repo.sh
```

**Step 4: Commit**

```bash
git add plugins/repo-profiler/skills/repo-profiler/scripts/fetch_repo.sh
git commit -m "Add fetch_repo.sh script for repo-profiler"
```

---

### Task 4: Write collect_history.sh

Collects PR and commit data from a cloned repo. Merges the previous
`collect_prs.sh` and `collect_commits.sh` into one script that outputs both.

**Files:**
- Create: `plugins/repo-profiler/skills/repo-profiler/scripts/collect_history.sh`

**Step 1: Write the script**

Write to `plugins/repo-profiler/skills/repo-profiler/scripts/collect_history.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

print_usage() {
  cat <<'USAGE'
Usage: collect_history.sh [options]

Collects PR data and commit history from a GitHub repository.

Options:
  --repo OWNER/NAME     GitHub repository (required)
  --repo-path PATH      Local clone path (required)
  --days N              Look back N days (default: 90)
  --limit N             Max PRs to fetch (default: 200)
  --out-dir PATH        Output directory (default: .)
  -h, --help            Show this help text
USAGE
}

DAYS=90
LIMIT=200
OUT_DIR="."
REPO=""
REPO_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --repo-path)
      REPO_PATH="$2"
      shift 2
      ;;
    --days)
      DAYS="$2"
      shift 2
      ;;
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    -h | --help)
      print_usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      print_usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${REPO}" ]]; then
  echo "--repo is required." >&2
  print_usage >&2
  exit 1
fi

if [[ -z "${REPO_PATH}" ]]; then
  echo "--repo-path is required." >&2
  print_usage >&2
  exit 1
fi

if [[ ! -d "${REPO_PATH}/.git" ]]; then
  echo "No .git directory found at ${REPO_PATH}" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required but not installed." >&2
  exit 1
fi

SINCE_DATE=$(python3 -c "
import datetime, sys
days = int(sys.argv[1])
since = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)
print(since.strftime('%Y-%m-%d'))
" "${DAYS}")

mkdir -p "${OUT_DIR}"

PR_JSON="${OUT_DIR}/pr-data.json"
COMMIT_LOG="${OUT_DIR}/commit-log.txt"
REVERT_LOG="${OUT_DIR}/reverts.txt"

# Collect merged PRs
echo "Collecting merged PRs since ${SINCE_DATE}..." >&2
gh pr list \
  --repo "${REPO}" \
  --state merged \
  --search "merged:>${SINCE_DATE}" \
  --limit "${LIMIT}" \
  --json number,title,body,labels,mergedAt,url \
  >"${PR_JSON}"

# Collect commit log
echo "Collecting commit log..." >&2
git -C "${REPO_PATH}" log \
  --since="${SINCE_DATE}" \
  --pretty=format:"%h %s" \
  >"${COMMIT_LOG}"

# Collect reverted commits
echo "Collecting reverted commits..." >&2
git -C "${REPO_PATH}" log \
  --since="${SINCE_DATE}" \
  --pretty=format:"%h %s" \
  --grep="Revert" \
  >"${REVERT_LOG}" || true

PR_COUNT=$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "${PR_JSON}")
COMMIT_COUNT=$(wc -l <"${COMMIT_LOG}" | tr -d ' ')
REVERT_COUNT=$(wc -l <"${REVERT_LOG}" | tr -d ' ')

cat <<EOF
{
  "pr_json": "${PR_JSON}",
  "commit_log": "${COMMIT_LOG}",
  "revert_log": "${REVERT_LOG}",
  "pr_count": ${PR_COUNT},
  "commit_count": ${COMMIT_COUNT},
  "revert_count": ${REVERT_COUNT},
  "since_date": "${SINCE_DATE}"
}
EOF
```

**Step 2: Make executable and lint**

```bash
chmod +x plugins/repo-profiler/skills/repo-profiler/scripts/collect_history.sh
shellcheck plugins/repo-profiler/skills/repo-profiler/scripts/collect_history.sh
shfmt -i 2 -ci -d plugins/repo-profiler/skills/repo-profiler/scripts/collect_history.sh
```

Fix any issues. If shfmt finds formatting problems:

```bash
shfmt -i 2 -ci -w plugins/repo-profiler/skills/repo-profiler/scripts/collect_history.sh
```

**Step 3: Commit**

```bash
git add plugins/repo-profiler/skills/repo-profiler/scripts/collect_history.sh
git commit -m "Add collect_history.sh script for repo-profiler"
```

---

### Task 5: Write analysis-guide.md

Reference doc telling the agent what to look for in each analysis phase.

**Files:**
- Create: `plugins/repo-profiler/skills/repo-profiler/references/analysis-guide.md`

**Step 1: Write the file**

Write to `plugins/repo-profiler/skills/repo-profiler/references/analysis-guide.md`:

```markdown
# Analysis Guide

What to look for in each phase of the repo analysis.

## Phase 2: Tooling Detection

### Config File Lookup Table

| File | What It Tells You |
|------|-------------------|
| `pyproject.toml` | Python project: deps, ruff/mypy/pytest config, build system |
| `package.json` | Node project: deps, scripts (test, lint, build), engine version |
| `Cargo.toml` | Rust project: deps, clippy/rustfmt config, workspace layout |
| `go.mod` | Go project: module path, Go version, deps |
| `Makefile` | Build commands, common developer workflows |
| `Dockerfile` | Runtime environment, deployment pattern |
| `docker-compose.yml` | Service dependencies, development environment |
| `.github/workflows/*.yml` | CI pipeline: test commands, lint commands, deploy steps |
| `.circleci/config.yml` | CI pipeline (CircleCI variant) |
| `.pre-commit-config.yaml` | Pre-commit hooks: linters, formatters, checks |
| `.editorconfig` | Editor settings: indent style, line endings |
| `CLAUDE.md` | Existing Claude Code instructions |
| `CONTRIBUTING.md` | Contribution guidelines, review process |
| `.eslintrc*` / `eslint.config.*` | ESLint config (JS/TS linting) |
| `.prettierrc*` | Prettier config (JS/TS formatting) |
| `ruff.toml` / `[tool.ruff]` | Ruff config (Python lint + format) |
| `tsconfig.json` | TypeScript compiler settings, strictness |
| `.rubocop.yml` | RuboCop config (Ruby linting) |
| `Gemfile` | Ruby project: deps, version constraints |

### What to Extract

For each detected tool, record:
- **Tool name and version** (from config or lock files)
- **Run command** (from CI or Makefile or package.json scripts)
- **Key settings** (strictness level, enabled rules, ignored patterns)

### Framework Detection

Look for these patterns in dependencies:
- **Web frameworks:** express, fastapi, flask, django, rails, axum, gin
- **Test frameworks:** pytest, jest, vitest, mocha, rspec, cargo test
- **ORMs:** sqlalchemy, prisma, activerecord, diesel, gorm
- **Frontend:** react, vue, svelte, angular, next.js, nuxt

## Phase 3: History Analysis

### PR Categorization

Categorize each PR by its title prefix or content:

| Prefix/Pattern | Category |
|----------------|----------|
| `fix:`, `bug:`, `hotfix:` | Bug fix |
| `feat:`, `feature:`, `add:` | Feature |
| `refactor:`, `cleanup:` | Refactoring |
| `test:`, `spec:` | Testing |
| `docs:`, `doc:` | Documentation |
| `ci:`, `build:` | Infrastructure |
| `revert:`, `Revert "` | Revert |
| `chore:`, `deps:` | Maintenance |

### Bug Hotspot Detection

For PRs categorized as bug fixes:
1. Look at which files/directories they touch (from PR body or title)
2. Count fixes per top-level directory
3. Directories with 3+ fixes in 90 days are hotspots
4. Note the specific bug patterns (from PR title/body keywords)

### Revert Analysis

Reverted commits indicate things that went wrong enough to undo:
- What was the original change trying to do?
- What went wrong? (from revert message or linked PR)
- What directory/module was affected?

## Phase 4: Code Sampling

### What to Sample

Read 2-3 files from each major directory. Prioritize:
1. **Entry points** — main.py, index.ts, main.rs, cmd/main.go, app.rb
2. **Route/API definitions** — routes/, api/, handlers/, controllers/
3. **Core business logic** — the most-changed directories from Phase 3
4. **Test files** — one test file per major directory to understand test patterns
5. **Config/setup** — settings.py, config.ts, .env.example

### What to Look For

**Import patterns:**
- Are imports absolute or relative?
- Is there a consistent layering? (e.g., handlers import services import models)
- Are there circular dependency risks?

**Error handling:**
- Does the codebase use exceptions, Result types, or error codes?
- Are errors logged? With what library?
- Is there a consistent error handling pattern?

**Naming conventions:**
- snake_case vs camelCase vs PascalCase for functions/methods
- File naming: kebab-case, snake_case, or PascalCase?
- Test naming: test_*, *_test, *.spec.*, *.test.*

**Test patterns:**
- Test framework and assertion style
- Fixture/setup patterns
- Mocking approach (what gets mocked?)
- Test file location (colocated vs separate tests/ directory)
```

**Step 2: Commit**

```bash
git add plugins/repo-profiler/skills/repo-profiler/references/analysis-guide.md
git commit -m "Add analysis-guide.md reference for repo-profiler"
```

---

### Task 6: Write output-templates.md

Templates for the three generated output files.

**Files:**
- Create: `plugins/repo-profiler/skills/repo-profiler/references/output-templates.md`

**Step 1: Write the file**

Write to `plugins/repo-profiler/skills/repo-profiler/references/output-templates.md`:

````markdown
# Output Templates

Templates for the three files generated by repo-profiler. Adapt each
template based on analysis findings. Remove sections that don't apply.
Replace all `{placeholders}` with actual values.

## CLAUDE.md Template

```markdown
# {Project Name}

{One-sentence description of what this project is.}

## Stack

- **Language:** {language} {version}
- **Framework:** {framework} {version}
- **Test framework:** {test_framework}
- **Linter:** {linter} (run: `{lint_command}`)
- **Formatter:** {formatter} (run: `{format_command}`)

## Directory Structure

{Brief explanation of the top-level directory layout and what each
major directory contains. Focus on what an agent needs to navigate
the codebase, not exhaustive detail.}

## Development Commands

```bash
# Install dependencies
{install_command}

# Run tests
{test_command}

# Run linter
{lint_command}

# Run formatter
{format_command}

# Build
{build_command}
```

## Coding Conventions

{Conventions detected from code sampling. Only include conventions
that are consistently followed in the codebase. Examples:}

- {Import style: absolute imports, grouped by stdlib/third-party/local}
- {Naming: snake_case for functions, PascalCase for classes}
- {Error handling: raise exceptions with context messages, no bare except}
- {Testing: colocated test files, pytest fixtures for setup}

## Known Problem Areas

{From bug hotspot analysis. Only include directories with 3+ bug fixes
in the analysis window.}

- **{directory_path}/** — {N} bug fixes in last {days} days. Common issues: {pattern_summary}
- **{directory_path}/** — {N} bug fixes. Watch for: {specific_anti_pattern}

## Anti-Patterns to Avoid

{Derived from PR history and revert analysis. Only include patterns
that actually caused bugs in this repo, not generic advice.}

- **{Anti-pattern name}:** {What it is and why it's a problem in this codebase. Reference specific PRs if possible.}
```

## hooks.json Template

```json
{
  "hooks": [
    {
      "type": "PreToolUse",
      "matcher": "Bash",
      "hooks": [
        {
          "command": "{hook_command}",
          "timeout": 10000
        }
      ]
    }
  ]
}
```

### Hook Types to Generate

**Formatter hooks** — if the repo has a formatter configured:

```json
{
  "type": "PostToolUse",
  "matcher": "Write|Edit",
  "hooks": [
    {
      "command": "echo 'Remember to run {formatter_command} before committing'",
      "timeout": 5000
    }
  ]
}
```

**Protection hooks** — if the repo has sensitive files:

```json
{
  "type": "PreToolUse",
  "matcher": "Write|Edit",
  "hooks": [
    {
      "command": "echo $TOOL_INPUT | jq -r '.file_path' | grep -qE '\\.(env|pem|key)$' && echo 'BLOCK: Do not modify sensitive files' && exit 1 || exit 0",
      "timeout": 5000
    }
  ]
}
```

**Lock file protection** — prevent direct edits to lock files:

```json
{
  "type": "PreToolUse",
  "matcher": "Write|Edit",
  "hooks": [
    {
      "command": "echo $TOOL_INPUT | jq -r '.file_path' | grep -qE '(package-lock\\.json|yarn\\.lock|Cargo\\.lock|uv\\.lock|Gemfile\\.lock|poetry\\.lock)$' && echo 'BLOCK: Do not edit lock files directly — use the package manager' && exit 1 || exit 0",
      "timeout": 5000
    }
  ]
}
```

## repo-review Skill Template

```markdown
---
name: repo-review
description: "Reviews code changes in {project_name} with checks weighted by historical bug patterns. Use after implementing features or before creating PRs."
allowed-tools:
  - Read
  - Grep
  - Glob
---

# {Project Name} Review Checklist

Review code changes against this project's known patterns and problem areas.

## When to Use

- After implementing a feature in this repository
- Before creating a pull request
- When reviewing someone else's changes

## When NOT to Use

- For repositories other than {project_name}
- For documentation-only changes
- For dependency version bumps with no code changes

## Review Order

Evaluate in this order. Stop and flag issues before moving to the next level.

### 1. Architecture ({N} bugs from layer violations)

{Only include if import direction or layer boundary bugs were found.}

- [ ] Import direction follows: {detected_layer_order}
- [ ] No circular dependencies introduced
- [ ] New files are in the correct directory for their responsibility

### 2. Known Problem Areas

{One section per bug hotspot directory.}

#### {directory_path}/ ({N} recent bug fixes)

- [ ] {Specific check derived from the bugs that happened here}
- [ ] {Another specific check}

### 3. Error Handling ({N} bugs from silent failures)

{Only include if error handling bugs were found.}

- [ ] No bare `except: pass` or equivalent
- [ ] Error paths log or raise with context
- [ ] Resources acquired before potential exceptions are cleaned up

### 4. Test Coverage

- [ ] New behavior has corresponding tests
- [ ] Tests follow project convention: {test_convention_summary}
- [ ] Edge cases from known problem areas are covered

## Rationalizations to Reject

{Derived from patterns that caused past bugs. Each entry is a common
excuse that leads to the specific bugs this repo has experienced.}

- **"It's just a small change"** — {X}% of bugs in this repo came from changes under 20 lines
- **"{Specific rationalization}"** — {Why this leads to the specific bug pattern found}
```
````

**Step 2: Commit**

```bash
git add plugins/repo-profiler/skills/repo-profiler/references/output-templates.md
git commit -m "Add output-templates.md reference for repo-profiler"
```

---

### Task 7: Write SKILL.md

The main orchestration file — the agent's playbook for the entire workflow.

**Files:**
- Create: `plugins/repo-profiler/skills/repo-profiler/SKILL.md`

**Step 1: Write the file**

Write to `plugins/repo-profiler/skills/repo-profiler/SKILL.md`:

````markdown
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
````

**Step 2: Verify line count**

```bash
wc -l plugins/repo-profiler/skills/repo-profiler/SKILL.md
```

Expected: under 500 lines. If over, split content into references/.

**Step 3: Verify frontmatter**

```bash
head -10 plugins/repo-profiler/skills/repo-profiler/SKILL.md
```

Confirm valid YAML frontmatter with `name` and `description`.

**Step 4: Commit**

```bash
git add plugins/repo-profiler/skills/repo-profiler/SKILL.md
git commit -m "Add SKILL.md orchestration for repo-profiler"
```

---

### Task 8: Write profile-repo.md command

Slash command for `/profile-repo <url>`.

**Files:**
- Create: `plugins/repo-profiler/commands/profile-repo.md`

**Step 1: Write the file**

Write to `plugins/repo-profiler/commands/profile-repo.md`:

```markdown
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
```

**Step 2: Commit**

```bash
git add plugins/repo-profiler/commands/profile-repo.md
git commit -m "Add /profile-repo slash command"
```

---

### Task 9: Write README.md

**Files:**
- Create: `plugins/repo-profiler/README.md`

**Step 1: Write the file**

Write to `plugins/repo-profiler/README.md`:

```markdown
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
```

**Step 2: Commit**

```bash
git add plugins/repo-profiler/README.md
git commit -m "Add README.md for repo-profiler"
```

---

### Task 10: Update marketplace.json and root README.md

Replace coderabbit-config-generator with repo-profiler in both registries.

**Files:**
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md`

**Step 1: Update marketplace.json**

In `.claude-plugin/marketplace.json`, replace the coderabbit-config-generator
entry (lines 284-293) with:

```json
    {
      "name": "repo-profiler",
      "version": "1.0.0",
      "description": "Analyzes a remote GitHub repository and generates Claude Code configuration files (CLAUDE.md, hooks, review skill) tailored to the codebase's patterns, tooling, and bug history.",
      "author": {
        "name": "Trail of Bits",
        "url": "https://github.com/trailofbits/skills-curated"
      },
      "source": "./plugins/repo-profiler"
    }
```

**Step 2: Update root README.md**

In `README.md`, replace the coderabbit-config-generator row (line 24) with:

```markdown
| [repo-profiler](plugins/repo-profiler/) | Analyze a repo and generate Claude Code config (CLAUDE.md, hooks, review skill) |
```

**Step 3: Commit**

```bash
git add .claude-plugin/marketplace.json README.md
git commit -m "Replace coderabbit-config-generator with repo-profiler in marketplace"
```

---

### Task 11: Lint and validate

Run all linters and structural checks.

**Files:** (no new files — validation only)

**Step 1: Lint shell scripts**

```bash
shellcheck plugins/repo-profiler/skills/repo-profiler/scripts/fetch_repo.sh
shellcheck plugins/repo-profiler/skills/repo-profiler/scripts/collect_history.sh
shfmt -i 2 -ci -d plugins/repo-profiler/skills/repo-profiler/scripts/fetch_repo.sh
shfmt -i 2 -ci -d plugins/repo-profiler/skills/repo-profiler/scripts/collect_history.sh
```

Fix any issues found.

**Step 2: Validate JSON**

```bash
python3 -m json.tool plugins/repo-profiler/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
```

**Step 3: Check for hardcoded paths**

```bash
grep -rE '/home/[a-z]|/Users/[A-Z]' plugins/repo-profiler/ && echo "FAIL" || echo "PASS"
```

**Step 4: Verify SKILL.md frontmatter**

Check that `name` and `description` are present in SKILL.md frontmatter.

**Step 5: Verify all {baseDir}/ paths point to files that exist**

```bash
grep -oP '\{baseDir\}/[^\s`"]+' plugins/repo-profiler/skills/repo-profiler/SKILL.md | \
  sed 's|{baseDir}/|plugins/repo-profiler/skills/repo-profiler/|' | \
  while read -r path; do
    if [[ ! -e "${path}" ]]; then
      echo "MISSING: ${path}"
    fi
  done
```

**Step 6: Verify plugin.json name matches SKILL.md frontmatter name**

Both should be `repo-profiler`.

**Step 7: Commit any fixes**

If linting required changes:

```bash
git add plugins/repo-profiler/
git commit -m "Fix lint issues in repo-profiler"
```

---

### Task 12: Security scan

**Step 1: Run security scanner**

```bash
uv run scripts/scan_plugin.py plugins/repo-profiler/
```

If any BLOCK findings, fix them. WARN findings for the `gh repo clone`
network call and `find` command are expected and acceptable.

**Step 2: Commit any fixes**

If changes were needed:

```bash
git add plugins/repo-profiler/
git commit -m "Fix security findings in repo-profiler"
```

---

### Task 13: Deep review

**Step 1: Run the review-plugin command**

Read `.claude/commands/review-plugin.md` and execute its full review process
against `plugins/repo-profiler/`.

**Step 2: Fix all BLOCK and WARN findings**

**Step 3: Re-run linters after fixes**

```bash
shellcheck plugins/repo-profiler/skills/repo-profiler/scripts/*.sh
shfmt -i 2 -ci -d plugins/repo-profiler/skills/repo-profiler/scripts/*.sh
```

**Step 4: Commit fixes**

```bash
git add plugins/repo-profiler/
git commit -m "Fix review findings in repo-profiler"
```

---

### Task 14: Final commit and push

**Step 1: Verify clean state**

```bash
git status
git log --oneline -10
```

**Step 2: Push**

```bash
git push -u origin HEAD
```

**Step 3: Update the PR**

If a PR already exists for this branch, it will be updated automatically
by the push. If not, create one:

```bash
gh pr create --title "Add repo-profiler plugin" --body "$(cat <<'EOF'
## Summary

Replaces coderabbit-config-generator with repo-profiler.

Analyzes a remote GitHub repository and generates Claude Code configuration
files (CLAUDE.md, hooks, review skill) tailored to the codebase's patterns,
tooling, and bug history.

## What Changed

- Removed: `plugins/coderabbit-config-generator/`
- Added: `plugins/repo-profiler/` with SKILL.md, 2 helper scripts, 2 reference
  docs, slash command, and README
- Updated: marketplace.json and root README.md

## How It Works

1. Clones the target repo via `gh repo clone`
2. Detects tooling from config files
3. Analyzes 90 days of PR/commit history for bug patterns
4. Samples source files for architecture and conventions
5. Generates CLAUDE.md, hooks.json, and a review skill
EOF
)"
```
