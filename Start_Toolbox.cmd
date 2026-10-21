@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 server.py --open
  goto end
)
where python >nul 2>nul
if %errorlevel% equ 0 (
  python server.py --open
  goto end
)
echo Python 3.11 oder neuer wird benoetigt.
:end
pause
