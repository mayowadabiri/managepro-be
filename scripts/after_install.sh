#!/usr/bin/env bash
# after_install.sh — robust for managepro (CodeDeploy AfterInstall)
set -euo pipefail

LOG=/home/ec2-user/managepro/deploy-afterinstall.log
APP_DIR=/home/ec2-user/managepro
VENV_DIR="$APP_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_BIN_DIR="$VENV_DIR/bin"

echo "=== AfterInstall started at $(date -u) ===" | tee -a "$LOG"
cd "$APP_DIR"

# ensure python3 exists
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found on PATH" | tee -a "$LOG"
  exit 1
fi
PYTHON3=$(command -v python3)
echo "Using system python: $PYTHON3" | tee -a "$LOG"

# create venv if missing
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtualenv at $VENV_DIR using $PYTHON3" | tee -a "$LOG"
  "$PYTHON3" -m venv "$VENV_DIR"
fi

# activate venv
# shellcheck disable=SC1091
source "$VENV_BIN_DIR/activate"

# -----------------------------------------------------------------------------
# Helper: ensure pip exists in the venv (try ensurepip, fallback to get-pip.py)
ensure_pip_in_venv() {
  if "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
    echo "pip already present in venv" | tee -a "$LOG"
    return 0
  fi

  echo "Bootstrapping pip into venv (ensurepip -> get-pip fallback)" | tee -a "$LOG"
  if "$VENV_PYTHON" -m ensurepip --upgrade >/dev/null 2>&1; then
    echo "ensurepip succeeded" | tee -a "$LOG"
    return 0
  fi

  TMP_GET_PIP="/tmp/get-pip-$$.py"
  if command -v curl >/dev/null 2>&1; then
    curl -sSfL https://bootstrap.pypa.io/get-pip.py -o "$TMP_GET_PIP" || {
      echo "Failed to download get-pip.py with curl" | tee -a "$LOG"
      return 1
    }
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TMP_GET_PIP" https://bootstrap.pypa.io/get-pip.py || {
      echo "Failed to download get-pip.py with wget" | tee -a "$LOG"
      return 1
    }
  else
    echo "Neither curl nor wget available to fetch get-pip.py" | tee -a "$LOG"
    return 1
  fi

  # Install pip using venv python
  if ! "$VENV_PYTHON" "$TMP_GET_PIP" >/dev/null 2>&1; then
    echo "get-pip.py failed to install pip into venv" | tee -a "$LOG"
    rm -f "$TMP_GET_PIP" || true
    return 1
  fi
  rm -f "$TMP_GET_PIP" || true
  echo "pip bootstrapped successfully" | tee -a "$LOG"
  return 0
}
# -----------------------------------------------------------------------------

# Bootstrap pip initially (so we can run uv if uv needs pip); ignore errors here — we'll ensure pip after uv too.
ensure_pip_in_venv || echo "initial pip bootstrap failed (will re-check after sync)" | tee -a "$LOG"

# upgrade packaging tools (best-effort)
echo "Upgrading pip/setuptools/wheel in venv (best-effort)" | tee -a "$LOG"
if "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
  "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || {
    echo "pip upgrade warning (continuing)" | tee -a "$LOG"
  }
else
  echo "pip missing now — will ensure after uv sync" | tee -a "$LOG"
fi

# Install uv (optional) and choose sync command
echo "Installing uv (if desired) into venv (non-fatal)" | tee -a "$LOG"
"$VENV_PYTHON" -m pip install --upgrade uv >/dev/null 2>&1 || {
  echo "uv install failed or not needed (continuing)" | tee -a "$LOG"
}

UV_BIN="$VENV_BIN_DIR/uv"
if [ -x "$UV_BIN" ]; then
  UV_CMD="$UV_BIN"
else
  UV_CMD="$VENV_PYTHON -m uv"
fi

# Run dependency sync (do not fail entire deploy if uv sync fails)
echo "Running dependency sync: $UV_CMD sync" | tee -a "$LOG"
set +e
$UV_CMD sync | tee -a "$LOG"
UV_EXIT=$?
set -e
if [ "$UV_EXIT" -ne 0 ]; then
  echo "uv sync returned $UV_EXIT (continuing to explicit installs)" | tee -a "$LOG"
fi

# IMPORTANT: ensure pip again AFTER uv sync (uv may have altered venv and removed pip)
if ! ensure_pip_in_venv; then
  echo "ERROR: could not bootstrap pip after uv sync" | tee -a "$LOG"
  # fail early so CodeDeploy logs show the pip bootstrap problem
  exit 1
fi

# Now ensure packaging tools and gunicorn exist in venv (this is the critical guarantee)
echo "Ensuring pip/setuptools/wheel and gunicorn are present in venv" | tee -a "$LOG"
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel gunicorn | tee -a "$LOG"

# Run Django migrations (non-fatal)
echo "Running Django migrations (manage.py migrate --noinput)" | tee -a "$LOG"
set +e
"$VENV_PYTHON" manage.py migrate --noinput | tee -a "$LOG"
MIG_EXIT=$?
set -e
if [ $MIG_EXIT -ne 0 ]; then
  echo "Migrations exit code $MIG_EXIT — continuing; inspect logs if needed" | tee -a "$LOG"
fi

# Final systemd housekeeping & restart gunicorn safely
echo "Reset failed state and restarting gunicorn.service" | tee -a "$LOG"
sudo systemctl reset-failed gunicorn.service || true
sudo systemctl daemon-reload || true
sudo systemctl restart gunicorn.service || true
sudo systemctl enable gunicorn.service || true

echo "=== AfterInstall completed at $(date -u) ===" | tee -a "$LOG"
