#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_DIR="$ROOT_DIR/karnyx/heroes"
OUTPUT_DIR="$ROOT_DIR/characters/karnyx"

shopt -s nullglob
html_files=("$SOURCE_DIR"/*.html)

if (( ${#html_files[@]} == 0 )); then
  printf 'Aucune page HTML trouvée dans %s\n' "$SOURCE_DIR" >&2
  exit 1
fi

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m dicethrone_helper extract-karnyx \
  "${html_files[@]}" \
  --output "$OUTPUT_DIR" \
  --skip-up-to-date