#!/usr/bin/env bash
# after_install.sh — idempotent deploy helper for managepro
set -euo pipefail

LOG=/home/ec2-user/managepro/deploy-afterinstall.log
APP_DIR=/home/ec2-user/managepro
VENV_DIR="$APP_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_BIN_DIR="$VENV_DIR/bin"

echo "=== AfterInstall started at $(date -u) ===" | tee -a "$LOG"
cd "$APP_DIR"

# --- ensure python3 exists ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found on PATH" | tee -a "$LOG"
  exit 1
fi

PYTHON3=$(command -v python3)
echo "Using system python: $PYTHON3" | tee -a "$LOG"

# --- ensure venv exists ---
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtualenv at $VENV_DIR using $PYTHON3" | tee -a "$LOG"
  "$PYTHON3" -m venv "$VENV_DIR"
fi

# Activate venv for the duration of this script
# shellcheck disable=SC1091
source "$VENV_BIN_DIR/activate"

# --- bootstrap pip in venv if missing ---
if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
  echo "pip missing inside venv — attempting ensurepip" | tee -a "$LOG"
  if "$VENV_PYTHON" -m ensurepip --upgrade >/dev/null 2>&1; then
    echo "ensurepip succeeded" | tee -a "$LOG"
  else
    echo "ensurepip failed; trying get-pip.py" | tee -a "$LOG"
    TMP_GET_PIP="/tmp/get-pip.py"
    if command -v curl >/dev/null 2>&1; then
      curl -sSfL https://bootstrap.pypa.io/get-pip.py -o "$TMP_GET_PIP"
    elif command -v wget >/dev/null 2>&1; then
      wget -qO "$TMP_GET_PIP" https://bootstrap.pypa.io/get-pip.py
    else
      echo "ERROR: neither curl nor wget available to bootstrap pip" | tee -a "$LOG"
      exit 1
    fi
    "$VENV_PYTHON" "$TMP_GET_PIP"
    rm -f "$TMP_GET_PIP"
  fi
fi

# verify pip now available
if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
  echo "ERROR: pip still not available in venv after bootstrap" | tee -a "$LOG"
  exit 1
fi

# --- upgrade packaging tools ---
echo "Upgrading pip/setuptools/wheel in venv" | tee -a "$LOG"
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || {
  echo "WARNING: pip upgrade failed (continuing)" | tee -a "$LOG"
}

# --- install uv (optional) and choose sync command ---
echo "Installing uv (if used) into venv" | tee -a "$LOG"
"$VENV_PYTHON" -m pip install --upgrade uv >/dev/null 2>&1 || {
  echo "uv install failed or not needed (continuing)" | tee -a "$LOG"
}

UV_BIN="$VENV_BIN_DIR/uv"
if [ -x "$UV_BIN" ]; then
  UV_CMD="$UV_BIN"
else
  UV_CMD="$VENV_PYTHON -m uv"
fi

# --- dependency sync: try uv sync but always ensure requirements/gunicorn after ---
echo "Running dependency sync: $UV_CMD sync" | tee -a "$LOG" || true
# run it but do not fail whole script if uv sync fails (we'll still ensure deps below)
set +e
$UV_CMD sync | tee -a "$LOG"
UV_EXIT=$?
set -e
if [ "$UV_EXIT" -ne 0 ]; then
  echo "uv sync returned $UV_EXIT (continuing to explicit installs)" | tee -a "$LOG"
fi

# --- ensure runtime packages in venv: prefer requirements.txt if present ---
echo "Ensuring runtime dependencies in venv" | tee -a "$LOG"
if [ -f "$APP_DIR/requirements.txt" ]; then
  echo "Installing from requirements.txt" | tee -a "$LOG"
  "$VENV_PYTHON" -m pip install --upgrade -r "$APP_DIR/requirements.txt" | tee -a "$LOG"
else
  echo "requirements.txt not found — ensuring gunicorn present" | tee -a "$LOG"
  "$VENV_PYTHON" -m pip install --upgrade gunicorn | tee -a "$LOG"
fi

# --- run django migrations (use venv python) ---
echo "Running Django migrations" | tee -a "$LOG"
set +e
"$VENV_PYTHON" manage.py migrate --noinput | tee -a "$LOG"
MIG_EXIT=$?
set -e
if [ $MIG_EXIT -ne 0 ]; then
  echo "Migrations reported exit $MIG_EXIT; check logs above" | tee -a "$LOG"
fi