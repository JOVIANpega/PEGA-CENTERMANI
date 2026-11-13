@echo off
chcp 65001 >nul
title Centimani Studio V2.4 - 智慧腳本健檢修復與母體產生工作台
cd /d "%~dp0"
echo ============================================================================
echo   Centimani Studio V2.4 - 啟動全螢幕瀏覽器模式 (127.0.0.1:8765)
echo   1. 健檢修復：直接在「原檔案所在資料夾」產出 *_FIXED.xlsx 與自動簽章！
echo   2. 簡潔書籤：點選後只顯示當前功能，另一個完全隱藏不佔螢幕！
echo ============================================================================
powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue; if ($c) { $c.OwningProcess | Select-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }"
python app_server.py
pause
