@echo off
cd /d C:\ai_survival
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
