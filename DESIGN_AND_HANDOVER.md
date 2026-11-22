# Centimani Studio V2.4 — 跨電腦開發交接與設計邏輯紀錄 (Design & Handover Log)

> **用途說明**：本文件完整記錄在此台電腦 (`M:\PYTHON\PEGA-CENTERMANI`) 所完成的核心問題修復、工程思考邏輯與架構決策。當您換到另一台電腦時，只需 `git pull` 下載本專案並閱讀此文件（或讓另一台電腦的 AI 讀取此文件與 `AGENTS.md`），即可無縫接軌所有開發脈絡。

---

## 一、核心設計思考邏輯：為什麼 `System.ini` 與 `Global.ini` 改用「Checkbox 打勾 ＋ 下拉選單」一頁式面板？

### 1. 真實產線 INI 檔案分析結論
經過實際拆解產線專案（`VALO360`、`ZEBRA`、`KANGAROO`、`RAPTOR`）的 `System.ini` 與 `Global.ini` 後發現：
- 雖然兩份 INI 加起來有 80~100 行，但 **85% 的參數從頭到尾都是固定不動的模板預設值**。
- 工程師在**出包給工廠**或**現場架設治具 / 韌體進版**時，真正會動到的其實只有以下 **9 個固定位置**（而且大部分改過一次定型後就不再更動）：

#### 🔹 `System.ini` 真正會改的 4 個地方（出包給工廠時設一次即固定）
1. **4 個核心模式開關（直接用 `Checkbox 打勾` 最直覺）**：
   - `DebugMode`：勾選=`1`（工程調試免驗 Checksum 簽章）；取消勾選=`0`（正式量產強制檢驗 64 碼 Checksum）。
   - `SFIS_Enable`：勾選=`1`（開啟 SFIS 產線過站路由檢查）；取消勾選=`0`（單機離線調試）。
   - `iPLAS_Enable` & `SFIS_LinkIPLAS`：勾選=`1`（測試完成自動打包上傳 Log 至 iPLAS）。
2. **出廠廠區伺服器網址 `SFIS_WebLink` ＋ `iPLAS_Site`（直接用 `下拉選單 6 選 1`）**：
   - 在真實 `VALO360/System.ini` 中，工程師原本是把 5 條廠區網址用 `//` 註解寫在檔案裡切換。現已直接內建為下拉選單，選廠區即自動連動 `SFIS_WebLink` 與 `iPLAS_Site`：
     - 🇹🇼 台灣 / PXD 通用域名 (`http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx` ｜ `Site=DC`)
     - 🇮🇩 巴淡廠 PTB (`http://10.176.33.13/SFISWebService/SFISTSPWebService.asmx,2,ErrorMapping.el` ｜ `Site=PTB`)
     - 🇨🇳 重慶廠 PCQ (`http://172.18.125.49/SFISWebService/SFISTSPWebService.asmx,2,ErrorMapping.el` ｜ `Site=PCQ`)
     - 🇨🇳 蘇州廠-1 PSZ (`http://172.24.248.17/SFISWebService/SFISTSPWebService.asmx,2,ErrorMapping.el` ｜ `Site=PSZ`)
     - 🇨🇳 蘇州廠-2 PSZ (`http://172.24.255.113/SFISWebService/SFISTSPWebService.asmx,2,ErrorMapping.el` ｜ `Site=PSZ`)
     - 🇨🇳 蘇州廠 Lot5 PSZ (`http://172.24.248.15/SFISWebService/SFISTSPWebService.asmx,2,ErrorMapping.el` ｜ `Site=PSZ`)
3. **重測次數 `RetryCount`（`0 ~ 5 次` 下拉選單）**。
4. **站別路由碼 `SFIS_TSP` 與專案名 `iPLAS_ProjectName`**（開案設定一次，如 `5GB,2`、`VALO360`）。
   *(註：`NewFormatScriptFile`、`TestItemCodeFile`、`StationList` 與 `[Checksum]` 均由系統於匯出時全自動寫入，無須人工修改)*

#### 🔹 `Global.ini` 真正會改的 5 個地方（架設機台或韌體進版時改一次）
1. **一拖四槽位開關 `LOAD_1 ~ LOAD_4`（`Checkbox 打勾`）**：勾選即 `true`，取消即 `false`。
2. **硬體序列埠號（`COM1 ~ COM30` 下拉選單）**：
   - `DUT_UR1`（待測物 UART COM Port）
   - `PCUART_fixture` / `PCUART_fixture_1`（氣動治具控制 COM Port）
   - `LED_AZ1`（FeasaLED 色彩分析儀 COM Port）
3. **NI 電壓量測卡代號 `DAQ_1`（`Dev1 ~ Dev4` 下拉選單）**。
4. **網路 IP 與 SFIS 機台號**：`DUTIP_1`（待測物 IP）、`PCIP_1`（電腦網卡 IP，附一鍵同步同網段按鈕）、`DEVID_1`（SFIS 機台設備號）。
5. **`[Scripts]` 韌體版號與機種 SKU**：`FW_VERSION`、`MFG_WIFI_MB`、`sfisSKU`（僅在韌體升版或換 SKU 時改一次）。

### 2. 為什麼捨棄 AI 問答框，改回「Checkbox ＋ 下拉選單 ＋ 本次變更確認清單」？
- **原因**：INI 屬於明確的硬體與廠區規格設定，用自然語言打字給 AI 容易遇到語意模糊（還要擔心 AI 改了哪裡、有沒有漏改關聯欄位）。
- **最終最佳解 (`Build v0.5.9`)**：
  1. 一打開就是**一頁式「Checkbox 打勾 ＋ 下拉選單」面板**，滑鼠點兩下、3 秒完成設定。
  2. 任何被修改過的格子會**原地亮黃底反白並顯示 `原本: xxx`**。
  3. 面板底部獨立列出 **「📝 本次已修改項目確認 (`原本舊值 ➔ 修改後新值`)」** 與防呆檢查提醒（如廠區網址與 `iPLAS_Site` 是否配對、網段是否一致）。
  4. 點擊右下角唯一的 **`💾 存檔並直接彈出剛剛改的 INI 記事本`**，即刻寫入硬碟並直接用 Windows `notepad.exe` 彈出該 `.ini` 檔（不會誤開 Excel）。

---

## 二、已解決的重大技術問題與修復清單 (`Build v0.5.0` ➔ `Build v0.5.9`)

### 1. 徹底解決「打開 / 匯出 Excel 常常卡死或無法彈出視窗」的陳年問題
- **根因 A（Excel `max_row` / `max_column` 幽靈空白格爆炸）**：
  - 產線舊 Excel 檔常帶有被格式化到第 16,384 欄或數萬列的空白儲存格，加上原本 `delete_rows(1, max_row)` 會殘留壞損的 `DataValidation` 與 256 欄幽靈格，導致 `openpyxl` 與 Excel 開檔卡死。
  - **修復**（`core/excel_engine.py`）：新增 `_read_bounded_rows()`（連續 50 列空白即停止讀取），且匯出 In-Place 測試站時改為乾淨重建該工作表 (`wb.remove` + `wb.create_sheet(index=idx_pos)`)，匯出耗時從卡死降至 **0.3 秒**。
- **根因 B（Windows 背景無頭 `EXCEL.EXE` 搶佔 DDE 與視窗焦點）**：
  - 若系統背景殘留沒有視窗 (`MainWindowHandle == 0`) 的 `EXCEL.EXE`，或是透過 `os.startfile` 被瀏覽器阻擋前景權限，Excel 就不會彈出。
  - **修復**（`啟動_Centimani腳本工具.bat` & `app_server.py`）：啟動時自動清除無頭 `EXCEL.EXE`，匯出時直接尋找系統 `EXCEL.EXE` 實體路徑啟動並呼叫 Win32 API `SetWindowPos(HWND_TOPMOST -> HWND_NOTOPMOST)` 強制拉到桌面最上層。
- **根因 C（Python 3.13 移除 `cgi` 模組導致網頁上傳 Excel 失敗）**：
  - **修復**（`app_server.py`）：自行實作相容 Python 3.10 ~ 3.13+ 的 `_parse_multipart_form()`，並保留原始上傳檔名與自動對應 `TEST_SECRIPT` / `SCRIPTS` 原目錄。

### 2. 🧱 積木順序排序（拖拉 Phase）自動鎖定開啟目標 Sheet 並標記「柔和淡藍色底色 (`#E8F4FD`)」
- **修復**（`core/block_sorter.py` & `core/excel_engine.py`）：
  - 凡被拖拉移動或重新順編 Phase 的積木區塊，整列 16 欄自動標記為**柔和粉彩淡藍底色 (`#E8F4FD`)**（與自動修復的亮黃底色 `#FEF08A` 清楚區隔）。
  - 匯出時透過 `_set_active_worksheet(wb, workspace, active_sheet)` 強制設定 `wb.active`、`wb.views[0].activeTab` 與每個 Sheet 的 `tabSelected`（將 `Properties` 的 `tabSelected` 設為 `False`、剛修改的測試站 Sheet 設為 `True`），保證 Excel 打開第一眼就是剛才修改的那個 Sheet！

### 3. 🔌 書籤三（34 款儀器範本）RF 下拉選單連動與互動人機直接生成 Excel
- **修復**（`web/index.html` & `web/js/inst_hmi.js`）：
  - 修復 `tab3OnCatChange()` 分類連動，切換至 `📡 RF 無線 / 功率計 / 切換器` 時完整列出 8 款 RF 標準儀器（`InstIQApiA`、`XelM8-B`、`MT8870A`、`E4418B`、`U2004A`、`OSP120`、`SAn9000`、`vnxRFSW`）。
  - 在書籤三進入「🔌 互動人機設定」（如 NI-6008/6009 32-Pin 接線圖、FeasaLED、IQxel RF）設定完按下確認後，直接自動由母體產出完整 Excel、開啟資料夾並置頂打開 Excel 的 `MB` 工作表。

### 4. 🔢 修復「Excel 站別與 ISN 條碼」改 3 碼會跳回 15 碼的問題
- **修復**（`web/js/audit_editors.js` & `app_server.py`）：
  - 移除原本寫死在 HTML 的 `value="15"`，改為雙向即時同步 (`STATE.lastIsnLen`)，並新增 **`⚡ 一鍵設 3 碼 (調試)`** 與 **`⚡ 一鍵設 15 碼 (量產)`** 快捷按鈕。

### 5. ⏳ 所有匯出與開檔動作統一顯示「全螢幕防誤觸鎖定計時視窗 (`withLoadingTimer`)」
- 無論在書籤一匯出 `*_FIXED.xlsx`、積木排序匯出、INI 存檔彈出記事本、書籤二建新母體、書籤三生成儀器範本，都會出現鎖定計時視窗（`已耗時 0.0 秒 ➔ 1.2 秒`），清楚呈現系統正在寫入檔案並喚醒視窗。

---

## 三、一鍵全功能自動驗收機制 (`一鍵全功能自動驗收.bat`)

為了不讓使用者每次改完都要人工一個個點選檢查，專案根目錄提供 **`一鍵全功能自動驗收.bat`**（執行 `centimani_studio/tests/verify_all_features.py`）：
- **5 秒內自動跑完 40 項端到端驗收**：
  1. 模擬網頁上傳 `Zebra_20190417_TestFlow.XLSX` ➔ 拖拉 `ET5X_FA5` Phase 順序 ➔ 匯出並拆解檢查 Excel 是否鎖定於 `ET5X_FA5`、是否標記 `#E8F4FD` 淡藍底色。
  2. 模擬修改 INI 並獨立存檔 ➔ 檢查 `Global.ini` / `System.ini` 是否正確寫入且只彈出 INI 記事本（不誤開 Excel）。
  3. 模擬修改 ISN 為 3 碼 ➔ 檢查覆檢後是否正確識別為 3 碼。
  4. 模擬書籤三 NI-6009 / FeasaLED / IQxel RF 人機介面確認生成母體 Excel（含 21/22 步 `WIFI Tx/Rx MCS` 子工作表）。
  5. 模擬書籤一插入 `Agilent34401A` 儀器並匯出 `*_FIXED.xlsx`。
  6. 模擬書籤二建立新母體與無硬體試跑版 (Dry-Run)。
  7. 自動呼叫 `node --check` 編譯檢查所有前端 `.js` 與 `index.html` 語法 0 錯誤、檢查前後端 `Build vX.Y.Z` 版本號一致、檢查 `.bat` 檔維持標準 Windows `CRLF` 格式。
