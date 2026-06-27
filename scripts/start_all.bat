@echo off
echo ========================================
echo  Starting Security Monitor Application
echo ========================================
echo.

echo [1/2] Starting Backend (FastAPI on port 8000)...
start "Backend" cmd /k "cd /d c:\Users\adria\Desktop\proiectNou\backend && echo Backend is starting... && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [2/2] Starting Frontend (Vite + React on port 5173)...
start "Frontend" cmd /k "cd /d c:\Users\adria\Desktop\proiectNou\frontend && echo Frontend is starting... && npm run dev"

echo.
echo Both servers are starting up!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo.
echo Close this window to stop the servers.
pause
