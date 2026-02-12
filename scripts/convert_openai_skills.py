#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Convert OpenAI curated skills to Claude Code plugin format.

Fetches skills from github.com/openai/skills and transforms them
into installable Claude Code plugins under plugins/openai-{name}/.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

REPO = "openai/skills"
CURATED_PATH = "skills/.curated"
PLUGINS_DIR = Path("plugins")
MARKETPLACE_PATH = Path(".claude-plugin/marketplace.json")

SKIP_MCP = frozenset(
    {
        "figma",
        "figma-implement-design",
        "linear",
        "notion-knowledge-capture",
        "notion-meeting-intelligence",
        "notion-research-documentation",
        "notion-spec-to-implementation",
    }
)

SKIP_OPENAI_API = frozenset(
    {
        "imagegen",
        "sora",
        "speech",
        "transcribe",
        "openai-docs",
    }
)

# Skills that depend on Codex-hosted infrastructure
SKIP_CODEX_INFRA = frozenset(
    {
        "vercel-deploy",  # deploy.sh calls codex-deploy-skills.vercel.sh
    }
)

SKIP_ALL = SKIP_MCP | SKIP_OPENAI_API | SKIP_CODEX_INFRA

OPENAI_API_MARKERS = re.compile(
    r"OPENAI_API_KEY|openai\.|gpt-image|sora|gpt-4o-mini-tts",
    re.IGNORECASE,
)

CODEX_PATH_RE = re.compile(
    r"\$CODEX_HOME/skills/[^/]+/|"
    r"\$\{CODEX_HOME[^}]*\}/skills/[^/]+/",
)

# Broader match: any $CODEX_HOME reference (for references/ files)
CODEX_HOME_RE = re.compile(
    r'\$CODEX_HOME|\$\{CODEX_HOME[^}]*\}|~/\.codex/skills/[^/\s"]+/',
)

SKILL_PATH_SECTION_RE = re.compile(
    r"^## Skill path.*?(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)

# Codex sandbox instructions that don't apply to Claude Code
SANDBOX_ESCALATION_RE = re.compile(
    r"[^\n]*sandbox_permissions\s*=\s*require_escalated[^\n]*\n?",
)

# <path-to-skill> placeholder used in some skills
PATH_TO_SKILL_RE = re.compile(r"<path-to-skill>")


def run_gh(*args: str) -> str:
    """Run a gh CLI command and return stdout."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def check_gh_auth() -> None:
    """Verify gh CLI is authenticated."""
    try:
        subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        print(
            "Error: gh CLI not found. Install from https://cli.github.com/",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError:
        print(
            "Error: gh CLI not authenticated. Run 'gh auth login' first.",
            file=sys.stderr,
        )
        sys.exit(1)


def list_curated_skills() -> list[str]:
    """List all skill names under skills/.curated."""
    raw = run_gh(
        "api",
        f"repos/{REPO}/contents/{CURATED_PATH}",
        "--jq",
        ".[].name",
    )
    return [name for name in raw.strip().splitlines() if name and not name.startswith(".")]


def fetch_file(path: str) -> str | None:
    """Fetch a single file from the repo, base64-decode it."""
    try:
        raw = run_gh(
            "api",
            f"repos/{REPO}/contents/{path}",
            "--jq",
            ".content",
        )
        content = raw.strip()
        if not content:
            return None
        return base64.b64decode(content).decode("utf-8")
    except subprocess.CalledProcessError:
        return None


def fetch_directory(path: str) -> dict[str, str]:
    """Fetch all files in a directory recursively."""
    files: dict[str, str] = {}
    try:
        raw = run_gh(
            "api",
            f"repos/{REPO}/contents/{path}",
        )
        entries = json.loads(raw)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return files

    for entry in entries:
        if entry["type"] == "file":
            content = fetch_file(entry["path"])
            if content is not None:
                rel = entry["path"].removeprefix(path).lstrip("/")
                files[rel] = content
        elif entry["type"] == "dir":
            sub = fetch_directory(entry["path"])
            for sub_path, sub_content in sub.items():
                rel_dir = entry["name"]
                files[f"{rel_dir}/{sub_path}"] = sub_content

    return files


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split YAML frontmatter from markdown body."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm_str = content[3:end].strip()
    body = content[end + 3 :].lstrip("\n")
    try:
        fm = yaml.safe_load(fm_str) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


def content_hash(text: str) -> str:
    """SHA-256 hex digest of text content."""
    return hashlib.sha256(text.encode()).hexdigest()


def has_mcp_dependencies(skill_name: str) -> bool:
    """Check if the skill's agents/openai.yaml has MCP deps."""
    path = f"{CURATED_PATH}/{skill_name}/agents/openai.yaml"
    content = fetch_file(path)
    if content is None:
        return False
    try:
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError:
        return False
    deps = data.get("dependencies", {})
    tools = deps.get("tools", [])
    return any(t.get("type") == "mcp" for t in tools if isinstance(t, dict))


def has_openai_api_usage(
    body: str,
    scripts: dict[str, str],
) -> bool:
    """Scan SKILL.md body and scripts for OpenAI API markers."""
    if OPENAI_API_MARKERS.search(body):
        return True
    return any(OPENAI_API_MARKERS.search(c) for c in scripts.values())


def should_skip(
    skill_name: str,
    body: str,
    scripts: dict[str, str],
) -> str | None:
    """Return skip reason or None if skill should be converted."""
    if skill_name in SKIP_MCP:
        return "MCP dependency"
    if skill_name in SKIP_OPENAI_API:
        return "OpenAI API dependency"
    if has_mcp_dependencies(skill_name):
        return "MCP dependency (detected)"
    if has_openai_api_usage(body, scripts):
        return "OpenAI API usage (detected)"
    return None


def infer_allowed_tools(
    body: str,
    scripts: dict[str, str],
) -> list[str]:
    """Infer Claude Code allowed-tools from skill content."""
    tools = ["Read", "Grep", "Glob"]
    has_code_blocks = "```" in body
    has_bash = bool(re.search(r"```(?:bash|sh)\b", body))
    has_cli_refs = bool(
        re.search(
            r"\bgit\b|\bnpm\b|\bnpx\b|\bgh\b|\bcurl\b|\bpip\b|\buv\b",
            body,
        )
    )
    if scripts or has_bash or has_code_blocks or has_cli_refs:
        tools.insert(0, "Bash")
    write_patterns = re.compile(
        r"creat|writ|generat|edit|modif|output|save|render",
        re.IGNORECASE,
    )
    if write_patterns.search(body):
        tools.extend(["Write", "Edit"])
    return tools


def transform_text(text: str) -> str:
    """Apply common text transformations to any file content.

    Shared across SKILL.md body, references, and markdown files.
    """
    text = CODEX_PATH_RE.sub("{baseDir}/", text)
    text = CODEX_HOME_RE.sub("{baseDir}", text)
    text = PATH_TO_SKILL_RE.sub("{baseDir}", text)
    text = SANDBOX_ESCALATION_RE.sub("", text)
    # Remove export CODEX_HOME=... lines (now redundant)
    text = re.sub(r"^export CODEX_HOME=.*\n?", "", text, flags=re.MULTILINE)
    # Specific patterns first (before general "codex" -> "the agent")
    text = re.sub(r"\bcodex/", "claude/", text)
    text = re.sub(r"\[codex\]", "[claude]", text)
    # "Codex" as agent name (capitalized)
    text = re.sub(
        r"\bCodex\b(?!\s*(?:CLI|API|SDK|home|path|repo))",
        "the agent",
        text,
    )
    # "codex" in prose (lowercase, not in paths/URLs/var names)
    text = re.sub(
        r"(?<![/\w.])codex(?!\.\w)(?![/\w_-])",
        "the agent",
        text,
    )
    return text


def transform_body(body: str) -> str:
    """Apply body transformations for SKILL.md specifically."""
    body = transform_text(body)
    body = SKILL_PATH_SECTION_RE.sub(
        "Scripts and references are located under `{baseDir}/`.\n\n",
        body,
    )
    if "## When to Use" not in body and "## When to use" not in body:
        body += "\n## When to Use\n\n<!-- TODO: review -->\n\n"
    if (
        "## When NOT to Use" not in body
        and "## When not to use" not in body
        and "## When Not to Use" not in body
    ):
        body += "## When NOT to Use\n\n<!-- TODO: review -->\n\n"
    return body


def build_frontmatter(
    name: str,
    original_fm: dict,
    body: str,
    scripts: dict[str, str],
) -> str:
    """Build Claude Code YAML frontmatter."""
    claude_name = f"openai-{name}"
    desc = original_fm.get("description", "")
    if desc:
        desc = transform_text(desc).strip().rstrip(".")
        desc += ". Originally from OpenAI's curated skills catalog."
    else:
        desc = (
            f"Converted from OpenAI's {name} skill. "
            "Originally from OpenAI's curated skills catalog."
        )
    allowed = infer_allowed_tools(body, scripts)
    fm = {
        "name": claude_name,
        "description": desc,
        "allowed-tools": allowed,
    }
    raw = yaml.dump(
        fm,
        default_flow_style=False,
        sort_keys=False,
        width=100,
    )
    return f"---\n{raw}---"


def transform_skill_md(
    name: str,
    skill_md: str,
    scripts: dict[str, str],
) -> str:
    """Full transformation of SKILL.md content."""
    original_fm, body = parse_frontmatter(skill_md)
    body = transform_body(body)
    fm = build_frontmatter(name, original_fm, body, scripts)
    return f"{fm}\n\n{body}"


def generate_plugin_json(
    name: str,
    original_fm: dict,
) -> str:
    """Generate .claude-plugin/plugin.json content."""
    desc = original_fm.get("description", "")
    if desc:
        desc = transform_text(desc).strip().rstrip(".")
        desc += ". Originally from OpenAI's curated skills catalog."
    else:
        desc = (
            f"Converted from OpenAI's {name} skill. "
            "Originally from OpenAI's curated skills catalog."
        )
    data = {
        "name": f"openai-{name}",
        "version": "1.0.0",
        "description": desc,
        "author": {
            "name": "OpenAI",
            "url": f"https://github.com/{REPO}",
        },
    }
    return json.dumps(data, indent=2) + "\n"


def generate_readme(
    name: str,
    original_fm: dict,
    body: str,
) -> str:
    """Generate plugin README.md."""
    display = name.replace("-", " ").title()
    desc = original_fm.get("description", "")
    if not desc:
        desc = f"Converted from OpenAI's {name} skill."

    headers = re.findall(r"^##\s+(.+)$", body, re.MULTILINE)
    covers = ""
    if headers:
        items = "\n".join(f"- {h}" for h in headers[:8])
        covers = f"\n## What It Covers\n\n{items}\n"

    source_url = f"https://github.com/{REPO}/tree/main/{CURATED_PATH}/{name}"

    lines = [
        f"# {display}",
        "",
        desc.strip(),
        "",
        "## Installation",
        "",
        "```",
        f"/plugin install trailofbits/skills-curated/plugins/openai-{name}",
        "```",
        "",
    ]
    if covers:
        lines.append(covers)
    lines.extend(
        [
            "## Credits",
            "",
            f"Originally from [OpenAI's curated skills catalog]({source_url}).",
            "Converted to Claude Code plugin format for the Trail of Bits",
            "curated skills marketplace.",
            "",
        ]
    )
    return "\n".join(lines)


def read_existing_version(plugin_dir: Path) -> str | None:
    """Read version from existing plugin.json if it exists."""
    pj = plugin_dir / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        return None
    try:
        data = json.loads(pj.read_text())
        return data.get("version")
    except (json.JSONDecodeError, OSError):
        return None


def read_existing_hash(plugin_dir: Path) -> str | None:
    """Read stored content hash from .source-hash file."""
    hf = plugin_dir / ".source-hash"
    if not hf.exists():
        return None
    return hf.read_text().strip()


def bump_patch(version: str) -> str:
    """Bump patch version: 1.0.0 -> 1.0.1."""
    parts = version.split(".")
    if len(parts) != 3:
        return "1.0.1"
    parts[2] = str(int(parts[2]) + 1)
    return ".".join(parts)


def write_plugin(
    name: str,
    skill_md: str,
    references: dict[str, str],
    scripts: dict[str, str],
    license_text: str | None,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> str | None:
    """Write a converted plugin to disk.

    Returns the version written, or None if skipped.
    """
    plugin_dir = PLUGINS_DIR / f"openai-{name}"
    skill_dir = plugin_dir / "skills" / f"openai-{name}"
    source_hash = content_hash(skill_md)

    existing_hash = read_existing_hash(plugin_dir)
    existing_version = read_existing_version(plugin_dir)

    if existing_hash == source_hash and not force:
        return None

    version = "1.0.0"
    if existing_version and existing_hash:
        version = bump_patch(existing_version)

    original_fm, body = parse_frontmatter(skill_md)
    transformed = transform_skill_md(name, skill_md, scripts)
    plugin_json = generate_plugin_json(name, original_fm)
    readme = generate_readme(name, original_fm, body)

    plugin_json_data = json.loads(plugin_json)
    plugin_json_data["version"] = version
    plugin_json = json.dumps(plugin_json_data, indent=2) + "\n"

    if dry_run:
        print(f"  Would write: {plugin_dir}/")
        return version

    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / ".claude-plugin").mkdir(exist_ok=True)
    skill_dir.mkdir(parents=True, exist_ok=True)

    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(plugin_json)
    (plugin_dir / "README.md").write_text(readme)
    (skill_dir / "SKILL.md").write_text(transformed)
    (plugin_dir / ".source-hash").write_text(source_hash + "\n")

    for ref_path, ref_content in references.items():
        ref_file = skill_dir / "references" / ref_path
        ref_file.parent.mkdir(parents=True, exist_ok=True)
        ref_file.write_text(transform_text(ref_content))

    for script_path, script_content in scripts.items():
        script_file = skill_dir / "scripts" / script_path
        script_file.parent.mkdir(parents=True, exist_ok=True)
        # Transform markdown/text in scripts, leave code alone
        if script_path.endswith((".md", ".txt")):
            script_content = transform_text(script_content)
        script_file.write_text(script_content)

    if license_text:
        (plugin_dir / "LICENSE").write_text(license_text)

    lint_plugin(plugin_dir)

    return version


def lint_plugin(plugin_dir: Path) -> None:
    """Run ruff and shfmt on imported scripts to match CI standards."""
    py_files = list(plugin_dir.rglob("*.py"))
    sh_files = list(plugin_dir.rglob("*.sh"))

    if py_files:
        with contextlib.suppress(FileNotFoundError):
            subprocess.run(
                [
                    "ruff",
                    "check",
                    "--fix",
                    "--unsafe-fixes",
                    "--silent",
                    *py_files,
                ],
                capture_output=True,
            )
            subprocess.run(
                ["ruff", "format", "--silent", *py_files],
                capture_output=True,
            )

    if sh_files:
        with contextlib.suppress(FileNotFoundError):
            subprocess.run(
                ["shfmt", "-i", "2", "-ci", "-w", *sh_files],
                capture_output=True,
            )


def update_marketplace(
    plugins: list[dict],
    *,
    dry_run: bool = False,
) -> None:
    """Merge converted plugin entries into marketplace.json."""
    mp = json.loads(MARKETPLACE_PATH.read_text())
    existing = {p["name"]: i for i, p in enumerate(mp["plugins"])}

    for plugin in plugins:
        entry = {
            "name": plugin["name"],
            "version": plugin["version"],
            "description": plugin["description"],
            "author": {
                "name": "OpenAI",
                "url": f"https://github.com/{REPO}",
            },
            "source": f"./plugins/{plugin['name']}",
        }
        if plugin["name"] in existing:
            mp["plugins"][existing[plugin["name"]]] = entry
        else:
            mp["plugins"].append(entry)

    if dry_run:
        print(f"\n  Would update {MARKETPLACE_PATH}")
        return

    MARKETPLACE_PATH.write_text(json.dumps(mp, indent=2) + "\n")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert OpenAI curated skills to Claude Code plugins",
    )
    parser.add_argument(
        "--skills",
        nargs="+",
        metavar="NAME",
        help="Convert specific skills only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing files",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_skills",
        help="List available curated skills and exit",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite even if source unchanged",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point."""
    args = parse_args()

    check_gh_auth()

    print("Fetching curated skill list...")
    all_skills = list_curated_skills()

    if args.list_skills:
        print(f"\n{len(all_skills)} curated skills:\n")
        for name in sorted(all_skills):
            tag = " (skip)" if name in SKIP_ALL else ""
            print(f"  {name}{tag}")
        portable = len(all_skills) - len(SKIP_ALL & set(all_skills))
        print(f"\n{portable} portable, {len(SKIP_ALL & set(all_skills))} skipped")
        return

    targets = args.skills if args.skills else all_skills
    converted: list[dict] = []
    skipped: list[tuple[str, str]] = []
    errors: list[tuple[str, str]] = []

    for i, name in enumerate(targets):
        print(f"\n[{i + 1}/{len(targets)}] {name}")

        if name in SKIP_ALL:
            if name in SKIP_MCP:
                reason = "MCP dependency"
            elif name in SKIP_OPENAI_API:
                reason = "OpenAI API dependency"
            else:
                reason = "Codex infrastructure dependency"
            print(f"  Skipped: {reason}")
            skipped.append((name, reason))
            continue

        try:
            skill_path = f"{CURATED_PATH}/{name}"
            skill_md = fetch_file(f"{skill_path}/SKILL.md")
            if skill_md is None:
                print("  Error: SKILL.md not found")
                errors.append((name, "SKILL.md not found"))
                continue

            refs_path = f"{skill_path}/references"
            references = fetch_directory(refs_path)

            scripts_path = f"{skill_path}/scripts"
            scripts = fetch_directory(scripts_path)

            skip_reason = should_skip(name, skill_md, scripts)
            if skip_reason:
                print(f"  Skipped: {skip_reason}")
                skipped.append((name, skip_reason))
                continue

            license_text = fetch_file(f"{skill_path}/LICENSE.txt")

            original_fm, _ = parse_frontmatter(skill_md)
            version = write_plugin(
                name,
                skill_md,
                references,
                scripts,
                license_text,
                force=args.force,
                dry_run=args.dry_run,
            )

            if version is None:
                print("  Unchanged (skipped)")
                skipped.append((name, "unchanged"))
            else:
                desc = original_fm.get("description", "")
                if desc:
                    desc = transform_text(desc).strip().rstrip(".")
                    desc += ". Originally from OpenAI's curated skills catalog."
                else:
                    desc = f"Converted from OpenAI's {name} skill."
                converted.append(
                    {
                        "name": f"openai-{name}",
                        "version": version,
                        "description": desc,
                    }
                )
                print(f"  Converted (v{version})")

        except Exception as exc:
            print(f"  Error: {exc}")
            errors.append((name, str(exc)))

        if i < len(targets) - 1:
            time.sleep(0.5)

    if converted:
        print("\nUpdating marketplace.json...")
        update_marketplace(converted, dry_run=args.dry_run)

    print("\n--- Summary ---")
    print(f"  Converted: {len(converted)}")
    print(f"  Skipped:   {len(skipped)}")
    print(f"  Errors:    {len(errors)}")

    if errors:
        print("\nErrors:")
        for name, err in errors:
            print(f"  {name}: {err}")

    if converted and not args.dry_run:
        print("\nDone. Review generated plugins and update README.md with the new OpenAI section.")


if __name__ == "__main__":
    main()
