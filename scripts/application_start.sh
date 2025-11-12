#!/bin/bash
set -e

echo "Restarting Gunicorn service..."

sudo systemctl daemon-reload       # reload unit files (optional, safe)
sudo systemctl restart gunicorn    # restart gunicorn service
sudo systemctl enable gunicorn     # ensure it starts on reboot
sudo systemctl status gunicorn --no-pager -l || true