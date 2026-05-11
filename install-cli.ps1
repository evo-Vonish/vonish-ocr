$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$bin = Join-Path $env:LOCALAPPDATA "VonishOCR\bin"
New-Item -ItemType Directory -Path $bin -Force | Out-Null

$vocr = Join-Path $bin "vocr.cmd"
$compat = Join-Path $bin "vonishocr.cmd"

@"
@echo off
set "VONISH_HOME=$root"
python -m cli.main %*
"@ | Set-Content -LiteralPath $vocr -Encoding ASCII

@"
@echo off
set "VONISH_HOME=$root"
python -m cli.main %*
"@ | Set-Content -LiteralPath $compat -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User") -split ";" | Where-Object { $_ }
if ($userPath -notcontains $bin) {
  $nextPath = ($userPath + $bin) -join ";"
  [Environment]::SetEnvironmentVariable("Path", $nextPath, "User")
  Write-Host "Added to user PATH: $bin"
  Write-Host "Open a new terminal before using vocr globally."
}

Write-Host "Installed: $vocr"
Write-Host "Compatibility alias: $compat"
