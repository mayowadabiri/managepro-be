#!/usr/bin/env bash
# application_start.sh — safe service start for CodeDeploy ApplicationStart
set -euo pipefail

echo "=== ApplicationStart $(date -u) ==="

# make sure systemd has a fresh view & clear previous failed state to allow restart
sudo systemctl reset-failed gunicorn.service || true
sudo systemctl daemon-reload

# restart and enable
sudo systemctl restart gunicorn.service
sudo systemctl enable gunicorn.service

# show status (non-fatal)
sudo systemctl status gunicorn.service --no-pager -l || true

echo "=== ApplicationStart completed ==="
