#!/bin/bash

cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
else
    source venv/bin/activate
fi

# Always install/update requirements
pip install -r requirements.txt

export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 src/leah_server.py 