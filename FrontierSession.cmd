@echo off
cd /d "%~dp0"
title Frontier Session
powershell -NoProfile -ExecutionPolicy Bypass -File Tools\session_preflight.ps1
if errorlevel 1 (
  echo A Frontier Core is already running. Not starting a second one. See Saves\Guardian_Test\Logs\session-preflight.txt
) else (
  start "Frontier Core" cmd /k StartGuardianLocomotion.cmd
)
start "Frontier Readiness Watch" cmd /k python Tools\watch_readiness.py
start "Frontier Motion Watch" cmd /k python Tools\watch_motion.py
timeout /t 5 >nul
exit
