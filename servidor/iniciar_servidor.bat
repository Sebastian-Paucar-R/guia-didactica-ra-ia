@echo off
echo ================================================
echo    Iniciando Backend - Tutor IA
echo ================================================
cd /d "%~dp0"

REM Activar entorno virtual (ajuste la ruta si es necesario)
call backend\venv\Scripts\activate 2>nul
if errorlevel 1 (
    call venv\Scripts\activate 2>nul
)

set PYTHONPATH=%cd%\backend

echo.
echo Iniciando servidor en http://127.0.0.1:8000 ...
echo.

python -m uvicorn app.main:app --reload --port 8000 --app-dir backend

pause