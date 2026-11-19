@echo off
where python >nul 2>nul
if %errorlevel%==0 (python "%~dp0cockpit_hub.py" %*) else (py -3 "%~dp0cockpit_hub.py" %*)
