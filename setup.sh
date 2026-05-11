#!/bin/bash
# setup.sh — One-time environment setup for BioSync
# Run this from the repo root after cloning: bash setup.sh

set -e  # Stop on any error

echo "=== Setting up BioSync ==="

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip -q

# Core Flask dependencies (from BioSync/requirements.txt)
pip install -r BioSync/requirements.txt -q

# Additional dependencies used by BioSync
pip install pdfplumber python-docx pandas numpy -q

echo ""
echo "Initializing the database..."
export FLASK_APP=BioSync
flask init-db

echo ""
echo "=== Setup complete ==="
echo "Run the app with: bash run.sh"
