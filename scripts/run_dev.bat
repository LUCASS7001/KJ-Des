@echo off
rem KJ Des - run from source (developer mode).
rem --source-dev: no installed recovery target is required; after a hard
rem crash the hosts block is cleaned on the next start instead of at logon.
chcp 65001 >nul
set "ROOT=%~dp0.."
pushd "%ROOT%" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv || goto :fail
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
)
".venv\Scripts\python.exe" app\main.py --source-dev %*
popd
exit /b %errorlevel%
:fail
echo [ERROR] Python 3.10+ is required (https://python.org).
popd
pause
exit /b 1
