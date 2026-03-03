#!/usr/bin/env bash
set -euo pipefail

if [ "${#}" -lt 4 ]; then
  echo "usage: scripts/doc_update.sh <date> <change> <modules_csv> <verify_cmd> [result] [risk]"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATE_TEXT="$1"
CHANGE_TEXT="$2"
MODULES_CSV="$3"
VERIFY_CMD="$4"
RESULT_TEXT="${5:-PASS}"
RISK_TEXT="${6:-}"

cd "$ROOT_DIR"
if command -v python3 >/dev/null 2>&1; then
  python3 -m driver.main doc-update \
    --date "$DATE_TEXT" \
    --change "$CHANGE_TEXT" \
    --modules "$MODULES_CSV" \
    --verify-command "$VERIFY_CMD" \
    --result "$RESULT_TEXT" \
    --risk "$RISK_TEXT"
else
  python -m driver.main doc-update \
    --date "$DATE_TEXT" \
    --change "$CHANGE_TEXT" \
    --modules "$MODULES_CSV" \
    --verify-command "$VERIFY_CMD" \
    --result "$RESULT_TEXT" \
    --risk "$RISK_TEXT"
fi
