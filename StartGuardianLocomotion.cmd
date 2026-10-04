@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp0Core;%PYTHONPATH%"
python -m frontier.probe --scout-link --guardian-locomotion
pause
