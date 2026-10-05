@echo off
cd /d "%~dp0"
title Frontier NMS (pyMHF)
set "PYTHONPATH=%~dp0Core;%PYTHONPATH%"
".venv-nms\Scripts\pymhf.exe" run nmspy
pause
