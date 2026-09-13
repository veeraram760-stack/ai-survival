@echo off
echo Starting AI Survival Backend...
cd /d C:\ai_survival

:loop
echo [%date% %time%] Starting backend... >> backend_24x7.log
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
echo [%date% %time%] Backend stopped, restarting in 5s... >> backend_24x7.log
timeout /t 5 /nobreak >nul
goto loop
