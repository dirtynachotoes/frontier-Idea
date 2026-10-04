@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1
set "PYTHONPATH=%CD%\Core"
python -m compileall -q Core Adapters Tools Tests
if errorlevel 1 exit /b 1
python -m unittest discover -s Tests -v
if errorlevel 1 exit /b 1
exit /b 0
