#!/usr/bin/env bash
# Проверки перед коммитом: слой 1 (pytest) + слой 2 (business_checks).
# Использование: ./pre_commit_check.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ -x .venv/bin/python ]]; then
  PYTHON=".venv/bin/python"
elif [[ -x .venv/bin/pytest ]]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

echo "pre_commit_check: pytest (слой 1)…"
if [[ -x .venv/bin/pytest ]]; then
  .venv/bin/pytest tests/ -q
else
  "$PYTHON" -m pytest tests/ -q
fi

echo "pre_commit_check: business_checks (слой 2)…"
"$PYTHON" business_checks.py

echo "pre_commit_check: OK"
