#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <issue-number> [extra args...]"
  echo "Example: $0 123 --test-command 'python3 -m unittest discover -s tests -q'"
  exit 1
fi

ISSUE_NUMBER="$1"
shift

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if command -v python3 >/dev/null 2>&1; then
  python3 -m driver.main issue-autopilot --issue-number "$ISSUE_NUMBER" "$@"
else
  python -m driver.main issue-autopilot --issue-number "$ISSUE_NUMBER" "$@"
fi
