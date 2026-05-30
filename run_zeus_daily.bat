@echo off
:: ============================================================
::  Zeus Daily Runner — chiamato da Windows Task Scheduler
::  Esegue l'orchestrator + commit + push su GitHub.
::  Cron equivalente: ogni giorno alle 08:05 (ora locale)
:: ============================================================
setlocal

set ZEUS_DIR=C:\Users\docum\Desktop\zeus
set LOG_FILE=%ZEUS_DIR%\output\run_zeus_daily.log
set CODEX_PY=C:\Users\docum\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
set SYS_PY=C:\Users\docum\AppData\Local\Programs\Python\Python311\python.exe

:: Scegli Python disponibile
if exist "%CODEX_PY%" (
    set PYTHON=%CODEX_PY%
) else if exist "%SYS_PY%" (
    set PYTHON=%SYS_PY%
) else (
    echo [ERROR] Python non trovato. >> "%LOG_FILE%"
    exit /b 1
)

echo [%DATE% %TIME%] Zeus Daily Runner START >> "%LOG_FILE%"
echo    Python: %PYTHON% >> "%LOG_FILE%"

:: Carica .env come variabili d'ambiente
for /f "usebackq tokens=1,2 delims==" %%A in ("%ZEUS_DIR%\.env") do (
    if not "%%A"=="" if not "%%A:~0,1%"=="#" set %%A=%%B
)

:: Esegui orchestrator (run-once mode)
cd /d "%ZEUS_DIR%"
"%PYTHON%" scheduler.py --once >> "%LOG_FILE%" 2>&1
echo [%DATE% %TIME%] Zeus Daily Runner END (exit: %ERRORLEVEL%) >> "%LOG_FILE%"

endlocal
