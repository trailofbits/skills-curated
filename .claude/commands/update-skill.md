---
name: update-skill
description: >-
  Check an imported plugin for upstream changes, analyze what changed,
  walk the user through triage, and apply approved updates via PR.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
---

# /update-skill -- Update an Imported Plugin from Upstream

Check an imported plugin's upstream source for changes since import,
analyze and categorize them, walk the user through choosing what to
apply, then create a PR with the approved updates.

**Argument:** A plugin name (e.g., `last30days`). Must exist in
`plugins/{name}/` and have an upstream URL in marketplace.json.

## Phase 1 — Resolve & Fetch

### Step 1: Look up the plugin

Read `.claude-plugin/marketplace.json` and find the entry matching the
plugin name. Extract `author.url` — this is the upstream GitHub URL.

If the plugin is not found, list available plugins and stop.

If `author.url` is missing or doesn't point to GitHub, stop and tell the
user there's no upstream source to check.

### Step 2: Parse the upstream repo

Extract `owner/repo` from the author URL. Supported formats:

| Format | Example |
|--------|---------|
| Repo URL | `https://github.com/owner/repo` |
| Tree URL | `https://github.com/owner/repo/tree/main/path` |
| With trailing slash | `https://github.com/owner/repo/` |

### Step 3: Verify `gh` auth

```bash
gh auth status
```

If not authenticated, stop and tell the user to run `gh auth login`.

### Step 4: Determine the import date

Find when this plugin was last imported or updated:

```bash
git log --format='%aI' --diff-filter=A -- plugins/{name}/ | tail -1
```

If that returns nothing (files were modified but not added), fall back to:

```bash
git log --format='%aI' -- plugins/{name}/ | tail -1
```

Parse the date (ISO 8601). This is the **baseline date** — upstream changes
after this date are what we care about.

### Step 5: Fetch upstream commit log

Get all commits since the baseline date:

```bash
gh api repos/{owner}/{repo}/commits --paginate \
  --jq '.[] | "\(.sha[0:8]) \(.commit.author.date) \(.commit.message)"'
```

Filter to commits after the baseline date. If there are no new commits, tell
the user the plugin is up to date and stop.

### Step 6: Fetch the upstream tree

```bash
uv run {baseDir}/scripts/fetch_github_tree.py "https://github.com/{owner}/{repo}"
```

Parse the JSON manifest. This gives us the current state of every upstream
file.

### Step 7: Read our downstream files

List all files in `plugins/{name}/`:

```bash
fd . plugins/{name}/ --type f
```

Read the key files (SKILL.md, main scripts, lib files) so you understand
our current state.

## Phase 2 — Analyze & Report

### Step 8: Categorize upstream commits

Group commits by type using conventional-commit prefixes:

| Prefix | Category | Priority |
|--------|----------|----------|
| `fix:` | Bug fixes | High — likely want to downstream |
| `feat:` | New features | Medium — user decides relevance |
| `docs:` | Documentation | Low — usually skip |
| `chore:`, `ci:`, `build:` | Maintenance | Low — usually skip |
| `refactor:` | Refactoring | Medium — may improve code quality |
| No prefix | Uncategorized | Read the message to classify |

For each category, list the commits with their one-line messages.

### Step 9: Map upstream files to downstream

Build a file mapping table. For each upstream file, determine the
downstream equivalent:

1. **Exact path match** — same relative path exists downstream
2. **Renamed file** — similar name or content exists downstream under
   a different name (e.g., upstream `bird_x.py` → downstream `xai_x.py`)
3. **New file** — no downstream equivalent exists
4. **Upstream-only** — files we intentionally excluded during import
   (e.g., `agents/openai.yaml`, `assets/`, marketing docs)

To detect renames, compare: file purposes (from imports and function names),
file sizes, and shared function/class names between upstream and downstream
files.

### Step 10: Analyze changes per file

For each file that was modified upstream (not new, not upstream-only):

1. Read the upstream version from the fetched tree
2. Read our downstream version
3. Summarize the differences — focus on behavioral changes, not formatting

For new upstream files:

1. Read the file
2. Summarize what it does and what it depends on

### Step 11: Present the report

Present a structured report to the user. Use this format:

```markdown
## Upstream Update Report: {name}

**Source:** {author.url}
**Our import date:** {baseline date}
**Upstream commits since:** {count}
**Date range:** {oldest} → {newest}

### Bug Fixes ({count})

{For each fix: one-line description, affected files with downstream
mapping, and what the fix addresses. Read the actual code changes,
don't just parrot the commit message.}

### New Features ({count})

{For each feature: what it does, what files it introduces, what
dependencies it adds, estimated scope of integration.}

### Refactoring ({count})

{For each refactor: what changed and whether it affects our downstream
code.}

### Documentation / Other ({count})

{Brief list — these are rarely downstreamed.}

### File Mapping

| Upstream File | Downstream Equivalent | Status |
|---------------|----------------------|--------|
| scripts/lib/bird_x.py | scripts/lib/xai_x.py | Modified upstream |
| scripts/lib/youtube_yt.py | (none) | New upstream |
| ... | ... | ... |
```

After presenting the report, tell the user: "Let's walk through each
category. I'll start with bug fixes."

## Phase 3 — Interactive Triage

Walk the user through each category **one group at a time**. Do not
present all categories at once.

### Step 12: Triage bug fixes

For each bug fix (or group of related fixes):

1. Explain what the bug was and how the fix works
2. Show which downstream file(s) would be affected
3. Note if the fix applies cleanly or needs adaptation (e.g., the fix
   is in a function we renamed, or in code we restructured)
4. Ask the user: **Apply, skip, or discuss further?**

If the user wants to discuss, explain the change in more detail — read
the specific upstream code, compare with our version, explain tradeoffs.

Collect the user's decisions. Track approved changes as a list of:
- Upstream file(s) involved
- Downstream file(s) to modify
- Transform strategy: `copy` (replace file), `merge` (apply specific
  changes into existing file), or `new` (add new file with transforms)

### Step 13: Triage new features

For each new feature:

1. Explain what it does and why it was added upstream
2. List all new files it introduces
3. Note any new dependencies (Python packages, external tools)
4. Note if it requires changes to existing files (e.g., new imports,
   new CLI flags, SKILL.md updates)
5. Ask the user: **Apply, skip, or discuss further?**

### Step 14: Triage refactoring and other changes

For remaining changes that don't fit bug fixes or new features:

1. Briefly describe each
2. Ask the user: **Apply, skip, or discuss?**

### Step 15: Confirm the plan

After all categories are triaged, present a summary of decisions:

```markdown
## Update Plan

### Will Apply
- {description of each approved change}

### Will Skip
- {description of each skipped change, with reason}

### Version
Current: {current version}
New: {bumped patch version}
```

Ask the user to confirm before proceeding.

## Phase 4 — Apply & PR

### Step 16: Create a working branch

```bash
git checkout -b update/{name}
```

If the branch already exists, append a timestamp:

```bash
git checkout -b update/{name}-$(date +%s)
```

### Step 17: Apply approved changes

For each approved change, apply based on the transform strategy:

**`copy` — Replace a file:**

1. Read the upstream file from the fetched tree
2. Apply standard transforms:
   - Replace platform-specific paths with `{baseDir}/`
   - Remove platform directives (sandbox_permissions, CODEX_HOME exports)
   - Replace platform agent names with "the agent"
3. Write to the downstream path

**`merge` — Apply specific changes to an existing file:**

1. Read both the upstream and downstream versions
2. Identify the specific changes to apply (from the triage notes)
3. Edit the downstream file to incorporate those changes
4. Preserve our local modifications (frontmatter, structure, naming)

**`new` — Add a new file:**

1. Read the upstream file from the fetched tree
2. Apply standard transforms (path substitution, platform cleanup)
3. Write to the appropriate downstream path
4. If it's a Python script, ensure PEP 723 metadata is present

### Step 18: Update SKILL.md if needed

If approved changes affect the skill's capabilities (new features, new
CLI flags, changed behavior):

1. Read the current SKILL.md
2. Update relevant sections to reflect the changes
3. Preserve frontmatter and structure
4. Keep under 500 lines

### Step 19: Lint and validate

```bash
# Python
ruff check --fix plugins/{name}/
ruff format plugins/{name}/

# Shell
fd -e sh . plugins/{name}/ -x shellcheck -x {}
fd -e sh . plugins/{name}/ -x shfmt -i 2 -ci -d {}

# Security scan
uv run scripts/scan_plugin.py plugins/{name}/

# Structure
python3 -m json.tool plugins/{name}/.claude-plugin/plugin.json > /dev/null
grep -rE '/home/[a-z]|/Users/[A-Z]' plugins/{name}/ && echo "FAIL: hardcoded paths" || true
```

Fix any issues before continuing.

### Step 20: Bump version

Read the current version from `plugins/{name}/.claude-plugin/plugin.json`.
Increment the patch version (e.g., 1.0.0 → 1.0.1).

Update the version in both:
- `plugins/{name}/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json` (the matching entry)

### Step 21: Commit, push, PR

```bash
git add plugins/{name}/ .claude-plugin/marketplace.json
```

Commit message: `Update {name} plugin from upstream ({owner}/{repo})`

```bash
git push -u origin HEAD
```

Create PR:

```bash
gh pr create --title "Update {name} plugin from upstream" --body "$(cat <<'EOF'
## Summary

Updates [{name}](plugins/{name}/) from upstream [{owner}/{repo}]({author_url}).

**Upstream commits since last import:** {count} ({date range})

## Applied Changes

{List each approved change with description}

## Skipped Changes

{List each skipped change with reason}

## Upstream Commit Range

{List commit SHAs and one-line messages for all upstream commits in range}

## Checklist

- [x] Changes reviewed and approved by user
- [x] Transforms applied (path substitution, platform cleanup)
- [x] Linters pass (ruff, shellcheck)
- [x] Security scan clean
- [x] Version bumped in plugin.json and marketplace.json
EOF
)"
```

Report the PR URL to the user.

### Step 22: Clean up

Remove the temporary directory created by the fetch script:

```bash
trash {output_dir}
```
