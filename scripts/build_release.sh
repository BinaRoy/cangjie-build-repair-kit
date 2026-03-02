#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${1:-$ROOT_DIR/dist/product_bundle}"
ZIP_PATH="${2:-$ROOT_DIR/release/product_bundle.zip}"

cd "$ROOT_DIR"
python -m driver.main export --output-dir "$OUTPUT_DIR" --force
mkdir -p "$(dirname "$ZIP_PATH")"
rm -f "$ZIP_PATH"
(
  cd "$OUTPUT_DIR"
  zip -r "$ZIP_PATH" .
)
echo "release zip generated: $ZIP_PATH"
