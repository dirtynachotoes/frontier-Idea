@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\Core"
python -m frontier.probe --scout-link
