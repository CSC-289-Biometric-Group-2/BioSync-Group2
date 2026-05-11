#!/bin/bash
# run.sh — Start the BioSync application
# Run from the repo root after setup.sh: bash run.sh

set -e

# Activate virtual environment
source venv/bin/activate

echo "Starting BioSync..."
echo "The app will be available at http://localhost:5000"
echo "Press Ctrl+C to stop."
echo ""

# BioSync uses an app factory in BioSync/__init__.py
export FLASK_APP=BioSync
export FLASK_DEBUG=1

flask run --host=0.0.0.0 --port=5000
