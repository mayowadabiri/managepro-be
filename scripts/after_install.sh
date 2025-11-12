#!/bin/bash

cd /home/ec2-user/managepro

source .venv/bin/activate

sudo uv sync

make migrate