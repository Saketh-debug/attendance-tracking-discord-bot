#!/bin/bash
cd "$(dirname "$0")"

# Activate the virtual environment
source venv/bin/activate

# Start the launcher UI
python3 launcher.py
