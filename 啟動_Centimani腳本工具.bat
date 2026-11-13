@echo off
chcp 65001 >nul
title Centimani Studio V2.4 - 智慧腳本健檢修復與母體產生工作台
cd /d "%~dp0centimani_studio"
powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue; if ($c) { $c.OwningProcess | Select-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }"
start "" python app_server.py
