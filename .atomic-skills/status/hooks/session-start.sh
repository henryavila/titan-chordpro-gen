#!/usr/bin/env bash
# SessionStart hook: injects project-status into context
set -euo pipefail

STATUS_FILE="$(pwd)/.atomic-skills/PROJECT-STATUS.md"
if [[ -f "$STATUS_FILE" ]]; then
  echo "=== PROJECT STATUS ==="
  head -60 "$STATUS_FILE"
  echo "====================="
fi
