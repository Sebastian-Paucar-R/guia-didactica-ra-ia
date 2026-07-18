@echo off
echo ================================================
echo    Iniciando Backend - Tutor IA
echo ================================================
cd /d "%~dp0"

call backend\venv\Scripts\activate

echo Iniciando servidor...
python -m uvicorn backend.app.main:app --reload --port 8000

pause