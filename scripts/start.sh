#!/bin/sh
set -eu

APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$APP_ROOT"

# A single process keeps the demo's in-memory request limits consistent.
# Render injects PORT; local use defaults to 8765.
exec python -m uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8765}" --workers 1
