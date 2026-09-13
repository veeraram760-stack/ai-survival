@echo off
echo Starting AI Survival Dashboard...
cd /d C:\ai_survival\dashboard

:loop
echo [%date% %time%] Starting dashboard... >> dashboard_24x7.log
npm run dev
echo [%date% %time%] Dashboard stopped, restarting in 5s... >> dashboard_24x7.log
timeout /t 5 /nobreak >nul
goto loop
