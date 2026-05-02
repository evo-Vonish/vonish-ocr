@echo off
echo Starting VonishOCR dev servers...

cd /d %~dp0\..

start "VonishOCR Backend" cmd /k "cd backend && python main.py"
start "VonishOCR Frontend" cmd /k "cd frontend && npm install && npm run dev"

echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
pause
