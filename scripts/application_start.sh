#!/bin/bash
set -e

echo "Restarting Gunicorn service..."

sudo systemctl reset-failed gunicorn.service || true
sudo systemctl daemon-reload || true
sudo systemctl restart gunicorn.service || true
sudo systemctl enable gunicorn.service || true