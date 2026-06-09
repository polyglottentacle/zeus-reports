@echo off
setlocal
set "ZEUS_DIR=%~dp0"
set "ZEUS_DIR=%ZEUS_DIR:~0,-1%"
set "CODEX_PY=C:\Users\docum\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "SYS_PY=C:\Users\docum\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%CODEX_PY%" (set "PYTHON=%CODEX_PY%") else (set "PYTHON=%SYS_PY%")
cd /d "%ZEUS_DIR%"
"%PYTHON%" hermes\briefing.py >> "%ZEUS_DIR%\output\run_hermes.log" 2>&1
exit /b %ERRORLEVEL%
endlocal
