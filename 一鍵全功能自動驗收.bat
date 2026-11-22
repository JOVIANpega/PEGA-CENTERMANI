@echo off
chcp 65001 >nul
title Centimani Studio V2.4 - E2E Auto Verifier (Build v0.5.9)
cd /d "%~dp0centimani_studio"
python -u "%~dp0centimani_studio\tests\verify_all_features.py"
echo.
pause
