#!/usr/bin/env bash

set -euo pipefail

if [[ ${1:-} == "--all" ]]; then
  if (( $# != 1 )); then
    printf 'Usage: %s --all\n' "$0" >&2
    exit 2
  fi
elif (( $# != 3 )); then
  printf 'Usage: %s HERO_SLUG HERO_SLUG HERO_SLUG\n       %s --all\n' "$0" "$0" >&2
  exit 2
fi

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m dicethrone_helper matchups "$@" --skip-up-to-date