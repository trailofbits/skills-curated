#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deterministic security scanner for imported plugins.

Scans plugin directories for external network access, unicode tricks,
and destructive operations. Exit codes: 0 = clean, 1 = BLOCK findings,
2 = WARN only.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Finding:
    level: str  # "BLOCK" or "WARN"
    category: str
    path: str
    line: int  # 1-indexed
    detail: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CODE_EXTENSIONS = frozenset(
    {".py", ".sh", ".js", ".ts", ".swift", ".ps1", ".json", ".yml", ".yaml"}
)

SKIP_FILENAMES = frozenset({"LICENSE", "LICENSE.md", "LICENSE.txt"})

# Bidi override codepoints (U+202A-202E, U+2066-2069)
BIDI_CODEPOINTS = frozenset(range(0x202A, 0x202F)) | frozenset(range(0x2066, 0x206A))

# Zero-width characters
ZERO_WIDTH_CODEPOINTS = frozenset({0x200B, 0x200C, 0x200D, 0xFEFF, 0x00AD})

# Network commands in scripts / code blocks
NETWORK_CMD_RE = re.compile(
    r"\b(?:curl|wget|nc|ncat|socat|ssh|scp|rsync)\b"
    r"|openssl\s+s_client"
)

# Python network imports
PY_NETWORK_RE = re.compile(
    r"^\s*(?:import|from)\s+"
    r"(?:requests|httpx|urllib|aiohttp|http\.client|socket|websocket)\b"
)

# Node / JS network patterns
NODE_NETWORK_RE = re.compile(
    r"\bfetch\s*\("
    r"|(?:require|import)\s*\(?['\"](?:axios|node-fetch|http|https)['\"]"
    r"|\b(?:http|https)\.get\s*\("
)

# URL pattern — matches http:// and https://
URL_RE = re.compile(r"https?://\S+")

# GitHub repo URL used as attribution in markdown prose (not fetched)
GITHUB_ATTR_RE = re.compile(r"^https?://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/?$")

# Punycode domain
PUNYCODE_RE = re.compile(r"https?://[^\s/]*xn--")

# Destructive commands
DESTRUCTIVE_RE = re.compile(
    r"\brm\s+-(r|rf|fr)\b"
    r"|\brmdir\b"
    r"|\bshred\b"
    r"|\bunlink\b"
    r"|\bgit\s+clean\s+-[A-Za-z]*f"
    r"|\bgit\s+reset\s+--hard\b"
    r"|\bgit\s+push\s+(?:--force|-f)\b"
    r"|\bgit\s+branch\s+-D\b"
    r"|\bchmod\s+(?:-R\s+)?777\b"
    r"|\bdd\s+if="
    r"|\bmkfs\b"
    r"|\bformat\s+[A-Za-z]:"
)

# Fenced code block detection in markdown
FENCE_OPEN_RE = re.compile(r"^(`{3,}|~{3,})")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_binary(path: Path) -> bool:
    """Detect binary files by checking for null bytes in the first 8KB."""
    try:
        chunk = path.read_bytes()[:8192]
    except OSError:
        return True
    return b"\x00" in chunk


def is_code_file(path: Path) -> bool:
    return path.suffix.lower() in CODE_EXTENSIONS


def markdown_code_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """Return (start, end) line index ranges for fenced code blocks.

    Both start and end are inclusive 0-indexed line numbers.
    """
    ranges: list[tuple[int, int]] = []
    fence_start: int | None = None
    fence_marker: str = ""

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if fence_start is None:
            m = FENCE_OPEN_RE.match(stripped)
            if m:
                fence_start = i
                fence_marker = m.group(1)[0]
        else:
            if stripped.startswith(fence_marker) and stripped.rstrip() == (
                fence_marker * len(stripped.rstrip())
            ):
                close_char = stripped.rstrip()[0]
                if close_char == fence_marker[0] and len(stripped.rstrip()) >= len(fence_marker):
                    ranges.append((fence_start, i))
                    fence_start = None
                    fence_marker = ""

    return ranges


def in_code_context(
    line_idx: int,
    path: Path,
    code_ranges: list[tuple[int, int]] | None,
) -> bool:
    """Determine whether a line is in a code context."""
    if is_code_file(path):
        return True
    if path.suffix.lower() == ".md" and code_ranges is not None:
        return any(start <= line_idx <= end for start, end in code_ranges)
    return False


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_unicode(
    line: str,
    line_idx: int,
    rel_path: str,
    path: Path,
    code_ranges: list[tuple[int, int]] | None,
) -> list[Finding]:
    findings: list[Finding] = []
    lineno = line_idx + 1

    for ch in line:
        cp = ord(ch)

        if cp in BIDI_CODEPOINTS:
            findings.append(
                Finding(
                    "BLOCK",
                    "bidi-override",
                    rel_path,
                    lineno,
                    f"U+{cp:04X} ({unicodedata.name(ch, 'UNKNOWN')})",
                )
            )
        elif cp in ZERO_WIDTH_CODEPOINTS:
            findings.append(
                Finding(
                    "BLOCK",
                    "zero-width-char",
                    rel_path,
                    lineno,
                    f"U+{cp:04X} ({unicodedata.name(ch, 'UNKNOWN')})",
                )
            )
        elif cp > 0x7F and unicodedata.category(ch).startswith("L"):
            is_code = in_code_context(line_idx, path, code_ranges)
            if is_code:
                findings.append(
                    Finding(
                        "BLOCK",
                        "homoglyph",
                        rel_path,
                        lineno,
                        f"{unicodedata.name(ch, 'UNKNOWN')} (U+{cp:04X}) in code context",
                    )
                )

    return findings


def check_network(
    line: str,
    line_idx: int,
    rel_path: str,
    path: Path,
    code_ranges: list[tuple[int, int]] | None,
) -> list[Finding]:
    findings: list[Finding] = []
    lineno = line_idx + 1
    is_code = in_code_context(line_idx, path, code_ranges)

    # Punycode URLs — always BLOCK
    if PUNYCODE_RE.search(line):
        findings.append(
            Finding(
                "BLOCK",
                "punycode-url",
                rel_path,
                lineno,
                PUNYCODE_RE.search(line).group(0),  # type: ignore[union-attr]
            )
        )

    # External URLs
    for m in URL_RE.finditer(line):
        url = m.group(0).rstrip(")")
        if GITHUB_ATTR_RE.match(url) and not is_code:
            continue  # attribution link in prose
        if PUNYCODE_RE.match(url):
            continue  # already flagged above
        findings.append(
            Finding(
                "WARN",
                "external-url",
                rel_path,
                lineno,
                url,
            )
        )

    # Network commands (only in code contexts)
    if is_code and NETWORK_CMD_RE.search(line):
        findings.append(
            Finding(
                "WARN",
                "network-cmd",
                rel_path,
                lineno,
                line.strip()[:120],
            )
        )

    # Python network imports
    if PY_NETWORK_RE.search(line):
        findings.append(
            Finding(
                "WARN",
                "network-import",
                rel_path,
                lineno,
                line.strip()[:120],
            )
        )

    # Node network patterns
    if is_code and NODE_NETWORK_RE.search(line):
        findings.append(
            Finding(
                "WARN",
                "network-import",
                rel_path,
                lineno,
                line.strip()[:120],
            )
        )

    return findings


def check_destructive(
    line: str,
    line_idx: int,
    rel_path: str,
    path: Path,
    code_ranges: list[tuple[int, int]] | None,
) -> list[Finding]:
    is_code = in_code_context(line_idx, path, code_ranges)
    if not is_code:
        return []

    m = DESTRUCTIVE_RE.search(line)
    if m:
        return [
            Finding(
                "WARN",
                "destructive-cmd",
                rel_path,
                line_idx + 1,
                line.strip()[:120],
            )
        ]
    return []


# ---------------------------------------------------------------------------
# File / plugin scanning
# ---------------------------------------------------------------------------


def scan_file(path: Path, rel_path: str) -> list[Finding]:
    if path.name in SKIP_FILENAMES:
        return []
    if is_binary(path):
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = text.splitlines()

    code_ranges: list[tuple[int, int]] | None = None
    if path.suffix.lower() == ".md":
        code_ranges = markdown_code_ranges(lines)

    findings: list[Finding] = []
    for idx, line in enumerate(lines):
        findings.extend(
            check_unicode(
                line,
                idx,
                rel_path,
                path,
                code_ranges,
            )
        )
        findings.extend(
            check_network(
                line,
                idx,
                rel_path,
                path,
                code_ranges,
            )
        )
        findings.extend(
            check_destructive(
                line,
                idx,
                rel_path,
                path,
                code_ranges,
            )
        )

    return findings


def scan_plugin(plugin_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(plugin_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(plugin_dir.parent.parent))
        findings.extend(scan_file(path, rel))
    return findings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <plugin-dir | plugins/>", file=sys.stderr)
        sys.exit(2)

    target = Path(sys.argv[1])
    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        sys.exit(2)

    # Determine if scanning one plugin or all plugins
    if target.name == "plugins" or (
        target.name != "plugins" and (target / ".claude-plugin").is_dir()
    ):
        if target.name == "plugins":
            plugin_dirs = sorted(
                d for d in target.iterdir() if d.is_dir() and (d / ".claude-plugin").is_dir()
            )
        else:
            plugin_dirs = [target]
    else:
        print(
            f"Error: {target} is not a plugin directory "
            "(missing .claude-plugin/) and is not a plugins/ parent",
            file=sys.stderr,
        )
        sys.exit(2)

    all_findings: list[Finding] = []
    for plugin_dir in plugin_dirs:
        all_findings.extend(scan_plugin(plugin_dir))

    if not all_findings:
        print("No findings.")
        sys.exit(0)

    has_block = False
    has_warn = False
    for f in all_findings:
        tag = "BLOCK" if f.level == "BLOCK" else "WARN "
        print(f"{tag}  {f.category:<18s} {f.path}:{f.line:<6d} {f.detail}")
        if f.level == "BLOCK":
            has_block = True
        else:
            has_warn = True

    if has_block:
        sys.exit(1)
    if has_warn:
        sys.exit(2)


if __name__ == "__main__":
    main()
