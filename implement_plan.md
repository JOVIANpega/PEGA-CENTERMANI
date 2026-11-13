# Centimani 自動化測試腳本生成、雙向編輯與邏輯健檢系統實作計畫書 (implement_plan.md)

| 項目 | 內容 |
| :--- | :--- |
| **文件名稱** | Centimani 自動化測試腳本生成、雙向編輯與邏輯健檢系統實作計畫書 (Implementation Plan) |
| **對應規格書** | [spec.md](file:///d:/PYTHON/自動化編寫EXCEL/spec.md) (V2.0.0) |
| **開發環境** | Windows / Python 3.10+ (`openpyxl` + 內建 `http.server` + HTML5/JS) |
| **狀態** | 正式啟動建置 |

---

## 📌 目錄
1. [實作架構總覽](#1-實作架構總覽)
2. [系統檔案結構 (`centimani_studio\`)](#2-系統檔案結構-centimani_studio)
3. [核心模組實作規格](#3-核心模組實作規格)
   - [3.1 黃金空白母體與實戰積木庫 (`core/golden_data.py`)](#31-黃金空白母體與實戰積木庫-coregolden_datapy)
   - [3.2 10 大邏輯錯誤健檢與自動修復器 (`core/script_doctor.py`)](#32-10-大邏輯錯誤健檢與自動修復器-corescript_doctorpy)
   - [3.3 雙向 16 欄 Excel 引擎與 Calibri 11 排版器 (`core/excel_engine.py`)](#33-雙向-16-欄-excel-引擎與-calibri-11-排版器-coreexcel_enginepy)
   - [3.4 INI 9 區段與雙區段作用域自動分流引擎 (`core/ini_engine.py`)](#34-ini-9-區段與雙區段作用域自動分流引擎-coreini_enginepy)
   - [3.5 本地 Web API 伺服器與互動式前端 (`app_server.py` & `web/index.html`)](#35-本地-web-api-伺服器與互動式前端-app_serverpy--webindexhtml)
4. [驗收與自動化測試流程](#4-驗收與自動化測試流程)

---

## 1. 實作架構總覽

```mermaid
flowchart LR
    subgraph Backend ["Python 核心後端 (centimani_studio/core)"]
        GD["golden_data.py\n• 黃金空白母體 (4大環境表)\n• 實戰積木庫 (16欄含TestID)\n• 5,349 筆合法 TestID 字典"]
        EE["excel_engine.py\n• 匯入任意 .xlsx 解析\n• 匯出 16 欄標準 .xlsx\n• Calibri 11 + 自動換行排版\n• 從舊腳本自動萃取新積木"]
        IE["ini_engine.py\n• System.ini 9 大標準區段\n• Global.ini 變數自動掃描\n• [Settings] vs [Scripts] 分流"]
        SD["script_doctor.py\n• 10 大邏輯錯誤深度檢查\n• 跨 Title 區域變數偵測\n• ExecMode 越界偵測\n• 一鍵自動修復 (Auto-Fix)"]
    end

    subgraph Frontend ["本地瀏覽器 Web HTML 介面 (web/index.html)"]
        UI1["🧱 積木拼裝 & 16 欄試算表編輯"]
        UI2["🔍 腳本邏輯健檢診斷 (Script Doctor)"]
        UI3["🔌 母體環境表 (DUTs / Instrument)"]
        UI4["⚙️ System.ini & Global.ini 聯動"]
    end

    Backend <-->|REST JSON API (app_server.py)| Frontend
```

---

## 2. 系統檔案結構 (`centimani_studio\`)

```text
📁 d:\PYTHON\自動化編寫EXCEL\centimani_studio\
 ├── 🚀 start_studio.bat             # 雙擊一鍵啟動伺服器並開啟瀏覽器
 ├── 🐍 app_server.py                # 本地 HTTP / REST API 伺服器 (Port 8765)
 ├── 📁 core\
 │    ├── __init__.py
 │    ├── golden_data.py             # 內建黃金空白母體、12 大類實戰積木庫、TestID 白名單
 │    ├── excel_engine.py            # 雙向讀寫 Excel (支援 16 欄、Calibri 11、wrap_text、萃取積木)
 │    ├── ini_engine.py              # System.ini (9區段) 與 Global.ini ([Settings]/[Scripts] 自動分流)
 │    └── script_doctor.py           # 10 大邏輯錯誤檢查、寫法建議與一鍵自動修正引擎
 ├── 📁 web\
 │    └── index.html                 # 單頁式工控級 Web UI (含 Handover 懸停變色回饋)
 └── 📁 output_system\               # 匯出之標準 .\System\ 資料夾 (可直接複製進測試程式包使用)
      ├── [Project]_TestFlow.xlsx
      ├── System.ini
      └── Global.ini
```

---

## 3. 核心模組實作規格

### 3.1 黃金空白母體與實戰積木庫 (`core/golden_data.py`)
* **黃金母體**：預設帶入標準 `Properties`、`DUTs`（含 `UART`, `CmdConsole`, `SSH1`, `UARTF`, `DLL:UtilityLibrary.dll`）、`Switch`（`RFSwitch3001.dll`）、`Instrument`（完整收錄 `Ver1.65` 常用儀器 DLL）。
* **12 大實戰積木（皆為標準 16 欄且預綁定合法 7 碼 `TestID`）**：
  1. `BLK_PRETEST_ROUTE`：前置條碼顯示與 SFIS 路由檢查 (`:ShowISN`, `:SfCheckRoute`, `TestID: B7PL025 / OTFX064`)
  2. `BLK_FIXTURE_DOWN`：氣動治具下壓與安全延遲 (`UARTF@G\r\n`, `TestID: OTFX157`)
  3. `BLK_POWER_ON_IPOWER`：iPower2401 電源供應器冷開機上電序列 (`:ObtainDevice` ➔ `SwitchOFF` ➔ `SwitchON` ➔ `:ReleaseDevice` `ExecMode=3`)
  4. `BLK_VOLT_NI6008_BATCH`：NI6008 (`DaqUSBNi.dll`) 多通道批次電壓量測 + `:CheckLimit`（`MU310` / `VALO360` 實戰標準寫法）
  5. `BLK_VOLT_SINGLE_RAIL`：單軌電壓量測積木（可自訂軌道名稱、通道與上下限）
  6. `BLK_VOLT_MDA2700`：Keithley 2700 / DAQ970A 萬用電表 DC 電壓量測積木（`Raptor` 實戰寫法）
  7. `BLK_UART_LOGIN_VER`：UART 連線、登入檢查與韌體版本比對 (`*$(FW_VERSION)`)
  8. `BLK_SFIS_MAC_69PN`：從 SFIS 讀取 MAC 與 69PN 並寫入比對（`MU310` 實戰寫法）
  9. `BLK_PYTHON_CMD`：透過 `CmdConsole@python.exe` 呼叫外部 Python 腳本並擷取回傳值（`Olympus SSH_C.py / 1KHz.py` 實戰寫法）
  10. `BLK_UTILITY_PING_LAN`：`UtilityLibrary` 網路 Ping 與 Telnet/SSH 連線測試 (`:Utility.Ping`)
  11. `BLK_LED_FEASA`：Feasa LED 色彩與亮度分析量測
  12. `BLK_PHASE97_TEARDOWN`：Phase 97 強制安全收尾（斷電、治具抬起、釋放設備鎖與斷開所有連線，`ExecMode=3`）

### 3.2 10 大邏輯錯誤健檢與自動修復器 (`core/script_doctor.py`)
* 支援檢查**當前編輯專案**或**直接掃描 `SCRIPTS/` / `AI_SOURCE/` 下任意既有 Excel 檔案**。
* 提供 **「🔧 一鍵自動修正 (Auto-Fix)」** 功能：
  - 自動補齊空白或不合法的第 16 欄 `TestID`（預設補為通用合法碼 `B7PL025`）。
  - 自動將跨 `Title` 使用卻漏加 `$` 的 `Ref` 區域變數升級為 `$` 全域變數。
  - 自動將 `:ReleaseDevice` / `:Disconnect` / `:CloseMessage` 的 `ExecMode` 修正為 `3` (Continue)。
  - 自動重編連續 `Index (000, 001...)` 並修正表頭 `Index_XXX`。
  - 自動修正越界的 `ExecMode 2:X` 重試點為 `2:0`（跳回該 Title 第一步）。
  - 自動將站位表與環境表的 `*$(變數)` 分流補齊至 `Global.ini` 的 `[Scripts]` 與 `[Settings]`。

---

## 4. 驗收與自動化測試流程

1. 啟動後端模組自檢：驗證黃金母體 생성、16 欄格式、Calibri 11 排版、INI 雙區段分流。
2. 驗證 `script_doctor.py` 對 `AI_SOURCE` 真實腳本的錯誤檢出能力與一鍵自動修復能力。
3. 啟動本地 Web 伺服器並驗證所有 API 端點運作正常。
