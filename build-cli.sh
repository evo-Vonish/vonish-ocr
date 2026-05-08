#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pyinstaller click PyYAML
pyinstaller --onefile --name vonishocr cli/main.py
echo "CLI binary: dist/vonishocr"
