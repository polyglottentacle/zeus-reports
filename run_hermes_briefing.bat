@echo off
:: ============================================================
::  Hermes Briefing — chiamato da Windows Task Scheduler
::  Scarica daily_report.json da GitHub e manda briefing Telegram.
::  Task: ogni giorno alle 08:10 (dopo il daily runner Zeus)
:: ============================================================
setlocal

set ZEUS_DIR=C:\Users\docum\Desktop\zeus
set LOG_FILE=%ZEUS_DIR%\output\run_hermes.log
set CODEX_PY=C:\Users\docum\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
set SYS_PY=C:\Users\docum\AppData\Local\Programs\Python\Python311\python.exe

if exist "%CODEX_PY%" (set PYTHON=%CODEX_PY%) else (set PYTHON=%SYS_PY%)

echo [%DATE% %TIME%] Hermes Briefing START >> "%LOG_FILE%"

:: Carica variabili d'ambiente da .env
for /f "usebackq tokens=1,2 delims==" %%A in ("%ZEUS_DIR%\.env") do (
    if not "%%A"=="" if not "%%A:~0,1%"=="#" set %%A=%%B
)

cd /d "%ZEUS_DIR%"
"%PYTHON%" hermes\briefing.py >> "%LOG_FILE%" 2>&1
echo [%DATE% %TIME%] Hermes Briefing END (exit: %ERRORLEVEL%) >> "%LOG_FILE%"

endlocal
