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
