#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pyinstaller click PyYAML
pyinstaller --onefile --name vocr cli/main.py
cp "dist/vocr" "dist/vonishocr" 2>/dev/null || true
echo "CLI binary: dist/vocr"
echo "Compatibility alias: dist/vonishocr"
