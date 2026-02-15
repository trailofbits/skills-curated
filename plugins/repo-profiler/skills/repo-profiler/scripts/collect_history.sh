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
