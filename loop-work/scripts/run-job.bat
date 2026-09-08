@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
if exist "%ROOT%\.venv\Scripts\python.exe" (
  "%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\assemble.py" %*
) else (
  python "%ROOT%\scripts\assemble.py" %*
)
exit /b %ERRORLEVEL%
