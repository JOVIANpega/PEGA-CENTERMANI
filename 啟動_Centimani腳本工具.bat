@echo off
chcp 65001 >nul
title Centimani Studio V2.4 (Build v0.8.028)
cd /d "%~dp0centimani_studio"
powershell -NoProfile -Command "$p = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue; if ($p) { $p.OwningProcess | Select-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }; Get-Process -Name 'EXCEL*' -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -eq 0 } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }"
start "" python "%~dp0centimani_studio\app_server.py"
