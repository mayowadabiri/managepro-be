#!/bin/bash

cd /home/ec2-user/managepro

source .venv/bin/activate

uv sync

make migrate