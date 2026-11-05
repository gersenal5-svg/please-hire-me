#!/usr/bin/env bash
# please-hire-me (approval fork) — REVIEW. Opens the list of found listings in your browser so you can
# approve or reject each one. Nothing is submitted here.
#   ./review.sh          review page in your browser
#   ./review.sh --cli    same thing, in the terminal
set -euo pipefail
cd "$(dirname "$0")"
if [ "${1:-}" = "--cli" ]; then exec python3 scripts/review.py cli; fi
exec python3 scripts/review.py serve
