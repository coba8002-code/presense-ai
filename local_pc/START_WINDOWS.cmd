@echo off
cd /d "%~dp0.."
py -3.12 local_pc\pc.py doctor --output pc-report.json
pause
