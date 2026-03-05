#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <issue-number>"
  exit 1
fi

ISSUE_NUMBER="$1"
if ! [[ "$ISSUE_NUMBER" =~ ^[0-9]+$ ]]; then
  echo "Issue number must be an integer."
  exit 1
fi

CURRENT_BRANCH="$(git branch --show-current)"

if command -v gh >/dev/null 2>&1; then
  ISSUE_TITLE="$(gh issue view "$ISSUE_NUMBER" --json title --jq .title)"
  ISSUE_URL="$(gh issue view "$ISSUE_NUMBER" --json url --jq .url)"
else
  ISSUE_TITLE="issue-${ISSUE_NUMBER}"
  ISSUE_URL="(gh not installed; issue metadata unavailable)"
  echo "Warning: gh not found. Branch will be created without issue title slug."
fi

SLUG="$(echo "$ISSUE_TITLE" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
if [[ -z "$SLUG" ]]; then
  SLUG="issue-${ISSUE_NUMBER}"
fi

BRANCH_NAME="issue/${ISSUE_NUMBER}-${SLUG}"
git checkout -b "$BRANCH_NAME"

echo "Created branch: $BRANCH_NAME (from $CURRENT_BRANCH)"
echo "Issue: #$ISSUE_NUMBER"
echo "Issue URL: $ISSUE_URL"
echo
echo "Next steps:"
echo "  1) Implement changes"
echo "  2) Run tests"
echo "  3) git add . && git commit -m \"fix: <summary> (#$ISSUE_NUMBER)\""
echo "  4) git push -u origin $BRANCH_NAME"
echo "  5) gh pr create --fill --base main --head $BRANCH_NAME"
