#!/bin/bash
set -e

echo "Restarting Gunicorn service..."

sudo systemctl daemon-reload       
sudo systemctl restart gunicorn    
sudo systemctl enable gunicorn     
sudo systemctl status gunicorn --no-pager -l || true