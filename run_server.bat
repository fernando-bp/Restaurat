@echo off
REM Script para ejecutar uvicorn en Windows

cd /d C:\Users\FernandoBohorquezPar\Desktop\Restaurat\mv_pos

REM Activar virtual environment
call .venv\Scripts\activate.bat

REM Ejecutar uvicorn
python -m uvicorn app.main:app --reload --port 8000

REM Si hay error, mostrar y esperar
if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR AL INICIAR UVICORN
    echo.
    pause
)
