@echo off
setlocal
set "VONISH_HOME=%~dp0"
python -m cli.main %*
