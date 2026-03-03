#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_PATH="${1:-$ROOT_DIR/docs/session_snapshot.md}"
SOURCE_DOC="${2:-$ROOT_DIR/docs/development_assessment_and_followup.md}"

cd "$ROOT_DIR"
if command -v python3 >/dev/null 2>&1; then
  python3 -m driver.main snapshot --output "$OUTPUT_PATH" --source-doc "$SOURCE_DOC"
else
  python -m driver.main snapshot --output "$OUTPUT_PATH" --source-doc "$SOURCE_DOC"
fi
