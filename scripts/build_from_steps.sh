#!/usr/bin/env bash
set -euo pipefail

# Build bcfeed using the high-level steps from build_steps.md.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Configuration
PY_VERSION="${PY_VERSION:-3.14.2}"
VENV="${VENV:-$ROOT/.venv-build}"

ensure_pyenv() {
  if command -v pyenv >/dev/null 2>&1; then
    return
  fi
  echo "pyenv not found; please install pyenv before running this script." >&2
  exit 1
}

select_python() {
  ensure_pyenv
  local pybin
  pybin="$(pyenv which "python${PY_VERSION%.*}" 2>/dev/null || true)"
  # Try full version match if minor lookup fails
  if [ -z "$pybin" ]; then
    pybin="$(pyenv which "python${PY_VERSION}" 2>/dev/null || true)"
  fi
  if [ -z "$pybin" ]; then
    echo "Python $PY_VERSION not found in pyenv. Install it with: pyenv install $PY_VERSION" >&2
    exit 1
  fi
  echo "$pybin"
}

PYTHON_BIN="${PYTHON_BIN:-$(select_python)}"

# Recreate venv if missing or wrong version
if [ -x "$VENV/bin/python" ]; then
  VENV_VER="$("$VENV/bin/python" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")')"
  if [ "$VENV_VER" != "$PY_VERSION" ]; then
    echo "Rebuilding $VENV with $PYTHON_BIN (was Python $VENV_VER)"
    rm -rf "$VENV"
  fi
fi

if [ ! -d "$VENV" ]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi

source "$VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

python -m PyInstaller --clean --noconfirm bcfeed.spec

echo "Build complete. App bundle is in $ROOT/dist/bcfeed.app"
