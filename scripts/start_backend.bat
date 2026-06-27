@echo off
cd /d c:\Users\adria\Desktop\proiectNou\backend
echo Starting Backend (FastAPI)...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
