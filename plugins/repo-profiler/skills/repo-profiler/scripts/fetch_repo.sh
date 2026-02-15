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

gh repo clone "${REPO}" "${DEST}" -- --single-branch

# Get repo metadata
DEFAULT_BRANCH=$(git -C "${DEST}" rev-parse --abbrev-ref HEAD)
CONTRIBUTOR_COUNT=$(gh api "repos/${REPO}/contributors" --jq 'length' 2>/dev/null || echo "0")
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
