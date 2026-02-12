#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fetch a directory tree from GitHub via the gh CLI.

Recursively downloads files from a GitHub repo path and writes
them to a local directory. Prints a JSON manifest to stdout.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


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


def parse_github_url(url: str) -> tuple[str, str, str | None]:
    """Parse a GitHub URL into (repo, path, branch).

    Supports:
      https://github.com/{owner}/{repo}/tree/{branch}/{path}
      https://github.com/{owner}/{repo}/blob/{branch}/{path}
      github.com/{owner}/{repo}/tree/{branch}/{path}
      {owner}/{repo}  (shorthand: root path, default branch)

    For blob URLs, uses the parent directory.

    Returns:
        (repo, path, branch) where branch may be None
        for default branch.
    """
    url = url.strip().rstrip("/")

    # Strip protocol and github.com prefix
    cleaned = re.sub(r"^https?://", "", url)
    cleaned = re.sub(r"^github\.com/", "", cleaned)

    # Match tree/blob URL: owner/repo/(tree|blob)/branch/path
    m = re.match(
        r"^([^/]+/[^/]+)/(tree|blob)/([^/]+)(?:/(.*))?$",
        cleaned,
    )
    if m:
        repo = m.group(1)
        url_type = m.group(2)
        branch = m.group(3)
        path = m.group(4) or ""
        if url_type == "blob" and "/" in path:
            # Use parent directory for blob URLs
            path = path.rsplit("/", 1)[0]
        elif url_type == "blob":
            path = ""
        return repo, path, branch

    # Shorthand: owner/repo (or owner/repo/extra but no tree/blob)
    m = re.match(r"^([^/]+/[^/]+)$", cleaned)
    if m:
        return m.group(1), "", None

    print(
        f"Error: Could not parse GitHub URL: {url}\n"
        "Expected formats:\n"
        "  https://github.com/owner/repo/tree/branch/path\n"
        "  https://github.com/owner/repo/blob/branch/path\n"
        "  owner/repo",
        file=sys.stderr,
    )
    sys.exit(1)


def get_default_branch(repo: str) -> str:
    """Get the default branch for a repository."""
    raw = run_gh(
        "api",
        f"repos/{repo}",
        "--jq",
        ".default_branch",
    )
    return raw.strip()


def get_repo_license(repo: str) -> str | None:
    """Get the SPDX license identifier for a repository."""
    try:
        raw = run_gh(
            "api",
            f"repos/{repo}",
            "--jq",
            ".license.spdx_id",
        )
        license_id = raw.strip()
        if license_id and license_id != "null" and license_id != "NOASSERTION":
            return license_id
    except subprocess.CalledProcessError:
        pass
    return None


def fetch_file_content(repo: str, path: str) -> bytes | None:
    """Fetch a single file's content, base64-decoded."""
    try:
        raw = run_gh(
            "api",
            f"repos/{repo}/contents/{path}",
            "--jq",
            ".content",
        )
        content = raw.strip()
        if not content or content == "null":
            return None
        return base64.b64decode(content)
    except (subprocess.CalledProcessError, Exception):
        return None


def fetch_tree(
    repo: str,
    path: str,
    *,
    list_only: bool = False,
) -> dict[str, bytes | None]:
    """Recursively fetch all files under a path.

    Returns dict mapping relative paths to file content bytes.
    If list_only is True, values are None (no content fetched).
    """
    files: dict[str, bytes | None] = {}
    try:
        raw = run_gh(
            "api",
            f"repos/{repo}/contents/{path}",
        )
        entries = json.loads(raw)
    except subprocess.CalledProcessError:
        print(
            f"Error: Path '{path}' not found in {repo}.",
            file=sys.stderr,
        )
        sys.exit(1)
    except json.JSONDecodeError:
        print(
            f"Error: Unexpected response for {repo}/{path}.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Single file (API returns object, not array)
    if isinstance(entries, dict):
        entries = [entries]

    for entry in entries:
        rel = entry["path"].removeprefix(path).lstrip("/")
        if not rel:
            rel = entry["name"]

        if entry["type"] == "file":
            if list_only:
                files[rel] = None
            else:
                content = fetch_file_content(repo, entry["path"])
                files[rel] = content
                time.sleep(0.5)
        elif entry["type"] == "dir":
            sub = fetch_tree(
                repo,
                entry["path"],
                list_only=list_only,
            )
            for sub_path, sub_content in sub.items():
                files[f"{rel}/{sub_path}"] = sub_content

    return files


def write_tree(
    files: dict[str, bytes | None],
    output_dir: Path,
) -> None:
    """Write fetched files to disk."""
    for rel_path, content in files.items():
        if content is None:
            continue
        out_file = output_dir / rel_path
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(content)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch a directory tree from GitHub",
    )
    parser.add_argument(
        "url",
        help="GitHub URL or owner/repo shorthand",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory to write files to (default: temp dir)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_only",
        help="List files without downloading",
    )
    args = parser.parse_args()

    check_gh_auth()

    repo, path, branch = parse_github_url(args.url)

    if branch is None:
        branch = get_default_branch(repo)

    license_id = get_repo_license(repo)

    if args.list_only:
        files = fetch_tree(repo, path, list_only=True)
        manifest = {
            "repo": repo,
            "path": path,
            "branch": branch,
            "license": license_id,
            "files": sorted(files.keys()),
        }
        print(json.dumps(manifest, indent=2))
        return

    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path(tempfile.mkdtemp(prefix="skill-import-"))

    files = fetch_tree(repo, path)
    write_tree(files, output_dir)

    manifest = {
        "repo": repo,
        "path": path,
        "branch": branch,
        "license": license_id,
        "output_dir": str(output_dir),
        "files": sorted(k for k, v in files.items() if v is not None),
    }
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
