@echo off
cd /d %~dp0
powershell -ExecutionPolicy Bypass -File "%~dp0update_and_run.ps1"
pause
