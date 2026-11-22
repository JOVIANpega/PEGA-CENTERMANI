# Centimani Studio V2.4 — AI Agent Development & Regression Verification Rules

任何 AI 代理（Antigravity / Claude / Cursor / Copilot）在未來修改或擴充本專案時，**必須嚴格遵守以下 5 條開發鐵則**：

1. **強制執行一鍵全功能自動驗收 (`verify_all_features.py`)**：
   - 每次修改完任何後端 (`.py`) 或前端 (`.html` / `.js`) 程式碼後，**必須執行**：
     ```powershell
     python centimani_studio\tests\test_studio_core.py
     python centimani_studio\tests\verify_all_features.py
     ```
   - 該驗收腳本除了測試所有核心 API、Excel 淡藍/亮黃底色、預設開啟 Sheet、INI 獨立存檔外，還會自動呼叫 `node --check` 掃描所有前端 `.js` 與 `index.html` 內嵌腳本的 JavaScript 語法錯誤、檢查前後端 Build 版本號一致性，以及檢查 `.bat` 批次檔是否維持標準 Windows `CRLF (\r\n)` 格式。

2. **新增功能必須同步擴充 `verify_all_features.py`**：
   - 未來每當新增一個 API 或前端功能，**必須同步在 `centimani_studio/tests/verify_all_features.py` 中新增對應的 `check(...)` 驗收斷言**，讓自動驗收項目隨著專案功能同步成長，杜絕「改好新功能卻弄壞舊功能」的迴歸錯誤。

3. **每次完成修改必須進一版本號 (`Build vX.Y.Z`) 並 Commit 至 Git**：
   - 必須同步更新以下四處的版本號與快取參數：
     - `centimani_studio/web/index.html` 頂部 `#appVersionBadge` (`Build vX.Y.Z`)
     - `centimani_studio/web/index.html` 內所有 `<script src="/js/...?v=X.Y.Z">`
     - `centimani_studio/app_server.py` 啟動訊息 (`Build vX.Y.Z`)
     - `啟動_Centimani腳本工具.bat` 與 `一鍵全功能自動驗收.bat` 的 `title`

4. **Windows `.bat` 批次檔必須維持 `CRLF (\r\n)` 換行格式**：
   - 切勿將 `.bat` 檔存為 `LF (\n)`，否則 Windows `cmd.exe` 在執行 `chcp 65001` 後會發生位元組位移錯誤（例如將 `title` 截斷為 `'tle' 不是內部或外部命令`）。

5. **切勿由 AI 背景沙盒 (`run_command`) 殘留 `app_server.py` 或背景 `EXCEL.EXE`**：
   - AI 工具的 `run_command` 執行於隱藏的虛擬桌面 (`exebox`)，若在其中啟動 `app_server.py` 或留下無視窗的 `EXCEL.EXE`，會搶佔 Port 8765 與 Excel DDE 通道，導致使用者桌面上看不到彈出的 Excel 視窗。請務必讓使用者從檔案總管雙擊 `啟動_Centimani腳本工具.bat` 啟動服務。
