@echo off
chcp 65001 >nul
:: Start Anthropic-to-OpenAI proxy for Claude Code + DeepSeek
cd /d "F:\VonishOCR\backend"
python anthropic_proxy.py
pause
