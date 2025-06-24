#!/bin/bash

cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv venv
    source venv/bin/activate
else
    source venv/bin/activate
fi

# Always install/update requirements
pip install -r requirements.txt

# Clear .pyc files
find . -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -r {} +

export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 src/leah_server.py "$@" 