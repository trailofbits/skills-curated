#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fetch a directory tree from GitHub via the gh CLI.

Recursively downloads files from a GitHub repo path and writes
them to a local directory. Prints a JSON manifest to stdout.

Note: Branch names with slashes (e.g., feature/foo) are not
supported in URL parsing. Use the full tree URL and the script
will capture only the first path segment as the branch name.
"""

import argparse
import base64
import binascii
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MAX_FILES = 200
MAX_DEPTH = 10
SUBPROCESS_TIMEOUT = 30
# Polite delay between API calls to avoid rate-limit pressure
API_DELAY_SECONDS = 0.3


def run_gh(*args: str) -> str:
    """Run a gh CLI command and return stdout."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=SUBPROCESS_TIMEOUT,
    )
    return result.stdout


def check_gh_auth() -> None:
    """Verify gh CLI is authenticated."""
    try:
        subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            check=True,
            timeout=SUBPROCESS_TIMEOUT,
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
    except subprocess.TimeoutExpired:
        print(
            "Error: gh auth check timed out.",
            file=sys.stderr,
        )
        sys.exit(1)


def _validate_component(value: str, name: str) -> None:
    """Reject path traversal and shell metacharacters."""
    if re.search(r"[;$`|&<>\\\x00-\x1f]", value):
        print(
            f"Error: Invalid characters in {name}: {value[:200]}",
            file=sys.stderr,
        )
        sys.exit(1)
    if ".." in value.split("/"):
        print(
            f"Error: Path traversal in {name}: {value[:200]}",
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
    Branch names with slashes are not supported; the regex
    captures only the first segment after tree/blob.

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
            path = path.rsplit("/", 1)[0]
        elif url_type == "blob":
            path = ""
        _validate_component(repo, "repo")
        _validate_component(branch, "branch")
        if path:
            _validate_component(path, "path")
        return repo, path, branch

    # Shorthand: owner/repo
    m = re.match(r"^([^/]+/[^/]+)$", cleaned)
    if m:
        repo = m.group(1)
        _validate_component(repo, "repo")
        return repo, "", None

    print(
        f"Error: Could not parse GitHub URL: {url[:200]}\n"
        "Expected formats:\n"
        "  https://github.com/owner/repo/tree/branch/path\n"
        "  https://github.com/owner/repo/blob/branch/path\n"
        "  owner/repo",
        file=sys.stderr,
    )
    sys.exit(1)


def get_repo_metadata(repo: str) -> tuple[str, str | None]:
    """Get the default branch and license in one API call."""
    raw = run_gh(
        "api",
        f"repos/{repo}",
        "--jq",
        "{branch: .default_branch, license: .license.spdx_id}",
    )
    data = json.loads(raw)
    branch = data["branch"]
    license_id = data.get("license")
    if license_id in (None, "null", "NOASSERTION"):
        license_id = None
    return branch, license_id


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
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        if "rate limit" in stderr.lower():
            print(
                "Error: GitHub API rate limit exceeded. "
                "Wait a few minutes or check 'gh api rate_limit'.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(
            f"Warning: Failed to fetch {path}: {stderr}",
            file=sys.stderr,
        )
        return None
    except binascii.Error:
        print(
            f"Warning: Invalid base64 for {path}, skipping.",
            file=sys.stderr,
        )
        return None


def fetch_tree(
    repo: str,
    path: str,
    *,
    _depth: int = 0,
    _file_count: int = 0,
) -> dict[str, bytes | None]:
    """Recursively fetch all files under a path.

    Args:
        repo: GitHub repo in 'owner/repo' format.
        path: Directory path within the repo.
        _depth: Current recursion depth (internal).
        _file_count: Running file count (internal).

    Returns:
        Dict mapping relative paths to file content bytes.
    """
    if _depth > MAX_DEPTH:
        print(
            f"Error: Maximum directory depth ({MAX_DEPTH}) exceeded at {path}.",
            file=sys.stderr,
        )
        sys.exit(1)

    files: dict[str, bytes | None] = {}
    try:
        raw = run_gh(
            "api",
            f"repos/{repo}/contents/{path}",
        )
        entries = json.loads(raw)
    except subprocess.CalledProcessError:
        print(
            f"Error: Path '{path[:200]}' not found in {repo}.",
            file=sys.stderr,
        )
        sys.exit(1)
    except json.JSONDecodeError:
        print(
            f"Error: Unexpected API response for {repo}/{path[:200]}.",
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

        # Reject paths with traversal components
        if ".." in rel.split("/"):
            print(
                f"Warning: Skipping suspicious path: {rel}",
                file=sys.stderr,
            )
            continue

        if entry["type"] == "file":
            _file_count += 1
            if _file_count > MAX_FILES:
                print(
                    f"Error: Too many files (>{MAX_FILES}). Use a more specific path.",
                    file=sys.stderr,
                )
                sys.exit(1)
            content = fetch_file_content(repo, entry["path"])
            files[rel] = content
            time.sleep(API_DELAY_SECONDS)
        elif entry["type"] == "dir":
            sub = fetch_tree(
                repo,
                entry["path"],
                _depth=_depth + 1,
                _file_count=_file_count,
            )
            _file_count += len(sub)
            for sub_path, sub_content in sub.items():
                files[f"{rel}/{sub_path}"] = sub_content

    return files


def write_tree(
    files: dict[str, bytes | None],
    output_dir: Path,
) -> None:
    """Write fetched files to disk with path traversal protection."""
    resolved_base = output_dir.resolve()
    for rel_path, content in files.items():
        if content is None:
            continue
        out_file = (output_dir / rel_path).resolve()
        if not str(out_file).startswith(str(resolved_base) + "/"):
            print(
                f"Error: Path traversal detected: {rel_path}",
                file=sys.stderr,
            )
            sys.exit(1)
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
    args = parser.parse_args()

    check_gh_auth()

    repo, path, branch = parse_github_url(args.url)

    default_branch, license_id = get_repo_metadata(repo)
    if branch is None:
        branch = default_branch

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
