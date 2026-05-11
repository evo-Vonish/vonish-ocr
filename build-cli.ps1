$ErrorActionPreference = "Stop"

python -m pip install --upgrade pyinstaller click PyYAML
pyinstaller --onefile --name vocr cli/main.py

$src = Join-Path $PSScriptRoot "dist\vocr.exe"
$compat = Join-Path $PSScriptRoot "dist\vonishocr.exe"
if (Test-Path $src) {
  Copy-Item -LiteralPath $src -Destination $compat -Force
}

Write-Host "CLI binary: dist\vocr.exe"
Write-Host "Compatibility alias: dist\vonishocr.exe"
