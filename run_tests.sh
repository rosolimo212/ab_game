#!/usr/bin/env bash
# Запуск автотестов слоя 1 (pytest).
# Использование: ./run_tests.sh
# Опции pytest можно передать аргументами: ./run_tests.sh -v

set -euo pipefail
cd "$(dirname "$0")"

if [[ -x .venv/bin/pytest ]]; then
  exec .venv/bin/pytest tests/ -q "$@"
fi

if command -v pytest >/dev/null 2>&1; then
  exec pytest tests/ -q "$@"
fi

echo "pytest не найден. Сделайте:" >&2
echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt" >&2
echo "или минимум: .venv/bin/pip install numpy PyYAML pytest" >&2
exit 1
