#!/bin/bash
set -euo pipefail
LOG=/home/ec2-user/managepro/deploy-afterinstall.log
echo "=== AfterInstall started at $(date) ===" | tee -a "$LOG"

cd /home/ec2-user/managepro

# Ensure Python exists
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found" | tee -a "$LOG"
  exit 1
fi

# Create venv if missing
if [ ! -d ".venv" ]; then
  echo "Creating virtualenv at .venv" | tee -a "$LOG"
  python3 -m venv .venv
fi

# Activate venv
# shellcheck disable=SC1091
source .venv/bin/activate

# Upgrade pip and install uv into the venv (ensures uv is available)
python -m pip install --upgrade pip setuptools wheel
pip install uv

# Optional: if you manage deps via requirements.txt instead, use that:
# pip install -r requirements.txt

# Sync/install dependencies via uv (will create/update uv.lock if needed)
uv sync | tee -a "$LOG"

# Run migrations using uv so it uses the venv python environment
# Alternatively call manage.py directly: python manage.py migrate
uv run python manage.py migrate | tee -a "$LOG"

echo "=== AfterInstall completed at $(date) ===" | tee -a "$LOG"
