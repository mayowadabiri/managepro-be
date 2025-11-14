#!/bin/bash
set -euo pipefail
LOG=/home/ec2-user/managepro/deploy-afterinstall.log
echo "=== AfterInstall started at $(date) ===" | tee -a "$LOG"

cd /home/ec2-user/managepro

# Use explicit python3 everywhere
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found" | tee -a "$LOG"
  exit 1
fi
PYTHON3=$(command -v python3)

# Create venv if missing
if [ ! -d ".venv" ]; then
  echo "Creating virtualenv at .venv using $PYTHON3" | tee -a "$LOG"
  # try to create venv normally
  "$PYTHON3" -m venv .venv || {
    echo "Failed to create venv with $PYTHON3 -m venv" | tee -a "$LOG"
    exit 1
  }
fi

VENV_PYTHON="/home/ec2-user/managepro/.venv/bin/python"
VENV_BIN_DIR="/home/ec2-user/managepro/.venv/bin"

# Activate venv in this script (sourcing is retained for readability)
# shellcheck disable=SC1091
source "$VENV_BIN_DIR/activate"

# Ensure pip exists in the venv. Try ensurepip first, then fallback to get-pip.py
if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
  echo "pip missing inside venv — attempting to bootstrap via ensurepip" | tee -a "$LOG"
  if "$VENV_PYTHON" -m ensurepip --upgrade >/dev/null 2>&1; then
    echo "ensurepip succeeded" | tee -a "$LOG"
  else
    echo "ensurepip not available or failed — attempting get-pip.py" | tee -a "$LOG"
    TMP_GET_PIP="/tmp/get-pip.py"
    if command -v curl >/dev/null 2>&1; then
      curl -sSfL https://bootstrap.pypa.io/get-pip.py -o "$TMP_GET_PIP" || {
        echo "Failed to download get-pip.py with curl" | tee -a "$LOG"
        exit 1
      }
    elif command -v wget >/dev/null 2>&1; then
      wget -qO "$TMP_GET_PIP" https://bootstrap.pypa.io/get-pip.py || {
        echo "Failed to download get-pip.py with wget" | tee -a "$LOG"
        exit 1
      }
    else
      echo "Neither curl nor wget available to fetch get-pip.py; cannot bootstrap pip" | tee -a "$LOG"
      exit 1
    fi

    # run get-pip.py using the venv python
    "$VENV_PYTHON" "$TMP_GET_PIP" || {
      echo "get-pip.py failed to install pip into venv" | tee -a "$LOG"
      rm -f "$TMP_GET_PIP" || true
      exit 1
    }
    rm -f "$TMP_GET_PIP" || true
  fi
fi

# Verify pip is available now
if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
  echo "pip still missing after bootstrap attempts" | tee -a "$LOG"
  exit 1
fi

# Use the venv python to upgrade packaging tools and install uv
echo "Upgrading pip/setuptools/wheel and installing uv using $VENV_PYTHON" | tee -a "$LOG"
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel | tee -a "$LOG"

# Install uv in venv (use -m pip to ensure venv-targeted install)
"$VENV_PYTHON" -m pip install uv | tee -a "$LOG"

# Prefer the venv-installed uv binary if present
UV_BIN="$VENV_BIN_DIR/uv"
if [ -x "$UV_BIN" ]; then
  echo "Using uv at $UV_BIN" | tee -a "$LOG"
  UV_CMD="$UV_BIN"
else
  # fallback to python -m uv (works if package provides a module entrypoint)
  UV_CMD="$VENV_PYTHON -m uv"
fi

# Sync/install dependencies via uv (will create/update uv.lock if needed)
echo "Running dependency sync: $UV_CMD sync" | tee -a "$LOG"
$UV_CMD sync | tee -a "$LOG"

# Run migrations using uv so it uses the venv python environment
# If uv isn't available or fails, fallback to using venv python directly for manage.py
set +e
$UV_CMD run python manage.py migrate | tee -a "$LOG"
UV_EXIT=$?
set -e

if [ $UV_EXIT -ne 0 ]; then
  echo "uv run migrate failed (exit $UV_EXIT) — attempting direct venv python manage.py migrate" | tee -a "$LOG"
  "$VENV_PYTHON" manage.py migrate | tee -a "$LOG"
fi

# Finished
echo "=== AfterInstall completed at $(date) ===" | tee -a "$LOG"
