@echo off
chcp 65001 >nul
title Centimani Studio - 一鍵全功能端到端自動驗收
cd /d "%~dp0centimani_studio"
python -u tests\verify_all_features.py
echo.
pause
