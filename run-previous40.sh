#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec "${TUA_PYTHON:-$HOME/TUA-Bench/.venv/bin/python}" -m tua.local.run "$@"
