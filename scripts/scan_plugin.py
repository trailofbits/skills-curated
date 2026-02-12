#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deterministic security scanner for imported plugins.

Scans plugin directories for:
  1. Unicode tricks (bidi overrides, zero-width chars, homoglyphs)
  2. Network access (URLs, curl/wget, Python/Node imports)
  3. Destructive commands (rm -rf, git reset --hard, etc.)
  4. Code execution (pipe-to-shell, eval/exec, subprocess)
  5. Credential access (SSH keys, AWS config, etc.)
  6. Encoded payloads (hex escapes, fromCharCode, atob/btoa)
  7. Privilege escalation (sudo, setuid, chmod +s)
  8. Compiled bytecode (.pyc, .pyo, __pycache__)

Exit codes: 0 = clean, 1 = usage error, 2 = BLOCK findings,
3 = WARN only.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Finding:
    level: Literal["BLOCK", "WARN"]
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
    r"\brm\s+-[rRf]*[rR][rRf]*\b"
    r"|\brm\s+--recursive\b"
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

# Pipe-to-shell — no legitimate plugin use
PIPE_TO_SHELL_RE = re.compile(
    r"\|\s*(?:bash|sh|zsh|dash|python[23]?|perl|ruby|node)\b"
    r"|\b(?:bash|sh|zsh)\s+-c\s"
    r"|\bsource\s+<\("
    r'|\beval\s+"\$\('
)

# Eval/exec — legitimate in educational docs
EVAL_EXEC_RE = re.compile(
    r"\beval\s*\("
    r"|\bexec\s*\("
    r"|\bFunction\s*\("
    r"|\b__import__\s*\("
    r"|\bimportlib\.import_module\s*\("
    r'|\bcompile\s*\([^)]*[\'"]exec[\'"]'
)

# Python shell-out — legitimate in helper scripts
PY_SHELLOUT_RE = re.compile(
    r"\bsubprocess\b"
    r"|\bos\.system\s*\("
    r"|\bos\.popen\s*\("
    r"|\bos\.exec[lv]p?\s*\("
)

# Sensitive credential paths
SENSITIVE_PATH_RE = re.compile(
    r"~/\.ssh\b"
    r"|~/\.aws\b"
    r"|~/\.gnupg\b"
    r"|~/\.config/gh\b"
    r"|~/\.netrc\b"
    r"|/etc/shadow\b"
    r"|\bid_rsa\b"
    r"|\bid_ed25519\b"
)

# Encoded / obfuscated payloads
ENCODED_PAYLOAD_RE = re.compile(
    r"(?:\\x[0-9a-fA-F]{2}){8,}"
    r"|\bString\.fromCharCode\s*\("
    r"|\bchr\s*\(\s*0x[0-9a-fA-F]"
    r"|\batob\s*\("
    r"|\bbtoa\s*\("
)

# Privilege escalation
PRIVILEGE_RE = re.compile(
    r"\bsudo\b"
    r"|\bdoas\b"
    r"|\bchown\s+root\b"
    r"|\bsetuid\b"
    r"|\bchmod\s+[ugo]*s"
)

# Compiled bytecode extensions
BYTECODE_EXTENSIONS = frozenset({".pyc", ".pyo"})

# Fenced code block detection in markdown
FENCE_OPEN_RE = re.compile(r"^(`{3,}|~{3,})")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_file_text(path: Path) -> str | None:
    """Read a file as UTF-8 text, returning None for binary or unreadable files.

    Detects binary files by checking for null bytes in the first 8 KB.
    """
    try:
        chunk = path.read_bytes()[:8192]
    except OSError:
        print(f"Warning: Cannot read {path}", file=sys.stderr)
        return None
    if b"\x00" in chunk:
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        print(f"Warning: Cannot read {path}", file=sys.stderr)
        return None


def markdown_code_ranges(lines: list[str]) -> frozenset[int]:
    """Return the set of line indices that fall inside fenced code blocks.

    Handles backtick and tilde fences. A closing fence must use the same
    character as the opener and be at least as long.
    """
    code_lines: set[int] = set()
    fence_start: int | None = None
    fence_char: str = ""
    fence_len: int = 0

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if fence_start is None:
            m = FENCE_OPEN_RE.match(stripped)
            if m:
                fence_start = i
                fence_char = m.group(1)[0]
                fence_len = len(m.group(1))
        else:
            close = stripped.rstrip()
            if close and all(c == fence_char for c in close) and len(close) >= fence_len:
                for j in range(fence_start, i + 1):
                    code_lines.add(j)
                fence_start = None
                fence_char = ""
                fence_len = 0

    return frozenset(code_lines)


def _is_code_context(
    line_idx: int,
    suffix: str,
    code_lines: frozenset[int] | None,
) -> bool:
    """Determine whether a line is in a code context."""
    if suffix in CODE_EXTENSIONS:
        return True
    if suffix == ".md" and code_lines is not None:
        return line_idx in code_lines
    return False


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_unicode(
    line: str,
    line_idx: int,
    rel_path: str,
    suffix: str,
    code_lines: frozenset[int] | None,
) -> list[Finding]:
    """Check a line for dangerous unicode characters."""
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
        elif (
            cp > 0x7F
            and unicodedata.category(ch).startswith("L")
            and _is_code_context(line_idx, suffix, code_lines)
        ):
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
    suffix: str,
    code_lines: frozenset[int] | None,
) -> list[Finding]:
    """Check a line for network access patterns."""
    findings: list[Finding] = []
    lineno = line_idx + 1
    is_code = _is_code_context(line_idx, suffix, code_lines)

    # Punycode URLs — always BLOCK
    punycode_match = PUNYCODE_RE.search(line)
    if punycode_match:
        findings.append(
            Finding(
                "BLOCK",
                "punycode-url",
                rel_path,
                lineno,
                punycode_match.group(0),
            )
        )

    # External URLs — strip trailing parens from markdown links
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
    suffix: str,
    code_lines: frozenset[int] | None,
) -> list[Finding]:
    """Check a line for destructive shell commands."""
    if not _is_code_context(line_idx, suffix, code_lines):
        return []

    if DESTRUCTIVE_RE.search(line):
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


def check_code_execution(
    line: str,
    line_idx: int,
    rel_path: str,
    suffix: str,
    code_lines: frozenset[int] | None,
) -> list[Finding]:
    """Check a line for code execution patterns."""
    if not _is_code_context(line_idx, suffix, code_lines):
        return []

    findings: list[Finding] = []
    lineno = line_idx + 1
    detail = line.strip()[:120]

    if PIPE_TO_SHELL_RE.search(line):
        findings.append(Finding("BLOCK", "pipe-to-shell", rel_path, lineno, detail))

    if EVAL_EXEC_RE.search(line):
        findings.append(Finding("WARN", "eval-exec", rel_path, lineno, detail))

    if PY_SHELLOUT_RE.search(line):
        findings.append(Finding("WARN", "py-shellout", rel_path, lineno, detail))

    return findings


def check_credential_access(
    line: str,
    line_idx: int,
    rel_path: str,
    suffix: str,
    code_lines: frozenset[int] | None,
) -> list[Finding]:
    """Check a line for access to sensitive credential paths."""
    if not _is_code_context(line_idx, suffix, code_lines):
        return []

    if SENSITIVE_PATH_RE.search(line):
        return [
            Finding(
                "BLOCK",
                "credential-access",
                rel_path,
                line_idx + 1,
                line.strip()[:120],
            )
        ]
    return []


def check_obfuscation(
    line: str,
    line_idx: int,
    rel_path: str,
    suffix: str,
    code_lines: frozenset[int] | None,
) -> list[Finding]:
    """Check a line for encoded or obfuscated payloads."""
    if not _is_code_context(line_idx, suffix, code_lines):
        return []

    if ENCODED_PAYLOAD_RE.search(line):
        return [
            Finding(
                "WARN",
                "encoded-payload",
                rel_path,
                line_idx + 1,
                line.strip()[:120],
            )
        ]
    return []


def check_privilege(
    line: str,
    line_idx: int,
    rel_path: str,
    suffix: str,
    code_lines: frozenset[int] | None,
) -> list[Finding]:
    """Check a line for privilege escalation patterns."""
    if not _is_code_context(line_idx, suffix, code_lines):
        return []

    if PRIVILEGE_RE.search(line):
        return [
            Finding(
                "WARN",
                "privilege-cmd",
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
    """Scan a single file for security findings."""
    if path.name in SKIP_FILENAMES:
        return []

    suffix = path.suffix.lower()
    if suffix in BYTECODE_EXTENSIONS:
        return [
            Finding(
                "BLOCK",
                "compiled-bytecode",
                rel_path,
                0,
                f"compiled Python bytecode ({suffix})",
            )
        ]

    text = _read_file_text(path)
    if text is None:
        return []

    lines = text.splitlines()

    code_lines: frozenset[int] | None = None
    if suffix == ".md":
        code_lines = markdown_code_ranges(lines)

    findings: list[Finding] = []
    for idx, line in enumerate(lines):
        if not line.isascii():
            findings.extend(check_unicode(line, idx, rel_path, suffix, code_lines))
        findings.extend(check_network(line, idx, rel_path, suffix, code_lines))
        findings.extend(check_destructive(line, idx, rel_path, suffix, code_lines))
        findings.extend(check_code_execution(line, idx, rel_path, suffix, code_lines))
        findings.extend(check_credential_access(line, idx, rel_path, suffix, code_lines))
        findings.extend(check_obfuscation(line, idx, rel_path, suffix, code_lines))
        findings.extend(check_privilege(line, idx, rel_path, suffix, code_lines))

    return findings


def scan_plugin(plugin_dir: Path) -> list[Finding]:
    """Scan all files in a plugin directory."""
    findings: list[Finding] = []
    plugins_dir = plugin_dir.parent
    for path in sorted(plugin_dir.rglob("*")):
        rel = str(path.relative_to(plugins_dir))
        if path.is_dir() and path.name == "__pycache__":
            findings.append(
                Finding(
                    "BLOCK",
                    "compiled-bytecode",
                    rel,
                    0,
                    "__pycache__ directory (unreviable bytecode)",
                )
            )
            continue
        if not path.is_file():
            continue
        findings.extend(scan_file(path, rel))
    return findings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _discover_plugins(target: Path) -> list[Path]:
    """Resolve target path to a list of plugin directories."""
    if target.name == "plugins":
        return sorted(d for d in target.iterdir() if d.is_dir() and (d / ".claude-plugin").is_dir())
    if (target / ".claude-plugin").is_dir():
        return [target]

    print(
        f"Error: {target} is not a plugin directory "
        "(missing .claude-plugin/) and is not a plugins/ parent",
        file=sys.stderr,
    )
    sys.exit(1)


def _escape_md_table(text: str) -> str:
    """Escape pipe characters so text doesn't break markdown tables."""
    return text.replace("|", "\\|")


def _format_markdown(findings: list[Finding]) -> str:
    """Format findings as a GitHub-flavored markdown report."""
    if not findings:
        return "<!-- security-scan -->\nNo security findings."

    blocks = [f for f in findings if f.level == "BLOCK"]
    warns = [f for f in findings if f.level == "WARN"]

    parts: list[str] = [
        "<!-- security-scan -->",
        "## Security Scanner Report",
        "",
        f"**{len(findings)}** finding(s): **{len(blocks)}** BLOCK, **{len(warns)}** WARN",
    ]

    for label, subset in [("BLOCK", blocks), ("WARN", warns)]:
        if not subset:
            continue
        parts.append("")
        parts.append(f"### {label} findings")
        parts.append("")
        parts.append("| Category | File | Line | Detail |")
        parts.append("|----------|------|------|--------|")
        for f in subset:
            detail = f.detail[:80]
            detail = _escape_md_table(detail)
            parts.append(f"| {f.category} | {f.path} | {f.line} | `{detail}` |")

    return "\n".join(parts) + "\n"


def _format_text(findings: list[Finding]) -> None:
    """Print findings in plain-text format (original behavior)."""
    if not findings:
        print("No findings.")
        return

    for f in findings:
        tag = "BLOCK" if f.level == "BLOCK" else "WARN "
        print(f"{tag}  {f.category:<18s} {f.path}:{f.line:<6d} {f.detail}")

    print(
        f"\nSummary: {len(findings)} finding(s) — "
        f"{sum(1 for f in findings if f.level == 'BLOCK')} BLOCK, "
        f"{sum(1 for f in findings if f.level == 'WARN')} WARN",
        file=sys.stderr,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministic security scanner for imported plugins.",
    )
    parser.add_argument(
        "target",
        type=Path,
        help="Plugin directory or plugins/ parent directory",
    )
    parser.add_argument(
        "--format",
        choices=["text", "markdown"],
        default="text",
        dest="output_format",
        help="Output format (default: text)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    target: Path = args.target

    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        sys.exit(1)

    plugin_dirs = _discover_plugins(target)

    all_findings: list[Finding] = []
    for plugin_dir in plugin_dirs:
        all_findings.extend(scan_plugin(plugin_dir))

    if args.output_format == "markdown":
        print(_format_markdown(all_findings))
    else:
        _format_text(all_findings)

    has_block = any(f.level == "BLOCK" for f in all_findings)
    has_warn = any(f.level == "WARN" for f in all_findings)

    if has_block:
        sys.exit(2)
    if has_warn:
        sys.exit(3)


if __name__ == "__main__":
    main()
