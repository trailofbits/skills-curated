# Skill Importer

Import skills from GitHub into the curated marketplace. Downloads source files, transforms them to meet plugin standards, validates the result, and creates a PR.

## Installation

```
/plugin install trailofbits/skills-curated/plugins/trailofbits
```

## Usage

```
/trailofbits:import-skill https://github.com/mitsuhiko/agent-stuff/tree/main/skills/ghidra
```

Accepts GitHub URLs in several formats:

- `https://github.com/{owner}/{repo}/tree/{branch}/{path}`
- `https://github.com/{owner}/{repo}/blob/{branch}/{file}` (uses parent dir)
- `github.com/owner/repo/tree/branch/path` (no protocol)
- `owner/repo` (root path, default branch)

## What It Does

1. Fetches the skill source tree from GitHub
2. Reads and understands the skill content
3. Asks you to confirm the plugin name
4. Transforms paths, platform references, and frontmatter
5. Adds missing required sections ("When to Use", "When NOT to Use")
6. Generates `plugin.json`, `README.md`, and directory structure
7. Lints scripts and validates structure
8. Registers in `marketplace.json` and root `README.md`
9. Creates a branch, commits, and opens a PR

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth login`)
- `uv` for running the fetch script
- `ruff` for Python linting (optional, for script cleanup)
- `shellcheck` and `shfmt` for shell linting (optional)

## Credits

Built for the Trail of Bits [curated skills marketplace](https://github.com/trailofbits/skills-curated).
