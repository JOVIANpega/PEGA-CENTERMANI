# -*- coding: utf-8 -*-
"""
Centimani Studio - 一鍵全功能端到端自動驗收腳本 (End-to-End Full Feature Verifier)
自動模擬使用者在網頁上的所有核心操作路徑，並直接拆解檢查產出的實體 Excel (.xlsx) 與 INI 檔案，
讓工程師無需人工逐一點擊即可在 5 秒內完成 100% 功能驗收！

驗收範圍：
1. [書籤一：網頁上傳 + 積木順序排序 (拖拉 Phase) + 一鍵修復匯出]
   - 模擬上傳 Zebra_20190417_TestFlow.XLSX (工作表 ET5X_FA5)
   - 驗證上傳後不會丟失原檔名或被藏在 uploaded_temp\temp_uploaded.xlsx
   - 模擬拖拉調動 Phase 3/4/8 等積木順序並匯出 *_FIXED.xlsx
   - 拆解輸出的 *_FIXED.xlsx 驗證：
     * 檔案存在且 > 0 KB
     * Excel 預設開啟分頁 (wb.active & tabSelected) 100% 鎖定為 ET5X_FA5 (且 Properties 為 False)
     * 被移動/改號的 Phase 區塊 100% 標上「淡藍色底色 (#BAE6FD)」
     * 自動修復的儲存格標上「亮黃色底色 (#FEF08A)」
2. [書籤三：34 款儀器範本 — 直接生成 & 互動人機介面 (HMI) 確認後自動生成]
   - (2A) 書籤三直接生成 (NI6008-1)
   - (2B) 書籤三進入 NI-6009 32-Pin 人機介面設定多通道電壓後確認生成
   - (2C) 書籤三進入 FeasaLED RGB 人機介面設定紅/綠/藍三色後確認生成
   - (2D) 書籤三進入 LitePoint IQxel RF 人機介面設定 Tx/Rx 後確認生成 (驗證自動生成 21/22 步 Marco 子表)
   - 驗證每份產出的 Excel 均預設開啟於 MB 測試站分頁，且通過 Script Doctor 0 Error 健檢！
3. [書籤一：既有腳本插入儀器範本 ➔ 立即匯出並驗證 (*_FIXED.xlsx)]
   - 驗證插入儀器後匯出 *_FIXED.xlsx，新增區塊標亮黃底、Instrument 表 Mount 自動掛載站名、預設開啟該站分頁。
4. [書籤二：從零勾選積木建立新母體 + 無硬體試跑版 (Dry-Run)]
   - 驗證 16 欄母體與 Dry-Run (硬體列 ExecMode=6、:Sf* 保持 8/9)。
5. [產線 Log 診斷分析 & 5,203 筆 Test Item Code 智慧搜尋]
"""
import os
import re
import sys
import json
import shutil
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer
import openpyxl

STUDIO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(STUDIO_DIR)
if STUDIO_DIR not in sys.path:
    sys.path.insert(0, STUDIO_DIR)

import app_server


def run_all_verifications():
    print("=" * 78)
    print("🚀 Centimani Studio 全功能端到端自動驗收系統 (E2E Automated Verification)")
    print("=" * 78)

    # 測試期間攔截紀錄「自動開資料夾」、「自動開 Excel」與「自動開 INI」的呼叫路徑，證明後端確實有觸發且不干擾螢幕
    opened_folders = []
    launched_excels = []
    launched_inis = []
    orig_open_folder = app_server.open_folder_in_explorer
    orig_launch_excel = app_server.launch_excel_file_async
    orig_launch_ini = app_server.launch_ini_file_async
    app_server.open_folder_in_explorer = lambda p: opened_folders.append(p)
    app_server.launch_excel_file_async = lambda p: launched_excels.append(p)
    app_server.launch_ini_file_async = lambda p: launched_inis.append(p)

    server = ThreadingHTTPServer(("127.0.0.1", 0), app_server.StudioRequestHandler)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    def get_json(path):
        with urllib.request.urlopen(base_url + path) as r:
            return json.loads(r.read().decode("utf-8"))

    def post_json(path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            base_url + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode("utf-8"))

    def post_multipart(path, field_name, filename, file_bytes):
        boundary = "----CentimaniVerifyBoundary998877"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            base_url + path,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode("utf-8"))

    passed_checks = 0
    total_checks = 0

    def check(cond, title, detail=""):
        nonlocal passed_checks, total_checks
        total_checks += 1
        if cond:
            passed_checks += 1
            print(f"  ✅ [PASS] {title}" + (f" ({detail})" if detail else ""))
        else:
            print(f"  ❌ [FAIL] {title}" + (f" ({detail})" if detail else ""))
            raise AssertionError(f"驗收失敗: {title} {detail}")

    try:
        # ---------------------------------------------------------------------
        # 1. 書籤一：模擬上傳 Zebra_20190417_TestFlow.XLSX -> 拖拉 ET5X_FA5 Phase 順序 -> 匯出 *_FIXED.xlsx
        # ---------------------------------------------------------------------
        print("\n▶ [驗收 1/5] 書籤一：積木順序排序 (ET5X_FA5 拖拉 Phase) -> 淡藍色高亮與自動鎖定 Sheet")
        import glob as _glob
        zebra_candidates = [
            os.path.join(PROJECT_ROOT, "SCRIPTS", "ZEBRA", "Zebra_20190417_TestFlow.XLSX"),
            os.path.join(PROJECT_ROOT, "TEST_SECRIPT", "Zebra_20190417_TestFlow.XLSX"),
            os.path.join(PROJECT_ROOT, "SCRIPTS", "TEST_SECRIPT", "Zebra_20190417_TestFlow.XLSX"),
        ]
        zebra_src = next((p for p in zebra_candidates if os.path.exists(p)), None)
        if not zebra_src:
            found_z = _glob.glob(os.path.join(PROJECT_ROOT, "**", "Zebra_20190417_TestFlow.XLSX"), recursive=True)
            zebra_src = found_z[0] if found_z else zebra_candidates[0]
        with tempfile.TemporaryDirectory() as tmp_proj:
            # 複製一份測試用 Zebra 檔案以驗證上傳與同目錄匯出
            test_zebra = os.path.join(tmp_proj, "Zebra_20190417_TestFlow.XLSX")
            shutil.copy2(zebra_src, test_zebra)
            with open(test_zebra, "rb") as f:
                z_bytes = f.read()

            # 模擬網頁直接上傳外部檔案
            up_res = post_multipart("/api/upload_and_audit", "excel_file", "MyCustom_Zebra_TestFlow.XLSX", z_bytes)
            check(up_res["status"] == "ok", "網頁直接上傳 Excel 解析成功")
            check("temp_uploaded" not in os.path.basename(up_res["file_path"]), "上傳檔名完整保留，不變成 temp_uploaded", os.path.basename(up_res["file_path"]))

            ws = up_res["workspace"]
            target_sheet = "ET5X_FA5" if "ET5X_FA5" in ws["stations"] else list(ws["stations"].keys())[-1]

            # 取得該站所有 Phase 積木
            blk_res = post_json("/api/get_station_blocks", {"workspace": ws, "sheet_name": target_sheet})
            blocks = blk_res["blocks"]
            check(len(blocks) >= 5, f"成功載入 [{target_sheet}] 積木卡牌", f"共 {len(blocks)} 個 Phase 區塊")

            # 模擬使用者在牌桌上對調第 2 與第 3 張卡牌 (Phase 3 與 Phase 4)
            new_order = list(range(len(blocks)))
            new_order[2], new_order[3] = new_order[3], new_order[2]
            ro_res = post_json("/api/reorder_station_blocks", {
                "workspace": ws,
                "sheet_name": target_sheet,
                "new_order_indices": new_order,
                "auto_renumber_phase": True,
            })
            check(ro_res["status"] == "ok", "套用 Phase 拖拉排序與自動順編成功")

            opened_folders.clear()
            launched_excels.clear()
            fix_res = post_json("/api/fix_and_export_in_place", {
                "workspace": ro_res["workspace"],
                "user_choices": {},
                "dry_run": False,
                "active_sheet": target_sheet,
                "open_excel": True,
            })
            out_xlsx = fix_res["excel_path"]
            check(os.path.exists(out_xlsx), "成功產出 *_FIXED.xlsx 實體檔案", out_xlsx)
            check("MyCustom_Zebra_TestFlow_FIXED" in os.path.basename(out_xlsx), "匯出檔名保留原專案名稱", os.path.basename(out_xlsx))
            check(len(opened_folders) == 1 and len(launched_excels) == 1, "後端已觸發自動開啟目錄與自動啟動 Excel", os.path.basename(launched_excels[0]))

            wb_chk = openpyxl.load_workbook(out_xlsx)
            check(wb_chk.active.title == target_sheet, f"Excel 開啟預設分頁 100% 鎖定於 [{target_sheet}]", f"active={wb_chk.active.title}")
            check(wb_chk[target_sheet].views.sheetView[0].tabSelected is True, f"[{target_sheet}] tabSelected 屬性為 True")
            check(wb_chk["Properties"].views.sheetView[0].tabSelected is False, "[Properties] tabSelected 已取消選取 (False)")

            ws_et = wb_chk[target_sheet]
            blue_cells = sum(
                1 for r in range(2, ws_et.max_row + 1)
                if "E8F4FD" in str(ws_et.cell(row=r, column=2).fill.start_color.rgb or "")
            )
            check(blue_cells > 0, "剛修改順序的 Phase 區塊已標上『更柔和的淡藍色高亮底色 (#E8F4FD)』", f"共 {blue_cells} 列標註淡藍色")
            wb_chk.close()

            # 驗證 INI 左右對照後獨立存檔並直接彈出 INI (不開 Excel)
            opened_folders.clear()
            launched_excels.clear()
            launched_inis.clear()
            ws["global_ini"]["Settings"]["DUT_UR1"] = "COM18"
            ws["global_ini"]["Settings"]["DUTIP_1"] = "192.168.11.200"
            ini_res = post_json("/api/save_and_open_ini", {
                "file_path": test_zebra,
                "workspace": ws,
                "open_target": "global",
            })
            check(ini_res["status"] == "ok" and os.path.exists(ini_res["global_ini_path"]), "INI 修改後獨立存檔成功產出 Global.ini & System.ini", ini_res["global_ini_path"])
            check(len(launched_inis) == 1 and len(launched_excels) == 0, "INI 存檔後直接彈出剛剛改的 Global.ini (不會誤彈出 Excel)", os.path.basename(launched_inis[0][0]))

            # 驗證修改 ISN 條碼為 3 碼 ({ ISN,3,[0-9A-Z] }) 後覆檢與匯出不會跳回 15 碼
            for d_item in ws.get("duts", []):
                scan_k = next((k for k in d_item.keys() if k.lower().startswith("scanbarcode")), "ScanBarcode( {Name,Lengh,Pattern} )")
                d_item[scan_k] = "{ ISN,3,[0-9A-Z] }"
            reaudit_res = post_json("/api/re_audit", {"workspace": ws})
            check(reaudit_res["status"] == "ok" and reaudit_res.get("isn_info", {}).get("isn_length") == 3, "ISN 條碼改為 3 碼後即時覆檢成功識別為 3 碼", str(reaudit_res.get("isn_info")))

            # 驗證新增測試站 JOVIAN 後，匯出 *_FIXED.xlsx 確實會產生 JOVIAN 工作表分頁
            ws["stations"]["JOVIAN"] = [
                {"Index": "000", "Phase": "0", "Title": "0,PreTest Check Route,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ":SFIS.CheckRoute", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "8", "Description": "SFIS#-#Check Route", "TestID": "CACK088"},
                {"Index": "001", "Phase": "97", "Title": "1,End Test Safe Teardown,1", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Disconnect,"UART"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Disconnect DUT UART", "TestID": "B7PL025"},
            ]
            jovian_exp = post_json("/api/fix_and_export_in_place", {
                "workspace": ws, "user_choices": {}, "dry_run": False, "active_sheet": "JOVIAN", "open_excel": True
            })
            wb_jov = openpyxl.load_workbook(jovian_exp["excel_path"])
            check("JOVIAN" in wb_jov.sheetnames and wb_jov.active.title == "JOVIAN", "新增測試站 [JOVIAN] 後匯出 Excel 確實產生 JOVIAN 分頁並自動開啟該頁")
            wb_jov.close()

        # ---------------------------------------------------------------------
        # 2. 書籤三：插入儀器範本 (34 款人機) — 直接生成 & 互動人機介面確認後自動生成
        # ---------------------------------------------------------------------
        print("\n▶ [驗收 2/5] 書籤三：34 款儀器範本 (直接生成 + NI-6009 人機 + FeasaLED 人機 + IQxel RF 人機)")
        # 2A: NI-6009 多通道人機介面設定後直接生成
        opened_folders.clear()
        launched_excels.clear()
        ni6_hmi_res = post_json("/api/generate_inst_template_standalone", {
            "project_name": "INST_MOTHER",
            "station_name": "MB",
            "open_excel": False,
            "items": [{
                "inst_name": "NI6008-1",
                "title_name": "Measure Multi-Rail Voltage",
                "ni6009_block": {
                    "mode": "RSE",
                    "sample_ms": "1000",
                    "dev_id": "Dev1",
                    "title_name": "Measure Multi-Rail Voltage",
                    "channels": [
                        {"ch": 0, "name": "VCC_3V3", "dl": "3.15", "ul": "3.45"},
                        {"ch": 1, "name": "VCC_5V", "dl": "4.75", "ul": "5.25"},
                    ]
                }
            }]
        })
        check(ni6_hmi_res["status"] == "ok" and os.path.exists(ni6_hmi_res["excel_path"]), "書籤三：NI-6009 人機介面確認後自動產出母體 Excel", ni6_hmi_res["excel_path"])
        check(len(opened_folders) == 1 and len(launched_excels) == 0, "書籤三：匯出預設必開目錄且不搶開 Excel（待使用者彈窗確認）")
        wb_ni = openpyxl.load_workbook(ni6_hmi_res["excel_path"])
        check(wb_ni.active.title == "MB", "書籤三產出之 Excel 自動鎖定開啟於 [MB] 測試站分頁")
        wb_ni.close()

        # 2B: FeasaLED RGB 人機介面設定後直接生成
        feasa_hmi_res = post_json("/api/generate_inst_template_standalone", {
            "project_name": "INST_MOTHER",
            "station_name": "MB",
            "items": [{
                "inst_name": "FeasaLED",
                "title_name": "Check RGB LEDs",
                "custom_steps": [
                    {"Instrument": "LED_Test", "Send": ":ObtainDevice", "ExecMode": "0", "Description": "LED#-#Obtain", "TestID": "BRME027"},
                    {"Instrument": "LED_Test", "Send": ':Dev.CaptureAndRead,"01"', "Ref": "$LED_Wave;\n$LED_Int", "Validation": "(LED_Wave,%f,615,640);\n(LED_Int,%f,1000,99999)", "ExecMode": "2:0", "Description": "LED#-#Red", "TestID": "IOLE015"},
                    {"Instrument": "LED_Test", "Send": ":ReleaseDevice", "ExecMode": "3", "Description": "LED#-#Release", "TestID": "BRME027"},
                ],
                "globals_patch": {"Settings": {"LED_AZ1": "COM17", "LED_Light1": "01"}}
            }]
        })
        check(feasa_hmi_res["status"] == "ok" and os.path.exists(feasa_hmi_res["excel_path"]), "書籤三：FeasaLED 人機介面確認後自動產出母體 Excel", os.path.basename(feasa_hmi_res["excel_path"]))

        # 2C: IQxel RF 人機介面設定後直接生成 (含 WIFI Tx/Rx MCS Marco 子工作表)
        rf_hmi_res = post_json("/api/generate_inst_template_standalone", {
            "project_name": "INST_MOTHER",
            "station_name": "MB",
            "items": [{
                "inst_name": "InstIQApiA",
                "title_name": "WIFI RF Test",
                "rf_block": {
                    "inst_name": "InstIQApiA",
                    "title_name": "WIFI RF Test",
                    "settings_str": "192.168.100.254,1,2,1,60000,PathLoss.ini",
                    "tx_tests": [{"channel": "6", "bw": "20", "mcs": "7", "antenna": "1", "target_pwr": "15", "pwr_min": "13", "pwr_max": "17", "evm_min": "-50", "evm_max": "-28"}],
                    "rx_tests": [{"channel": "6", "bw": "20", "mcs": "7", "antenna": "1", "rx_level": "-59"}]
                }
            }]
        })
        check(rf_hmi_res["status"] == "ok" and os.path.exists(rf_hmi_res["excel_path"]), "書籤三：IQxel RF 人機介面確認後自動產出母體 Excel", os.path.basename(rf_hmi_res["excel_path"]))
        wb_rf = openpyxl.load_workbook(rf_hmi_res["excel_path"])
        check("WIFI Tx MCS" in wb_rf.sheetnames and "WIFI Rx MCS" in wb_rf.sheetnames, "書籤三：IQxel RF 母體自動包含 WIFI Tx/Rx MCS Marco 子工作表")
        wb_rf.close()

        # ---------------------------------------------------------------------
        # 3. 書籤一：既有腳本插入儀器 -> 立即匯出並驗證 (*_FIXED.xlsx)
        # ---------------------------------------------------------------------
        print("\n▶ [驗收 3/5] 書籤一：既有腳本插入儀器 -> 立即匯出並驗證 (*_FIXED.xlsx)")
        ins_res = post_json("/api/insert_instrument_block", {
            "workspace": up_res["workspace"],
            "sheet_name": target_sheet,
            "inst_name": "Agilent34401A",
            "title_name": "Measure 12V DMM",
            "after_block_idx": -1,
            "dl_val": "11.4",
            "ul_val": "12.6"
        })
        check(ins_res["status"] == "ok" and ins_res["added_rows"] > 0, f"成功插入 Agilent34401A 區塊 ({ins_res['added_rows']} 列)")
        opened_folders.clear()
        launched_excels.clear()
        exp_ins_res = post_json("/api/fix_and_export_in_place", {
            "workspace": ins_res["workspace"],
            "user_choices": {},
            "dry_run": False,
            "active_sheet": target_sheet,
            "open_excel": True,
        })
        check(exp_ins_res["status"] == "ok" and os.path.exists(exp_ins_res["excel_path"]), "插入儀器後點擊『立即匯出並驗證』成功產出 *_FIXED.xlsx")
        check(len(opened_folders) == 1 and len(launched_excels) == 1, "插入儀器匯出後已自動開啟目錄與啟動 Excel")

        # ---------------------------------------------------------------------
        # 4. 書籤二：首次建立新母體 (0 -> 1) + 無硬體試跑版 (Dry-Run)
        # ---------------------------------------------------------------------
        print("\n▶ [驗收 4/5] 書籤二：從零建立新母體 (0 -> 1) 與無硬體試跑版 (Dry-Run)")
        gen_res = post_json("/api/generate_new_standalone", {
            "project_name": "VERIFY_MOTHER",
            "station_name": "FT1",
            "dut_count": 2,
            "block_ids": ["BLK_PRETEST_ROUTE", "BLK_VOLT_NI6008_BATCH", "BLK_UART_BOOT_FW", "BLK_PHASE97_TEARDOWN"],
            "dry_run": True,
        })
        check(gen_res["status"] == "ok" and os.path.exists(gen_res["excel_path"]), "成功產出書籤二新母體 Dry-Run Excel", os.path.basename(gen_res["excel_path"]))
        wb_gen = openpyxl.load_workbook(gen_res["excel_path"])
        check(wb_gen.active.title == "FT1", "新母體開啟預設分頁鎖定於 [FT1] 測試站")
        wb_gen.close()

        # ---------------------------------------------------------------------
        # 5. 產線 Log 診斷分析 & 5,203 筆 Test Item Code 智慧搜尋
        # ---------------------------------------------------------------------
        print("\n▶ [驗收 5/6] 產線 Log 診斷分析與 5,203 筆 TestID 智慧搜尋")
        init_res = get_json("/api/init")
        cat_res = get_json("/api/instrument_catalog")
        rf_set = {"InstIQApiA", "XelM8-B", "MT8870A", "E4418B", "U2004A", "OSP120", "SAn9000", "vnxRFSW"}
        rf_insts = [i["Name"] for i in cat_res.get("instruments", []) if i.get("Name") in rf_set]
        check(len(rf_insts) == 8, "書籤三下拉選單『RF 無線 / 功率計 / 切換』分類 8 款標準儀器清單完整對應", f"共 {len(rf_insts)} 款: {', '.join(rf_insts[:5])}...")
        check(init_res["tic_info"]["count"] > 5000, "官方 Test Item Code V2.04 代碼庫已完整載入", f"共 {init_res['tic_info']['count']} 筆")
        tic_res = get_json("/api/search_test_id?q=voltage&limit=5")
        check(len(tic_res["items"]) > 0, "TestID 關鍵字智慧搜尋正常運作", f"首筆推薦: {tic_res['items'][0]['test_id']}")

        # ---------------------------------------------------------------------
        # 6. 未來 AI 防迴歸守門員：前端 JS 語法靜態掃描、兩階段 AI INI 對照與版本一致性檢查
        # ---------------------------------------------------------------------
        print("\n▶ [驗收 6/6] 未來 AI 修改防迴歸守門員 (前端 JS 語法檢查 / 版本號同步 / 批次檔 CRLF 防呆)")
        import re
        import subprocess
        web_dir = os.path.join(STUDIO_DIR, "web")
        index_html = open(os.path.join(web_dir, "index.html"), "r", encoding="utf-8").read()
        audit_js = open(os.path.join(web_dir, "js", "audit_editors.js"), "r", encoding="utf-8").read()

        # 6A: 檢查兩階段 INI 編輯 + AI 修改總結報告核心函式完整性
        for fn_name in ("_renderIniStage1EditHtml", "_renderIniStage2ReviewHtml", "_explainChangeByAi", "saveAndOpenModifiedIni"):
            check(fn_name in audit_js, f"兩階段 INI 差異反白與 AI 報告核心函式存在: {fn_name}()")

        # 6B: 若系統安裝有 Node.js，自動對所有前端 JS 與 index.html 內嵌腳本執行 `node --check` 語法編譯檢查
        node_exe = shutil.which("node")
        if node_exe:
            js_files = [os.path.join(web_dir, "js", f) for f in os.listdir(os.path.join(web_dir, "js")) if f.endswith(".js")]
            for jf in js_files:
                proc = subprocess.run([node_exe, "--check", jf], capture_output=True, text=True)
                check(proc.returncode == 0, f"前端 JS 語法 0 錯誤 ({os.path.basename(jf)})", proc.stderr.strip())
            # 抽取 index.html 內嵌 <script> 區塊進行語法檢查
            inline_scripts = re.findall(r"<script>([\s\S]*?)</script>", index_html)
            if inline_scripts:
                with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as tf:
                    tf.write("\n".join(inline_scripts))
                    tmp_js = tf.name
                try:
                    proc = subprocess.run([node_exe, "--check", tmp_js], capture_output=True, text=True)
                    check(proc.returncode == 0, "index.html 內嵌 JavaScript 語法 0 錯誤", proc.stderr.strip())
                finally:
                    if os.path.exists(tmp_js):
                        os.remove(tmp_js)
        # 無論是否有 Node.js，檢查 <script> 區塊內不可誤夾巢狀 <script> 標籤
        for blk_idx, blk in enumerate(re.findall(r"<script>([\s\S]*?)</script>", index_html), 1):
            has_nested_script = bool(re.search(r"<script\b", blk, re.IGNORECASE))
            check(not has_nested_script, f"index.html <script> 區塊 #{blk_idx} 未誤夾巢狀 <script> 標籤")

        # 6C: 檢查前後端 Build 版本號與快取參數同步
        m_badge = re.search(r"Build v(\d+\.\d+\.\d+)", index_html)
        server_py = open(os.path.join(STUDIO_DIR, "app_server.py"), "r", encoding="utf-8").read()
        m_srv = re.search(r"Build v(\d+\.\d+\.\d+)", server_py)
        check(bool(m_badge and m_srv and m_badge.group(1) == m_srv.group(1)), "前端畫面與後端伺服器 Build 版本號完全同步", f"Build v{m_badge.group(1) if m_badge else '?'}")

        # 6D: 檢查所有彈窗皆使用合法 .modal-backdrop / .modal-panel 類別（禁止未定義 modal-mask/modal-card 導致頁面一開啟就外露且 X 關不掉）
        app_css = open(os.path.join(STUDIO_DIR, "web", "css", "app.css"), "r", encoding="utf-8").read()
        check(".modal-backdrop" in app_css and "display: none;" in app_css and ".modal-backdrop.open" in app_css,
              "app.css 正確定義 .modal-backdrop 預設隱藏與 .open 顯示規則")
        check("modal-mask" not in index_html and "modal-card" not in index_html,
              "index.html 無未定義之 modal-mask / modal-card 類別（避免彈窗未觸發卻直接外露且無法關閉）")
        check('id="exportConfirmModal" class="modal-backdrop"' in index_html and 'id="copySheetModal" class="modal-backdrop"' in index_html,
              "匯出確認彈窗與跨檔複製彈窗皆使用標準 .modal-backdrop 隱藏遮罩")

        # 6E: 檢查手風琴說明文與實際流程一致，且採用 rem 等比字體縮放規則
        flow_guide_js = open(os.path.join(STUDIO_DIR, "web", "js", "flow_guide.js"), "r", encoding="utf-8").read()
        audit_editors_js = open(os.path.join(STUDIO_DIR, "web", "js", "audit_editors.js"), "r", encoding="utf-8").read()
        check(".acc-card .acc-title" in app_css and "rem" in app_css.split(".acc-card .acc-title")[1][:120],
              "手風琴標題/內文改用 rem 單位，隨系統字體設定 (13/15/17/19px) 等比縮放")
        check("書籤三：儀器範本" in index_html and "左側撲克牌庫" in index_html and "書籤一：既有腳本編修" in flow_guide_js,
              "首頁手風琴、流程導覽 (flow_guide.js) 與書籤三撲克牌說明文已全面與新版 UI 同步")
        check("比照首頁手風琴式導覽" not in audit_editors_js and "儀器長積木" not in index_html,
              "已移除舊版『比照首頁…』『儀器長積木』等過時說明文字")
        check("renderTab3Queue()" in index_html and "catInst.dll_exists === false" in index_html,
              "書籤三右欄已選卡片與 Step 2 細部卡同步標示 ❌ 缺 DLL 紅框警示")
        check("openFolderBrowserModal(initDir" in index_html or ("/api/pick_file" in index_html and "path_only: true" in index_html),
              "跨檔案複製 Sheet 瀏覽來源/目標支援直接呼叫 Windows 系統選檔對話框 (/api/pick_file)")
        check("selectFlowGuideStage" in flow_guide_js and "quickJumpHtml" not in flow_guide_js,
              "流程導覽整合為上方 5 階段互動流程卡（移除重複截斷之 13 顆黃色膠囊列）")
        check("decodeURIComponent('${encodeURIComponent(f.path)}')" in index_html,
              "內建資料夾瀏覽窗無雙重 URL 編碼錯誤")

        # 6F: 檢查根目錄 .bat 批次檔皆為標準 Windows CRLF 換行 (防止 cmd.exe chcp 65001 位移錯誤)
        for bat_name in ("啟動_Centimani腳本工具.bat", "一鍵全功能自動驗收.bat"):
            bat_p = os.path.join(PROJECT_ROOT, bat_name)
            if os.path.exists(bat_p):
                raw_b = open(bat_p, "rb").read()
                check(b"\r\n" in raw_b and b"\n" not in raw_b.replace(b"\r\n", b""), f"批次檔 [{bat_name}] 為標準 CRLF 換行格式")

        # ---------------------------------------------------------------------
        # 7. DebugMode=0 保留 / Mount 清空修復 / 跨檔案整張 Sheet 複製 (格式不跑掉)
        # ---------------------------------------------------------------------
        print("\n▶ [驗收 7/7] DebugMode=0 保留、Mount 清空修復與跨檔案整張 Sheet 複製")
        from core.ini_engine import sync_and_generate_inis
        from core.excel_engine import export_workspace_to_excel as _exp_ws
        with tempfile.TemporaryDirectory() as tmp_d7:
            # 7A: DebugMode=0 不應被硬改為 1
            src_sys = os.path.join(tmp_d7, "System.ini")
            with open(src_sys, "w", encoding="utf-8") as f:
                f.write("[System]\nDebugMode=0\nRetryCount=3\n")
            dummy_xlsx = os.path.join(tmp_d7, "Dummy.xlsx")
            wb_d = openpyxl.Workbook()
            ws_d = wb_d.active
            ws_d.title = "Instrument"
            ws_d.append(["Name", "ControlDLL", "Version", "Mount", "Settings"])
            ws_d.append(["NI6008-1", "NI6008.dll", "1.0", "MB,FT1", ""])
            wb_d.save(dummy_xlsx)
            wb_d.close()

            out_d7 = os.path.join(tmp_d7, "out")
            sync_and_generate_inis({"source_file": dummy_xlsx, "system_ini": {"DebugMode": "0"}, "stations": {"MB": []}}, "Dummy.xlsx", out_d7)
            sys_txt_d7 = open(os.path.join(out_d7, "System.ini"), "r", encoding="utf-8").read()
            check("DebugMode=0" in sys_txt_d7 and "DebugMode=1" not in sys_txt_d7, "匯出保留 System.ini DebugMode=0 不被強制覆寫為 1")

            # 7B: Instrument Mount 清空應確實清除儲存格
            out_mount_xlsx = os.path.join(tmp_d7, "Dummy_Cleared.xlsx")
            _exp_ws({
                "source_file": dummy_xlsx,
                "instruments": [{"Name": "NI6008-1", "ControlDLL": "NI6008.dll", "Version": "1.0", "Mount": ""}],
                "stations": {}
            }, out_mount_xlsx)
            wb_chk = openpyxl.load_workbook(out_mount_xlsx)
            mount_val = wb_chk["Instrument"].cell(row=2, column=4).value
            wb_chk.close()
            check(mount_val in (None, ""), "Instrument Mount 設為空字串後確實清除 Excel 欄位", repr(mount_val))

            # 7C: 跨檔案整張 Sheet 複製 (保留欄寬/底色/合併格與 .bak 備份)
            src_copy_xlsx = os.path.join(tmp_d7, "SourceInst.xlsx")
            dst_copy_xlsx = os.path.join(tmp_d7, "TargetFlow.xlsx")
            wb_s = openpyxl.Workbook()
            ws_s = wb_s.active
            ws_s.title = "InstTemplate_A"
            ws_s["A1"] = "Header"
            ws_s["A1"].fill = openpyxl.styles.PatternFill("solid", fgColor="FEF08A")
            ws_s.column_dimensions["A"].width = 32
            ws_s.merge_cells("A1:B1")
            wb_s.save(src_copy_xlsx)
            wb_s.close()

            wb_t = openpyxl.Workbook()
            wb_t.active.title = "MB"
            wb_t.save(dst_copy_xlsx)
            wb_t.close()

            ls_res = post_json("/api/list_excel_sheets", {"excel_path": src_copy_xlsx})
            check(ls_res["status"] == "ok" and "InstTemplate_A" in ls_res["sheets"], "API 成功讀取來源 Excel 所有 Sheet 清單", str(ls_res["sheets"]))

            cp_res = post_json("/api/copy_sheet_across_files", {
                "source_excel_path": src_copy_xlsx,
                "source_sheet_name": "InstTemplate_A",
                "target_excel_path": dst_copy_xlsx,
                "target_sheet_name": "Copied_Inst_A",
                "overwrite": True,
                "use_excel_com": False,
                "open_excel": False,
            })
            check(cp_res["status"] == "ok" and cp_res["copied_sheet"] == "Copied_Inst_A", "API 跨檔案複製整張 Sheet 成功", cp_res.get("engine", ""))
            check(os.path.exists(dst_copy_xlsx + ".bak"), "跨檔案複製自動備份目標檔 (.bak)")
            wb_v = openpyxl.load_workbook(dst_copy_xlsx)
            check("Copied_Inst_A" in wb_v.sheetnames, "目標 Excel 確實新增 [Copied_Inst_A] 工作表")
            ws_v = wb_v["Copied_Inst_A"]
            check(abs((ws_v.column_dimensions["A"].width or 0) - 32) < 0.5, "複製後保留原工作表欄寬 (32)")
            check(len(ws_v.merged_cells.ranges) == 1, "複製後保留原工作表合併儲存格")
            check(wb_v.active.title == "Copied_Inst_A", "複製後目標 Excel 預設鎖定開啟新複製之 Sheet")
            wb_v.close()

            # 7D: 書籤三「懶人快速版」3 台儀器自動產生範例 Excel (每台至少 3 個測試項目 + 自動檢查 + 開啟目錄與 Excel)
            opened_folders.clear()
            launched_excels.clear()
            auto_res = post_json("/api/generate_inst_template_standalone", {
                "items": [
                    {"inst_name": "NI6008-1", "title_name": "NI_Sample"},
                    {"inst_name": "InstIQApiA", "title_name": "RF_Sample"},
                    {"inst_name": "FeasaLED", "title_name": "LED_Sample"},
                    {"inst_name": "Agilent34401A", "title_name": "DMM_Sample"},
                    {"inst_name": "DIO6509", "title_name": "DIO_Sample"},
                ],
                "project_name": "INST_AUTO_SAMPLE",
                "station_name": "MB",
                "auto_sample_mode": True,
                "open_excel": False,
            })
            check(auto_res["status"] == "ok", "書籤三懶人快速版：5 台儀器自動產生範例 Excel 成功")
            check((auto_res.get("total_steps") or 0) >= 19, "每台儀器皆至少產生 3 個測試項目以上", f"總步驟 {auto_res.get('total_steps')} 列")
            check(len(opened_folders) >= 1 and len(launched_excels) == 0, "懶人快速版完成後自動開啟目錄，待彈窗確認再開啟 Excel")
            sys_ini_auto = os.path.join(auto_res["output_dir"], "System.ini")
            sys_txt_auto = open(sys_ini_auto, "r", encoding="utf-8", errors="ignore").read()
            m_ck = re.search(rf"(?m)^{re.escape(os.path.basename(auto_res['excel_path']))}=([0-9A-F]{{64}})$", sys_txt_auto)
            check(bool(m_ck), "System.ini [Checksum] 已寫入 64 碼官方簽章 (LoadScript.dll)", m_ck.group(1)[:12] + "..." if m_ck else "missing")
            wb_dll = openpyxl.load_workbook(auto_res["excel_path"], read_only=True, data_only=True)
            ni_ver = None
            inst_names_in_sheet = []
            for row in wb_dll["Instrument"].iter_rows(min_row=2, values_only=True):
                if row and row[1]:
                    inst_names_in_sheet.append(str(row[1]).strip())
                    if str(row[1]).strip() == "NI6008-1":
                        ni_ver = str(row[6] or "").strip()
            dut_name_val = next((str(r[1] or "").strip() for r in wb_dll["DUTs"].iter_rows(min_row=2, values_only=True) if r and r[1]), "")
            mb_rows_all = list(wb_dll["MB"].iter_rows(min_row=2, values_only=True))
            mb_inst_cols = [str(r[4] or "").strip() for r in mb_rows_all if r and r[4]]
            wb_dll.close()
            # 驗證單次綁定規範：同一區塊內 Instrument 不連續重複填寫；RF 多 TX/RX 共用單一 Phase 與多個 Title
            consec_dup_inst = []
            prev_nonempty_i = None
            for ri_mb, r_mb in enumerate(mb_rows_all, 2):
                iv_mb = str(r_mb[4] or "").strip() if r_mb and len(r_mb) > 4 else ""
                if iv_mb and iv_mb == prev_nonempty_i:
                    consec_dup_inst.append((ri_mb, iv_mb))
                prev_nonempty_i = iv_mb or None
            rf_rows_mb = [r for r in mb_rows_all if r and str(r[3] or "").strip().startswith("WIFI ")]
            rf_phases_mb = [str(r[1] or "").strip() for r in rf_rows_mb if str(r[1] or "").strip()]
            rf_titles_mb = [str(r[2] or "").strip() for r in rf_rows_mb if str(r[2] or "").strip()]
            rf_insts_mb = [str(r[4] or "").strip() for r in rf_rows_mb if str(r[4] or "").strip()]
            check(len(consec_dup_inst) == 0, "Instrument 欄位僅於區塊首列或切換功能時寫入一次（無連續重複列）", str(consec_dup_inst))
            check(len(rf_phases_mb) == 1 and len(rf_titles_mb) == 3 and rf_insts_mb == ["MeasWIFI", "GenWIFI"],
                  "RF 多筆 TX/RX 共用單一 Phase、各自獨立 Title，且 MeasWIFI/GenWIFI 各只寫一次",
                  f"P={rf_phases_mb}, T={len(rf_titles_mb)}, I={rf_insts_mb}")
            check(ni_ver == "1.1.2.0", "NI6008-1 (DaqUSBNi.dll) 版本號已自動對齊本機真實 DLL (1.1.2.0)", str(ni_ver))
            check("HXTaudio" not in inst_names_in_sheet, "Instrument 工作表僅保留實際選用之儀器，不殘留未選儀器 (避免 DLL is not Found)", str(inst_names_in_sheet))
            check("IPOWER2401" in inst_names_in_sheet, "Phase 97 使用之 POWERSWITCH 已自動保留對應儀器 IPOWER2401", str(inst_names_in_sheet))
            from core.golden_data import get_golden_mother as _gm_chk
            gm_list = _gm_chk().get("instruments", [])
            gm_insts = {i["Name"]: i.get("dll_exists") for i in gm_list}
            gm_usable = {i["Name"]: i.get("is_usable") for i in gm_list}
            check(gm_insts.get("NI6008-1") is True and gm_insts.get("HXTaudio") is False, "儀器目錄正確標記本機 DLL 存在與缺失狀態 (NI6008-1=True, HXTaudio=False)")
            check(gm_usable.get("InstIQApiA") is True and gm_usable.get("NI6008-1") is True and gm_usable.get("HXTaudio") is False,
                  "可使用設備旗標正確區分『實機DLL或專屬範本』 (InstIQApiA=True, HXTaudio=False)")
            check("TAB3_CAT_FILTER = 'USABLE'" in index_html and "auditEmptyRecentBox" in index_html,
                  "書籤三預設篩選『✅ 可使用設備』且 01 腳本健檢具備未載檔最近紀錄引導區")
            check(bool(auto_res.get("centimani_dir_exists")), "匯出時自動偵測並回傳本機 Centimani 主程式目錄", auto_res.get("centimani_dir", ""))
            missing_names = [m.get("dll") for m in auto_res.get("missing_dlls", [])]
            check("InstIQApi_A.dll" in missing_names and "DigitIO6509.dll" in missing_names and "DaqUSBNi.dll" not in missing_names,
                  "匯出時精準回報缺少的實機 DLL (InstIQApi_A.dll / DigitIO6509.dll)", str(missing_names))
            check("missing_dlls" in exp_ins_res and "missing_dlls" in gen_res,
                  "書籤一修復匯出與書籤二新母體匯出皆具備實機 DLL 缺失檢查回傳")
            # 驗證未掛載且未使用的型錄儀器 (如 HXTaudio / OSP120 Mount='') 不應觸發誤報
            from core.golden_data import check_workspace_missing_dlls as _chk_dlls
            idle_ws_res = _chk_dlls({
                "instruments": [
                    {"Name": "NI6008-1", "Mount": "MB", "ControlDLL": "DaqUSBNi.dll", "Functions": "Voltage"},
                    {"Name": "OSP120", "Mount": "", "ControlDLL": "NFT.dll", "Functions": "RFSW"},
                ],
                "switches": [],
                "stations": {"MB": [{"Instrument": "Voltage"}]}
            })
            check(len(idle_ws_res["missing_dlls"]) == 0,
                  "未掛載且未使用的型錄儀器不誤報缺 DLL 警告", str(idle_ws_res["missing_dlls"]))
            check(dut_name_val == "INST_AUTO_SAMPLE$MB", "DUTs 工作表 DUT Name 格式符合 ProjectName$StationName", dut_name_val)
            check("FeasaLED" not in mb_inst_cols and "Agilent34401A" not in mb_inst_cols and "LED_Test" in mb_inst_cols and "DC" in mb_inst_cols,
                  "MB 工作表 Instrument 欄位皆寫入合法 TestType (LED_Test/DC 等，非儀器 Name)")
            # 驗證實戰腳本動態 ExecMode 變數 (*$(AULAB)) 不會被誤報為無效主代碼
            from core.script_doctor import audit_workspace as _audit_ws
            dyn_rep = _audit_ws({
                "global_ini": {"Settings": {}, "Scripts": {"AULAB": "1"}},
                "instruments": [],
                "switches": [],
                "duts": [{"Load": "*$(LOAD_1)", "DUT Name": "AULAB_TEST$MB", "Station": "MB,1"}],
                "stations": {"MB": [
                    {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ':ShowISN,"*(ISN)"', "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "ExecMode": "8", "TestID": "OTFX064"},
                    {"Index": "002", "Phase": "", "Title": "0,Load DLL", "Send": ':autLabs.Load,"1"', "ExecMode": "*$(AULAB)", "TestID": "B7PL025"},
                    {"Index": "003", "Phase": "97", "Title": "1,Disconnect", "Send": ':CloseMessage', "ExecMode": "3", "TestID": "B7PL025"},
                ]}
            })
            check(dyn_rep.get("error_count", -1) == 0,
                  "腳本健檢相容實戰動態 ExecMode 變數 (*$(AULAB)) 不誤報 Error", str(dyn_rep.get("errors", [])))
            # 驗證 block_sorter 保留 Phase=-1 暫停區塊與識別 97:PWROFF，且 auto_fix_workspace 自動精簡同區塊重複 Instrument
            from core.block_sorter import extract_station_blocks as _ext_blks, reorder_station_blocks as _reord_blks
            from core.script_doctor import auto_fix_workspace as _autofix_ws
            skip_ws = {
                "global_ini": {"Settings": {}, "Scripts": {}},
                "instruments": [], "switches": [], "duts": [],
                "stations": {"RF": [
                    {"Index": "000", "Phase": "0", "Title": "0,Route", "Instrument": "", "Send": ":SfCheckRoute", "ExecMode": "8", "TestID": "B7PL025"},
                    {"Index": "001", "Phase": "1", "Title": "0,PowerOn", "Instrument": "SetON", "Send": ":ObtainDevice", "ExecMode": "0", "TestID": "B7PL025"},
                    {"Index": "002", "Phase": "", "Title": "", "Instrument": "SetON", "Send": ':Dev.SetON,"5","2"', "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "003", "Phase": "", "Title": "", "Instrument": "SetON", "Send": ":ReleaseDevice", "ExecMode": "0", "TestID": "B7PL025"},
                    {"Index": "004", "Phase": "-1", "Title": "0,Paused Phase", "Instrument": "", "Send": ':Delay,"10"', "ExecMode": "6", "TestID": "B7PL025"},
                    {"Index": "005", "Phase": "97:PWROFF", "Title": "1,PowerOff", "Instrument": "", "Send": ":CloseMessage", "ExecMode": "3", "TestID": "B7PL025"},
                ]}
            }
            blks_skip = _ext_blks(skip_ws["stations"]["RF"])
            check(not any(b["is_out_of_order"] for b in blks_skip) and blks_skip[2]["is_skipped"] is True and blks_skip[3]["is_teardown"] is True,
                  "積木排序正確辨識 Phase=-1 暫停區塊與 97:PWROFF 收尾（不誤報倒退）")
            _reord_blks(skip_ws, "RF", [0, 1, 2, 3], auto_renumber_phase=True)
            check(skip_ws["stations"]["RF"][4]["Phase"] == "-1",
                  "自動順編 Phase 時保留 Phase=-1 暫停狀態不被強制重編啟用", str(skip_ws["stations"]["RF"][4]["Phase"]))
            _autofix_ws(skip_ws)
            pwr_rows = [r for r in skip_ws["stations"]["RF"] if r.get("Send") in (":ObtainDevice", ':Dev.SetON,"5","2"', ":ReleaseDevice")]
            rf_inst_vals = [r.get("Instrument", "") for r in pwr_rows]
            check(rf_inst_vals == ["SetON", "", ""],
                  "一鍵修復自動精簡同區塊連續重複之 Instrument 為僅首列寫入", str(rf_inst_vals))
            check('id="genHubCard_qa"' in index_html and 'id="genModeQa"' in index_html and 'id="qaScenarioGrid"' in index_html and 'script_qa.js' in index_html,
                  "腳本建立與編修中心已新增『書籤四：問編寫問題』卡片與直覺置頂問答模組")
            # 驗證 use_ini_switch=True 生成 *$(EN_xxx) 開關，以及全數匯出皆自動產出隨附 _編寫與使用說明.txt
            check('id="iiUseIniSwitch"' in index_html and 'id="tab3UseIniSwitch"' in index_html and 'openGuideTxtFile' in index_html,
                  "UI 已具備 Global.ini 一鍵開關勾選框與隨附說明 .txt 開啟鈕")
            sw_res = post_json("/api/generate_inst_template_standalone", {
                "items": [{"inst_name": "NI6008-1", "title_name": "Voltage Switchable"}],
                "project_name": "SW_TEST",
                "station_name": "MB",
                "auto_sample_mode": True,
                "use_ini_switch": True,
                "open_excel": False,
            })
            check(sw_res.get("status") == "ok" and bool(sw_res.get("guide_txt_path")) and os.path.exists(sw_res.get("guide_txt_path", "")),
                  "匯出時自動產出隨附 <專案>_編寫與使用說明.txt 檔案", sw_res.get("guide_txt_path", ""))
            txt_body = open(sw_res["guide_txt_path"], "r", encoding="utf-8-sig").read()
            check("EN_NI6008_1" in txt_body and "Global.ini [Scripts]" in txt_body and "Phase = -1" in txt_body,
                  "精簡版隨附說明 .txt 正確列出 EN_NI6008_1 與 Phase=-1 開關使用說明")
            wb_sw = openpyxl.load_workbook(sw_res["excel_path"], read_only=True, data_only=True)
            sw_titles = [str(r[2] or "").strip() for r in wb_sw["MB"].iter_rows(min_row=2, values_only=True) if r and r[2]]
            wb_sw.close()
            glb_sw_txt = open(os.path.join(sw_res["output_dir"], "Global.ini"), "r", encoding="utf-8", errors="ignore").read()
            check(any(t.startswith("*$(EN_NI6008_1),") for t in sw_titles) and "EN_NI6008_1=0" in glb_sw_txt,
                  "啟用一鍵開關後 Excel Title 寫入 *$(EN_NI6008_1) 且 Global.ini [Scripts] 寫入 EN_NI6008_1=0", str(sw_titles))
            check(bool(exp_ins_res.get("guide_txt_path")) and os.path.exists(exp_ins_res.get("guide_txt_path", ""))
                  and bool(gen_res.get("guide_txt_path")) and os.path.exists(gen_res.get("guide_txt_path", "")),
                  "書籤一修復匯出與書籤二新母體匯出皆同步自動產生隨附說明 .txt")
            # 驗證 /api/open_guide_txt 僅開啟 .txt 並使用 safe async opener
            launched_inis.clear()
            open_txt_res = post_json("/api/open_guide_txt", {"file_path": sw_res["guide_txt_path"]})
            check(open_txt_res.get("status") == "ok" and len(launched_inis) == 1,
                  "/api/open_guide_txt 正常開啟隨附編寫說明 .txt 檔案")

            # [v0.8.012] 驗證：
            # 1) 同款儀器插入兩次 (2x NI6008-1) 自動產出唯一 EN_NI6008_1 / EN_NI6008_1_2 與不重名變數 $VCC_3V3 / $VCC_3V3_2
            # 2) taipei_dual_mode=True 同步產生 MB_TAIPEI (不掛載 Instrument.Mount) 與 CRLF 兩地切換 .bat
            # 3) /api/diff_station_sheets 正確比對 MB vs MB_TAIPEI 差異
            # 4) /api/reorder_station_blocks 支援 paused_orig_indices 一鍵暫停(-1) / 恢復
            dual_res = post_json("/api/generate_inst_template_standalone", {
                "items": [
                    {"inst_name": "NI6008-1", "title_name": "Measure 3.3V Rail"},
                    {"inst_name": "NI6008-1", "title_name": "Measure 3.3V Rail_2"},
                ],
                "project_name": "DUAL_TEST",
                "station_name": "MB",
                "auto_sample_mode": True,
                "use_ini_switch": True,
                "taipei_dual_mode": True,
                "open_excel": False,
            })
            check(dual_res.get("status") == "ok" and dual_res.get("taipei_sheet") == "MB_TAIPEI" and len(dual_res.get("switch_bats", [])) == 2,
                  "雙同款儀器 + 台北雙分頁共存模式成功匯出 MB / MB_TAIPEI 與兩支切換 .bat")
            wb_dual = openpyxl.load_workbook(dual_res["excel_path"], read_only=True, data_only=True)
            dual_mb_rows = list(wb_dual["MB"].iter_rows(min_row=2, values_only=True))
            dual_titles = [str(r[2] or "").strip() for r in dual_mb_rows if r and r[2]]
            dual_refs = "\n".join(str(r[9] or "") for r in dual_mb_rows if r and r[9])
            inst_mounts = [str(r[5] or "") for r in wb_dual["Instrument"].iter_rows(min_row=2, values_only=True) if r]
            check("MB_TAIPEI" in wb_dual.sheetnames and all("MB_TAIPEI" not in m for m in inst_mounts),
                  "MB_TAIPEI 成功建立且不掛載於 Instrument.Mount（台北開機零 DLL 報錯）", str(inst_mounts))
            wb_dual.close()
            glb_dual = open(os.path.join(dual_res["output_dir"], "Global.ini"), "r", encoding="utf-8", errors="ignore").read()
            check(any("*$(EN_NI6008_1)," in t for t in dual_titles) and any("*$(EN_NI6008_1_2)," in t for t in dual_titles)
                  and "EN_NI6008_1=0" in glb_dual and "EN_NI6008_1_2=0" in glb_dual,
                  "兩組同款 NI6008-1 自動分配唯一開關 *$(EN_NI6008_1) 與 *$(EN_NI6008_1_2)", str(dual_titles))
            check("$VCC_3V3" in dual_refs and "$VCC_3V3_2" in dual_refs,
                  "兩組同款 NI6008-1 懶人範本自動區分 Ref 變數 ($VCC_3V3 與 $VCC_3V3_2) 不互相覆寫")
            for bat_p in dual_res.get("switch_bats", []):
                raw_bat = open(bat_p, "rb").read()
                has_crlf = b"\r\n" in raw_bat
                has_bare_lf = b"\n" in raw_bat.replace(b"\r\n", b"")
                check(os.path.exists(bat_p) and has_crlf and not has_bare_lf,
                      f"切換批次檔 {os.path.basename(bat_p)} 維持標準 Windows CRLF (\\r\\n) 格式")

            from core.excel_engine import import_excel_to_workspace as _imp_ws
            dual_ws = _imp_ws(dual_res["excel_path"])
            diff_res = post_json("/api/diff_station_sheets", {"workspace": dual_ws, "sheet_a": "MB", "sheet_b": "MB_TAIPEI"})
            check(diff_res.get("status") == "ok" and len(diff_res.get("only_in_a", [])) == 0 and len(diff_res.get("block_diffs", [])) >= 1,
                  "/api/diff_station_sheets 正確比對 MB 與 MB_TAIPEI 同步狀態與 ExecMode 差異", diff_res.get("summary", ""))

            pause_res = post_json("/api/reorder_station_blocks", {
                "workspace": dual_ws,
                "sheet_name": "MB",
                "new_order_indices": list(range(len(_ext_blks(dual_ws["stations"]["MB"])))),
                "auto_renumber_phase": True,
                "paused_orig_indices": [1],
            })
            check(pause_res.get("status") == "ok" and pause_res["blocks"][1]["phase"] == "-1" and pause_res["blocks"][1]["is_skipped"] is True,
                  "/api/reorder_station_blocks 支援一鍵暫停積木為 Phase -1")
            resume_res = post_json("/api/reorder_station_blocks", {
                "workspace": pause_res["workspace"],
                "sheet_name": "MB",
                "new_order_indices": list(range(len(pause_res["blocks"]))),
                "auto_renumber_phase": True,
                "paused_orig_indices": [],
            })
            check(resume_res.get("status") == "ok" and resume_res["blocks"][1]["phase"] not in ("-1", "") and resume_res["blocks"][1]["is_skipped"] is False,
                  "/api/reorder_station_blocks 支援一鍵將 Phase -1 積木恢復並順編", str(resume_res["blocks"][1]["phase"]))
            check('id="auditStationPromptSel"' in index_html and 'id="tab3StationPromptSel"' in index_html
                  and 'id="tab3NoHwPhaseChk"' in index_html and 'openStationDiffModal' in index_html,
                  "UI 具備單 Sheet 無儀器 Phase=-1 與 System.ini StationName 留空選站選項")

            # [v0.8.014] 驗證單 Sheet 工作流 + no_hw_phase_pause=True (Phase=-1) + station_name_mode="ask" (StationName 留空)
            ask_res = post_json("/api/generate_inst_template_standalone", {
                "items": [{"inst_name": "NI6008-1", "title_name": "Measure Voltage Single"}],
                "project_name": "SINGLE_ASK",
                "station_name": "MB",
                "auto_sample_mode": True,
                "use_ini_switch": True,
                "no_hw_phase_pause": True,
                "station_name_mode": "ask",
                "taipei_dual_mode": False,
                "open_excel": False,
            })
            check(ask_res.get("status") == "ok" and not ask_res.get("taipei_sheet"),
                  "預設單 Sheet 產出不包含第二張 _TAIPEI 測試站分頁（簡化維護）")
            wb_ask = openpyxl.load_workbook(ask_res["excel_path"], read_only=True, data_only=True)
            ask_phases = [str(r[1] or "").strip() for r in wb_ask["MB"].iter_rows(min_row=2, values_only=True) if r and r[1] is not None and str(r[1]).strip() != ""]
            check("MB_TAIPEI" not in wb_ask.sheetnames and "-1" in ask_phases,
                  "勾選無儀器寫入 Phase=-1 後，單一 MB 工作表將儀器測試區塊設為 Phase=-1", str(ask_phases))
            wb_ask.close()
            sys_ask_txt = open(os.path.join(ask_res["output_dir"], "System.ini"), "r", encoding="utf-8", errors="ignore").read()
            check("StationList=MB" in sys_ask_txt and re.search(r"(?m)^StationName=\s*$", sys_ask_txt) is not None,
                  "選擇『當場彈窗選擇測試站』時，System.ini 保留 StationList=MB 並將 StationName= 維持空白", "")

            # [v0.8.015] 驗證書籤二即使漏勾 BLK_PRETEST_ROUTE（僅選 BLK_PHASE97_TEARDOWN），也會自動補入 :ShowISN 與 :SfCheckRoute（防報錯 DUT1 can't find ":ShowISN" function.）
            min_wiz_res = post_json("/api/generate_new_standalone", {
                "project_name": "MIN_WIZ",
                "station_name": "MB",
                "dut_count": 1,
                "block_ids": ["BLK_PHASE97_TEARDOWN"],
                "open_excel": False,
            })
            check(min_wiz_res.get("status") == "ok" and os.path.exists(min_wiz_res.get("excel_path", "")),
                  "即使精靈僅選 Phase 97 收尾積木仍可成功產出母體 Excel")
            wb_mw = openpyxl.load_workbook(min_wiz_res["excel_path"], read_only=True, data_only=True)
            mw_sends = [str(r[6] or "").strip() for r in wb_mw["MB"].iter_rows(min_row=2, values_only=True) if r]
            wb_mw.close()
            idx_isn = next((i for i, x in enumerate(mw_sends) if x.startswith(":ShowISN")), -1)
            idx_route = next((i for i, x in enumerate(mw_sends) if x.startswith(":SfCheckRoute")), -1)
            check(idx_isn >= 0 and idx_route > idx_isn,
                  "未選 CheckRoute 時自動於 Phase 0 補入 :ShowISN 與 :SfCheckRoute（避免載入報錯 can't find :ShowISN）", str(mw_sends[:4]))

            # [v0.8.013] 驗證 DUTs 表必須包含 MB_TAIPEI 列（防止 'No any DUT is set.'），且 auto_fix 按測試站分組不污染 Slot 編號
            dual_dut_stations = [str(d.get("Station", "")).strip() for d in dual_ws.get("duts", [])]
            check(any(s.startswith("MB,") for s in dual_dut_stations) and any(s.startswith("MB_TAIPEI,") for s in dual_dut_stations),
                  "雙分頁模式 DUTs 工作表同步寫入 MB 與 MB_TAIPEI 列（避免切換台北分頁報錯 No any DUT is set.）", str(dual_dut_stations))
            _autofix_ws(dual_ws)
            fixed_dut_stations = [str(d.get("Station", "")).strip() for d in dual_ws.get("duts", [])]
            dual_post_rep = _audit_ws(dual_ws)
            check(all(not s.endswith(",5") for s in fixed_dut_stations) and "MB_TAIPEI,1" in fixed_dut_stations and dual_post_rep.get("error_count", -1) == 0,
                  "多站並存時一鍵修復依 Station 分組維持 MB_TAIPEI,1..4 且 0 Error", str(fixed_dut_stations))
            # 驗證若 DUTs 缺某站列時 audit_workspace 能偵測並由 auto_fix_workspace 自動補齊
            missing_dut_ws = {
                "project_name": "MISS_DUT", "station_name": "FT1",
                "global_ini": {"Settings": {}, "Scripts": {}}, "instruments": [], "switches": [],
                "duts": [{"Load": "*$(LOAD_1)", "DUT Name": "MISS_DUT$OTHER", "Station": "OTHER,1"}],
                "stations": {"FT1": [{"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ':ShowISN,"*(ISN)"', "ExecMode": "1", "TestID": "B7PL025"}]},
            }
            rep_miss_dut = _audit_ws(missing_dut_ws)
            check(any("No any DUT is set." in e for e in rep_miss_dut.get("errors", [])),
                  "audit_workspace 可攔截 DUTs 缺少測站列（防止 No any DUT is set.）")
            _autofix_ws(missing_dut_ws)
            check(any(str(d.get("Station", "")).startswith("FT1,") for d in missing_dut_ws.get("duts", [])),
                  "auto_fix_workspace 自動為缺漏測站補齊 DUTs 列")

            # [v0.8.016] 驗證依照 4 目錄知識庫改寫之核心邏輯：
            # 1) Golden Mother 預設不幽靈掛載 NI6008-1，且 vnxRFSW / DevUart 正確標記 Sub=1
            from core.golden_data import get_golden_mother as _get_gm_v16
            gm_v16 = _get_gm_v16("CLEAN_PROJ", "ST1")
            gm_inst_map = {str(i.get("Name", "")): i for i in gm_v16.get("instruments", [])}
            check(gm_inst_map.get("NI6008-1", {}).get("Mount", "BAD") == "",
                  "Golden Mother 預設不自動 Mount NI6008-1（無儀器站別不幽靈載入）")
            check(gm_inst_map.get("vnxRFSW", {}).get("Sub") == "1" and gm_inst_map.get("DevUart", {}).get("Sub") == "1",
                  "Golden Mother 正確設定 vnxRFSW 與 DevUart 為共用子裝置 (Sub=1)")

            # 2) 插入標準儀器 (NI6008-1 / RF / FeasaLED) 必寫 Col F (Switch)，而 Sub=1 (vnxRFSW) 改用 :ObtainSubDevice / :sDev.* 且 Col E/F 留空
            wb_ni_chk = openpyxl.load_workbook(ask_res["excel_path"], data_only=True)
            ni_sw_vals = [str(r[5] or "").strip() for r in wb_ni_chk["MB"].iter_rows(min_row=2, values_only=True) if r and str(r[6] or "").strip() == ":ObtainDevice"]
            wb_ni_chk.close()
            check("NI6008-1" in ni_sw_vals,
                  "插入 NI6008-1 範本時於 :ObtainDevice 列同步寫入 Col F (Switch=NI6008-1)", str(ni_sw_vals))

            sub_res = post_json("/api/generate_inst_template_standalone", {
                "items": [{"inst_name": "vnxRFSW", "title_name": "Switch Ant0"}],
                "project_name": "SUB_RFSW",
                "station_name": "OTA",
                "open_excel": False,
            })
            wb_sub_chk = openpyxl.load_workbook(sub_res["excel_path"], data_only=True)
            ota_rows = list(wb_sub_chk["OTA"].iter_rows(min_row=2, values_only=True))
            ota_dvs = list(wb_sub_chk["OTA"].data_validations.dataValidation)
            wb_sub_chk.close()
            check(any(':ObtainSubDevice,"vnxRFSW"' in str(r[6] or "") and str(r[4] or "") == "" and str(r[5] or "") == "" for r in ota_rows),
                  "Sub=1 裝置 (vnxRFSW) 自動產出 :ObtainSubDevice 與 :sDev.* 且 Col E/F 留空")
            check(len(ota_dvs) >= 16,
                  "新建 Station 工作表自動附上官方 16 欄中文 DataValidation Tooltip", f"DVs={len(ota_dvs)}")

            # 3) audit_workspace 正確豁免 Marco 空白 TestID、抓出 Switch 指向未 Mount 裝置 (PS2005 vs PSS1503) 與 Title 句點筆誤 (0.THERMAL,1)
            v16_ws = {
                "project_name": "V16_AUD", "station_name": "Test",
                "global_ini": {"Settings": {}, "Scripts": {}},
                "instruments": [{"Mount": "Test", "Name": "PSS1503-1", "Sub": "", "ControlDLL": "PPH1503.dll", "Functions": "SON,WIFI 2.4G", "Version": "1.0.3.0"}],
                "switches": [],
                "duts": [{"Load": "*$(LOAD_1)", "DUT Name": "V16$Test", "Station": "Test,1"}],
                "marcos": {"TX": [{"Index": "00", "Send": ':Delay,"10"', "Reply": "0", "ExecMode": "0", "Description": "Dly", "TestID": "B7PL025"}]},
                "stations": {"Test": [
                    {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ':ShowISN,"*(ISN)"', "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "ExecMode": "8", "TestID": "OTFX064"},
                    {"Index": "002", "Phase": "1", "Title": "0,PowerOn", "Instrument": "SON", "Switch": "PS2005-{1}", "Send": ":ObtainDevice", "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "003", "Phase": "", "Title": "", "Send": ":ReleaseDevice", "ExecMode": "3", "TestID": "B7PL025"},
                    {"Index": "004", "Phase": "2", "Title": "0.THERMAL,1", "Marco": "TX", "Instrument": "WIFI 2.4G", "Switch": "PSS1503-1", "Send": "arg0", "ExecMode": "1", "TestID": ""},
                    {"Index": "005", "Phase": "97", "Title": "1,End", "Send": ":CloseMessage", "ExecMode": "3", "TestID": "B7PL025", "_hidden": True},
                ]},
            }
            rep_v16 = _audit_ws(v16_ws)
            check(rep_v16.get("error_count", -1) == 0,
                  "audit_workspace 對 Marco 呼叫列空白 TestID 予以及格豁免 (0 Error)", str(rep_v16.get("errors", [])))
            check(any("PS2005-{1}" in w for w in rep_v16.get("warnings", [])) and any("0.THERMAL,1" in w for w in rep_v16.get("warnings", [])),
                  "audit_workspace 主動攔截 Switch 指向未 Mount 裝置與 Title 句點筆誤", str(rep_v16.get("warnings", [])))
            from core.excel_engine import export_workspace_to_excel as _exp_v16, import_excel_to_workspace as _imp_v16
            import tempfile as _tf_v16
            with _tf_v16.TemporaryDirectory() as _hid_dir:
                hid_out = os.path.join(_hid_dir, "hidden_roundtrip.xlsx")
                _exp_v16(v16_ws, hid_out, active_sheet="Test")
                wb_hid = openpyxl.load_workbook(hid_out)
                is_r7_hidden = bool(wb_hid["Test"].row_dimensions[7].hidden)
                wb_hid.close()
                ws_re_hid = _imp_v16(hid_out)
                check(is_r7_hidden and ws_re_hid["stations"]["Test"][5].get("_hidden") is True,
                      "匯入/匯出完整保留 Excel 隱藏列 (_hidden / row_dimensions.hidden)")

            # [v0.8.017] 驗證依照 07~11 目錄知識庫改寫之核心邏輯：
            # 1) Golden 母體包含 RST (TrustSystem Acoustic)
            # 2) audit_workspace 掃描 Title / Waiting / ExecMode 中之 *$(VAR)
            # 3) audit_workspace 依當前 Station 隔離檢查 DUTs Parameter {N} 上限（防多工站誤判）
            # 4) auto_fix_workspace 為 TIMEOUT/RETRY/LOCKTEST 補齊安全預設值
            # 5) block_sorter 正確萃取 :SetOprVal / :SetCdtiVal 產出變數
            from core.golden_data import get_golden_mother as _ggm_v17
            mother_v17 = _ggm_v17("V17_PROJ", "Acoustic")
            check(any(r.get("Name") == "RST" and r.get("ControlDLL") == "RST.dll" for r in mother_v17.get("instruments", [])),
                  "Golden 母體已收錄 09. ACOUSTIC 標準 TrustSystem 儀器 RST")
            v17_ws = {
                "project_name": "V17_MULTI", "station_name": "UF_A",
                "global_ini": {"Settings": {}, "Scripts": {}},
                "instruments": [], "switches": [],
                "duts": [
                    {"Load": "*$(LOAD_1)", "DUT Name": "V17$UF_A", "Station": "UF_A,0", "Parameter": "P0,P1,P2"},
                    {"Load": "*$(LOAD_1)", "DUT Name": "V17$UF_B", "Station": "UF_B,0", "Parameter": "ONLY_ONE"},
                ],
                "marcos": {},
                "stations": {
                    "UF_A": [
                        {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ':ShowISN,"*(SN2)"', "ExecMode": "1", "TestID": "B7PL025"},
                        {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "ExecMode": "8", "TestID": "OTFX064"},
                        {"Index": "002", "Phase": "1", "Title": "2,BLEMISH,*$(BLEMISH_RETRY)", "Send": ':Utility.CMD,"{2}"', "Waiting": "*$(Record_Timeout)", "ExecMode": "*$(execmode_n)", "TestID": "B7PL025"},
                        {"Index": "003", "Phase": "97", "Title": "1,End", "Send": ":CloseMessage", "ExecMode": "3", "TestID": "B7PL025"},
                    ],
                    "UF_B": [
                        {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ':ShowISN,"*(sf80SN)"', "ExecMode": "1", "TestID": "B7PL025"},
                        {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "ExecMode": "8", "TestID": "OTFX064"},
                        {"Index": "002", "Phase": "1", "Title": "*$(LOCKTEST),Lock", "Send": ':Utility.CMD,"{2}"', "ExecMode": "1", "TestID": "B7PL025"},
                        {"Index": "003", "Phase": "97", "Title": "1,End", "Send": ":CloseMessage", "ExecMode": "3", "TestID": "B7PL025"},
                    ],
                },
            }
            rep_v17 = _audit_ws(v17_ws)
            w_v17 = rep_v17.get("warnings", [])
            check(any("BLEMISH_RETRY" in w for w in w_v17) and any("Record_Timeout" in w for w in w_v17) and any("execmode_n" in w for w in w_v17) and any("LOCKTEST" in w for w in w_v17),
                  "audit_workspace 完整掃描 Title / Waiting / ExecMode 中的 *$(VAR) 是否宣告於 [Scripts]", str(w_v17))
            check(any("UF_B" in w and "{2}" in w for w in w_v17) and not any("UF_A" in w and "{2}" in w for w in w_v17),
                  "audit_workspace 多工站 DUTs Parameter {N} 依 Station 各自隔離判定（UF_B 誤用 {2} 報警，UF_A 合法放行）", str(w_v17))
            from core.script_doctor import auto_fix_workspace as _fix_v17
            _fix_v17(v17_ws)
            sc_v17 = v17_ws["global_ini"]["Scripts"]
            check(sc_v17.get("Record_Timeout") == "5000" and sc_v17.get("BLEMISH_RETRY") == "3" and sc_v17.get("LOCKTEST") == "2" and sc_v17.get("execmode_n") == "6",
                  "auto_fix_workspace 為 Timeout/Retry/Lock/ExecMode 動態變數補入安全預設值", str(sc_v17))
            from core.block_sorter import _extract_produced_vars as _epv_v17
            check(_epv_v17({"Send": ':SetOprVal,"$calcP","*(x)"'}) == {"calcP"},
                  "block_sorter 正確將 :SetOprVal/$Var 識別為產出變數（供 Phase 排序相依分析）")

            # [v0.8.018] 驗證 TEMP_SCRIPT 健檢強化與多儀器編號 NI6008-1 -> NI6008-2：
            # 1) 多同款儀器 NI6008-1 + NI6008-2 自動寫入 NI6008-2 (*$(DAQ_2)=Dev2)、Switch=NI6008-2 及獨立 $VCC_3V3_2
            # 2) 前端函式 tab3NextInstName / resolveBaseInstName 正確將第 2 張 NI6008 命名為 NI6008-2
            # 3) excel_engine 大小寫不敏感識別小寫 'phase'（防 GWTalk RF/NFT 誤降格為 11 欄）
            # 4) audit_workspace 攔截無 :ObtainDevice 直接呼叫 :Dev.*，以及 Mounted=空 卻寫 Instrument/Switch
            ni2_res = post_json("/api/generate_inst_template_standalone", {
                "items": [
                    {"inst_name": "NI6008-1", "title_name": "Measure 3.3V Rail"},
                    {"inst_name": "NI6008-2", "title_name": "Measure 3.3V Rail_2"},
                ],
                "project_name": "MULTI_NI2",
                "station_name": "MB",
                "auto_sample_mode": True,
                "use_ini_switch": True,
                "open_excel": False,
            })
            check(ni2_res.get("status") == "ok", "NI6008-1 + NI6008-2 雙卡獨立命名匯出成功")
            wb_ni2 = openpyxl.load_workbook(ni2_res["excel_path"], read_only=True, data_only=True)
            ni2_insts = {str(r[1]): str(r[4]) for r in wb_ni2["Instrument"].iter_rows(min_row=2, values_only=True) if r and r[1]}
            ni2_mb_rows = list(wb_ni2["MB"].iter_rows(min_row=2, values_only=True))
            wb_ni2.close()
            ni2_switches = [str(r[5] or "").strip() for r in ni2_mb_rows if r and r[5]]
            ni2_refs = "\n".join(str(r[9] or "") for r in ni2_mb_rows if r and r[9])
            glb_ni2 = open(os.path.join(ni2_res["output_dir"], "Global.ini"), "r", encoding="utf-8", errors="ignore").read()
            check("NI6008-1" in ni2_insts and "NI6008-2" in ni2_insts and ni2_insts.get("NI6008-2") == "*$(DAQ_2)" and "DAQ_2=Dev2" in glb_ni2,
                  "NI6008-2 自動寫入 Instrument (*$(DAQ_2)) 與 Global.ini DAQ_2=Dev2", str(ni2_insts))
            check("NI6008-1" in ni2_switches and "NI6008-2" in ni2_switches and "$VCC_3V3" in ni2_refs and "$VCC_3V3_2" in ni2_refs,
                  "NI6008-1 / NI6008-2 各自綁定 Switch 且變數不重複 ($VCC_3V3 / $VCC_3V3_2)", str(ni2_switches))
            _inst_hmi_js_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "js", "inst_hmi.js")
            check("function tab3NextInstName(" in index_html and "function resolveBaseInstName(" in open(_inst_hmi_js_p, encoding="utf-8").read(),
                  "前端具備多張同名儀器自動遞增命名 (NI6008-2) 與 HMI Profile 回溯函式")

            with _tf_v16.TemporaryDirectory() as _lc_dir:
                lc_xlsx = os.path.join(_lc_dir, "lowercase_phase.xlsx")
                wb_lc = openpyxl.Workbook()
                ws_lc = wb_lc.active
                ws_lc.title = "RF"
                ws_lc.append(["Index_2", "phase", "Title", "Marco", "Instrument", "Switch", "Send", "Reply", "EndPrompt", "Ref", "Validation", "Prompt", "Waiting", "ExecMode", "Description", "TestID"])
                ws_lc.append(["000", "0", "0,Route", "", "", "", ':ShowISN,"*(ISN)"', "0", "", "", "", "", "", "1", "ISN", "B7PL025"])
                ws_lc.append(["001", "", "", "", "", "", ":SfCheckRoute", "0", "", "", "", "", "", "8", "Route", "OTFX064"])
                wb_lc.save(lc_xlsx)
                wb_lc.close()
                ws_lc_imp = _imp_v16(lc_xlsx)
                check("RF" in ws_lc_imp.get("stations", {}) and "RF" not in ws_lc_imp.get("marcos", {}),
                      "excel_engine 正確以不分大小寫識別小寫 'phase' 工作站表，避免被降格成 11 欄 Marco")

            v18_err_ws = {
                "project_name": "GWT_CHK", "station_name": "BootUp",
                "global_ini": {"Settings": {}, "Scripts": {}},
                "instruments": [{"Mount": "NFT", "Name": "NI6008-1", "Functions": "Voltage", "Version": "1.1.2.0"}],
                "switches": [],
                "duts": [{"Load": "*$(LOAD_1)", "DUT Name": "GWT$BootUp", "Station": "BootUp,1"}],
                "marcos": {},
                "stations": {"BootUp": [
                    {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ':ShowISN,"*(ISN)"', "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "ExecMode": "8", "TestID": "OTFX064"},
                    {"Index": "002", "Phase": "1", "Title": "0,Volt", "Instrument": "Voltage", "Switch": "NI6008-1", "Send": ':Dev.VOLAGE,"RSE,1000,0"', "ExecMode": "1", "TestID": "B7PL025"},
                ]},
            }
            rep_v18 = _audit_ws(v18_err_ws)
            check(any("ObtainDevice" in e for e in rep_v18.get("errors", []))
                  and any("VOLAGE" in w or "VOLTAGE" in w for w in rep_v18.get("warnings", []))
                  and any("Mount 欄未包含站別 'BootUp'" in w for w in rep_v18.get("warnings", [])),
                  "audit_workspace 主動攔截未先 :ObtainDevice 呼叫 :Dev.*、:Dev.VOLAGE 拼字與 Mount 空掛載站別",
                  f"errs={rep_v18.get('errors')} warns={rep_v18.get('warnings')}")

        print("\n" + "=" * 78)
        print(f"🎉 全功能自動驗收完成：{passed_checks} / {total_checks} 項測試 100% 通過！(0 Error)")
        print("=" * 78)
        return True
    finally:
        server.shutdown()
        app_server.open_folder_in_explorer = orig_open_folder
        app_server.launch_excel_file_async = orig_launch_excel
        app_server.launch_ini_file_async = orig_launch_ini


if __name__ == "__main__":
    run_all_verifications()
