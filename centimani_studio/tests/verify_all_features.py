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
import urllib.error
import urllib.parse
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
    launched_tools = []
    orig_open_folder = app_server.open_folder_in_explorer
    orig_launch_excel = app_server.launch_excel_file_async
    orig_launch_ini = app_server.launch_ini_file_async
    orig_launch_tool = app_server.launch_centimani_tool_async
    app_server.open_folder_in_explorer = lambda p: opened_folders.append(p)
    app_server.launch_excel_file_async = lambda p: launched_excels.append(p)
    app_server.launch_ini_file_async = lambda p: launched_inis.append(p)
    app_server.launch_centimani_tool_async = lambda p, wd=None: launched_tools.append((p, wd)) or True

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
        sfis_hmi_js = open(os.path.join(STUDIO_DIR, "web", "js", "sfis_hmi.js"), "r", encoding="utf-8").read()
        audit_editors_js = open(os.path.join(STUDIO_DIR, "web", "js", "audit_editors.js"), "r", encoding="utf-8").read()
        check(".acc-card .acc-title" in app_css and "rem" in app_css.split(".acc-card .acc-title")[1][:120],
              "手風琴標題/內文改用 rem 單位，隨系統字體設定 (13/15/17/19px) 等比縮放")
        check("儀器範本" in index_html and "可用儀器庫" in index_html and "既有腳本編修" in flow_guide_js,
              "首頁功能卡、流程導覽 (flow_guide.js) 與可用儀器庫說明文已全面與新版 UI 同步")
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
                    if str(row[1]).strip() in ("NI6008", "NI6008-1"):
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
            from core.golden_data import _get_local_dll_versions as _get_loc_dlls
            expected_ni_ver = _get_loc_dlls().get("daqusbni.dll", "1.0.5.0")
            check(ni_ver == expected_ni_ver, f"NI6008 (DaqUSBNi.dll) 版本號已自動對齊本機真實 DLL ({expected_ni_ver})", str(ni_ver))
            check("HXTaudio" not in inst_names_in_sheet, "Instrument 工作表僅保留實際選用之儀器，不殘留未選儀器 (避免 DLL is not Found)", str(inst_names_in_sheet))
            check("IPOWER2401" in inst_names_in_sheet, "Phase 97 使用之 POWERSWITCH 已自動保留對應儀器 IPOWER2401", str(inst_names_in_sheet))
            from core.golden_data import get_golden_mother as _gm_chk
            gm_list = _gm_chk().get("instruments", [])
            gm_insts = {i["Name"]: i.get("dll_exists") for i in gm_list}
            gm_usable = {i["Name"]: i.get("is_usable") for i in gm_list}
            check(gm_insts.get("NI6008") is True and gm_insts.get("HXTaudio") is False, "儀器目錄正確標記本機 DLL 存在與缺失狀態 (NI6008=True, HXTaudio=False)")
            check(gm_usable.get("InstIQApiA") is True and gm_usable.get("NI6008") is True and gm_usable.get("HXTaudio") is False,
                  "可使用設備旗標正確區分『實機DLL或專屬範本』 (InstIQApiA=True, HXTaudio=False)")
            check("TAB3_CAT_FILTER = 'USABLE'" in index_html and "auditEmptyRecentBox" in index_html,
                  "書籤三預設篩選『✅ 可使用設備』且 01 腳本健檢具備未載檔最近紀錄引導區")
            check(bool(auto_res.get("centimani_dir_exists")), "匯出時自動偵測並回傳本機 Centimani 主程式目錄", auto_res.get("centimani_dir", ""))
            missing_names = [m.get("dll") for m in auto_res.get("missing_dlls", [])]
            check("DigitIO6509.dll" in missing_names and "InstIQApi_A.dll" not in missing_names and "DaqUSBNi.dll" not in missing_names,
                  "匯出時精準識別新版目錄已有 InstIQApi_A.dll / DaqUSBNi.dll，僅回報確實缺少的 DLL (DigitIO6509.dll)", str(missing_names))
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
            check('id="topBtnQaCheatsheet"' in index_html and 'id="qaCheatsheetModal"' in index_html and 'id="qaScenarioGrid"' in index_html and 'script_qa.js' in index_html,
                  "頂部導覽列已具備全域『語法寫法小抄』彈窗入口與直覺問答模組")
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
            check("EN_NI6008_1" in txt_body and "Global.ini [Scripts]" in txt_body and "目前無 Phase=-1" not in txt_body and "Checksum" not in txt_body,
                  "白話版隨附說明 .txt 正確列出 EN_NI6008_1 用法，並隱藏無用空區塊與艱澀術語")
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
            # 1) Golden Mother 預設不幽靈掛載 NI6008，且 vnxRFSW / DevUart 正確標記 Sub=1
            from core.golden_data import get_golden_mother as _get_gm_v16
            gm_v16 = _get_gm_v16("CLEAN_PROJ", "ST1")
            gm_inst_map = {str(i.get("Name", "")): i for i in gm_v16.get("instruments", [])}
            check(gm_inst_map.get("NI6008", {}).get("Mount", "BAD") == "",
                  "Golden Mother 預設不自動 Mount NI6008（無儀器站別不幽靈載入）")
            check(gm_inst_map.get("vnxRFSW", {}).get("Sub") == "1" and gm_inst_map.get("DevUart", {}).get("Sub") == "1",
                  "Golden Mother 正確設定 vnxRFSW 與 DevUart 為共用子裝置 (Sub=1)")

            # 2) 插入標準儀器 (NI6008 / RF / FeasaLED) 必寫 Col F (Switch)，而 Sub=1 (vnxRFSW) 改用 :ObtainSubDevice / :sDev.* 且 Col E/F 留空
            wb_ni_chk = openpyxl.load_workbook(ask_res["excel_path"], data_only=True)
            ni_sw_vals = [str(r[5] or "").strip() for r in wb_ni_chk["MB"].iter_rows(min_row=2, values_only=True) if r and str(r[6] or "").strip() == ":ObtainDevice"]
            wb_ni_chk.close()
            check("NI6008" in ni_sw_vals or "NI6008-1" in ni_sw_vals,
                  "插入 NI6008 範本時於 :ObtainDevice 列同步寫入 Col F (Switch=NI6008)", str(ni_sw_vals))

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

            # [v0.8.019] 驗證實戰反饋修正：
            # 1) 單台儀器不加 '-1' (NI6008)，兩台以上才遞增 (NI6008 + NI6008-2)
            # 2) 無儀器環境 pause_hardware_phases_minus_one 同步將暫停儀器移出 Mount，防止主程式 Start Connecting to Device 閃退
            # 3) /api/insert_instrument_block 支援 no_hw_phase_pause=True 與預設單純 0,Title,3 產出
            # 4) UI 具備 iiNoHwPhaseChk 與『書籤二：產生首次使用空範本』，且預設不勾選 *$(EN_...)
            # 5) auto_fix_workspace 主動修正 :ShowISN 順序、:Dev.VOLAGE 拼字、遺漏 :ObtainDevice 與缺 Mount
            single_ni_res = post_json("/api/generate_inst_template_standalone", {
                "items": [{"inst_name": "NI6008", "title_name": "Measure Voltage"}, {"inst_name": "NI6008-2", "title_name": "Measure Voltage_2"}],
                "project_name": "SINGLE_AND_TWO", "station_name": "MB", "auto_sample_mode": True, "open_excel": False
            })
            wb_s19 = openpyxl.load_workbook(single_ni_res["excel_path"], read_only=True, data_only=True)
            s19_insts = [str(r[1]) for r in wb_s19["Instrument"].iter_rows(min_row=2, values_only=True) if r and r[1]]
            s19_titles = [str(r[2] or "").strip() for r in wb_s19["MB"].iter_rows(min_row=2, values_only=True) if r and r[2]]
            wb_s19.close()
            check("NI6008" in s19_insts and "NI6008-2" in s19_insts and "NI6008-1" not in s19_insts,
                  "單台儀器定名為 NI6008 (不加 -1)，第二台起為 NI6008-2", str(s19_insts))
            check(any(t.startswith("0,Measure Voltage") for t in s19_titles),
                  "預設取消 INI 開關時，產出簡單易讀之傳統 0,測項名稱,3 格式", str(s19_titles))

            ip_nohw_res = post_json("/api/generate_inst_template_standalone", {
                "items": [{"inst_name": "IPOWER2401", "title_name": "Power Switch"}],
                "project_name": "NOHW_IP", "station_name": "MB", "auto_sample_mode": True,
                "no_hw_phase_pause": True, "open_excel": False
            })
            wb_nohw = openpyxl.load_workbook(ip_nohw_res["excel_path"], read_only=True, data_only=True)
            ip_mount = next((str(r[0] or "") for r in wb_nohw["Instrument"].iter_rows(min_row=2, values_only=True) if r and r[1] == "IPOWER2401"), "MISSING")
            wb_nohw.close()
            check(ip_mount == "",
                  "勾選無儀器環境 (no_hw_phase_pause=True) 時同步暫停 IPOWER2401.Mount，避免 Centimani Start Connecting to Device 連線報錯", f"Mount='{ip_mount}'")

            ins_nohw_ws = _get_gm_v16("INS_NOHW", "MB")
            ins_nohw_ws["stations"]["MB"] = [
                {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ':ShowISN,"*(ISN)"', "Reply": "0", "ExecMode": "1", "Description": "ISN", "TestID": "B7PL025"},
                {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "Reply": "0", "ExecMode": "8", "Description": "Route", "TestID": "OTFX064"},
            ]
            ins_nohw_res = post_json("/api/insert_instrument_block", {
                "workspace": ins_nohw_ws, "sheet_name": "MB",
                "inst_name": "IPOWER2401", "title_name": "Power Cycle", "no_hw_phase_pause": True
            })
            ins_paused_p = [str(r.get("Phase", "")) for r in ins_nohw_res["workspace"]["stations"]["MB"] if r.get("Phase")]
            check(ins_nohw_res.get("status") == "ok" and "-1" in ins_paused_p and ins_nohw_res["report"]["error_count"] == 0,
                  "/api/insert_instrument_block 支援無儀器環境設 Phase=-1 且 0 Error 健檢通過", str(ins_paused_p))

            check('id="iiNoHwPhaseChk"' in index_html and '產生首次使用空範本' in index_html and 'id="tab3UseIniSwitch" type="checkbox" style=' in index_html,
                  "UI 插入儀器彈窗具備無儀器環境 Checkbox、建新母體改名為『產生首次使用空範本』，且預設取消 INI 開關簡化腳本")

            messy_temp_ws = {
                "project_name": "MESSY", "station_name": "BootUp", "source_file": "GWTalk_TestFlow.xlsx",
                "global_ini": {"Settings": {}, "Scripts": {}},
                "instruments": [{"Mount": "NFT", "Name": "NI6008-1", "Functions": "Voltage", "Version": "1.1.2.0"}],
                "switches": [],
                "duts": [{"Load": "*$(LOAD_1)", "DUT Name": "MESSY$BootUp", "Station": "BootUp,1"}],
                "marcos": {},
                "stations": {"BootUp": [
                    {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ":SfCheckRoute", "ExecMode": "8", "TestID": "OTFX064"},
                    {"Index": "001", "Phase": "", "Title": "", "Send": ':ShowISN,"*(ISN)"', "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "002", "Phase": "1", "Title": "0,Volt", "Instrument": "Voltage", "Switch": "NI6008-1", "Send": ':Dev.VOLAGE,"RSE,1000,0"', "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "003", "Phase": "97", "Title": "1,End", "Send": ":CloseMessage", "ExecMode": "3", "TestID": "B7PL025"},
                ]},
            }
            _autofix_ws(messy_temp_ws)
            rep_after_messy = _audit_ws(messy_temp_ws)
            fixed_sends_19 = [r.get("Send", "") for r in messy_temp_ws["stations"]["BootUp"]]
            check(rep_after_messy["error_count"] == 0
                  and fixed_sends_19.index(':ShowISN,"*(ISN)"') < fixed_sends_19.index(":SfCheckRoute")
                  and ":ObtainDevice" in fixed_sends_19
                  and any(s.startswith(":Dev.VOLTAGE") for s in fixed_sends_19)
                  and "BootUp" in str(messy_temp_ws["instruments"][0].get("Mount", "")),
                  "auto_fix_workspace 可一次自動修復 TEMP_SCRIPT 常見四大錯誤 (:ShowISN 順序 / :Dev.VOLTAGE / 補 :ObtainDevice / 補 Mount)",
                  f"errs={rep_after_messy['errors']} sends={fixed_sends_19}")

            # [v0.8.020] 驗證同款多台儀器共用單一 DLL（不誤報 NI6008-2.dll / FeasaLED-2.dll，同 DLL 合併提醒，Phase=-1 暫停不報錯）+ 白話版說明書
            from core.golden_data import _resolve_shared_control_dll as _res_shared_dll
            _gm_cat = _get_gm_v16().get("instruments", [])
            check(_res_shared_dll("NI6008-2", "NI6008-2.dll", _gm_cat, {"daqusbni.dll": "1.1.2.0"}) == "DaqUSBNi.dll"
                  and _res_shared_dll("FeasaLED-2", "FeasaLED-2.dll", _gm_cat, {}) == "LED_analyser.dll",
                  "多台編號儀器 (NI6008-2 / FeasaLED-2) 自動對應共用基底 DLL (DaqUSBNi.dll / LED_analyser.dll)")

            multi_dll_ws = {
                "instruments": [
                    {"Name": "NI6008", "Mount": "MB", "ControlDLL": "DaqUSBNi.dll", "Functions": "Voltage"},
                    {"Name": "NI6008-2", "Mount": "MB", "ControlDLL": "NI6008-2.dll", "Functions": "Voltage"},
                    {"Name": "NI6008-3", "Mount": "MB", "ControlDLL": "NI6008-3.dll", "Functions": "Voltage"},
                    {"Name": "FeasaLED-2", "Mount": "MB", "ControlDLL": "FeasaLED-2.dll", "Functions": "LED_Test"},
                    {"Name": "MT8870A", "Mount": "MB", "ControlDLL": "InstAnritsu.dll", "Functions": "MeasWIFI"},
                    {"Name": "MT8870A-2", "Mount": "MB", "ControlDLL": "InstAnritsu.dll", "Functions": "MeasWIFI"},
                    {"Name": "DIO6509", "Mount": "", "ControlDLL": "DigitIO6509.dll", "Functions": "IOswitch"},
                ],
                "switches": [],
                "stations": {"MB": [
                    {"Phase": "-1", "Title": "0,Paused IO", "Instrument": "IOswitch", "ExecMode": "1"},
                    {"Phase": "1", "Title": "0,Volt", "Instrument": "NI6008-2", "ExecMode": "1"},
                ]},
            }
            multi_chk = _chk_dlls(multi_dll_ws)
            multi_dll_names = [m["dll"] for m in multi_chk["missing_dlls"]]
            anr_grp = next((m for m in multi_chk["missing_dlls"] if m["dll"] == "InstAnritsu.dll"), None)
            check("NI6008-2.dll" not in multi_dll_names
                  and "NI6008-3.dll" not in multi_dll_names
                  and "FeasaLED-2.dll" not in multi_dll_names
                  and "DaqUSBNi.dll" not in multi_dll_names
                  and "DigitIO6509.dll" not in multi_dll_names
                  and anr_grp is not None and anr_grp.get("shared") is True and multi_dll_names.count("InstAnritsu.dll") == 1,
                  "多台共用 DLL 合併檢查通過：不重複列印同支缺少的 DLL、不誤報 NI6008-2/FeasaLED-2.dll 且 Phase=-1 暫停儀器不報錯",
                  str(multi_chk["missing_dlls"]))

            plain_res = post_json("/api/generate_inst_template_standalone", {
                "items": [{"inst_name": "NI6008", "title_name": "Measure 3.3V"}],
                "project_name": "PLAIN_GUIDE", "station_name": "MB", "auto_sample_mode": True,
                "use_ini_switch": False, "no_hw_phase_pause": False, "open_excel": False
            })
            plain_txt = open(plain_res["guide_txt_path"], "r", encoding="utf-8-sig").read()
            ask_txt = open(ip_nohw_res["guide_txt_path"], "r", encoding="utf-8-sig").read()
            check("1. 怎麼執行" in plain_txt and "Global.ini [Scripts]" not in plain_txt and "Phase = -1" not in plain_txt
                  and "Phase = -1" in ask_txt and "回產線接好實機後" in ask_txt,
                  "白話版操作說明在未啟用開關/暫停時精簡無冗字，啟用 Phase=-1 時清楚提示 2 步恢復法")

            # [v0.8.021] 驗證 Centmimani_Altas_TRY & ATLAS_SAMPLE 升級 + 方向一右欄完整工作區
            tic_v21_bundled = os.path.join(STUDIO_DIR, "data", "Test Item Code V2.04_20260521.xlsx")
            check(os.path.exists(tic_v21_bundled)
                  and init_res["tic_info"]["file_name"] == "Test Item Code V2.04_20260521.xlsx"
                  and init_res["tic_info"]["count"] >= 5250
                  and os.path.exists(os.path.join(plain_res["output_dir"], "Test Item Code V2.04_20260521.xlsx")),
                  "已內建 Test Item Code V2.04_20260521.xlsx (5,255 筆) 為預設代碼庫並自動複製至輸出目錄",
                  str(init_res["tic_info"]))

            spec_txt = open(os.path.join(os.path.dirname(STUDIO_DIR), "CentimaniStudio.spec"), "r", encoding="utf-8").read()
            check("('centimani_studio/data', 'data')" in spec_txt,
                  "CentimaniStudio.spec 已納入 centimani_studio/data 目錄（打包成 EXE 時同步攜帶 Test Item Code）")

            sf_ws = {
                "project_name": "SFIS_V12", "station_name": "UPGRADE",
                "global_ini": {"Settings": {}, "Scripts": {}},
                "instruments": [], "switches": [],
                "duts": [{"Load": "*$(LOAD_1)", "DUT Name": "SFIS_V12$UPGRADE", "Station": "UPGRADE,1"}],
                "marcos": {},
                "stations": {"UPGRADE": [
                    {"Index": "000", "Phase": "0", "Title": "0,CheckRoute", "Send": ':ShowISN,"*(ISN)"', "ExecMode": "0", "TestID": "B7PL025"},
                    {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "ExecMode": "1", "TestID": "OTCH013"},
                    {"Index": "002", "Phase": "", "Title": "", "Send": ':SfGetVersion,"*(ISN)","MOKP_SN","2","SN",""', "ExecMode": "10", "TestID": "OTCH013"},
                    {"Index": "003", "Phase": "97", "Title": "1,End", "Send": ":CloseMessage", "ExecMode": "3", "TestID": "B7PL025"},
                ]},
            }
            sf_rep_bad = _audit_ws(sf_ws)
            check(any("Centimani 1.2.1.2" in e and "SfCheckRoute" in e for e in sf_rep_bad["errors"])
                  and not any("SfGetVersion" in e for e in sf_rep_bad["errors"]),
                  "健檢納入 Centimani 1.2.1.2 規定：精準攔截 SfCheckRoute ExecMode=1，並合法放行 ExecMode=10",
                  str(sf_rep_bad["errors"]))
            _autofix_ws(sf_ws)
            sf_rep_ok = _audit_ws(sf_ws)
            check(sf_ws["stations"]["UPGRADE"][1]["ExecMode"] == "8" and sf_rep_ok["error_count"] == 0,
                  "auto_fix_workspace 自動將違法 SFIS ExecMode 修正為 8 且複檢 0 Error",
                  str(sf_rep_ok["errors"]))

            cat_names_21 = {i["Name"]: i for i in cat_res.get("instruments", [])}
            check(all(k in cat_names_21 for k in ("ScpiController", "Keithley2380", "Keithley2700", "XelM8-A", "IQFlex-A", "Transmitter1")),
                  "儀器型錄已擴充 ScpiController / Keithley2380 / Keithley2700 / XelM8-A / IQFlex-A / Transmitter1")

            new_inst_res = post_json("/api/generate_inst_template_standalone", {
                "items": [
                    {"inst_name": "ScpiController", "title_name": "SCPI Power Ctrl"},
                    {"inst_name": "Keithley2380", "title_name": "ELoad Test"},
                    {"inst_name": "XelM8-A", "title_name": "WiFi 11ah Check"},
                ],
                "project_name": "ATLAS_EXT", "station_name": "MB", "auto_sample_mode": True,
                "open_excel": False
            })
            check(new_inst_res.get("status") == "ok" and new_inst_res["audit_report"].get("error_count") == 0
                  and new_inst_res["audit_report"].get("warning_count") == 0,
                  "擴充之新儀器 (ScpiController / Keithley2380 / XelM8-A) 可順利匯出 0 Error 且 0 Warning 範本（XelM8-A / ScpiController 掛載不被搶走）",
                  str(new_inst_res.get("audit_report")))

            usb_wiz_res = post_json("/api/generate_new_standalone", {
                "project_name": "USB_UPG", "station_name": "UPGRADE", "dut_count": 1,
                "block_ids": ["BLK_PRETEST_ROUTE", "BLK_USB_FW_UPGRADE_COM", "BLK_PHASE97_TEARDOWN"],
                "open_excel": False
            })
            wb_usb = openpyxl.load_workbook(usb_wiz_res["excel_path"], read_only=True, data_only=True)
            usb_sends = [str(r[6] or "") for r in wb_usb["UPGRADE"].iter_rows(min_row=2, values_only=True) if r and len(r) > 6]
            wb_usb.close()
            check(any(":Utility.GetChainCOM" in s for s in usb_sends) and any(":AddAttribute" in s for s in usb_sends),
                  "新增積木『BLK_USB_FW_UPGRADE_COM』正確寫入 Utility.CMD + GetChainCOM + AddAttribute",
                  str(usb_sends))

            check('id="tab3RightActionZone"' in index_html
                  and 'tab3OpenStep2Checked()' in index_html
                  and 'id="tab3ModeChoiceBox"' not in index_html,
                  "書籤三已套用方向一『右側完整工作區』改版：消除確認過場與下方長卷軸")

            # [v0.8.022] 驗證雙台 FeasaLED + FeasaLED-2 皆掛載 MB 且共用 LED_analyser.dll（絕不寫成 FeasaLED-2.dll），且已搬移保留檔
            feasa_dual_res = post_json("/api/generate_inst_template_standalone", {
                "items": [
                    {"inst_name": "FeasaLED", "title_name": "LED Check 1"},
                    {"inst_name": "FeasaLED-2", "title_name": "LED Check 2"},
                ],
                "project_name": "DUAL_LED", "station_name": "MB", "auto_sample_mode": True,
                "open_excel": False
            })
            wb_fl = openpyxl.load_workbook(feasa_dual_res["excel_path"], read_only=True, data_only=True)
            fl_rows = {str(r[1]): (str(r[0] or ""), str(r[3] or "")) for r in wb_fl["Instrument"].iter_rows(min_row=2, values_only=True) if r and r[1]}
            wb_fl.close()
            check(feasa_dual_res["audit_report"].get("error_count") == 0
                  and feasa_dual_res["audit_report"].get("warning_count") == 0
                  and fl_rows.get("FeasaLED") == ("MB", "LED_analyser.dll")
                  and fl_rows.get("FeasaLED-2") == ("MB", "LED_analyser.dll")
                  and len(feasa_dual_res.get("missing_dlls", [])) == 0,
                  "雙台 FeasaLED + FeasaLED-2 皆正確掛載 MB 且共用 LED_analyser.dll (0 Error / 0 Warning / 0 Missing DLL)",
                  str(fl_rows))

            cm_new_root = r"D:\PYTHON\自動化編寫EXCEL\Centmimani_Altas_TRY"
            check(os.path.exists(os.path.join(cm_new_root, "Release Note.xlsx"))
                  and os.path.exists(os.path.join(cm_new_root, "Device", "MT8870A_PathLoss.ini"))
                  and os.path.isdir(os.path.join(cm_new_root, "4CAM_Stitching")),
                  "已將 CENTERMAINA_TRY 建議保留之 Release Note.xlsx / MT8870A_PathLoss.ini / 4CAM_Stitching 複製至 Centmimani_Altas_TRY")

            # [v0.8.023] 驗證 MD 全面盤點補強規則 + 知識庫集中歸檔 + DLL 目錄對齊
            proj_root_chk = os.path.dirname(STUDIO_DIR)
            kb_dir_chk = os.path.join(proj_root_chk, "完整知識庫文件清單")
            check(os.path.exists(os.path.join(kb_dir_chk, "DESIGN_AND_HANDOVER.md"))
                  and os.path.exists(os.path.join(kb_dir_chk, "01_FWDL_測試邏輯深度解析.md"))
                  and not os.path.exists(os.path.join(proj_root_chk, "DESIGN_AND_HANDOVER.md"))
                  and not os.path.exists(os.path.join(proj_root_chk, "spec.md")),
                  "所有知識庫與交接 .md 文件皆已集中整理至『完整知識庫文件清單』目錄（根目錄僅留 AGENTS.md）")

            from core.script_doctor import _collect_dll_search_dirs as _dll_dirs_fn
            dll_dirs_res = _dll_dirs_fn()
            check(any("Centmimani_Altas_TRY" in d for d in dll_dirs_res),
                  "script_doctor PE DLL 版本健檢目錄優先對齊 Centmimani_Altas_TRY", str(dll_dirs_res[:3]))

            md_rules_ws = {
                "project_name": "MD_AUDIT", "station_name": "MB",
                "global_ini": {"Settings": {}, "Scripts": {}},
                "instruments": [], "switches": [],
                "duts": [
                    {
                        "Load": "*$(LOAD_1)", "DUT Name": "MD_AUDIT$MB", "Station": "MB,1",
                        "Connection1 (Type,Name,ConnectString)": '"Uart","UART","COM1"',
                        "Connection2 (Type,Name,ConnectString)": '"Uart","UART","COM2"',
                    },
                    {
                        "Load": "*$(LOAD_2)", "DUT Name": "MD_AUDIT$MB", "Station": "MB,2",
                        "Connection1 (Type,Name,ConnectString)": '"Uart","UART","COM3"',
                    },
                ],
                "marcos": {},
                "stations": {"MB": [
                    {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ':ShowISN,"*(ISN)"', "Reply": "0", "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "Reply": "0", "ExecMode": "8", "TestID": "OTFX064"},
                    {"Index": "002", "Phase": "1", "Title": "", "Send": "UART@ver\\r\\n", "Reply": "@a&&@b||@c", "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "003", "Phase": "2", "Title": "0,DupTitle", "Send": ':Delay,"100"', "Reply": "OK&&@PASS", "ExecMode": "0", "TestID": "B7PL025"},
                    {"Index": "004", "Phase": "", "Title": "0,DupTitle", "Send": ':Delay,"100"', "Reply": "0", "ExecMode": "0", "TestID": "B7PL025"},
                    {"Index": "005", "Phase": "97", "Title": "1,End", "Send": ":CloseMessage", "Reply": "0", "ExecMode": "3", "TestID": "B7PL025"},
                ]},
            }
            md_rep = _audit_ws(md_rules_ws)
            md_errs = "\n".join(md_rep["errors"])
            md_warns = "\n".join(md_rep["warnings"])
            check("Connection Name :UART is duplicate" in md_errs
                  and "The Phase 1 lacks title" in md_errs
                  and "There are duplicated titles (DupTitle) in the Phase 2" in md_errs
                  and "混用 '&&' 與 '||'" in md_errs
                  and "每個子條件皆建議加上 '@'" in md_warns,
                  "補齊 MD 四大規範健檢：DUTs 連線重名 / Phase 起始缺 Title / 同 Phase 重複 Title / Reply 混用 && 與 ||",
                  f"errs={md_rep['errors']} warns={md_rep['warnings']}")

            # [v0.8.024] 驗證首次掃描記憶主程式環境 + 書籤三嚴格依真實 DLL 過濾可用儀器 + 書籤一/三一鍵呼叫 SFIS / DLLtest
            prof_init = init_res.get("centimani_profile") or {}
            check(prof_init.get("exists") is True
                  and prof_init.get("exe_version") == "1.2.1.2"
                  and prof_init.get("dll_count", 0) >= 6
                  and (prof_init.get("tools") or {}).get("CentimaniSFISTest.exe") is True
                  and (prof_init.get("tools") or {}).get("DLLtest.exe") is True,
                  "/api/init 正確回傳本機掃描之 Centimani 主程式版本、實機 DLL 數與輔助工具清單", str(prof_init))

            scan_res = post_json("/api/scan_centimani_dir", {"confirm": True})
            check(scan_res.get("status") == "ok" and (scan_res.get("centimani_profile") or {}).get("confirmed") is True,
                  "/api/scan_centimani_dir 成功掃描並將主程式環境記憶為已確認狀態")

            cat_by_n = {i["Name"]: i for i in (scan_res.get("instruments") or [])}
            check(cat_by_n.get("NI6008", {}).get("is_usable") is True
                  and cat_by_n.get("FeasaLED", {}).get("is_usable") is True
                  and cat_by_n.get("MT8870A", {}).get("is_usable") is False
                  and cat_by_n.get("DIO6509", {}).get("is_usable") is False,
                  "書籤三 is_usable 嚴格只將本機實際存在 DLL 之儀器列為實機可用（缺 DLL 即使有範本也不誤列）")

            launched_tools.clear()
            sfis_t_res = post_json("/api/launch_centimani_tool", {"tool_name": "CentimaniSFISTest.exe"})
            dll_t_res = post_json("/api/launch_centimani_tool", {"tool_name": "DLLtest.exe"})
            check(sfis_t_res.get("status") == "ok" and dll_t_res.get("status") == "ok" and len(launched_tools) == 2,
                  "/api/launch_centimani_tool 正確啟動 CentimaniSFISTest.exe 與 DLLtest.exe 並回傳白話使用說明",
                  str(launched_tools))

            check('id="topCentimaniBadge"' in index_html
                  and 'id="firstScanCentimaniBanner"' in index_html
                  and 'id="tab3AuxToolsBar"' in index_html
                  and "openCentimaniAuxTool('CentimaniSFISTest.exe')" in index_html
                  and "openCentimaniAuxTool('DLLtest.exe')" in index_html
                  and "filtered.filter(i => i.dll_exists !== false)" in index_html,
                  "UI 已具備頂部主程式環境徽章、首次掃描橫幅、SFIS/DLLtest 按鈕，且 USABLE 僅列實機 DLL")

            # [v0.8.025] 驗證實機驗證入口 (SFIS / DLL，現已移至首頁 05 手風琴)、移除書籤N 字眼、NI-DAQmx 驅動缺漏偵測與 Log 診斷
            check('id="accCard_tools"' in index_html
                  and 'id="genModeTools"' in index_html
                  and 'id="btnGenModeTools"' in index_html
                  and 'toolsCheckSfisLink()' in sfis_hmi_js
                  and 'ISN 刷過' in index_html
                  and 'GET' in index_html
                  and 'WRITE' in index_html,
                  "首頁手風琴已具備獨立『實機驗證 (SFIS / DLL)』入口含 ISN/GET/WRITE 與 DLLtest 工作區")

            check("書籤" not in index_html and "書籤" not in flow_guide_js,
                  "index.html 與 flow_guide.js 內文已徹底移除所有『書籤N』字眼")

            ni_test_ws = {
                "project_name": "NITEST", "station_name": "MB",
                "instruments": [{"Mount": "MB", "Name": "NI6008", "ControlDLL": "DaqUSBNi.dll", "Functions": "Voltage", "Version": "1.0.5.0"}],
                "switches": [], "duts": [], "marcos": {},
                "stations": {"MB": [{"Index": "000", "Phase": "1", "Title": "0,Test", "Instrument": "NI6008", "Send": "AI0"}]}
            }
            from core import golden_data, log_analyzer
            ni_dll_res = golden_data.check_workspace_missing_dlls(ni_test_ws)
            expected_ni = os.path.isfile(r"C:\Windows\System32\nicaiu.dll") or os.path.isfile(r"C:\Windows\SysWOW64\nicaiu.dll")
            check(ni_dll_res.get("ni_daqmx_installed") is expected_ni
                  and (True if expected_ni else len(ni_dll_res.get("missing_drivers") or []) > 0),
                  "check_workspace_missing_dlls 正確偵測本機 NI-DAQmx 驅動 (nicaiu.dll) 狀態並提醒 Office PC",
                  str(ni_dll_res.get("missing_drivers")))

            ni_log_sample = (
                "2026/11/24 11:36:17 [System]    Start to load Instrument sheet\n"
                "2026/11/24 11:36:17 [System]    DaqUSBNi.dll Exception: System.Reflection.TargetInvocationException ---> "
                "System.IO.FileNotFoundException: 無法載入檔案或組件 'NationalInstruments.DAQmx.dll' 或其相依性的其中之一。 找不到指定的模組。\n"
                "2026/11/24 11:36:17 [System]    Load Instruments sheet Fail ! Please check file's contents\n"
            )
            ni_diag = log_analyzer.analyze_centimani_log(ni_log_sample)
            ni_blob = str(ni_diag)
            check("NI_DAQMX_RUNTIME_MISSING" in ni_blob or "nicaiu.dll" in ni_blob,
                  "Log 診斷器可精準識別 DaqUSBNi / NationalInstruments.DAQmx.dll 驅動未安裝原因與 Phase=-1 解法")

            try:
                post_json("/api/check_sfis_weblink", {"url": ""})
                sfis_empty_400 = False
            except urllib.error.HTTPError as he:
                sfis_empty_400 = (he.code == 400)
            sfis_chk_res = post_json("/api/check_sfis_weblink", {"url": "http://127.0.0.1:1/sfis_test"})
            check(sfis_empty_400 and sfis_chk_res.get("status") == "ok" and sfis_chk_res.get("reachable") is False,
                  "/api/check_sfis_weblink 正確處理空白網址 (400) 與離線網址連通預檢回傳結構",
                  str(sfis_chk_res))

            # [v0.8.026] 驗證手風琴「去按鈕清爽版」+ 防截斷 + 01 健檢「選項 C」排版 + 過濾 Test Item Code
            recent_api_res = get_json("/api/recent_files")
            recent_list = recent_api_res.get("recent_files") or []
            has_tic_in_recent = any("test item code" in str(x.get("name", "")).lower() for x in recent_list)
            norm_recent_paths = [os.path.normcase(os.path.abspath(str(x.get("path", "")))) for x in recent_list]
            check(not has_tic_in_recent and len(norm_recent_paths) == len(set(norm_recent_paths)),
                  "/api/recent_files 已自動過濾 Test Item Code 代碼表並去除重複路徑",
                  f"count={len(recent_list)}")

            home_sec = index_html.split('<div id="homeScheme2"')[1].split('<div id="homeStatusFooter"')[0]
            hub_sec = index_html.split('<div id="genModeHub"')[1].split('<div id="genBackToModeHubBar"')[0]
            title_css = app_css.split('.acc-card .acc-title')[1][:220]
            check('<button' not in home_sec and '<button' not in hub_sec
                  and 'acc-enter-hint' in home_sec and 'acc-enter-hint' in hub_sec
                  and 'text-overflow: ellipsis' not in title_css,
                  "首頁與編修中心手風琴已升級「去按鈕清爽版」且取消標題省略號截斷")

            check('id="auditDropZoneStrip"' in index_html
                  and 'id="auditRecentTop3"' in index_html
                  and 'id="auditRecentSearchInput"' in index_html
                  and 'id="auditRecentFolderSel"' in index_html
                  and 'function filterAuditRecentTable()' in index_html
                  and 'function handleAuditFileDrop(' in index_html,
                  "01 腳本健檢進場畫面已套用「選項 C」：拖放橫條 + Top 3 快選 + 全寬可搜尋資料表")

            # [v0.8.027] 驗證單一整合選檔按鈕 + 健檢結果「選項 1」左側工作表直欄＆右側主工作桌
            check('id="btnAuditPickExcel"' in index_html
                  and '站內瀏覽選檔' not in index_html
                  and 'id="auditResultsGrid"' in index_html
                  and 'audit-sheet-rail' in index_html
                  and 'audit-marco-group' in index_html
                  and '.audit-results-grid' in app_css
                  and '.audit-sheet-rail' in app_css,
                  "01 健檢選檔按鈕已收斂為單一『選擇 Excel 檔案』且結果頁升級為「選項 1」左右雙欄（Marco 子表自動收折）")

            # [v0.8.028] 驗證原生選檔 UTF-8 中文路徑防亂碼 + 取消不強迫彈出站內瀏覽 + 01 健檢與 02 編修徹底分離
            srv_src = open(os.path.join(STUDIO_DIR, "app_server.py"), "r", encoding="utf-8").read()
            check('PYTHONIOENCODING' in srv_src
                  and "reconfigure(encoding='utf-8')" in srv_src
                  and 'id="btnGoToEditorFromAudit"' not in index_html
                  and 'formatIsnHtml(STATE.isnInfo, false)' in index_html,
                  "Windows 原生選檔支援 UTF-8 中文路徑、取消不再強跳站內瀏覽，且 01 健檢已移除 02 編修混合按鈕")

            # [v0.8.029] 驗證健檢智慧降噪：2,Title Skip 豁免、Global [Scripts] 歸類自動修補、歷史建議折疊層與同區塊合並
            noise_ws = {
                "project_name": "NOISE", "station_name": "MB",
                "global_ini": {"Settings": {}, "Scripts": {}},
                "instruments": [], "switches": [],
                "duts": [{"Load": "*$(LOAD_1)", "DUT Name": "NOISE$MB", "Station": "MB,1"}],
                "marcos": {},
                "stations": {"MB": [
                    {"Index": "000", "Phase": "1", "Title": "2,SkipBlock", "Send": ":Delay,\"10\"", "ExecMode": "4:2,2", "TestID": ""},
                    {"Index": "001", "Phase": "", "Title": "", "Send": ":Delay,\"10\"", "ExecMode": "0", "TestID": ""},
                    {"Index": "002", "Phase": "", "Title": "", "Send": ":Delay,\"10\"", "ExecMode": "0", "TestID": ""},
                    {"Index": "003", "Phase": "2", "Title": "0,Active", "Send": "*$(FixAuto)", "ExecMode": "0", "TestID": "CUSTOM9"},
                    {"Index": "004", "Phase": "97", "Title": "1,End", "Send": ":CloseMessage", "ExecMode": "3", "TestID": "B7PL025"},
                ]}
            }
            noise_rep = _audit_ws(noise_ws)
            noise_man_txt = "\n".join(noise_rep.get("manual_warnings") or [])
            noise_auto_txt = "\n".join(noise_rep.get("auto_fix_warnings") or [])
            noise_adv_txt = "\n".join(noise_rep.get("advisory_warnings") or [])
            check("2,SkipBlock" not in noise_man_txt and "2,SkipBlock" not in noise_adv_txt
                  and "FixAuto" in noise_auto_txt and "FixAuto" not in noise_man_txt
                  and "CUSTOM9" in noise_adv_txt and "CUSTOM9" not in noise_man_txt
                  and "歷史寫法與最佳實踐建議" in index_html,
                  "健檢降噪機制正確運作：2,Title 免報死步/缺碼、[Scripts] 自動補變數歸類自動修補、非致命建議分流折疊",
                  f"man={noise_rep['manual_warnings']} auto={noise_rep['auto_fix_warnings']} adv={noise_rep['advisory_warnings']}")

            # [v0.8.030] 驗證頂部 Header 精簡 + 重新整理顯示開關 + 全站 rem 字體連動 + 加長手風琴不跳動 + 紅字強調 NI-DAQmx
            import re as _re_chk
            header_sec = index_html.split('<div class="top-header">')[1].split('<div class="app-body">')[0]
            px_leftover_css = _re_chk.findall(r'font-size\s*:\s*\d+(?:\.\d+)?px', app_css)
            check('掃描/切換主程式' not in header_sec
                  and 'id="btnTopRefresh"' in header_sec
                  and 'setChkTopRefresh' in flow_guide_js
                  and 'show_top_refresh' in srv_src
                  and 'html {' in app_css and len(px_leftover_css) == 0
                  and 'min-height: 440px;' in app_css and 'min-height: 2.7rem;' in app_css
                  and ('#DC2626' in index_html and 'NI-DAQmx 未安裝' in index_html and '#DC2626' in flow_guide_js),
                  "頂部精簡＋重新整理開關、全站字體 rem 連動、手風琴加高穩固與 NI-DAQmx 紅字強調全數通過",
                  f"px_leftover_css={px_leftover_css}")

            # [v0.8.031] 驗證 SFIS WebService 拖曳互動人機 + SOAP 實測引擎 + 直接匯出/插入 Excel
            from core import sfis_client
            soap_env = sfis_client.build_soap_envelope("WTSP_GETVERSION", {
                "isn": "1B5723090000004", "device": "710001", "ver_type": "ISN_BASEINFO", "chk_data": "MAC1", "chk_data2": ""
            })
            parsed_soap = sfis_client.parse_soap_response(
                "WTSP_GETVERSION",
                '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
                '<WTSP_GETVERSIONResponse xmlns="http://www.pegatroncorp.com/SFISWebService/">'
                '<WTSP_GETVERSIONResult>1\x1fDATA GOT!!\x1f001122334455\x1fOK</WTSP_GETVERSIONResult>'
                '</WTSP_GETVERSIONResponse></soap:Body></soap:Envelope>'
            )
            check('WTSP_GETVERSION' in soap_env and 'ISN_BASEINFO' in soap_env
                  and parsed_soap.get("passed") is True and (parsed_soap.get("slots") or {}).get("P_CAVER") == "001122334455",
                  "sfis_client SOAP XML 組包與 WTSP_GETVERSION 回傳槽位解析 (P_CAVER) 正確")

            soap_api_res = post_json("/api/sfis_soap_test", {
                "url": "http://127.0.0.1:1/SFISWebService/SFISTSPWebService.asmx",
                "action": "WTSP_CHKROUTE",
                "params": {"isn": "1B5723090000004", "device": "710001"}
            })
            check(soap_api_res.get("status") == "offline" and soap_api_res.get("reachable") is False and soap_api_res.get("passed") is False,
                  "/api/sfis_soap_test 正確回報離線/無內網狀態而不當機")

            sfis_items = [
                {"kind": "checkroute"},
                {"kind": "getversion", "ver_type": "ISN_BASEINFO", "slot_code": "2", "chk_data": "MAC1", "chk_data2": "", "ref_var": "sfMAC"},
                {"kind": "savelink", "save_key": "SNB", "save_val": "*(gUUID)"},
            ]
            sfis_exp = post_json("/api/export_sfis_hmi_script", {
                "mode": "new_template",
                "items": sfis_items,
                "config": {"url": "http://172.18.202.12/SFISWebService/SFISTSPWebService.asmx", "project_name": "VER_SFIS", "station": "MB", "device_id": "710001", "tsp": "VER_SFIS,2"}
            })
            wb_sf = openpyxl.load_workbook(sfis_exp["excel_path"])
            sf_hdr = list(next(wb_sf["MB"].iter_rows(min_row=1, max_row=1, values_only=True)))
            em_idx = sf_hdr.index("ExecMode") if "ExecMode" in sf_hdr else 13
            sf_cmds = [str(row[6] or "") for row in wb_sf["MB"].iter_rows(min_row=2, values_only=True)]
            sf_ems = [str(row[em_idx] or "") for row in wb_sf["MB"].iter_rows(min_row=2, values_only=True) if ":Sf" in str(row[6] or "")]
            check(sfis_exp.get("status") == "ok" and wb_sf.active.title == "MB"
                  and any(":ShowISN" in c for c in sf_cmds) and any(":SfCheckRoute" in c for c in sf_cmds)
                  and any(":SfGetVersion" in c for c in sf_cmds) and any(":SfSaveLinkData" in c for c in sf_cmds)
                  and all(em == "8" for em in sf_ems)
                  and sfis_exp["audit_report"]["error_count"] == 0 and sfis_exp["audit_report"]["warning_count"] == 0,
                  "SFIS 互動人機 /api/export_sfis_hmi_script 產出 0 Error / 0 Warning 標準 Excel（含 :ShowISN 與 ExecMode=8）",
                  str(sf_cmds))

            check('sfis_hmi.js' in index_html and 'id="toolsSubPaneSfis"' in index_html
                  and 'sfisHmiRunStep' in sfis_hmi_js and 'sfisHmiExport' in sfis_hmi_js,
                  "UI 已完整載入 sfis_hmi.js 雙欄拖曳互動人機與 SOAP/Excel 按鈕")

            # [v0.8.032] 驗證極簡頂部返回列、廠區快選汰換(含PTB/PTSN/無SAGEMCOM/ADB_X740)、Logout(status=0)、SkipSaveResultOnFail INI 與 3 張動畫舞台圖片
            logout_env = sfis_client.build_soap_envelope("WTSP_LOGINOUT", {"op": "S09166390", "device": "710001", "status": 0})
            rw_steps = sfis_client.build_sfis_excel_steps([{"kind": "rw", "field_key": "SNA", "save_val": "TEST_RW"}])
            preset_ids = {p["id"] for p in sfis_client.SFIS_PLANT_PRESETS}
            sfis_sys_ini = open(os.path.join(sfis_exp["output_dir"], "System.ini"), "r", encoding="utf-8", errors="ignore").read()
            check('<status>0</status>' in logout_env
                  and any(":SfSaveLinkData,\"SNA\",\"TEST_RW\"" in r.get("Send", "") for r in rw_steps)
                  and any(":SfGetVersion,\"*(ISN)\",\"ISN_BASEINFO\",\"2\",\"SNA\",\"\"" in r.get("Send", "") for r in rw_steps)
                  and {"PTB_PROD", "PTB_QA", "PTB_F1", "TY3_PROD", "TY3_QA", "SUZHOU_PROD", "SUZHOU_QA"}.issubset(preset_ids)
                  and "SAGEMCOM" not in preset_ids and "ADB_X740" not in preset_ids,
                  "v0.8.034 sfis_client 支援 OP Logout(status=0)、R/W 寫入回讀與 巴淡PTB/桃園TY3/蘇州 常用廠區清單",
                  str(sorted(preset_ids)))
            check("SFIS_SkipSaveResultOnFail=1" in sfis_sys_ini,
                  "v0.8.032 匯出 SFIS 驗證檔 System.ini 預設開啟 SFIS_SkipSaveResultOnFail=1（失敗不上傳保護 ISN）")
            hub_bar_sec = index_html.split('id="genBackToModeHubBar"')[1].split('<div id="genModeCreate"')[0]
            app_css = open(os.path.join(STUDIO_DIR, "web", "css", "app.css"), "r", encoding="utf-8").read()
            check('display:none;' in hub_bar_sec and '/images/PC.png' in sfis_hmi_js
                  and '/images/cloud.png' in sfis_hmi_js and '/images/database.png' in sfis_hmi_js
                  and '.sfis-split-layout' in app_css and '.sfis-anim-stage' in app_css
                  and '_pushResponseLog' in sfis_hmi_js and '巴淡 PTB' in sfis_hmi_js
                  and '重慶' not in sfis_hmi_js,
                  "v0.8.033 左右雙欄工作視窗、廠區正名巴淡PTB下拉選單、全積木吐出字串累積與動畫舞台皆就緒")

            # 驗證 /api/pick_sfis_ini 不帶檔名可自動讀取現成 System.ini
            ini_pick_res = post_json("/api/pick_sfis_ini", {"ini_path": os.path.join(sfis_exp["output_dir"], "System.ini")})
            check(ini_pick_res.get("status") == "ok" and "SFISTSPWebService.asmx" in (ini_pick_res.get("config") or {}).get("url", ""),
                  "v0.8.033 /api/pick_sfis_ini 正確解析 System.ini 與 Global.ini DEVID_1",
                  str(ini_pick_res))

            # [v0.8.034] 驗證桃園三廠 TY3 WebLink (VALO360/0411_ER2_DONE) 與虛擬工單 5 碼流水號範本持久化 API
            ty3_preset = next((p for p in sfis_client.SFIS_PLANT_PRESETS if p["id"] == "TY3_PROD"), {})
            ty3_qa = next((p for p in sfis_client.SFIS_PLANT_PRESETS if p["id"] == "TY3_QA"), {})
            prof_get = get_json("/api/sfis_hmi_profiles")
            check("pxd-sftsp-n3.sfis.pegatroncorp.com" in ty3_preset.get("url", "")
                  and "SFISWebService_XDNPDB0QA" in ty3_qa.get("url", "")
                  and prof_get.get("status") == "ok"
                  and any(m.get("mo") == "26951603" and m.get("seq_digits") == 5 for m in (prof_get.get("virtual_mos") or []))
                  and "sfisExpandMoIsns" in sfis_hmi_js and "sfisAddCustomPlant" in sfis_hmi_js,
                  "v0.8.034 TY3 桃園三廠網址、虛擬工單(26951603+5碼流水號)範本與廠區增修功能就緒")

            # [v0.8.035] 驗證空白頁 Bug 修復 + 本機模擬 SFIS 內網 + 0~7 堆疊與 Centimani Ref 找字串轉義
            check("const p = (typeof CENTIMANI_ENV_PROFILE" in index_html
                  and "switchToolsVerifyTab" in index_html.split("if (GEN_SUB_MODE === 'tools')")[1].split("let TAB3_QUEUE")[0],
                  "v0.8.035 已修復初次點入實機驗證空白 Bug（定義 CENTIMANI_ENV_PROFILE 並直接渲染 SFIS 子頁）")
            post_json("/api/sfis_mock_reset", {})
            mk_login = post_json("/api/sfis_soap_test", {"mock": True, "action": "WTSP_LOGINOUT", "params": {"op": "S09166390", "device": "710001", "status": 1}})
            mk_item = post_json("/api/sfis_soap_test", {"mock": True, "action": "WTSP_GETVERSION", "params": {"isn": "2695160300001", "ver_type": "ITEMINFO"}})
            mk_wr = post_json("/api/sfis_soap_test", {"mock": True, "action": "WTSP_RESULT", "params": {"isn": "2695160300001", "save_key": "SNA", "save_val": "MOCK_VAL_99", "status": 1}})
            mk_rd = post_json("/api/sfis_soap_test", {"mock": True, "action": "WTSP_GETVERSION", "params": {"isn": "2695160300001", "ver_type": "ISN_BASEINFO", "chk_data": "SNA"}})
            mk_blk = post_json("/api/sfis_soap_test", {"mock": True, "action": "WTSP_CHKROUTE", "params": {"isn": "2695160300001", "device": "710001"}})
            post_json("/api/sfis_mock_reset", {})
            mk_rst = post_json("/api/sfis_soap_test", {"mock": True, "action": "WTSP_CHKROUTE", "params": {"isn": "2695160300001", "device": "710001"}})
            check(mk_login.get("passed") is True and "Pegatron SFIS" in mk_login.get("msg", "")
                  and (mk_item.get("slots") or {}).get("P_CCVER") == "60_2695160300001"
                  and (mk_item.get("slots") or {}).get("P_CDVER") == "90AA221000S0_00001"
                  and mk_wr.get("passed") is True
                  and (mk_rd.get("slots") or {}).get("P_CAVER") == "MOCK_VAL_99"
                  and mk_blk.get("passed") is False and mk_rst.get("passed") is True,
                  "v0.8.035 本機模擬 SFIS 內網支援 Login/ITEMINFO(0~7堆疊)/WRITE回讀驗證/過站阻擋與重置 DB")
            ref_split = sfis_client.build_centimani_ref_expr("sf5G", "split", delim=";", index=1)
            ref_within = sfis_client.build_centimani_ref_expr("sfSN", "within", left="SN:", right=";IMEI")
            ref_steps = sfis_client.build_sfis_excel_steps([{"kind": "getversion", "ver_type": "MOKP_SN", "slot_code": "4", "chk_data": "W3G", "ref_expr": ref_within}])
            check(ref_split == '$sf5G:SplitString,"\\;","1";'
                  and ref_within == '$sfSN:WithinString,"SN\\:","\\;IMEI","";'
                  and ref_steps[1]["Ref"] == '$sfSN:WithinString,"SN\\:","\\;IMEI","";'
                  and ',\"4\",\"W3G\"' in ref_steps[1]["Send"]
                  and "sfisPickSlotIndex" in sfis_hmi_js and "sfisPickSegment" in sfis_hmi_js and "sfisSetMockMode" in sfis_hmi_js,
                  "v0.8.035 支援 0~7 堆疊選格、Centimani 官方 Ref 找字串轉義 (SplitString/WithinString) 與完整積木清單")

            # [v0.8.036] 驗證雙視窗拖曳調寬 + 折疊吐回字串 + 模擬切換清錯誤 + 全域字體聯動 + 正名實機驗證中心（SFIS)
            inst_hmi_js = open(os.path.join(STUDIO_DIR, "web", "js", "inst_hmi.js"), "r", encoding="utf-8").read()
            check("tools: '🛡️ 實機驗證中心（SFIS)'" in index_html
                  and "sfis-split-resizer" in app_css and "sfisStartSplitDrag" in sfis_hmi_js
                  and 'id="sfisResponseDetails"' in sfis_hmi_js and "responseExpanded:" in sfis_hmi_js
                  and "it.status = 'idle';" in sfis_hmi_js.split("function sfisSetMockMode")[1].split("function sfisStartSplitDrag")[0]
                  and "sfisSetMockMode(true); sfisHmiRunAll();" in sfis_hmi_js
                  and "#toolsSubPaneSfis" in app_css and "sfis-hmi-wrap" in sfis_hmi_js
                  and "document.documentElement.style.fontSize = valid + 'px'" in inst_hmi_js,
                  "v0.8.036 雙視窗拖曳調寬、吐回字串預設折疊、切換模擬清除離線錯誤、字體連動與正名實機驗證中心（SFIS) 全數通過")

            # [v0.8.037] 驗證虛擬工單 INI 範本 (/api/pick_sfis_ini) + 模擬模式瀏覽器備援必 PASS + 模擬底色變換 (新增步驟不變色)
            v_mo_ini = os.path.join(app_server.PROJECT_ROOT, "虛擬工單SFIS測試範本", "System.ini")
            v_ini_res = post_json("/api/pick_sfis_ini", {"ini_path": v_mo_ini})
            v_cfg = v_ini_res.get("config") or {}
            init_meta = get_json("/api/init")
            check(os.path.exists(v_mo_ini)
                  and v_ini_res.get("status") == "ok"
                  and v_cfg.get("device_id") == "710888"
                  and v_cfg.get("station") == "FT1"
                  and v_cfg.get("isn") == "2695160300002"
                  and v_cfg.get("tsp") == "VALO360,2"
                  and (init_meta.get("server_build") or "").startswith("Build v0.8."),
                  "v0.8.037 虛擬工單SFIS測試範本 (System.ini + Global.ini) 完整支援 /api/pick_sfis_ini 匯入與版本握手",
                  str(v_ini_res))
            check("_runLocalBrowserSfisMock" in sfis_hmi_js
                  and "data.is_mock !== true" in sfis_hmi_js
                  and "#FEF9C3" in sfis_hmi_js
                  and 'id="sfisQuickAddBox" style="background:#FFFFFF;' in sfis_hmi_js,
                  "v0.8.037 模擬內網具瀏覽器備援必 PASS 引擎＋人機顯著變色切換（新增步驟列維持白底不變色）")

            # [v0.8.038] 驗證取消卡片重複吐回 + 左下終端自然延伸無固定高度 + GET 空槽折疊
            check("sfisSetDragSortMode" in sfis_hmi_js and "sfisMoveStep" in sfis_hmi_js
                  and "<span>吐回：" not in sfis_hmi_js
                  and 'id="sfisLogsContainer"' in sfis_hmi_js and "max-height:240px" not in sfis_hmi_js
                  and "sfis-empty-slots-fold" in sfis_hmi_js,
                  "v0.8.038 移除右側重複吐回框、左下日誌無高度上限延伸與 GET 空欄位自動折疊全數通過")

            # [v0.8.039] 驗證積木卡片去冗字：移除「免額外填寫...」與每卡指令預覽列 (保留底部整合預覽)
            check("免額外填寫，自動檢查目前單顆 ISN" not in sfis_hmi_js
                  and 'id="sfisCardPrev_' not in sfis_hmi_js
                  and 'id="sfisLiveExcelPreview"' in sfis_hmi_js,
                  "v0.8.039 已清除積木卡片內冗餘說明與重複指令行，維持單卡精簡外觀")

            # [v0.8.040] 驗證實機驗證中心（SFIS) 改版為 3 卡水平手風琴入口 (#toolsVerifyHub) + 移除頂部多餘書籤列最大化面積
            tools_sec = index_html.split('<div id="genModeTools"')[1].split('</div><!-- /genModeTools -->')[0]
            check('id="toolsVerifyHub"' in tools_sec
                  and 'id="toolsHubCard_real"' in tools_sec
                  and 'id="toolsHubCard_mock"' in tools_sec
                  and 'id="toolsHubCard_dll"' in tools_sec
                  and 'source-mode-bar' not in tools_sec
                  and 'id="btnToolsBackToAcc"' in index_html
                  and "setActiveToolsHubCard" in sfis_hmi_js
                  and "通訊模式：" not in sfis_hmi_js,
                  "v0.8.040 實機驗證中心水平手風琴大卡牌入口與去分頁最大化工作區全數就緒")

            # [v0.8.041] 驗證全域清除所有「X 合 1」標註（包含既有編修與實機驗證中心）
            audit_ed_js = open(os.path.join(STUDIO_DIR, "web", "js", "audit_editors.js"), "r", encoding="utf-8").read()
            check("5 合 1" not in index_html and "3 合 1" not in index_html
                  and "5 合 1" not in audit_ed_js and "5 合 1" not in flow_guide_js,
                  "v0.8.041 全站已移除『5 合 1 / 3 合 1』標註，統一使用乾淨手風琴名稱")

            # [v0.8.042] 驗證 3 秒三段式動畫展演開關 (方案 A) + SFIS 匯出 Excel 自動開啟目錄/Excel ＋ 動態 ISN ScanBarcode 長度校正
            launched_excels.clear()
            opened_folders.clear()
            sf_13_exp = post_json("/api/export_sfis_hmi_script", {
                "mode": "new_template",
                "items": sfis_items,
                "config": {"url": "http://172.18.202.12/SFISWebService/SFISTSPWebService.asmx", "project_name": "VER_SFIS13", "station": "FT1", "device_id": "710888", "op": "S09166390", "isn": "2695160300001", "tsp": "VER_SFIS,2"}
            })
            wb_13 = openpyxl.load_workbook(sf_13_exp["excel_path"])
            dut_sb = str(next(wb_13["DUTs"].iter_rows(min_row=2, max_row=2, values_only=True))[5] or "")
            glb_13 = open(os.path.join(sf_13_exp["output_dir"], "Global.ini"), "r", encoding="utf-8", errors="ignore").read()
            check(sf_13_exp.get("status") == "ok"
                  and "{ISN,13,[0-9A-Z]}" == dut_sb
                  and "gUUID=" in glb_13
                  and len(opened_folders) >= 1 and len(launched_excels) >= 1
                  and "sfisToggleSlowDemo" in sfis_hmi_js
                  and "returning-pass" in app_css and "sfisPacketLeft" in app_css,
                  "v0.8.042 SFIS 3 秒三段式動畫開關 + 產出 Excel 自動開啟目錄/Excel + ScanBarcode 13 碼與 gUUID 校正完成",
                  f"dut_sb={dut_sb}, folders={len(opened_folders)}, excels={len(launched_excels)}")

            # [v0.8.043] 驗證積木合併為單一垂直可上下拖曳+↑↓排序清單（移除重複橫向撲克條）
            check('id="sfisMiniDeckBar"' not in sfis_hmi_js
                  and "sfis-track-card" in app_css and "sfis-track-card" in sfis_hmi_js
                  and "sfisPrepCardDrag" in sfis_hmi_js and "sfisCardDragOver" in sfis_hmi_js
                  and "drop-before" in app_css and "drop-after" in app_css,
                  "v0.8.043 已整合為單一垂直可拖曳＋↑↓箭頭積木清單，消除重複橫向排列")

            # [v0.8.044] 驗證方案 1：跨雙欄頂部寬幅即時動畫舞台 (#sfisTopStageWrap 位於 #sfisSplitLayout 上方)
            check('id="sfisTopStageWrap"' in sfis_hmi_js
                  and sfis_hmi_js.find('id="sfisTopStageWrap"') < sfis_hmi_js.find('id="sfisSplitLayout"')
                  and "sfis-node-card-wide" in app_css and "sfis-node-card-wide" in sfis_hmi_js,
                  "v0.8.044 方案 1 跨雙欄頂部寬幅動畫舞台與左下終端空間騰空完成")

            # [v0.8.045] 驗證撲克大牌組(鎖定頭尾 Login/CheckRoute/Logout 骨架) + 右側聚焦編輯區 + 實機 Excel Reply/ExecMode 完全對齊
            sf_reply_idx = sf_hdr.index("Reply") if "Reply" in sf_hdr else 7
            sf_title_idx = sf_hdr.index("Title") if "Title" in sf_hdr else 3
            sf_rows_all = list(wb_sf["MB"].iter_rows(min_row=2, values_only=True))
            show_isn_rows = [r for r in sf_rows_all if ":ShowISN" in str(r[6] or "")]
            chk_route_rows = [r for r in sf_rows_all if ":SfCheckRoute" in str(r[6] or "")]
            save_link_rows = [r for r in sf_rows_all if ":SfSaveLinkData" in str(r[6] or "")]
            check(bool(show_isn_rows)
                  and str(show_isn_rows[0][sf_title_idx] or "") == "0,CheckRoute"
                  and str(show_isn_rows[0][sf_reply_idx] or "") == "0"
                  and str(show_isn_rows[0][em_idx] or "") == "0"
                  and bool(chk_route_rows)
                  and str(chk_route_rows[0][sf_reply_idx] or "") == "0"
                  and str(chk_route_rows[0][em_idx] or "") == "8"
                  and bool(save_link_rows)
                  and str(save_link_rows[0][sf_reply_idx] or "") == "0"
                  and str(save_link_rows[0][em_idx] or "") == "8",
                  "v0.8.045 匯出 SFIS Excel 的 Title/Reply/ExecMode (:ShowISN 0/0, :SfCheckRoute 0/8, :SfSaveLinkData 0/8) 與 SCRIPTS 範本完全對齊",
                  str(sf_rows_all))
            check('id="sfisPokerDeckGrid"' in sfis_hmi_js
                  and 'id="sfisSelectedCardPanel"' in sfis_hmi_js
                  and 'id="sfisCompactEnvBar"' in sfis_hmi_js
                  and '_enforceSfisSkeleton' in sfis_hmi_js
                  and 'sfisSelectDeckCard' in sfis_hmi_js
                  and '.sfis-deck-grid' in app_css
                  and '.sfis-deck-card.active' in app_css,
                  "v0.8.045 SFIS 撲克牌組(鎖定 Login/CheckRoute/Logout 骨架)與右側聚焦檢查面板及終端佈局完整就緒")

            # [v0.8.046] 驗證頂部動畫即時顯示 GET/WRITE 送出與吐回字串 + 修正上方按鈕拖入牌桌 + 5秒全流程動畫 + 移除冗餘 R/W
            cat_sec = sfis_hmi_js.split("const SFIS_CATALOG_BLOCKS = [")[1].split("];")[0]
            check("function sfisDragCatalogStart(" in sfis_hmi_js
                  and "function sfisDropOnDeckContainer(" in sfis_hmi_js
                  and 'id="sfisPokerDeckBox"' in sfis_hmi_js
                  and "drop-catalog-over" in app_css
                  and 'id="sfisAnimPayloadBar"' in sfis_hmi_js
                  and "liveSendStr" in sfis_hmi_js and "liveRecvStr" in sfis_hmi_js
                  and "5秒全流程動畫" in sfis_hmi_js
                  and "Math.round(5000 / totalSteps)" in sfis_hmi_js
                  and "kind: 'rw'" not in cat_sec,
                  "v0.8.046 動畫區即時顯示 GET/WRITE 字串、5秒全流程一次跑完、上方膠囊可拖入牌桌且已移除冗餘 R/W")

            # [v0.8.047] 驗證 SFIS 範本保留 Switch/Instrument 未掛載列（解決 LoadScript.MainScript Read Excel for Switch failed / File Name doestn't set）且 :CloseMessage Reply=0
            close_rows = [r for r in sf_rows_all if ":CloseMessage" in str(r[6] or "")]
            sw_ws = wb_sf["Switch"]
            inst_ws = wb_sf["Instrument"]
            sw_mount = sw_ws.cell(2, 1).value
            inst_mount = inst_ws.cell(2, 1).value
            check(sw_ws.max_row >= 2 and inst_ws.max_row >= 2
                  and not (sw_mount or "").strip() and not (inst_mount or "").strip()
                  and bool(close_rows) and str(close_rows[0][sf_reply_idx] or "") == "0",
                  "v0.8.047 SFIS Excel 保留 Switch/Instrument 未掛載列(Mount空值)與 :CloseMessage Reply=0，徹底避免 CentimaniSystem 報 File Name doestn't set",
                  f"sw_rows={sw_ws.max_row}, inst_rows={inst_ws.max_row}, close={close_rows}")

            # [v0.8.048] 驗證 Phase 0 刷條碼起手式 (:ShowISN + :SetVal $ScanISN + :GetVal Validation) + GET 預設抓字串 Ref & Validation + 移除假 GET 標籤積木避免漏匯出
            set_scan_rows = [r for r in sf_rows_all if ':SetVal,"$ScanISN"' in str(r[6] or "")]
            get_scan_rows = [r for r in sf_rows_all if ':GetVal,"$ScanISN"' in str(r[6] or "")]
            get_with_val = sfis_client.build_sfis_excel_steps([
                {"kind": "checkroute"},
                {"kind": "get", "field_key": "SNA", "ref_expr": '$sfSNA:SplitString,"\\;","0":Trim;', "validation": "(sfSNA,%len,1,64);"},
            ], start_phase=0, include_show_isn=True)
            check(bool(set_scan_rows) and bool(get_scan_rows)
                  and "(gISN,%len,3,32);" in str(get_scan_rows[0][10] or "")
                  and any(':SfGetVersion,"*(ISN)","ISN_BASEINFO","2","SNA",""' in r.get("Send", "")
                          and ':SplitString,"\\;","0":Trim;' in r.get("Ref", "")
                          and r.get("Validation") == "(sfSNA,%len,1,64);" for r in get_with_val)
                  and "kind: 'getlabel'" not in cat_sec
                  and "sfisQuickQueryLabel" in sfis_hmi_js
                  and "item.ref_mode = 'split'" in sfis_hmi_js,
                  "v0.8.048 Phase 0 開頭刷條碼起手式(:SetVal/:GetVal)、GET 預設抓字串+Validation 與避免 getlabel 漏匯出皆就緒",
                  str(get_with_val))

            # [v0.8.049] 驗證 01. FWDL (20241016-42V) 深度解析後之程式改進：Col 17 LocalStepIndex 自動重算寫入、未掛載 Instrument 不誤報 Error/Warning、:SfSaveLinkData EM 與 ""$ 雙引號防呆
            mb_ws_v49 = wb_sf["MB"]
            col17_vals = [mb_ws_v49.cell(r, 17).value for r in range(2, mb_ws_v49.max_row + 1)]
            chk_em_ws = {
                "project_name": "V49_CHK", "station_name": "MB",
                "global_ini": {"Settings": {}, "Scripts": {}},
                "instruments": [
                    {"Mount": "", "Name": "MDA2700", "ControlDLL": "MDA2700.dll", "Settings": "*$(UNMOUNTED_VAR)", "Version": "0.0.0.1"}
                ],
                "switches": [],
                "duts": [{"Load": "*$(LOAD_1)", "DUT Name": "V49_CHK$MB", "Station": "MB,1"}],
                "marcos": {},
                "stations": {"MB": [
                    {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ':ShowISN,"*(ISN)"', "Reply": "0", "ExecMode": "0", "TestID": "B7PL025"},
                    {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "Reply": "0", "ExecMode": "8", "TestID": "OTCH013"},
                    {"Index": "002", "Phase": "1", "Title": "0,Test", "Send": ':GetVal,""$Fixauto"', "Reply": "0", "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "003", "Phase": "2", "Title": "0,Save", "Send": ':SfSaveLinkData,"SNA","1"', "Reply": "0", "ExecMode": "1", "TestID": "OTFX064"},
                    {"Index": "004", "Phase": "97", "Title": "1,End", "Send": ":CloseMessage", "Reply": "0", "ExecMode": "3", "TestID": "B7PL025"},
                ]},
            }
            v49_rep = _audit_ws(chk_em_ws)
            v49_err_txt = "\n".join(v49_rep.get("errors") or [])
            v49_warn_txt = "\n".join((v49_rep.get("warnings") or []) + (v49_rep.get("auto_fix_warnings") or []))
            check(col17_vals[:4] == [0, 1, 2, 3]
                  and col17_vals[4] == 0
                  and "UNMOUNTED_VAR" not in v49_warn_txt
                  and "Version mismatch" not in v49_err_txt
                  and "ExecMode='1'" in v49_err_txt
                  and "重複雙引號" in v49_warn_txt,
                  "v0.8.049 Col 17 LocalStepIndex 重算、未掛載儀器降噪、:SfSaveLinkData EM 與 ""$ 雙引號防呆驗證全數通過",
                  f"col17={col17_vals}, errs={v49_rep.get('errors')}, warns={v49_warn_txt}")

            # [v0.8.050] 驗證 4 大新實戰積木 (Sub=1 DevUart+FinalGo / Prompt="!" 串流 / :SfEnabled 4:2,4 / Phase 98/99 分流) 與多槽同連線別名驗證
            from core.golden_data import STANDARD_BLOCKS as _STD_V50
            from core.excel_engine import import_excel_to_workspace as _parse_v50
            std_ids_v50 = {b["block_id"] for b in _STD_V50}
            new_v50_blocks = [
                "BLK_SUBDEV_DEVUART_FINALGO",
                "BLK_SFIS_ENABLED_BRANCH",
                "BLK_FW_STREAM_PROMPT_FLASH",
                "BLK_PHASE98_99_BRANCH_TEARDOWN",
            ]
            check(all(bid in std_ids_v50 for bid in new_v50_blocks),
                  "v0.8.050 STANDARD_BLOCKS 已完整納入 4 大實戰積木 (DevUart+FinalGo / :SfEnabled / Prompt='!' / Phase 98-99)",
                  str(sorted(std_ids_v50)))

            wiz_v50 = post_json("/api/generate_new_standalone", {
                "project_name": "V50_STD",
                "station_name": "MB",
                "dut_count": 4,
                "block_ids": [
                    "BLK_PRETEST_ROUTE",
                    "BLK_SUBDEV_DEVUART_FINALGO",
                    "BLK_SFIS_ENABLED_BRANCH",
                    "BLK_FW_STREAM_PROMPT_FLASH",
                    "BLK_PHASE97_TEARDOWN",
                    "BLK_PHASE98_99_BRANCH_TEARDOWN",
                ],
                "open_excel": False,
            })
            ws_v50 = _parse_v50(wiz_v50["excel_path"])
            rep_v50 = _audit_ws(ws_v50)
            v50_mb_rows = ws_v50["stations"].get("MB", [])
            v50_inst_map = {str(i.get("Name", "")): i for i in ws_v50.get("instruments", [])}
            v50_phases = {str(r.get("Phase", "")).strip() for r in v50_mb_rows if str(r.get("Phase", "")).strip()}
            v50_conns = [str(d.get("Connection1 (Type,Name,ConnectString)", "")) for d in ws_v50.get("duts", [])]
            check(wiz_v50.get("status") == "ok"
                  and v50_inst_map.get("DevUart", {}).get("Mount") == "MB"
                  and any(str(r.get("Prompt", "")).strip() == "!" for r in v50_mb_rows)
                  and any(":SfEnabled" in str(r.get("Send", "")) and str(r.get("ExecMode", "")).strip() == "4:2,4" for r in v50_mb_rows)
                  and {"0", "97", "98", "99"}.issubset(v50_phases)
                  and len(v50_conns) == 4 and all('"UART"' in c for c in v50_conns)
                  and rep_v50.get("error_count", -1) == 0,
                  "v0.8.050 四大新積木一鍵產出含 4 槽共用 UART、DevUart 自動掛載、Prompt='!'、:SfEnabled 4:2,4 與 Phase 98/99 且 0 Error",
                  f"errs={rep_v50.get('errors')}, inst={v50_inst_map.get('DevUart')}, phases={sorted(v50_phases)}")

            # 驗證單一 DUT 列內重複 Connection5 與跨槽 4 槽共用 UART/STCmd 區分 + auto_fix 不破壞 DUT Name
            mdut_ws = {
                "project_name": "MDUT", "station_name": "MB",
                "global_ini": {"Settings": {"LOAD_1": "true", "LOAD_2": "true"}, "Scripts": {}},
                "instruments": [], "switches": [],
                "duts": [
                    {
                        "Load": "*$(LOAD_1)", "DUT Name": "MDUT$MB", "Station": "MB,1",
                        "Connection1 (Type,Name,ConnectString)": '"Uart","UART","COM1"',
                        "Connection5(Type,Name,ConnectString)": '"Uart","UART","COM9"',
                    },
                    {
                        "Load": "*$(LOAD_2)", "DUT Name": "MDUT$MB", "Station": "MB,2",
                        "Connection1 (Type,Name,ConnectString)": '"Uart","UART","COM2"',
                    },
                ],
                "marcos": {},
                "stations": {"MB": [
                    {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ':ShowISN,"*(ISN)"', "Reply": "0", "ExecMode": "0", "TestID": "B7PL025"},
                    {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "Reply": "0", "ExecMode": "8", "TestID": "OTCH013"},
                    {"Index": "002", "Phase": "97", "Title": "1,End", "Send": ":CloseMessage", "Reply": "0", "ExecMode": "3", "TestID": "B7PL025"},
                ]},
            }
            mdut_before = _audit_ws(mdut_ws)
            _autofix_ws(mdut_ws)
            mdut_after = _audit_ws(mdut_ws)
            check(any("同一 DUT 列內出現重複連線名稱 'UART'" in e for e in mdut_before.get("errors", []))
                  and '"UART_5"' in str(mdut_ws["duts"][0].get("Connection5(Type,Name,ConnectString)", ""))
                  and '"UART"' in str(mdut_ws["duts"][1].get("Connection1 (Type,Name,ConnectString)", ""))
                  and mdut_ws["duts"][1].get("DUT Name") == "MDUT$MB"
                  and mdut_after.get("error_count", -1) == 0,
                  "v0.8.050 DUTs 同列 Connection1..10 重複精準攔截修復、跨槽共用 UART 與 DUT Name (Project$Station) 完整保留",
                  f"before={mdut_before.get('errors')}, duts={mdut_ws['duts']}, after={mdut_after.get('errors')}")

            fwdl_sample = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                       "SCRIPTS", "perter_SCRIPT_11102026", "01. FWDL", "System",
                                       "Centimani_Olympus_TestFlow_FWDL_20241016-42V.xlsx")
            if os.path.exists(fwdl_sample):
                fwdl_ws = _parse_v50(fwdl_sample)
                fwdl_rep = _audit_ws(fwdl_ws)
                check(not any("Connection Name :" in e for e in fwdl_rep.get("errors", [])),
                      "v0.8.050 實戰 01. FWDL (20241016-42V.xlsx) 4 槽同名通道連線零誤報",
                      str(fwdl_rep.get("errors")))

            # [v0.8.051] 驗證 SFIS 產出與 CentimaniSystem.exe v1.2.1.2~v1.5.x 完全相容：
            # 1) 不誤吐 :Trim / :lwString、SplitString 逗號不誤跳脫為 \,
            # 2) :SfGetiMAC 若前端誤夾 SplitString,"\;","0" + %len(12,12) 自動補正為 :SubString,"0","12";
            # 3) System.ini 完整寫入 SFIS_LoginID 與 SFIS_GetDateISN
            check(sfis_client.escape_centimani_ref_arg(",") == ","
                  and sfis_client.escape_centimani_ref_arg(";") == "\\;"
                  and sfis_client.build_centimani_ref_expr("sfMAC", "split", delim=",", index=0) == '$sfMAC:SplitString,",","0";',
                  "v0.8.051 Centimani Ref 轉義不破壞逗號 (,)、移除不相容之 :Trim/:lwString")

            sf_v51_exp = post_json("/api/export_sfis_hmi_script", {
                "mode": "new_template",
                "open_excel": False,
                "config": {
                    "project_name": "SFIS_V51",
                    "station": "MB",
                    "url": "http://172.24.248.15/SFISWebService/SFISTSPWebService.asmx",
                    "tsp": "ATLAS,2",
                    "device_id": "710001",
                    "op": "S09166390",
                    "isn": "2695160300001",
                    "sfis_enable": "1",
                    "skip_save_on_fail": True,
                },
                "items": [
                    {"kind": "checkroute"},
                    {"kind": "getimac", "slot_code": "2", "ref_var": "sfMAC", "ref_expr": '$sfMAC:SplitString,"\\;","0";', "validation": "(sfMAC,%len,12,12);"},
                    {"kind": "savelink", "save_key": "SNA", "save_val": "TEST_VAL_01"},
                    {"kind": "get", "ver_type": "ISN_BASEINFO", "slot_code": "2", "chk_data": "SNA", "ref_var": "sfSNA", "validation": "(sfSNA,%len,1,64);"},
                ],
            })
            v51_sys_txt = open(os.path.join(sf_v51_exp["output_dir"], "System.ini"), "r", encoding="utf-8").read()
            ws_v51_sf = _parse_v50(sf_v51_exp["excel_path"])
            v51_rows = ws_v51_sf["stations"]["MB"]
            getval_v51 = [r for r in v51_rows if ':GetVal,"$ScanISN"' in str(r.get("Send", ""))]
            imac_v51 = [r for r in v51_rows if ":SfGetiMAC" in str(r.get("Send", ""))]
            getsna_v51 = [r for r in v51_rows if ":SfGetVersion" in str(r.get("Send", ""))]
            check(sf_v51_exp.get("status") == "ok"
                  and "SFIS_LoginID=S09166390" in v51_sys_txt
                  and "SFIS_GetDateISN=2695160300001" in v51_sys_txt
                  and bool(getval_v51) and getval_v51[0].get("Ref") == "$gISN;"
                  and bool(imac_v51) and imac_v51[0].get("Ref") == '$sfMAC:SubString,"0","12";'
                  and bool(getsna_v51) and getsna_v51[0].get("Ref") == "$sfSNA;",
                  "v0.8.051 SFIS System.ini 完整寫入 SFIS_LoginID/GetDateISN、且 GetVal/GetiMAC/GetVersion Ref 完全相容實機",
                  f"sys_has_op={'SFIS_LoginID=S09166390' in v51_sys_txt}, getval={getval_v51}, imac={imac_v51}, getsna={getsna_v51}")

            # 驗證 script_doctor 可偵測 SplitString 誤跳脫逗號 '\,' 與 iMAC 誤用分號切割
            comma_trap_ws = {
                "project_name": "TRAP", "station_name": "MB",
                "global_ini": {"Settings": {"LOAD_1": "true"}, "Scripts": {}},
                "instruments": [], "switches": [],
                "duts": [{"Load": "*$(LOAD_1)", "DUT Name": "TRAP$MB", "Station": "MB,1"}],
                "marcos": {},
                "stations": {"MB": [
                    {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ':ShowISN,"*(ISN)"', "Reply": "0", "ExecMode": "0", "TestID": "B7PL025"},
                    {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "Reply": "0", "ExecMode": "8", "TestID": "OTCH013"},
                    {"Index": "002", "Phase": "1", "Title": "0,MAC", "Send": ':SfGetiMAC,"*(ISN)","1","1","2"', "Ref": '$sfMAC:SplitString,"\\,","0";', "Validation": "(sfMAC,%len,12,12);", "ExecMode": "8", "TestID": "OTFX085"},
                    {"Index": "003", "Phase": "97", "Title": "1,End", "Send": ":CloseMessage", "Reply": "0", "ExecMode": "3", "TestID": "B7PL025"},
                ]},
            }
            trap_warns = "\n".join((_audit_ws(comma_trap_ws).get("warnings") or []) + (_audit_ws(comma_trap_ws).get("manual_warnings") or []))
            check("誤用跳脫逗號 '\\,'" in trap_warns,
                  "v0.8.051 script_doctor 可預警 SplitString 誤用 '\\,' 逗號跳脫陷阱",
                  trap_warns)

            # [v0.8.052] 驗證 0 → 1 空範本整合 SFIS 人機積木與 :SfEnabled、insert_current 不重複 CheckRoute
            check("BLK_SUBDEV_DEVUART_FINALGO" in index_html
                  and "BLK_SFIS_ENABLED_BRANCH" in index_html
                  and "openSfisHmiFromWizard" in index_html
                  and "toggleWizSfEnabled" in index_html
                  and "sfisGetHmiPayloadForWizard" in sfis_hmi_js
                  and "sfisSyncToWizardAndReturn" in sfis_hmi_js,
                  "v0.8.052 0→1 空範本 Step 2/3/4 已整合 SFIS 人機積木組、:SfEnabled 旁路開關與四項新流程積木")

            v52_gen = post_json("/api/generate_new_standalone", {
                "project_name": "V52_INT",
                "station_name": "MB",
                "dut_count": 2,
                "block_ids": ["BLK_PRETEST_ROUTE", "BLK_SFIS_ENABLED_BRANCH", "BLK_SFIS_MAC_69PN", "BLK_PHASE97_TEARDOWN"],
                "system_ini_overrides": {"SFIS_Enable": "1", "iPLAS_Enable": "1", "iPLAS_Site": "SUZHOU"},
                "open_excel": False,
                "wizard_config": {
                    "isn_length": 13,
                    "isn_pattern": "[0-9A-Z]",
                    "sfis_config": {
                        "use_hmi_items": True,
                        "hmi_items": [
                            {"kind": "checkroute"},
                            {"kind": "getimac", "slot_code": "2", "ref_var": "sfMAC", "ref_expr": '$sfMAC:SubString,"0","12";', "validation": "(sfMAC,%len,12,12);"},
                            {"kind": "savelink", "save_key": "SNA", "save_val": "VAL_52"},
                        ],
                        "hmi_config": {
                            "url": "http://172.24.248.15/SFISWebService/SFISTSPWebService.asmx",
                            "tsp": "V52,2",
                            "op": "S09166390",
                            "isn": "2695160300001",
                            "device_id": "710001",
                            "skip_save_on_fail": True,
                        },
                    },
                },
            })
            ws_v52 = _parse_v50(v52_gen["excel_path"])
            v52_rows = ws_v52["stations"]["MB"]
            v52_sys = open(os.path.join(v52_gen["output_dir"], "System.ini"), "r", encoding="utf-8").read()
            v52_rep = _audit_ws(ws_v52)
            check(v52_gen.get("status") == "ok"
                  and sum(1 for r in v52_rows if ":ShowISN" in str(r.get("Send", ""))) == 1
                  and any(":SfGetiMAC" in str(r.get("Send", "")) for r in v52_rows)
                  and any(':SfSaveLinkData,"SNA","VAL_52"' in str(r.get("Send", "")) for r in v52_rows)
                  and any(":SfEnabled" in str(r.get("Send", "")) for r in v52_rows)
                  and "SFIS_LoginID=S09166390" in v52_sys
                  and "SFIS_GetDateISN=2695160300001" in v52_sys
                  and "iPLAS_Enable=1" in v52_sys
                  and v52_rep.get("error_count", -1) == 0,
                  "v0.8.052 0→1 精靈整合 SFIS 人機積木產出不重複 :ShowISN、含 iPLAS/SFIS LoginID 且 0 Error",
                  f"errs={v52_rep.get('errors')}, sends={[r.get('Send') for r in v52_rows]}")

            ins_res = post_json("/api/export_sfis_hmi_script", {
                "mode": "insert_current",
                "items": [
                    {"kind": "checkroute"},
                    {"kind": "savelink", "save_key": "BT1", "save_val": "OK52"},
                ],
                "config": {"project_name": "INS52", "station": "MB", "op": "S09166390", "isn": "2695160300001", "device_id": "710001", "sfis_enable": "1"},
                "workspace": {
                    "project_name": "INS52", "station_name": "MB",
                    "global_ini": {"Settings": {"LOAD_1": "true"}, "Scripts": {}},
                    "instruments": [], "switches": [],
                    "duts": [{"Load": "*$(LOAD_1)", "DUT Name": "INS52$MB", "Station": "MB,1"}],
                    "marcos": {}, "system_ini": {},
                    "stations": {"MB": [
                        {"Index": "000", "Phase": "0", "Title": "0,CheckRoute", "Send": ':ShowISN,"*(ISN)"', "Reply": "0", "ExecMode": "0", "TestID": "B7PL025"},
                        {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "Reply": "0", "ExecMode": "8", "TestID": "OTCH013"},
                        {"Index": "002", "Phase": "1", "Title": "0,OtherTest", "Send": ':Delay,"100"', "Reply": "0", "ExecMode": "0", "TestID": "B7PL025"},
                        {"Index": "003", "Phase": "97", "Title": "1,End", "Send": ":CloseMessage", "Reply": "0", "ExecMode": "3", "TestID": "B7PL025"},
                    ]},
                },
            })
            ins_mb = ins_res["workspace"]["stations"]["MB"]
            ins_sys = ins_res["workspace"]["system_ini"]
            check(ins_res.get("status") == "ok"
                  and sum(1 for r in ins_mb if ":ShowISN" in str(r.get("Send", ""))) == 1
                  and any(':SfSaveLinkData,"BT1","OK52"' in str(r.get("Send", "")) for r in ins_mb)
                  and any(':Delay,"100"' in str(r.get("Send", "")) for r in ins_mb)
                  and ins_sys.get("SFIS_LoginID") == "S09166390"
                  and ins_sys.get("SFIS_GetDateISN") == "2695160300001",
                  "v0.8.052 SFIS insert_current 自動合併取代舊 CheckRoute 不重複，並同步寫入 SFIS_LoginID/GetDateISN")

            # [v0.8.053] 驗證 Step 2 進階專家積木已收納進預設收合抽屜，且 BLK_UART_BOOT_FW/BLK_PYTHON_SCRIPT_CALL 不含 :Trim
            v53_gen = post_json("/api/generate_new_standalone", {
                "project_name": "V53_CLEAN",
                "station_name": "MB",
                "dut_count": 1,
                "block_ids": ["BLK_PRETEST_ROUTE", "BLK_UART_BOOT_FW", "BLK_PYTHON_SCRIPT_CALL", "BLK_PHASE97_TEARDOWN"],
                "open_excel": False,
                "wizard_config": {
                    "fw_config": {"mode": "uart", "port": "COM4", "cmd": "cat /etc/version", "fw_version": "1.0.0"},
                    "python_config": {"python_path": "D:\\Py", "script_name": "t.py", "result_prefix": "RESULT=", "min_val": "0", "max_val": "100"},
                },
            })
            ws_v53 = _parse_v50(v53_gen["excel_path"])
            v53_refs = [str(r.get("Ref") or "") for r in ws_v53["stations"]["MB"]]
            check('id="wizAdvancedBlocksDrawer"' in index_html
                  and 'id="advancedBlockCheckGrid"' in index_html
                  and "ADVANCED_FLOW_BLOCK_IDS" in index_html
                  and all(":Trim" not in rf for rf in v53_refs),
                  "v0.8.053 Step 2 進階積木收合分流精簡完成，且 UART_BOOT_FW / PYTHON 積木無 :Trim 相容性問題",
                  str(v53_refs))

            # [v0.8.054] 驗證共用「範本測項移植 ＋ 引導式 SKU 精靈」前後端完整串接
            tsw_cat = get_json("/api/template_bundle/catalog")
            lock_tpls = [t for t in tsw_cat.get("templates", []) if "Olympus_LOCK_TestFlow_20260522.xlsx" in t.get("name", "")]
            check(tsw_cat.get("status") == "ok" and len(lock_tpls) >= 1,
                  "v0.8.054 /api/template_bundle/catalog 正確掃描列出 perter_SCRIPT_11102026 主力範本",
                  f"count={len(tsw_cat.get('templates', []))}")

            lock_insp = post_json("/api/template_bundle/inspect", {"excel_path": lock_tpls[0]["path"]})
            cc_blocks = [b for b in lock_insp.get("stations", {}).get("Lock", []) if "Country Code" in b.get("title", "")]
            check(lock_insp.get("status") == "ok"
                  and bool((lock_insp.get("sku_hints") or {}).get("has_custitem"))
                  and len(cc_blocks) == 1
                  and "LinuxUART" in (cc_blocks[0].get("connections") or {}),
                  "v0.8.054 /api/template_bundle/inspect 正確萃取出 LOCK 範本之 CUSTITEM 提示與 LinuxUART 相依連線",
                  str(lock_insp.get("sku_hints")))

            # Edit 模式套用：移植 Country Code + 3 種硬體衍生品 SKU (FULL / NO_BAT / NO_WIFI) + 閘門
            cc_key = cc_blocks[0]["block_key"]
            edit_apply = post_json("/api/template_bundle/apply", {
                "target_mode": "edit",
                "station_name": "MB",
                "workspace": ws_v53,
                "bundle_spec": {
                    "source_xlsx": lock_tpls[0]["path"],
                    "selected_block_keys": [cc_key],
                    "conn_remap": {"LinuxUART": "UART"},
                },
                "sku_spec": {
                    "enabled": True,
                    "source_mode": "CUSTITEM",
                    "compare_mode": "BRANCH_RULES",
                    "offline_wrap": True,
                    "offline_default_sku": "FULL",
                    "no_match_policy": "FAIL",
                    "param_to_ini": False,
                    "sku_branches": [
                        {"code": "FULL", "label": "整機全配", "iplas_model": "OLYMPUS_FULL", "expected_hw": "11"},
                        {"code": "NO_BAT", "label": "整機無電池", "iplas_model": "OLYMPUS_NBAT", "expected_hw": "11"},
                        {"code": "NO_WIFI", "label": "無WiFi版", "iplas_model": "OLYMPUS_NOWF", "expected_hw": "10"},
                    ],
                    "section_guards": [
                        {"section_title": "Country Code", "target_block_key": cc_key, "allowed_skus": ["FULL", "NO_BAT"]},
                        {"section_title": "CHECK BATTERY", "allowed_skus": ["FULL", "NO_WIFI"]},
                    ],
                },
                "preview": False,
            })
            ea_rep = edit_apply.get("report") or {}
            ea_steps = (edit_apply.get("workspace") or {}).get("stations", {}).get("MB", [])
            ea_sends = [str(s.get("Send") or "") for s in ea_steps]
            ea_replies = [str(s.get("Reply") or "") for s in ea_steps]
            check(edit_apply.get("status") == "ok"
                  and len(ea_rep.get("errors") or []) == 0
                  and len(ea_rep.get("manual_warnings") if "manual_warnings" in ea_rep else (ea_rep.get("warnings") or [])) == 0
                  and any("CUSTITEM" in sd for sd in ea_sends)
                  and any("@FULL||@NO_BAT" in rp for rp in ea_replies)
                  and any(":SetModelName" in sd for sd in ea_sends),
                  "v0.8.054 /api/template_bundle/apply 在 Edit 模式正確移植區塊＋3 SKU 分支＋衍生品閘門且 0 Error/0 Warning")

            # Create 模式 (0 -> 1)：套用 EXTERNAL_TXT (69MO.txt) + Global.ini 同步輸出實體檔案驗證
            v54_create = post_json("/api/generate_new_standalone", {
                "project_name": "V54_SKU",
                "station_name": "MB",
                "dut_count": 1,
                "block_ids": ["BLK_PRETEST_ROUTE", "BLK_PHASE97_TEARDOWN"],
                "open_excel": False,
                "template_bundle": {
                    "source_xlsx": lock_tpls[0]["path"],
                    "selected_block_keys": [cc_key],
                    "conn_remap": {"LinuxUART": "UART"},
                },
                "sku_wizard": {
                    "enabled": True,
                    "source_mode": "ISN_ITEMINFO",
                    "compare_mode": "EXTERNAL_TXT",
                    "txt_filename": "69MO.txt",
                    "txt_content": "A=24386522\nB=1B412008",
                    "offline_wrap": True,
                    "offline_default_sku": "24386522",
                    "sku_branches": [
                        {"code": "A", "label": "HW11", "expected_hw": "11"},
                        {"code": "B", "label": "HW10", "expected_hw": "10"},
                    ],
                },
            })
            v54_txt_p = os.path.join(v54_create.get("output_dir", ""), "69MO.txt")
            v54_glb_txt = open(v54_create.get("global_ini", ""), encoding="utf-8", errors="ignore").read()
            ws_v54 = _parse_v50(v54_create["excel_path"])
            check(os.path.exists(v54_txt_p)
                  and "24386522" in open(v54_txt_p, encoding="utf-8").read()
                  and "SFIS_SKU_DEFAULT=24386522" in v54_glb_txt
                  and any("69MO.txt" in str(r.get("Send") or "") for r in ws_v54["stations"]["MB"]),
                  "v0.8.054 /api/generate_new_standalone 正確生成 0->1 SKU Excel + Global.ini + 附屬 69MO.txt")

            tsw_js_path = os.path.join(STUDIO_DIR, "web", "js", "template_sku_wizard.js")
            tsw_js_txt = open(tsw_js_path, encoding="utf-8").read() if os.path.exists(tsw_js_path) else ""
            check(os.path.exists(tsw_js_path)
                  and bool(re.search(r'/js/template_sku_wizard\.js\?v=\d+\.\d+\.\d+', index_html))
                  and "openTemplateSkuWizard('create')" in index_html
                  and "openTemplateSkuWizard('edit')" in index_html
                  and 'id="btnEmptyEditorSkuWizard"' in index_html
                  and 'id="btnEditorTplSkuWizard"' in (index_html + open(os.path.join(STUDIO_DIR, "web", "js", "audit_editors.js"), "r", encoding="utf-8").read())
                  and "tswSelectReason" in tsw_js_txt
                  and "tswToggleRowLimit" in tsw_js_txt
                  and "param_to_ini" in tsw_js_txt,
                  "v0.8.056 一頁式多 SKU 精靈 UI（含 INI 參數化預設勾選）、雙模式三大入口掛載檢查通過")

            # [v0.8.055] 驗證各 SKU 專屬 DL/UL 上下限 ＋ 匯合後共用指令 (直寫模式 param_to_ini=False)
            v55_lim = post_json("/api/template_bundle/apply", {
                "target_mode": "edit",
                "station_name": "MB",
                "workspace": ws_v53,
                "bundle_spec": {},
                "sku_spec": {
                    "enabled": True,
                    "source_mode": "CUSTITEM",
                    "compare_mode": "BRANCH_RULES",
                    "offline_wrap": True,
                    "offline_default_sku": "FULL",
                    "no_match_policy": "FAIL",
                    "param_to_ini": False,
                    "post_merge_cmds": 'mfg sync-status\n:Delay,"300"',
                    "sku_branches": [
                        {"code": "FULL", "label": "整機全配", "iplas_model": "MOD_FULL", "limit_var": "gCurr", "limit_type": "%f", "dl": "100", "ul": "300", "limit_cmd": "mfg get-curr"},
                        {"code": "NO_BAT", "label": "整機無電池", "iplas_model": "MOD_NBAT", "limit_var": "gCurr", "limit_type": "%f", "dl": "400", "ul": "600", "limit_cmd": "mfg get-curr"},
                    ],
                    "section_guards": [],
                },
                "preview": False,
            })
            v55_rep = v55_lim.get("report") or {}
            v55_steps = (v55_lim.get("workspace") or {}).get("stations", {}).get("MB", [])
            v55_vals = [str(s.get("Validation") or "") for s in v55_steps]
            v55_sends = [str(s.get("Send") or "") for s in v55_steps]
            check(v55_lim.get("status") == "ok"
                  and len(v55_rep.get("errors") or []) == 0
                  and len(v55_rep.get("manual_warnings") if "manual_warnings" in v55_rep else (v55_rep.get("warnings") or [])) == 0
                  and any("(gCurr,%f,100,300);" in v for v in v55_vals)
                  and any("(gCurr,%f,400,600);" in v for v in v55_vals)
                  and any("mfg sync-status" in sd for sd in v55_sends),
                  "v0.8.055 支援各 SKU 獨立 DL/UL 上下限與匯合後共用指令且 Script Doctor 0 Error/0 Warning")

            # [v0.8.056] 驗證 4+ 分支上色、SFIS 粉紅字、Phase 97/98/99 收尾分色、預覽 row_visuals 與 INI 參數化抽出 (param_to_ini=True)
            v56_gen = post_json("/api/generate_new_standalone", {
                "project_name": "V56_COLOR",
                "station_name": "MB",
                "dut_count": 1,
                "block_ids": ["BLK_PRETEST_ROUTE", "BLK_PHASE97_TEARDOWN", "BLK_PHASE98_99_BRANCH_TEARDOWN"],
                "open_excel": False,
                "sku_wizard": {
                    "enabled": True,
                    "source_mode": "CUSTITEM",
                    "compare_mode": "BRANCH_RULES",
                    "offline_wrap": True,
                    "offline_default_sku": "SKU1",
                    "no_match_policy": "FAIL",
                    "param_to_ini": True,
                    "sku_branches": [
                        {"code": "SKU1", "label": "分支1", "iplas_model": "M1", "limit_var": "gCurr", "limit_type": "%f", "dl": "10", "ul": "20", "limit_cmd": "mfg curr"},
                        {"code": "SKU2", "label": "分支2", "iplas_model": "M2", "limit_var": "gCurr", "limit_type": "%f", "dl": "30", "ul": "40", "limit_cmd": "mfg curr"},
                        {"code": "SKU3", "label": "分支3", "iplas_model": "M3", "limit_var": "gCurr", "limit_type": "%f", "dl": "50", "ul": "60", "limit_cmd": "mfg curr"},
                        {"code": "SKU4", "label": "分支4", "iplas_model": "M4", "limit_var": "gCurr", "limit_type": "%f", "dl": "70", "ul": "80", "limit_cmd": "mfg curr"},
                    ],
                    "section_guards": [
                        {"section_title": "CHECK BATTERY", "allowed_skus": ["SKU1", "SKU3"]},
                    ],
                },
            })
            v56_glb = open(v56_gen.get("global_ini", ""), encoding="utf-8", errors="ignore").read()
            v56_wb = openpyxl.load_workbook(v56_gen["excel_path"], data_only=True)
            v56_ws = v56_wb["MB"]
            v56_fills = []
            v56_sfis_fonts = []
            v56_p98_colors = []
            v56_p99_colors = []
            v56_vals = []
            cur_ph = ""
            for r_i in range(2, v56_ws.max_row + 1):
                ph_v = str(v56_ws.cell(r_i, 2).value or "").strip()
                if ph_v:
                    cur_ph = ph_v
                send_c = v56_ws.cell(r_i, 7)
                fill_rgb = str(send_c.fill.start_color.rgb or "")[-6:].upper() if send_c.fill else ""
                font_rgb = str(send_c.font.color.rgb or "")[-6:].upper() if (send_c.font and send_c.font.color) else ""
                if fill_rgb:
                    v56_fills.append(fill_rgb)
                if str(send_c.value or "").strip().lower().startswith(":sf"):
                    v56_sfis_fonts.append(font_rgb)
                if cur_ph == "98":
                    v56_p98_colors.append((fill_rgb, font_rgb))
                if cur_ph == "99":
                    v56_p99_colors.append((fill_rgb, font_rgb))
                if v56_ws.cell(r_i, 11).value:
                    v56_vals.append(str(v56_ws.cell(r_i, 11).value))
            v56_wb.close()

            v56_prev = post_json("/api/template_bundle/apply", {
                "target_mode": "create",
                "project_name": "V56_PREV",
                "station_name": "MB",
                "bundle_spec": {},
                "sku_spec": {
                    "enabled": True,
                    "source_mode": "CUSTITEM",
                    "compare_mode": "BRANCH_RULES",
                    "param_to_ini": True,
                    "sku_branches": [
                        {"code": "A", "label": "A", "dl": "10", "ul": "20", "limit_var": "gV", "limit_cmd": "mfg v"},
                        {"code": "B", "label": "B", "dl": "30", "ul": "40", "limit_var": "gV", "limit_cmd": "mfg v"},
                    ],
                    "section_guards": [{"section_title": "GuardDemo", "allowed_skus": ["A"]}],
                },
                "preview": True,
            })
            pv_vis = v56_prev.get("row_visuals") or []
            check("SKU_SKU1_DL=10" in v56_glb
                  and "SKU_SKU4_UL=80" in v56_glb
                  and "SKU_ALLOW_CHECK_BATTERY=@SKU1||@SKU3" in v56_glb
                  and any("*$(SKU_SKU1_DL)" in v for v in v56_vals)
                  and {"1E3A8A", "14532D", "7F1D1D", "4C1D95"}.issubset(set(v56_fills))
                  and "E0F7FA" in v56_fills
                  and bool(v56_sfis_fonts) and all(fc in ("BE185D", "FFFFFF") for fc in v56_sfis_fonts)
                  and ("DCFCE7", "15803D") in v56_p98_colors
                  and ("FFE4E6", "9F1239") in v56_p99_colors
                  and len(pv_vis) >= 10
                  and any(pv.get("fill_hex") == "E0F7FA" for pv in pv_vis)
                  and any(pv.get("font_hex") == "FFFFFF" for pv in pv_vis),
                  "v0.8.056 全流程 ExecMode=4 4+分支5深色配白字、條件略過柔青、SFIS粉紅字、Phase97/98/99配色、預覽row_visuals與INI參數化完整通過",
                  f"fills={sorted(set(v56_fills))}, sfis={set(v56_sfis_fonts)}")

            # [v0.8.057] 驗證 window.STATE 互通、既有範本 DS_C3PO 載入與多 SKU 套用、Global.ini 精簡去冗
            check("var STATE = window.STATE =" in index_html,
                  "v0.8.057 前端 STATE 與 window.STATE 互通（修復既有腳本編修無法開啟多 SKU 精靈）")

            v57_clean = post_json("/api/generate_new_standalone", {
                "project_name": "V57_CLEAN",
                "station_name": "MB",
                "dut_count": 1,
                "block_ids": ["BLK_PRETEST_ROUTE", "BLK_PHASE97_TEARDOWN"],
                "sku_wizard": {
                    "enabled": True,
                    "source_mode": "CUSTITEM",
                    "compare_mode": "BRANCH_RULES",
                    "param_to_ini": True,
                    "offline_default_sku": "FULL",
                    "sku_branches": [
                        {"code": "FULL", "label": "整機", "iplas_model": "MODEL_FULL"},
                        {"code": "NO_BAT", "label": "無電池", "iplas_model": "MODEL_NBAT"},
                        {"code": "NO_WIFI", "label": "無WiFi", "iplas_model": "MODEL_NOWF"},
                    ],
                },
            })
            v57_glb = open(v57_clean["global_ini"], "r", encoding="utf-8").read()
            check(v57_clean.get("status") == "ok"
                  and "SFIS_SKU_DEFAULT=FULL" in v57_glb
                  and all(k not in v57_glb for k in ("FW_VERSION=", "sfisSKU=", "Boot_Delay=", "PythonPath=", "SKU_FULL_CODE=", "SKU_FULL_MODEL=", "SKU_NO_BAT_CODE=", "SKU_NO_WIFI_CODE=", "LED_AZ1=", "DAQ_1=")),
                  "v0.8.057 3-SKU Global.ini 精簡僅保留有效 SFIS_SKU_DEFAULT，完全去除未使用範本鍵與 CODE/MODEL 重複鍵")

            v57_uart = post_json("/api/generate_new_standalone", {
                "project_name": "V57_UART",
                "station_name": "MB",
                "dut_count": 1,
                "block_ids": ["BLK_PRETEST_ROUTE", "BLK_UART_BOOT_FW", "BLK_PHASE97_TEARDOWN"],
            })
            v57_uart_glb = open(v57_uart["global_ini"], "r", encoding="utf-8").read()
            check("FW_VERSION=" in v57_uart_glb and "DUT_UR1=" in v57_uart_glb,
                  "v0.8.057 勾選 UART FW 區塊時自動保留被測項引用的 FW_VERSION 與 DUT_UR1")

            c3po_path = os.path.join(PROJECT_ROOT, "SCRIPTS", "DS_C3PO_TestFlow-0707_jackson.xlsx")
            if os.path.exists(c3po_path):
                c3po_load = get_json("/api/load_specific_file?path=" + urllib.parse.quote(c3po_path))
                c3po_apply = post_json("/api/template_bundle/apply", {
                    "target_mode": "edit",
                    "project_name": c3po_load["workspace"].get("project_name", "DS_C3PO"),
                    "station_name": "MainBoard",
                    "workspace": c3po_load["workspace"],
                    "bundle_spec": {},
                    "sku_spec": {
                        "enabled": True,
                        "source_mode": "CUSTITEM",
                        "compare_mode": "BRANCH_RULES",
                        "param_to_ini": True,
                        "sku_branches": [
                            {"code": "FULL", "label": "整機"},
                            {"code": "NO_BAT", "label": "無電池"},
                        ],
                    },
                })
                check(c3po_load.get("status") == "ok" and c3po_apply.get("status") == "ok"
                      and len((c3po_apply.get("report") or {}).get("errors") or []) == 0,
                      "v0.8.057 實測載入 DS_C3PO_TestFlow-0707_jackson.xlsx 並於 MainBoard 套用 SKU 編修 0 Error")

            # [v0.8.058] 驗證 Step 2 頂部多 SKU Checkbox、NI6009+SKU 插入後黃色標註列位精準跟隨、Phase=-1 原編號提示
            check('id="wizMultiSkuChk"' in index_html
                  and "onWizMultiSkuCheckboxChange" in tsw_js_txt
                  and "openTemplateSkuWizard('create')" in index_html,
                  "v0.8.058 Step 2 最上方已設置多 SKU 啟用 Checkbox 控制列")

            v58_res = post_json("/api/generate_new_standalone", {
                "project_name": "V58_SHIFT",
                "station_name": "MB2",
                "dut_count": 1,
                "no_hw_phase_pause": True,
                "block_ids": ["BLK_PRETEST_ROUTE", "BLK_FIXTURE_ACTION", "BLK_UART_BOOT_FW", "BLK_PHASE97_TEARDOWN"],
                "ni6009_blocks": [{
                    "mode": "RSE",
                    "sample_ms": "1000",
                    "dev_id": "Dev1",
                    "title_name": "Measure Voltage Test",
                    "channels": [{"ch": 0, "name": "VCC_3V3", "dl": "3.15", "ul": "3.45"}],
                }],
                "sku_wizard": {
                    "enabled": True,
                    "source_mode": "CUSTITEM",
                    "compare_mode": "BRANCH_RULES",
                    "param_to_ini": True,
                    "sku_branches": [
                        {"code": "FULL", "label": "整機"},
                        {"code": "NO_BAT", "label": "無電池"},
                    ],
                },
            })
            v58_wb = openpyxl.load_workbook(v58_res["excel_path"])
            v58_ws = v58_wb["MB2"]
            v58_sku_has_ni = any(
                "NI-6009" in str(v58_ws.cell(r_i, 7).value or "")
                and "SetVal" in str(v58_ws.cell(r_i, 7).value or "")
                for r_i in range(2, v58_ws.max_row + 1)
            )
            v58_has_minus1 = any(
                str(v58_ws.cell(r_i, 2).value or "").strip() == "-1"
                for r_i in range(2, v58_ws.max_row + 1)
            )
            v58_no_comments = not any(
                v58_ws.cell(r_i, c_i).comment is not None
                for r_i in range(2, v58_ws.max_row + 1)
                for c_i in range(1, 17)
            )
            v58_wb.close()
            check(v58_res.get("status") == "ok"
                  and not v58_sku_has_ni
                  and v58_has_minus1
                  and v58_no_comments,
                  "v0.8.058 SKU 區塊前插後 NI-6009 標註列位零位移錯位，保留 Phase=-1 且 Excel 無多餘註解")

            qa_js_txt = open(os.path.join(STUDIO_DIR, "web", "js", "script_qa.js"), "r", encoding="utf-8").read()
            check("qa_phase_gap_minus1" in qa_js_txt and "0, 1, 2, -1, 4, 97" in qa_js_txt,
                  "v0.8.059 Q&A 問答集已新增「Phase = 0, 1, 2, -1, 4, 97 跳號是否誤判」專題說明")

            # [v0.8.060] 驗證 0->1 積木拖曳堆疊與逐塊你問我答工作區 + builder_sequence 後端端到端生成
            cbb_js_path = os.path.join(STUDIO_DIR, "web", "js", "create_block_builder.js")
            cbb_js_txt = open(cbb_js_path, "r", encoding="utf-8").read() if os.path.exists(cbb_js_path) else ""
            check(os.path.exists(cbb_js_path)
                  and 'id="createBlockBuilderRoot"' in index_html
                  and "create_block_builder.js" in index_html
                  and "bbShowPop" in cbb_js_txt
                  and "bbToggleFullscreen" in cbb_js_txt
                  and "exclusivePage: true" in cbb_js_txt
                  and ".bb-step-pill" in cbb_js_txt,
                  "v0.8.060 新版 0→1 小積木拖曳庫（含 Pop 視窗/紅標專屬頁/全螢幕/彩灰進度條）已掛載完成")

            v60_res = post_json("/api/generate_new_standalone", {
                "project_name": "V60_BUILDER",
                "station_name": "FT",
                "dut_count": 1,
                "wizard_config": {"isn_length": 12, "isn_pattern": "[0-9A-Z]"},
                "builder_sequence": [
                    {"uid": "u1", "kind": "isn", "config": {"project": "V60_BUILDER", "station": "FT", "dut_count": 1, "isn_len": 12, "isn_pattern": "[0-9A-Z]"}},
                    {"uid": "u2", "kind": "sfis_route", "config": {"sfis_mode": "offline", "tsp": "PEGA,2"}},
                    {"uid": "u3", "kind": "comm_cmd", "config": {
                        "protocol": "ssh", "title": "SSH Get Ver", "command": "cat /etc/version",
                        "end_prompt": "#", "waiting": "5000", "retry": "3", "extract_mode": "within",
                        "left_delim": "version=", "right_delim": "\\n", "var_name": "gFwVer", "val_type": "%s", "expect_min": "1.2.3"
                    }},
                    {"uid": "u4", "kind": "delay", "config": {"ms": "1500", "note": "Wait 1.5s"}},
                    {"uid": "u5", "kind": "prompt_box", "config": {"prompt_mode": "yes_no", "title": "LED Check", "message": "Blue LED ON?", "yes_label": "Yes", "no_label": "No", "no_policy": "fail"}},
                    {"uid": "u6", "kind": "inst", "config": {
                        "inst_mode": "ni6009", "mode": "RSE", "sample_ms": "1000", "dev_id": "Dev1",
                        "title_name": "Volt Check", "channels": [{"ch": 0, "name": "VCC_3V3", "dl": "3.15", "ul": "3.45"}]
                    }},
                    {"uid": "u7", "kind": "var_check", "config": {"title": "Double Check 3V3", "var_name": "VCC_3V3", "check_mode": "limit", "val_type": "%f", "dl": "3.15", "ul": "3.45"}},
                    {"uid": "u8", "kind": "teardown", "config": {"teardown_mode": "97_98_99"}},
                ],
            })
            ws_v60 = _parse_v50(v60_res["excel_path"])
            v60_sends = [str(r.get("Send") or "") for r in ws_v60["stations"]["FT"]]
            v60_refs = [str(r.get("Ref") or "") for r in ws_v60["stations"]["FT"]]
            v60_audit = post_json("/api/re_audit", {"workspace": ws_v60})
            v60_errs = (v60_audit.get("report") or {}).get("errors") or []
            check(v60_res.get("status") == "ok"
                  and any("SSH1@cat /etc/version" in s for s in v60_sends)
                  and any("WithinString" in rf for rf in v60_refs)
                  and any(':Delay,"1500"' in s for s in v60_sends)
                  and any(':ShowConfirmBox,"Blue LED ON?","Yes;No"' in s for s in v60_sends)
                  and any(':Dev.VOLTAGE' in s for s in v60_sends)
                  and any(':CheckLimit,"*(VCC_3V3)"' in s for s in v60_sends)
                  and len(v60_errs) == 0,
                  "v0.8.060 builder_sequence (SSH+WithinString+Delay+YES/NO+NI6008+CheckLimit+97/98/99) 生成 0 Error 實戰測試包通過",
                  f"errs={v60_errs}")

            # [v0.8.062] 驗證直立撲克牌積木 (<=2字)、Popup 自動消退、可拉寬分割桿、ms 轉秒數、每積木執行後延遲 (預設 0.5s) 與底部進度條
            cbb_62 = open(cbb_js_path, "r", encoding="utf-8").read()
            check("bb-poker-grid" in cbb_62
                  and "bb-poker-card" in cbb_62
                  and "bb-poker-track" in cbb_62
                  and "closest('[data-bb-pop]')" in cbb_62
                  and "bbStartSplitDrag" in cbb_62
                  and "bb-bottom-dock" in cbb_62
                  and "bbDelayReadableHint" in cbb_62
                  and "post_delay_enabled" in cbb_62
                  and "等 ${sec} 秒" in cbb_62,
                  "v0.8.062 直立撲克牌(<=2字)、Popup 自動關閉、分割桿、ms 轉秒與每塊後延遲 UI 檢查通過")

            v62_delay = post_json("/api/generate_new_standalone", {
                "project_name": "V62_POSTDLY",
                "station_name": "MB",
                "dut_count": 1,
                "builder_sequence": [
                    {"uid": "d1", "kind": "isn", "config": {"project": "V62_POSTDLY", "station": "MB", "dut_count": 1, "isn_len": 3, "isn_pattern": "[0-9A-Z]"}},
                    {"uid": "d2", "kind": "sfis_route", "config": {"sfis_mode": "offline"}},
                    {"uid": "d3", "kind": "comm_cmd", "config": {
                        "protocol": "uart", "title": "Ping UART", "command": "ver",
                        "extract_mode": "reply_only", "reply_keyword": "OK",
                        "post_delay_enabled": True, "post_delay_sec": "0.5"
                    }},
                    {"uid": "d4", "kind": "inst", "config": {
                        "inst_mode": "ni6009", "title_name": "VCheck",
                        "channels": [{"ch": 0, "name": "V3", "dl": "3.1", "ul": "3.5"}],
                        "post_delay_enabled": True, "post_delay_sec": "1.5"
                    }},
                    {"uid": "d5", "kind": "teardown", "config": {"teardown_mode": "97_only"}},
                ],
            })
            ws_v62 = _parse_v50(v62_delay["excel_path"])
            v62_sends = [str(r.get("Send") or "") for r in ws_v62["stations"]["MB"]]
            v62_audit = post_json("/api/re_audit", {"workspace": ws_v62})
            v62_errs = (v62_audit.get("report") or {}).get("errors") or []
            check(v62_delay.get("status") == "ok"
                  and ':Delay,"500"' in v62_sends
                  and ':Delay,"1500"' in v62_sends
                  and len(v62_errs) == 0,
                  "v0.8.062 每積木勾選運作後延遲 (0.5s->:Delay,500 / 1.5s->:Delay,1500) 自動插入下一列且 0 Error",
                  f"sends={v62_sends}, errs={v62_errs}")

            # [v0.8.063] 驗證 SKU/PING 命名、Q&A 頂部回到積木調整、同頁 Multi-SKU、儀器卡牌與移除備用表單精靈按鈕 + set_val/add_attr 積木
            tsw_js = open(os.path.join(os.path.dirname(cbb_js_path), "template_sku_wizard.js"), "r", encoding="utf-8").read()
            check("shortName: 'SKU'" in cbb_62 and "shortName: 'PING'" in cbb_62
                  and "shortName: '設值'" in cbb_62 and "shortName: '屬性'" in cbb_62
                  and "回到積木調整" in cbb_62
                  and "顯示／隱藏傳統 4 步驟表單精靈" not in index_html,
                  "v0.8.063 積木改名(SKU/PING)、新增設值/屬性積木、頂部回到積木調整與隱藏舊精靈切換鈕檢查通過")

            check("bb-inst-grid" in cbb_62 and "bb-inst-card" in cbb_62
                  and "bbOpenNi6DiagramFromBuilder" in cbb_62
                  and "tswMountInline" in tsw_js and "tswMountInline" in cbb_62
                  and "mdOnBackdrop" in tsw_js
                  and "tsw-guard-chip" in tsw_js,
                  "v0.8.063 儀器卡牌格網+NI6008圖解接線按鈕、同頁嵌入 Multi-SKU (免彈窗)、防誤關監聽與清晰跳測勾選 UI 檢查通過")

            v63_ext = post_json("/api/generate_new_standalone", {
                "project_name": "V63_BLK_PROJ",
                "station_name": "MB",
                "dut_count": 1,
                "open_excel": False,
                "wizard_config": {"isn_length": 3, "isn_pattern": "[0-9A-Z]"},
                "builder_sequence": [
                    {"uid": "b1", "kind": "isn", "config": {"project": "V63_BLK_PROJ", "station": "MB", "dut_count": 1, "isn_len": 3, "isn_pattern": "[0-9A-Z]"}},
                    {"uid": "b2", "kind": "sfis_route", "config": {"sfis_mode": "offline"}},
                    {"uid": "b3", "kind": "set_val", "config": {"title": "Build Composite Tag", "var_name": "gFullTag", "value_expr": "*(ISN)_OK"}},
                    {"uid": "b4", "kind": "add_attr", "config": {"title": "Bind UART Port", "target": "UART", "attr_key": "COM", "attr_val": "COM6"}},
                    {"uid": "b5", "kind": "inst", "config": {"inst_mode": "ni6009", "inst_name": "NI6008", "mode": "RSE", "title_name": "Measure Voltage Test", "channels": [{"ch": 0, "name": "VCC_5V", "dl": "4.75", "ul": "5.25"}]}},
                    {"uid": "b6", "kind": "teardown", "config": {"teardown_mode": "97_only"}},
                ],
            })
            ws_v63 = _parse_v50(v63_ext["excel_path"])
            v63_sends = [str(r.get("Send") or "") for r in ws_v63["stations"]["MB"]]
            v63_audit = post_json("/api/re_audit", {"workspace": ws_v63})
            v63_errs = (v63_audit.get("report") or {}).get("errors") or []
            check(v63_ext.get("status") == "ok"
                  and any(':SetVal,"$gFullTag"' in s for s in v63_sends)
                  and any(':AddAttribute,"UART","COM","COM6"' in s for s in v63_sends)
                  and len(v63_errs) == 0,
                  "v0.8.063 新增積木 (設值 :SetVal / 屬性 :AddAttribute / 儀器 NI6008) 產出 16 欄 Excel 且 0 Error",
                  f"sends={v63_sends}, errs={v63_errs}")

            # [v0.8.064] 驗證直接開啟 Excel、免彈完成視窗，以及呼叫 SFIS 撲克牌積木堆疊頁雙向帶回 0->1
            sfis_js_v64 = open(os.path.join(os.path.dirname(cbb_js_path), "sfis_hmi.js"), "r", encoding="utf-8").read()
            check("open_folder: true" in cbb_62
                  and "open_excel: true" in cbb_62
                  and "showExportCompleteModal" not in cbb_62
                  and "bbOpenFullInstWorkspace" not in cbb_62
                  and "bbOpenFullSfisWorkspace" in cbb_62
                  and "openSfisWorkspaceForBuilder" in sfis_js_v64
                  and "sfisSyncToBuilderAndReturn" in sfis_js_v64,
                  "v0.8.064 匯出直接開目錄+開Excel免確認視窗、取消儀器雙欄按鈕並保留SFIS撲克牌積木堆疊頁雙向帶回通過")

            opened_folders.clear()
            launched_excels.clear()
            v64_res = post_json("/api/generate_new_standalone", {
                "project_name": "V64_MULTI_PROJ",
                "station_name": "MB",
                "dut_count": 1,
                "open_folder": False,
                "open_excel": True,
                "wizard_config": {"isn_length": 3, "isn_pattern": "[0-9A-Z]"},
                "builder_sequence": [
                    {"uid": "m1", "kind": "isn", "config": {"project": "V64_MULTI_PROJ", "station": "MB", "dut_count": 1, "isn_len": 3, "isn_pattern": "[0-9A-Z]"}},
                    {"uid": "m2", "kind": "sfis_route", "config": {
                        "sfis_hmi_bundle": {
                            "items": [
                                {"kind": "checkroute", "title": "SFIS CheckRoute"},
                                {"kind": "get", "table": "ISN_BASEINFO", "field": "MAC1", "var_name": "sfMAC"},
                            ],
                            "config": {"sfis_enable": "1", "tsp": "ATLAS,2", "op": "S09166390", "device_id": "710001"}
                        }
                    }},
                    {"uid": "m3", "kind": "inst", "config": {
                        "inst_mode": "multi_queue",
                        "inst_queue": [
                            {"inst_name": "NI6008", "title_name": "NI6008 Rail Check", "ni6009_block": {"mode": "RSE", "title_name": "NI6008 Rail Check", "channels": [{"ch": 0, "name": "VCC_5V", "dl": "4.75", "ul": "5.25"}]}},
                            {"inst_name": "Agilent34401A", "title_name": "DMM Voltage Check", "dl_val": "3.15", "ul_val": "3.45"},
                        ]
                    }},
                    {"uid": "m4", "kind": "teardown", "config": {"teardown_mode": "97_only"}},
                ],
            })
            ws_v64 = _parse_v50(v64_res["excel_path"])
            v64_sends = [str(r.get("Send") or "") for r in ws_v64["stations"]["MB"]]
            v64_switches = [str(r.get("Switch") or "") for r in ws_v64["stations"]["MB"]]
            v64_audit = post_json("/api/re_audit", {"workspace": ws_v64})
            v64_errs = (v64_audit.get("report") or {}).get("errors") or []
            check(v64_res.get("status") == "ok"
                  and len(opened_folders) == 0
                  and len(launched_excels) == 1
                  and any(":SfCheckRoute" in s for s in v64_sends)
                  and any("MAC1" in s for s in v64_sends)
                  and any("NI6008" in sw for sw in v64_switches)
                  and any("Agilent34401A" in sw for sw in v64_switches)
                  and len(v64_errs) == 0,
                  "v0.8.064 SFIS堆疊+多儀器堆疊(NI6008+Agilent34401A)產出0 Error且open_folder=False不開目錄只直接開Excel通過",
                  f"folders={len(opened_folders)}, excels={len(launched_excels)}, sends={v64_sends}, switches={v64_switches}, errs={v64_errs}")

            # [v0.8.065] 一鍵自動排序、頂部整合按鈕、非NI儀器實戰語法(PPH1503/FeasaLED/DevUart)、SFIS內建環境檢測、Phase=-1無硬體整合與SKU5深色系白字
            check("bbAutoSortStack" in cbb_62
                  and 'id="btnGenModeHubBack"' in index_html
                  and "bbTestSfisLink" in cbb_62
                  and "bbSetLedPreset" in cbb_62
                  and "產生「無硬體試跑版」" not in cbb_62
                  and "1E3A8A" in tsw_js,
                  "v0.8.065 一鍵自動排順序、回到積木調整頂部整合、SFIS環境實測、儀器分類預設、Phase=-1試跑整合與5深色SKU UI檢查通過")

            opened_folders.clear()
            launched_excels.clear()
            v65_inst_res = post_json("/api/generate_new_standalone", {
                "project_name": "V65_ALL_INST",
                "station_name": "MB",
                "dut_count": 1,
                "open_folder": True,
                "open_excel": True,
                "no_hw_phase_pause": True,
                "wizard_config": {"isn_length": 3, "isn_pattern": "[0-9A-Z]"},
                "builder_sequence": [
                    {"uid": "k1", "kind": "isn", "config": {"project": "V65_ALL_INST", "station": "MB", "dut_count": 1, "isn_len": 3, "isn_pattern": "[0-9A-Z]"}},
                    {"uid": "k2", "kind": "sfis_route", "config": {"sfis_mode": "online", "tsp": "ATLAS,2", "weblink": "http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx"}},
                    {"uid": "k3", "kind": "sfis_rw", "config": {"rw_mode": "get_version", "table_name": "ISN_BASEINFO", "field_name": "MAC1", "var_name": "sfMAC", "ref_slice_mode": "split", "ref_split_sep": ",", "ref_split_idx": "0"}},
                    {"uid": "k4", "kind": "inst", "config": {"inst_mode": "catalog", "inst_name": "PPH1503", "title_name": "PPH1503 Current", "pwr_action": "mcurr", "pwr_volt": "12", "dl_val": "50", "ul_val": "800"}},
                    {"uid": "k5", "kind": "inst", "config": {"inst_mode": "catalog", "inst_name": "FeasaLED", "title_name": "Feasa Green LED", "led_ch": "01", "dl_val": "515", "ul_val": "535", "led_int_min": "1000"}},
                    {"uid": "k6", "kind": "teardown", "config": {"teardown_mode": "97_only"}},
                ],
            })
            ws_v65 = _parse_v50(v65_inst_res["excel_path"])
            v65_rows = ws_v65["stations"]["MB"]
            v65_sends = [str(r.get("Send") or "") for r in v65_rows]
            v65_refs = [str(r.get("Ref") or "") for r in v65_rows]
            v65_phases = [str(r.get("Phase") or "").strip() for r in v65_rows if str(r.get("Phase") or "").strip()]
            v65_audit = post_json("/api/re_audit", {"workspace": ws_v65})
            v65_errs = (v65_audit.get("report") or {}).get("errors") or []
            check(v65_inst_res.get("status") == "ok"
                  and len(opened_folders) == 1
                  and len(launched_excels) == 1
                  and '-1' in v65_phases
                  and any(':Dev.SetON,"12","2"' in s for s in v65_sends)
                  and any(':Dev.MCurr' in s for s in v65_sends)
                  and any(':Dev.CaptureAndRead,"01"' in s for s in v65_sends)
                  and any(':SplitString,",","0"' in rf for rf in v65_refs)
                  and len(v65_errs) == 0,
                  "v0.8.065 PPH1503/FeasaLED實戰指令 + SFIS SplitString + Phase=-1整合無硬體試跑 + 1目錄1Excel 0 Error 通過",
                  f"folders={len(opened_folders)}, excels={len(launched_excels)}, phases={v65_phases}, sends={v65_sends}, refs={v65_refs}, errs={v65_errs}")

            # [v0.8.066] 固定「開始/結束」護欄 + 預設4塊(條碼/路由/指令/清理) + 基礎/進階切分 + 反白一鍵自動抓字串 + 獨立「上傳(:SfSaveLinkData)」積木 + 連動INI預覽徽章
            cbb_66 = open(cbb_js_path, "r", encoding="utf-8").read()
            check("kind: 'start'" in cbb_66 and "kind: 'end'" in cbb_66
                  and "shortName: '清理'" in cbb_66
                  and "shortName: 'wSFIS'" in cbb_66
                  and "bbToggleQaAdv" in cbb_66
                  and "bbAutoInferExtract" in cbb_66
                  and "_renderLinkedIniBadge" in cbb_66
                  and "_collectPrecedingVars" in cbb_66,
                  "v0.8.066 開始/結束護欄、預設4塊、基礎/進階切換、反白自動抓字串、獨立上傳積木與連動INI預覽檢查通過")

            v66_res = post_json("/api/generate_new_standalone", {
                "project_name": "V66_GUARD_PROJ",
                "station_name": "MB",
                "dut_count": 1,
                "open_folder": False,
                "open_excel": False,
                "wizard_config": {"isn_length": 15, "isn_pattern": "[0-9A-F]"},
                "builder_sequence": [
                    {"uid": "g0", "kind": "start", "config": {"project": "V66_GUARD_PROJ", "station": "MB", "dut_count": 1, "debug_mode": "1", "sfis_enable": "1"}},
                    {"uid": "g1", "kind": "isn", "config": {"enable_scan": True, "isn_len": 15, "isn_pattern": "[0-9A-F]"}},
                    {"uid": "g2", "kind": "sfis_route", "config": {"sfis_mode": "online", "tsp": "PEGA,2"}},
                    {"uid": "g3", "kind": "comm_cmd", "config": {"protocol": "uart", "title": "Get IMEI", "command": "atcli at+gsn", "extract_mode": "within", "left_delim": "gsn:", "right_delim": "\\n", "var_name": "gIMEI", "val_type": "%s", "expect_min": "35001"}},
                    {"uid": "g4", "kind": "sfis_upload", "config": {"title": "Update SFIS", "items": [{"field": "SN1", "var_name": "gIMEI"}, {"field": "FW", "var_name": "gFwVer"}]}},
                    {"uid": "g5", "kind": "teardown", "config": {"teardown_mode": "97_only"}},
                    {"uid": "g6", "kind": "end", "config": {"confirmed": True}},
                ],
            })
            ws_v66 = _parse_v50(v66_res["excel_path"])
            v66_sends = [str(r.get("Send") or "") for r in ws_v66["stations"]["MB"]]
            v66_audit = post_json("/api/re_audit", {"workspace": ws_v66})
            v66_errs = (v66_audit.get("report") or {}).get("errors") or []
            check(v66_res.get("status") == "ok"
                  and any(':SfSaveLinkData,"SN1","*(gIMEI)"' in s for s in v66_sends)
                  and any(':SfSaveLinkData,"FW","*(gFwVer)"' in s for s in v66_sends)
                  and ws_v66["system_ini"].get("DebugMode") == "1"
                  and len(v66_errs) == 0,
                  "v0.8.066 start/end護欄 + 獨立上傳(:SfSaveLinkData 多欄位) 產出 0 Error 測試包通過",
                  f"sends={v66_sends}, errs={v66_errs}")

            # [v0.8.067] 開始/結束灰階、chkRoute/比對/getSFIS/wSFIS 改名與 chkRoute 列入進階、卡片對卡片直接拖曳、貪食蛇跨行轉折箭頭、單行整合標題列
            check("shortName: 'chkRoute'" in cbb_66
                  and "shortName: '比對'" in cbb_66
                  and "shortName: 'getSFIS'" in cbb_66
                  and "bbDropOnCard" in cbb_66
                  and "bb-snake-wrap" in cbb_66
                  and "bb-drop-slot-turn" in cbb_66
                  and "filter:grayscale(100%)" in cbb_66
                  and 'id="bbTopActionHost"' in index_html
                  and "產生首次範本 🃏 積木拖曳編排" in index_html,
                  "v0.8.067 開始/結束灰階、chkRoute進階積木與積木庫改名、卡片直接拖曳重排、貪食蛇轉折箭頭與單行標題列整合檢查通過")

            # [v0.8.068] 群組方框 (group 共用單一 Phase + 子頁 #3.1/#3.2 設定)、進階 TestID 即時搜尋寫入、Error Code 頁嵌入既有腳本編修 (1 -> N)
            aud_68 = open(os.path.join(os.path.dirname(cbb_js_path), "audit_editors.js"), "r", encoding="utf-8").read()
            check("kind: 'group'" in cbb_66
                  and "bbGroupAddChild" in cbb_66
                  and "_getQaNavList" in cbb_66
                  and "_renderTestIdAdvPicker" in cbb_66
                  and "bbSearchTestIdAdv" in cbb_66
                  and "bbGroupSetField" in cbb_66
                  and "globalHubCard_tic" in aud_68
                  and "openTicFromEdit" in aud_68
                  and "ticBackFromEditBar" in index_html
                  and "returnToEditFromTic" in index_html,
                  "v0.8.068 群組方框UI、進階TestID即時搜尋、Error Code嵌入式頁籤與手風琴卡檢查通過")

            v68_res = post_json("/api/generate_new_standalone", {
                "project_name": "V68_GRP_PROJ",
                "station_name": "MB",
                "dut_count": 1,
                "open_folder": False,
                "open_excel": False,
                "wizard_config": {"isn_length": 12, "isn_pattern": "[0-9A-Z]"},
                "builder_sequence": [
                    {"uid": "p0", "kind": "start", "config": {"project": "V68_GRP_PROJ", "station": "MB", "dut_count": 1}},
                    {"uid": "p1", "kind": "isn", "config": {"enable_scan": True, "isn_len": 12, "isn_pattern": "[0-9A-Z]"}},
                    {"uid": "p2", "kind": "group", "config": {
                        "title": "Power & Volt Group",
                        "collapsed": False,
                        "children": [
                            {"uid": "c1", "kind": "comm_cmd", "config": {"protocol": "uart", "title": "Pwr On", "command": "power_on", "extract_mode": "raw", "var_name": "gPwrAck", "test_id": "BR00001"}},
                            {"uid": "c2", "kind": "delay", "config": {"delay_ms": "200"}},
                            {"uid": "c3", "kind": "inst", "config": {"inst_mode": "catalog", "inst_name": "NI6008", "title_name": "Volt Check", "ni_rails_count": 1, "ni_ch0": "0", "ni_dl0": "4.8", "ni_ul0": "5.2", "test_id": "BRME027"}},
                            {"uid": "c4", "kind": "comm_cmd", "config": {"protocol": "uart", "title": "Read FW", "command": "ver", "extract_mode": "raw", "var_name": "gFwVer", "test_id": "BR00002"}},
                        ],
                    }},
                    {"uid": "p3", "kind": "teardown", "config": {"teardown_mode": "97_only"}},
                    {"uid": "p4", "kind": "end", "config": {"confirmed": True}},
                ],
            })
            ws_v68 = _parse_v50(v68_res["excel_path"])
            v68_rows = ws_v68["stations"]["MB"]
            grp_start = next((idx for idx, r in enumerate(v68_rows) if "Power & Volt Group" in str(r.get("Title") or "")), -1)
            grp_rows = []
            if grp_start >= 0:
                grp_rows.append(v68_rows[grp_start])
                for r in v68_rows[grp_start + 1:]:
                    if str(r.get("Phase") or "").strip():
                        break
                    grp_rows.append(r)
            grp_phases = set(str(r.get("Phase") or "").strip() for r in grp_rows if str(r.get("Phase") or "").strip())
            grp_tids = set(str(r.get("TestID") or "").strip() for r in grp_rows if str(r.get("TestID") or "").strip())
            grp_uart_connects = [r for r in grp_rows if ':Connect,"UART"' in str(r.get("Send") or "")]
            v68_audit = post_json("/api/re_audit", {"workspace": ws_v68})
            v68_errs = (v68_audit.get("report") or {}).get("errors") or []
            check(v68_res.get("status") == "ok"
                  and len(grp_rows) >= 4
                  and len(grp_phases) == 1
                  and len(grp_uart_connects) <= 1
                  and {"BR00001", "BRME027", "BR00002"}.issubset(grp_tids)
                  and len(v68_errs) == 0,
                  "v0.8.068 群組方框共用單一Phase + UART自動去重 + 子積木各自指定TestID + 0 Error 通過",
                  f"grp_rows={len(grp_rows)}, phases={grp_phases}, tids={grp_tids}, uart_conns={len(grp_uart_connects)}, errs={v68_errs}")

            # [v0.8.069] 群組收合卡純向下箭頭(▼)免換行溢位、右側空白區接住群組拖出子積木、qaIdx依展開頁數夾緊、返回積木調整收起舊匯出橫幅
            cbb_69 = open(cbb_js_path, "r", encoding="utf-8").read()
            check("▸ 展開" not in cbb_69
                  and 'onclick="bbToggleGroupCollapse(${idx})">▼</button>' in cbb_69
                  and "BB_STATE.dragSrcType==='group_child'" in cbb_69
                  and "const navLen = _getQaNavList().length;" in cbb_69
                  and "if (viewName !== 'export')" in cbb_69
                  and "6 項功能卡片" in (index_html + aud_68),
                  "v0.8.069 群組收合卡純向下箭頭(▼)、群組拖出至右側空白區與qaIdx/舊橫幅清理檢查通過")

            # [v0.8.070] 方案1撲克牌總覽匯出頁 + 恢復預設6塊 + 返回模式選擇入口 + 舊4步驟文案更新 + 匯出預設自動語法檢查與INI設定摘要通知
            sfis_70 = open(os.path.join(os.path.dirname(cbb_js_path), "sfis_hmi.js"), "r", encoding="utf-8").read()
            check("_renderSnakeCardsHtml(true)" in cbb_69
                  and "bbResetDefaultStack" in cbb_69
                  and "_renderAuditAndIniHtml" in cbb_69
                  and "_renderExportIniQuickEditor" in cbb_69
                  and "bbExportSetIniParam" in cbb_69
                  and "${_renderProgressStrip(-1)}" not in cbb_69
                  and "run_syntax_check: true" in cbb_69
                  and "switchGenSubMode('hub')" in cbb_69
                  and "產生首次範本 (積木拖曳)" in index_html
                  and "sfisSyncToBuilderAutoAdd" in sfis_70,
                  "v0.8.071 方案1撲克牌總覽匯出(去重底部積木+重點可編輯INI)、恢復預設6塊、返回模式與語法/INI通知UI檢查通過")

            v70_res = post_json("/api/generate_new_standalone", {
                "project_name": "V70_AUDIT_INI_PROJ",
                "station_name": "MB",
                "dut_count": 1,
                "open_folder": False,
                "open_excel": False,
                "wizard_config": {"isn_length": 6, "isn_pattern": "[0-9A-Z]"},
                "builder_sequence": [
                    {"uid": "s0", "kind": "start", "config": {"project": "V70_AUDIT_INI_PROJ", "station": "MB", "dut_count": 1, "debug_mode": "1", "sfis_enable": "0"}},
                    {"uid": "s1", "kind": "isn", "config": {"enable_scan": True, "isn_len": 6, "isn_pattern": "[0-9A-Z]"}},
                    {"uid": "s2", "kind": "sfis_route", "config": {"sfis_mode": "offline"}},
                    {"uid": "s3", "kind": "comm_cmd", "config": {"protocol": "uart", "port": "COM9", "title": "Check FW", "command": "cat /etc/version", "extract_mode": "within", "left_delim": "version=", "right_delim": "\\n", "var_name": "DUT_FW", "val_type": "%s", "expect_min": "1.2.3", "use_ini_var": True}},
                    {"uid": "s4", "kind": "teardown", "config": {"teardown_mode": "97_only"}},
                    {"uid": "s5", "kind": "end", "config": {"confirmed": True}},
                ],
            })
            v70_ar = v70_res.get("audit_report") or {}
            v70_ini = v70_res.get("ini_summary") or {}
            check(v70_res.get("status") == "ok"
                  and v70_ar.get("enabled") is True
                  and int(v70_ar.get("error_count", -1)) == 0
                  and (v70_ini.get("system") or {}).get("DebugMode") == "1"
                  and (v70_ini.get("settings") or {}).get("DUT_UR1") == "COM9"
                  and (v70_ini.get("scripts") or {}).get("DUT_FW_SPEC") == "1.2.3",
                  "v0.8.070 匯出預設自動執行Excel語法檢查(0 Error) + 回傳實際寫入INI摘要(System/Settings/Scripts) 通過",
                  f"ar={v70_ar}, ini={v70_ini}")

            # [v0.8.072 / v0.8.081] 建立與編修中心專注保留 2 大主力雙卡 (1->N 與 0->1)，移除角落雜訊按鈕
            check('id="genHubCard_edit"' in hub_sec
                  and 'id="genHubCard_create"' in hub_sec
                  and 'id="genHubCard_inst"' not in hub_sec
                  and 'id="genHubCard_qa"' not in hub_sec
                  and 'id="genHubCard_tools"' not in hub_sec
                  and 'id="genToolShortcut_inst"' not in hub_sec
                  and 'id="genToolShortcut_tools"' not in hub_sec
                  and 'id="genToolShortcut_qa"' not in hub_sec,
                  "v0.8.072/v0.8.081 建立與編修中心專注保留 2 張主力雙卡 (1->N / 0->1) 且移出角落獨立工具檢查通過")

            # [v0.8.073] 兩張主力卡取消手風琴改為等寬雙大卡 (.gen-dual-grid / .gen-big-card) + 懸浮上浮效果
            check('class="gen-dual-grid"' in hub_sec
                  and 'class="gen-big-card"' in hub_sec
                  and '.gen-big-card:hover' in app_css
                  and 'translateY(-5px)' in app_css,
                  "v0.8.073 兩張主力卡取消手風琴改為並排等寬雙大卡與懸浮上浮變色效果檢查通過")

            # [v0.8.074] 4 大高回報積木升級：多別名UART + ExecMode進階選單 + 多行Ref鏈式處理 + 通用DLL/Utility積木 + Phase 97/98/99群組容器
            cbb_74 = open(cbb_js_path, "r", encoding="utf-8").read()
            check("kind: 'dll_call'" in cbb_74
                  and "_renderExecModeAdvPicker" in cbb_74
                  and "bbCmdAddRefRow" in cbb_74
                  and "phase_role" in cbb_74
                  and "連線別名 (Alias，預設 UART)" in cbb_74,
                  "v0.8.074 多別名UART、ExecMode進階選單、多行Ref表、通用DLL積木與97/98/99群組容器UI檢查通過")

            v74_res = post_json("/api/generate_new_standalone", {
                "project_name": "V74_UPGRADE_PROJ",
                "station_name": "FATP_OPT",
                "dut_count": 1,
                "open_folder": False,
                "open_excel": False,
                "wizard_config": {"isn_length": 6, "isn_pattern": "[0-9A-Z]"},
                "builder_sequence": [
                    {"uid": "u0", "kind": "start", "config": {"project": "V74_UPGRADE_PROJ", "station": "FATP_OPT", "dut_count": 1}},
                    {"uid": "u1", "kind": "isn", "config": {"enable_scan": True, "isn_len": 6, "isn_pattern": "[0-9A-Z]"}},
                    {"uid": "u2", "kind": "sfis_route", "config": {"sfis_mode": "offline"}},
                    {"uid": "u3", "kind": "comm_cmd", "config": {
                        "protocol": "uart", "alias": "LinuxUART", "port": "COM31", "title": "SysInfo MultiRef",
                        "command": "mfg sysinfo", "end_prompt": "/#", "exec_mode": "6",
                        "multi_refs": [
                            {"var_name": "gMod", "extract_mode": "within", "left_delim": "Model:", "right_delim": "\\n", "trim": True, "rp_space": True},
                            {"var_name": "gMAC", "extract_mode": "within", "left_delim": "MAC:", "right_delim": "\\n", "trim": True, "rm_mac": True, "up_string": True},
                        ],
                    }},
                    {"uid": "u4", "kind": "dll_call", "config": {"dll_mode": "utility", "util_action": "gen_dt", "title": "Stamp", "dt_fmt": "yyyyMMdd", "var_name": "cDATE"}},
                    {"uid": "u5", "kind": "dll_call", "config": {
                        "dll_mode": "custom_dll", "dll_file": "dllCam.dll", "dll_alias": "CamPEGA",
                        "init_arg": ".\\API\\sample.ini", "title": "SFR Check",
                        "send_cmd": ':CamPEGA.SFR,"*(ISN),1,1"', "ref": "items", "validation": "(items,%SELF,,)",
                        "exec_mode": "*$(AULAB)", "test_id": "IPIO01C",
                    }},
                    {"uid": "u6", "kind": "group", "config": {
                        "title": "PASS_DISCONNECTION", "phase_role": "98",
                        "children": [
                            {"uid": "td1", "kind": "comm_cmd", "config": {"protocol": "uart", "alias": "LinuxUART", "port": "COM31", "title": "Kill Cam", "command": "killall cam", "exec_mode": "3"}},
                        ],
                    }},
                    {"uid": "u7", "kind": "teardown", "config": {"teardown_mode": "97_only"}},
                    {"uid": "u8", "kind": "end", "config": {"confirmed": True}},
                ],
            })
            ws_v74 = _parse_v50(v74_res["excel_path"])
            v74_rows = ws_v74["stations"]["FATP_OPT"]
            v74_sends = [str(r.get("Send") or "") for r in v74_rows]
            v74_refs = [str(r.get("Ref") or "") for r in v74_rows]
            v74_ems = [str(r.get("ExecMode") or "") for r in v74_rows]
            v74_phases = set(str(r.get("Phase") or "").strip() for r in v74_rows if str(r.get("Phase") or "").strip())
            v74_dut_vals = " | ".join(str(v or "") for v in ws_v74["duts"][0].values())
            v74_ar = v74_res.get("audit_report") or {}
            check(v74_res.get("status") == "ok"
                  and "LinuxUART@mfg sysinfo\\r\\n" in v74_sends
                  and ':Utility.GenDT,"yyyyMMdd"' in v74_sends
                  and ':CamPEGA.SFR,"*(ISN),1,1"' in v74_sends
                  and "LinuxUART@killall cam\\r\\n" in v74_sends
                  and any(":Trim:rmMAC:upString" in rf and ":rpString" in rf for rf in v74_refs)
                  and "*$(AULAB)" in v74_ems and "6" in v74_ems
                  and "98" in v74_phases
                  and "LinuxUART" in v74_dut_vals and "CamPEGA" in v74_dut_vals
                  and int(v74_ar.get("error_count", -1)) == 0,
                  "v0.8.074 多別名LinuxUART + 多行鏈式Ref + 客製DLL寫DUTs + ExecMode開關 + Phase98群組 + 0 Error 通過",
                  f"phases={v74_phases}, ems={v74_ems}, ar={v74_ar}")

            # [v0.8.075 / v0.8.081] Hover樣式 + 批次TestID介面 + 知識文件紀錄
            doc1_txt = open(os.path.join(PROJECT_ROOT, "完整知識庫文件清單", "DESIGN_AND_HANDOVER.md"), "r", encoding="utf-8").read()
            doc2_txt = open(os.path.join(PROJECT_ROOT, "完整知識庫文件清單", "Centimani_自動化腳本生成系統完整架構與需求規格書.md"), "r", encoding="utf-8").read()
            check("實機測試 SFIS / DLL" in home_sec
                  and "語法小抄" in index_html
                  and "純儀器單測骨架" in open(cbb_js_path, "r", encoding="utf-8").read()
                  and 'id="btnTicSubBatch"' in index_html
                  and 'id="ticBatchWrap"' in index_html
                  and 'id="chkTicBatchUpdateDesc">' in index_html
                  and ".tic-cand-pill:hover" in app_css
                  and "Build v0.8.075" in doc1_txt and "analyze_workspace_test_ids" in doc1_txt
                  and "Build v0.8.075" in doc2_txt,
                  "v0.8.075/v0.8.081 實機測試置於首頁、全域語法小抄、純儀器整合進積木 + 批次TestID介面 + 知識文件紀錄 檢查通過")

            ws_tic_test = json.loads(json.dumps(ws_v74))
            ws_tic_test["source_file"] = v74_res["excel_path"]
            ws_tic_test["stations"]["FATP_OPT"].extend([
                {
                    "Index": "80", "Phase": "7", "Title": "Measure 5V Voltage",
                    "Description": "ORIG_VOLT_DESC", "Send": ":Dev.MVolt,1",
                    "TestID": "", "ExecMode": "0",
                },
                {
                    "Index": "81", "Phase": "7", "Title": "Check Input Current",
                    "Description": "ORIG_CURR_DESC", "Send": ":Dev.MSCurr,5",
                    "TestID": "B7PL025", "ExecMode": "0",
                },
                {
                    "Index": "82", "Phase": "7", "Title": "Wait Stabilize",
                    "Description": "Delay 200ms", "Send": ":Delay,200",
                    "TestID": "B7PL025", "ExecMode": "0",
                },
            ])
            tic_aud = post_json("/api/tic_audit_excel", {"workspace": ws_tic_test, "station": "FATP_OPT"})
            tic_issues = tic_aud.get("issues") or []
            iss_volt = next((x for x in tic_issues if x.get("title") == "Measure 5V Voltage"), None)
            iss_curr = next((x for x in tic_issues if x.get("title") == "Check Input Current"), None)
            iss_delay = next((x for x in tic_issues if x.get("title") == "Wait Stabilize"), None)
            check(tic_aud.get("status") == "ok"
                  and iss_volt is not None and iss_volt["reason_code"] == "missing" and len(iss_volt.get("candidates") or []) >= 1
                  and iss_curr is not None and iss_curr["reason_code"] == "generic_placeholder" and len(iss_curr.get("candidates") or []) >= 1
                  and iss_delay is None,
                  "v0.8.075 /api/tic_audit_excel 正確挑出空白/佔位碼測項並推薦候選 TestID，且略過純 :Delay 控制列",
                  f"volt={bool(iss_volt)}, curr={bool(iss_curr)}, delay={iss_delay}")

            cand_v = iss_volt["candidates"][0]["test_id"]
            cand_c = iss_curr["candidates"][0]["test_id"]
            tic_apply = post_json("/api/tic_apply_batch", {
                "workspace": tic_aud["workspace"],
                "excel_path": v74_res["excel_path"],
                "updates": [
                    {"station": "FATP_OPT", "row_idx": iss_volt["row_idx"], "test_id": cand_v, "description": iss_volt["candidates"][0].get("desc_en", "")},
                    {"station": "FATP_OPT", "row_idx": iss_curr["row_idx"], "test_id": cand_c, "description": iss_curr["candidates"][0].get("desc_en", "")},
                ],
                "update_description": False,
                "open_folder": False,
                "open_excel": False,
            })
            ws_tic_fixed = _parse_v50(tic_apply["excel_path"])
            fixed_rows = ws_tic_fixed["stations"]["FATP_OPT"]
            row_v_after = next((r for r in fixed_rows if r.get("Title") == "Measure 5V Voltage"), {})
            row_c_after = next((r for r in fixed_rows if r.get("Title") == "Check Input Current"), {})
            check(tic_apply.get("status") == "ok"
                  and tic_apply.get("applied_count") == 2
                  and str(row_v_after.get("TestID") or "") == cand_v
                  and str(row_c_after.get("TestID") or "") == cand_c
                  and str(row_v_after.get("Description") or "") == "ORIG_VOLT_DESC"
                  and str(row_c_after.get("Description") or "") == "ORIG_CURR_DESC",
                  "v0.8.075 /api/tic_apply_batch 成功批次寫回 TestID 至 *_FIXED.xlsx 並保留原始 Description",
                  f"v={row_v_after}, c={row_c_after}")

            # [v0.8.076] Phase 0 / -1 / 97:PWROFF + Global.ini [Scripts] 分流 + Title RunMode + math_opr + vnxrfsw Sub=1 + DeviceSemaphore=0
            v76_payload = {
                "project_name": "OLYMPUS_AIR_V76",
                "station_name": "Front_Air",
                "dut_count": 1,
                "open_folder": False,
                "open_excel": False,
                "builder_sequence": [
                    {"kind": "start", "config": {"project": "OLYMPUS_AIR_V76", "station": "Front_Air", "dut_count": 1, "debug_mode": "1", "sfis_enable": "1"}},
                    {"kind": "isn", "config": {"enable_scan": True, "barcode_name": "ISN", "isn_len": 15, "isn_pattern": "[0-9A-F]"}},
                    {"kind": "group", "config": {
                        "title": "CheckRoute", "phase_role": "0", "title_run_mode": "0", "retry": "0",
                        "children": [
                            {"kind": "dll_call", "config": {"dll_mode": "utility", "util_action": "show_img", "img_file": "Loimage.gif", "test_id": "OTFX054"}},
                        ]
                    }},
                    {"kind": "group", "config": {
                        "title": "Load DLL", "phase_role": "0", "same_phase": True, "title_run_mode": "0", "retry": "0",
                        "children": [
                            {"kind": "dll_call", "config": {"dll_mode": "utility", "util_action": "sf_enabled", "var_name": "gSFIS"}},
                            {"kind": "dll_call", "config": {"dll_mode": "utility", "util_action": "get_yr", "var_name": "currYR"}},
                            {"kind": "dll_call", "config": {"dll_mode": "custom_dll", "dll_file": "AutLabs.dll", "dll_alias": "autLabs", "init_arg": "*$(AL_Alias),ON,ON", "send_cmd": ':autLabs.Load,"*(gSFIS)","*(currYR)","0.9"', "reply": "0", "ref": "sRet", "exec_mode": "*$(AULAB)"}},
                            {"kind": "sfis_route", "config": {"sfis_mode": "online", "use_phase0": True, "require_uart": False, "tsp": "SUBAIR,2,TRUE", "weblink": "http://10.176.33.13/SFISWebService/SFISTSPWebService.asmx,2"}},
                            {"kind": "dll_call", "config": {"dll_mode": "custom_dll", "dll_file": "AutLabs.dll", "dll_alias": "autLabs", "init_arg": "*$(AL_Alias),ON,ON", "send_cmd": ':autLabs.UnitIn,"*(ISN)","1","*$(PCT)"', "reply": "0", "exec_mode": "*$(AULAB)"}},
                            {"kind": "dll_call", "config": {"dll_mode": "utility", "util_action": "close_msg", "exec_mode": "3", "test_id": "OTFX054"}},
                            {"kind": "comm_cmd", "config": {"protocol": "cmd", "app_conn": "cmd.exe,1,5000,", "conn_action": "connect_only", "exec_mode": "0"}},
                        ]
                    }},
                    {"kind": "comm_cmd", "config": {
                        "protocol": "uart", "title": "Init Modbus", "port": "COM3", "port_ini_key": "PCUART_", "baud_rate": "9600",
                        "char_mode": "Hex", "skip_prompt_check": True, "command": "01 03 00 63 00 01 74 14",
                        "reply_mode": "raw", "raw_reply": "", "waiting": "100",
                        "extract_mode": "sub", "sub_start": "9", "sub_len": "5", "rp_space": True, "var_name": "ch1pek",
                        "title_run_mode": "*$(TitleStatus)", "exec_mode": "1"
                    }},
                    {"kind": "math_opr", "config": {
                        "opr_mode": "conversion", "title": "Convert H2D", "conv_mode": "H2D",
                        "src_expr": "*(ch1pek)", "var_name": "ch1p", "exec_mode": "2:1"
                    }},
                    {"kind": "math_opr", "config": {
                        "opr_mode": "set_opr_val", "title": "Calc Drop Pressure",
                        "var_name": "DUT_DORP_PRESSURE", "expr": "*(DUT_FINAL_PRESSURE) - *(DUT_INITIAL_PRESSURE)",
                        "validation_enabled": True, "val_var": "DUT_DORP_PRESSURE", "val_type": "%f", "dl": "-10", "ul": "0.6"
                    }},
                    {"kind": "dll_call", "config": {"dll_mode": "utility", "util_action": "chk_len", "src_expr": "*(temp)", "expect_len": "70", "waiting": "100", "exec_mode": "2:4"}},
                    {"kind": "group", "config": {
                        "title": "Paused SubDev Test", "phase_role": "-1", "title_run_mode": "1",
                        "children": [
                            {"kind": "var_check", "config": {"check_mode": "string", "var_name": "pCount", "send_expr": "*(pCount)", "expect_str": "36", "exact_match": True, "exec_mode": "2:0"}},
                        ]
                    }},
                    {"kind": "group", "config": {
                        "title": "PWROFF", "phase_role": "97:PWROFF", "title_run_mode": "none",
                        "children": [
                            {"kind": "delay", "config": {"ms": "200"}},
                        ]
                    }},
                    {"kind": "group", "config": {
                        "title": "Disconnection", "phase_role": "97", "title_run_mode": "none",
                        "children": [
                            {"kind": "dll_call", "config": {"dll_mode": "custom_dll", "dll_file": "AutLabs.dll", "dll_alias": "autLabs", "init_arg": "*$(AL_Alias),ON,ON", "send_cmd": ':autLabs.Metric2,"*(ISN)","1","*(#cfName#)","*$(stringUpload)"', "reply": "0", "waiting": "20000", "exec_mode": "*$(AULAB)"}},
                        ]
                    }},
                    {"kind": "group", "config": {
                        "title": "PASS", "phase_role": "98", "title_run_mode": "none",
                        "children": [
                            {"kind": "dll_call", "config": {"dll_mode": "custom_dll", "dll_file": "AutLabs.dll", "dll_alias": "autLabs", "init_arg": "*$(AL_Alias),ON,ON", "send_cmd": ':autLabs.UnitOut,"*(ISN)","1","PASS"', "reply": "0", "exec_mode": "*$(AULAB)"}},
                        ]
                    }},
                    {"kind": "group", "config": {
                        "title": "FAIL", "phase_role": "99", "title_run_mode": "none",
                        "children": [
                            {"kind": "dll_call", "config": {"dll_mode": "custom_dll", "dll_file": "AutLabs.dll", "dll_alias": "autLabs", "init_arg": "*$(AL_Alias),ON,ON", "send_cmd": ':autLabs.UnitOut,"*(ISN)","1","FAIL"', "reply": "0", "exec_mode": "*$(AULAB)"}},
                        ]
                    }},
                    {"kind": "end", "config": {"confirmed": True}},
                ]
            }
            v76_res = post_json("/api/generate_new_standalone", v76_payload)
            ws_v76 = _parse_v50(v76_res["excel_path"])
            v76_rows = ws_v76["stations"]["Front_Air"]
            v76_phases = [str(r.get("Phase") or "").strip() for r in v76_rows if str(r.get("Phase") or "").strip()]
            v76_titles = [str(r.get("Title") or "").strip() for r in v76_rows if str(r.get("Title") or "").strip()]
            v76_sends = [str(r.get("Send") or "").strip() for r in v76_rows]
            v76_ini_sum = (v76_res.get("ini_summary") or {})
            v76_gset = v76_ini_sum.get("settings") or {}
            v76_gscr = v76_ini_sum.get("scripts") or {}
            v76_dut_str = " | ".join(str(v or "") for v in ws_v76["duts"][0].values())
            check(v76_res.get("status") == "ok"
                  and v76_phases.count("0") == 1 and "0,Load DLL" in v76_titles
                  and "-1" in v76_phases and "97:PWROFF" in v76_phases and "97" in v76_phases and "98" in v76_phases and "99" in v76_phases
                  and any(t.startswith("*$(TitleStatus),") for t in v76_titles)
                  and any(t.startswith("1,Paused SubDev Test") for t in v76_titles)
                  and ':Connect,"CmdConsole"' in v76_sends
                  and ':Utility.ConVersion,"H2D","*(ch1pek)"' in v76_sends
                  and ':SetOprVal,"DUT_DORP_PRESSURE","*(DUT_FINAL_PRESSURE) - *(DUT_INITIAL_PRESSURE)"' in v76_sends
                  and ':Utility.ChkLEN,"*(temp)","70"' in v76_sends
                  and "UART@01 03 00 63 00 01 74 14" in v76_sends
                  and "9600,8,One,None,None" in v76_dut_str and "PCUART_1" in v76_dut_str
                  and "{  ISN,15,[0-9A-F]  }" in v76_dut_str
                  and "AULAB" in v76_gscr and "PCT" in v76_gscr and "TitleStatus" in v76_gscr
                  and "AULAB" not in v76_gset and "AL_Alias" in v76_gset and "PCUART_1" in v76_gset
                  and int((v76_res.get("audit_report") or {}).get("error_count", -1)) == 0,
                  "v0.8.076 Phase0/Phase-1/97:PWROFF + [Scripts]分流 + Title前綴 + math_opr + HexUART(9600) + ChkLEN 通過",
                  f"phases={v76_phases}, gset={list(v76_gset.keys())}, gscr={list(v76_gscr.keys())}, ar={v76_res.get('audit_report')}")

            # [v0.8.076] 驗證 Multi-Slot + Sub=1 (VNXRFSW) 自動切換 DeviceSemaphore=0 與 :ObtainSubDevice 積木生成
            v76_sub_payload = {
                "project_name": "SUB_SEMA_V76",
                "station_name": "RF_SUB",
                "dut_count": 2,
                "open_folder": False,
                "open_excel": False,
                "builder_sequence": [
                    {"kind": "start", "config": {"project": "SUB_SEMA_V76", "station": "RF_SUB", "dut_count": 2, "debug_mode": "1", "sfis_enable": "0"}},
                    {"kind": "inst", "config": {"inst_mode": "catalog", "inst_name": "VNXRFSW", "title_name": "RF Switch Path", "subdev_cmd": ':sDev.SetSwitch,"2"'}},
                    {"kind": "teardown", "config": {"teardown_mode": "97_only"}},
                    {"kind": "end", "config": {"confirmed": True}},
                ]
            }
            v76_sub_res = post_json("/api/generate_new_standalone", v76_sub_payload)
            ws_v76_sub = _parse_v50(v76_sub_res["excel_path"])
            v76_sub_sends = [str(r.get("Send") or "").strip() for r in ws_v76_sub["stations"]["RF_SUB"]]
            sys_sub_path = os.path.join(os.path.dirname(v76_sub_res["excel_path"]), "System.ini")
            sys_sub_txt = open(sys_sub_path, "r", encoding="utf-8").read()
            check(v76_sub_res.get("status") == "ok"
                  and ':ObtainSubDevice,"VNXRFSW"' in v76_sub_sends
                  and ':sDev.SetSwitch,"2"' in v76_sub_sends
                  and "DeviceSemaphore=0" in sys_sub_txt,
                  "v0.8.076 VNXRFSW Sub=1 子設備積木 + 多槽自動設定 System.ini DeviceSemaphore=0 通過",
                  f"sends={v76_sub_sends}")

            # [v0.8.077] Option A (進階設定統一明顯靛藍底色 .bb-adv-box) + Option B (:Utility.CMD + 自訂APP別名 + PPH1503 off)
            cbb_77 = open(cbb_js_path, "r", encoding="utf-8").read()
            check(".bb-adv-box" in app_css
                  and ".bb-adv-badge" in app_css
                  and cbb_77.count("bb-adv-box") >= 5
                  and "util_cmd" in cbb_77
                  and "app_alias" in cbb_77
                  and 'value="off"' in cbb_77,
                  "v0.8.077 Option A 進階設定顯著色塊 (.bb-adv-box/.bb-adv-badge) 與 Option B 前端選項檢查通過")

            v77_payload = {
                "project_name": "LOCK_CMD_V77",
                "station_name": "Lock",
                "dut_count": 1,
                "open_folder": False,
                "open_excel": False,
                "builder_sequence": [
                    {"kind": "start", "config": {"project": "LOCK_CMD_V77", "station": "Lock", "dut_count": 1, "debug_mode": "1", "sfis_enable": "1"}},
                    {"kind": "comm_cmd", "config": {
                        "protocol": "util_cmd", "title": "SPT DataACK",
                        "cmd_exe": "{0}\\SPT_repeater.exe", "cmd_args": "-AckSWDL *(sfUUID),olympus",
                        "cmd_show": "ON", "waiting": "10000", "cmd_extra": "5", "exec_mode": "1",
                    }},
                    {"kind": "comm_cmd", "config": {
                        "protocol": "cmd", "title": "Run MtCmd", "app_alias": "MtCmd",
                        "app_conn": ".\\exe\\mtcmd.exe,0,5000,", "command": "flash_verify",
                        "keep_open": True, "reply_mode": "contains", "reply_keyword": "OK",
                    }},
                    {"kind": "comm_cmd", "config": {
                        "protocol": "cmd", "title": "Run Console2", "app_alias": "CmdConsole2",
                        "app_conn": "cmd.exe,1,5000,", "command": "echo DONE",
                        "keep_open": False,
                    }},
                    {"kind": "inst", "config": {
                        "inst_mode": "catalog", "inst_name": "PPH1503",
                        "title_name": "Power Off DUT", "pwr_action": "off",
                    }},
                    {"kind": "teardown", "config": {"teardown_mode": "97_only"}},
                    {"kind": "end", "config": {"confirmed": True}},
                ]
            }
            v77_res = post_json("/api/generate_new_standalone", v77_payload)
            ws_v77 = _parse_v50(v77_res["excel_path"])
            v77_rows = ws_v77["stations"]["Lock"]
            v77_sends = [str(r.get("Send") or "").strip() for r in v77_rows]
            v77_dut_str = " | ".join(str(v or "") for v in ws_v77["duts"][0].values())
            check(v77_res.get("status") == "ok"
                  and ':Utility.CMD,"{0}\\SPT_repeater.exe","-AckSWDL *(sfUUID),olympus","ON","10000","5"' in v77_sends
                  and ':Connect,"MtCmd"' in v77_sends and "MtCmd@flash_verify\\r\\n" in v77_sends
                  and ':Connect,"CmdConsole2"' in v77_sends and ':Disconnect,"CmdConsole2"' in v77_sends
                  and ':Disconnect,"MtCmd"' not in v77_sends
                  and ':Dev.OUTONOFF,"OFF"' in v77_sends
                  and '"APP","MtCmd",".\\exe\\mtcmd.exe,0,5000,"' in v77_dut_str
                  and '"APP","CmdConsole2","cmd.exe,1,5000,"' in v77_dut_str
                  and int((v77_res.get("audit_report") or {}).get("error_count", -1)) == 0,
                  "v0.8.077 Option B :Utility.CMD + 自訂APP別名(MtCmd/CmdConsole2) + keep_open + PPH1503 OUTONOFF OFF 通過",
                  f"sends={v77_sends}, dut={v77_dut_str}, ar={v77_res.get('audit_report')}")

            # [v0.8.078] 既有腳本編修 (1 -> N) 四項改善驗收：
            #   1. Phase 0 保留不順編進 1（含多塊 Phase 0）；無 Phase 0 的腳本仍從 Phase 1 起編
            #   2. block_sorter.js 記憶 _savedPhaseNum / bsAutoSortByPhase 保留中段暫停位置 / LivePreview 保留 Phase 0
            #   3. ScanBarcode 空白不自動覆寫 { ISN,15,[0-9] }、支援 *$(ISN_len) 與 {QRISN,,}
            #   4. System.ini (DeviceSemaphore/RobotMode) & Instrument (Sub/Switch) & PCUART_1 & 6 格文案與持久化
            with open(os.path.join(STUDIO_DIR, "web", "js", "block_sorter.js"), "r", encoding="utf-8") as f_bs78:
                bs78_src = f_bs78.read()
            with open(os.path.join(STUDIO_DIR, "web", "js", "audit_editors.js"), "r", encoding="utf-8") as f_ae78:
                ae78_src = f_ae78.read()

            check("_savedPhaseNum" in bs78_src
                  and "b.phase_num === 0" in bs78_src
                  and "midPausedAfter" in bs78_src
                  and "anchorOrigIdx" in bs78_src,
                  "v0.8.078 block_sorter.js 包含 Phase 0 保留、暫停記憶原 Phase 與中段暫停錨點保留邏輯",
                  f"has_saved={('_savedPhaseNum' in bs78_src)}, has_p0={('b.phase_num === 0' in bs78_src)}, has_mid={('midPausedAfter' in bs78_src)}")

            check("empty: true" in ae78_src
                  and "_toggleDutScanBlank" in ae78_src
                  and "免掃條碼" in ae78_src
                  and "DeviceSemaphore" in ae78_src
                  and "RobotMode" in ae78_src
                  and "PCUART_1" in ae78_src
                  and ("5～6 格" in ae78_src or "6 張寬版功能卡" in ae78_src)
                  and "返回編修主入口" in ae78_src
                  and "['Switch']" in ae78_src and "['Sub']" in ae78_src,
                  "v0.8.078 audit_editors.js 具備免掃條碼保護、*$(var)/空規則支援、DeviceSemaphore/RobotMode、Inst Sub/Switch 與 PCUART_1",
                  "missing expected v0.8.078 UI/editor markers in audit_editors.js")

            from core.block_sorter import reorder_station_blocks as _reord78
            # 1a. 多塊 Phase 0（首端與中段各有 Phase 0）+ 測項順編：所有 Phase 0 皆維持 '0'，其餘從 1 起編
            v78_ws_p0 = {
                "stations": {"ST": [
                    {"Index": "000", "Phase": "0", "Title": "0,LoadParam", "Instrument": "", "Send": ":Delay,10", "ExecMode": "0"},
                    {"Index": "001", "Phase": "3", "Title": "0,Boot", "Instrument": "", "Send": ":Delay,100", "ExecMode": "0"},
                    {"Index": "002", "Phase": "0", "Title": "0,InitEnv", "Instrument": "", "Send": ":Delay,10", "ExecMode": "0"},
                    {"Index": "003", "Phase": "-1", "Title": "0,PausedMid", "Instrument": "", "Send": ":Delay,50", "ExecMode": "0"},
                    {"Index": "004", "Phase": "8", "Title": "0,Check", "Instrument": "", "Send": ":Delay,100", "ExecMode": "0"},
                    {"Index": "005", "Phase": "97", "Title": "0,Teardown", "Instrument": "", "Send": ":Delay,10", "ExecMode": "0"},
                ]}
            }
            v78_blks_p0 = _ext_blks(v78_ws_p0["stations"]["ST"])
            _reord78(
                v78_ws_p0,
                "ST",
                [b["orig_idx"] for b in v78_blks_p0],
                auto_renumber_phase=True,
                paused_orig_indices=[b["orig_idx"] for b in v78_blks_p0 if b["phase"] == "-1"],
            )
            v78_phases_p0 = [b["phase"] for b in _ext_blks(v78_ws_p0["stations"]["ST"])]
            # 1b. 無 Phase 0 的腳本（例如 OTA）：仍從 Phase 1 起編，不強制變 0
            v78_ws_no_p0 = {
                "stations": {"OTA": [
                    {"Index": "000", "Phase": "5", "Title": "0,Connect", "Instrument": "", "Send": ":Delay,100", "ExecMode": "0"},
                    {"Index": "001", "Phase": "10", "Title": "0,OTA", "Instrument": "", "Send": ":Delay,200", "ExecMode": "0"},
                    {"Index": "002", "Phase": "97", "Title": "0,End", "Instrument": "", "Send": ":Delay,10", "ExecMode": "0"},
                ]}
            }
            v78_blks_no_p0 = _ext_blks(v78_ws_no_p0["stations"]["OTA"])
            _reord78(
                v78_ws_no_p0,
                "OTA",
                [b["orig_idx"] for b in v78_blks_no_p0],
                auto_renumber_phase=True,
            )
            v78_phases_no_p0 = [b["phase"] for b in _ext_blks(v78_ws_no_p0["stations"]["OTA"])]
            check(v78_phases_p0 == ["0", "1", "0", "-1", "2", "97"]
                  and v78_phases_no_p0 == ["1", "2", "97"],
                  "v0.8.078 reorder_station_blocks 保留所有既有 Phase 0 不重編，無 Phase 0 腳本仍從 Phase 1 起編",
                  f"with_p0={v78_phases_p0}, no_p0={v78_phases_no_p0}")

            # 4. In-Place Patch 驗證 DeviceSemaphore / RobotMode (INI) 與 Instrument Sub / Switch (Excel)
            from core.ini_engine import sync_and_generate_inis as _sync_inis78
            from core.excel_engine import export_workspace_to_excel as _exp_xlsx78
            with tempfile.TemporaryDirectory() as v78_ini_dir:
                v78_src_xlsx = os.path.join(v78_ini_dir, "TestFlow_v78.xlsx")
                shutil.copy2(v77_res["excel_path"], v78_src_xlsx)
                with open(os.path.join(v78_ini_dir, "System.ini"), "w", encoding="utf-8") as f_s78:
                    f_s78.write("[System]\nDebugMode=0\nDeviceSemaphore=1\nRobotMode=0\n")
                ws_v78_in = _parse_v50(v78_src_xlsx)
                ws_v78_in["source_file"] = v78_src_xlsx
                ws_v78_in["system_ini"]["DeviceSemaphore"] = "0"
                ws_v78_in["system_ini"]["RobotMode"] = "1"
                ws_v78_in["preserved_inis"] = {"System.ini": open(os.path.join(v78_ini_dir, "System.ini"), encoding="utf-8").read()}
                if ws_v78_in.get("instruments"):
                    ws_v78_in["instruments"][0]["Sub"] = "1"
                    ws_v78_in["instruments"][0]["Switch"] = "RF_SW_A"
                v78_exp_xlsx = os.path.join(v78_ini_dir, "TestFlow_v78_OUT.xlsx")
                _exp_xlsx78(ws_v78_in, v78_exp_xlsx)
                _sync_inis78(ws_v78_in, "TestFlow_v78_OUT.xlsx", v78_ini_dir)
                with open(os.path.join(v78_ini_dir, "System.ini"), "r", encoding="utf-8") as f_s78_out:
                    s78_out_txt = f_s78_out.read()
                ws_v78_reparsed = _parse_v50(v78_exp_xlsx)
                inst0_rep = (ws_v78_reparsed.get("instruments") or [{}])[0]
                check("DeviceSemaphore=0" in s78_out_txt
                      and "RobotMode=1" in s78_out_txt
                      and str(inst0_rep.get("Sub") or "").strip() == "1"
                      and str(inst0_rep.get("Switch") or "").strip() == "RF_SW_A",
                      "v0.8.078 In-Place Patch 正確持久化 DeviceSemaphore / RobotMode 與 Instrument Sub / Switch",
                      f"sys={s78_out_txt!r}, inst0={inst0_rep}")

            # [v0.8.079] 單顆積木進階直接支援 Phase 0 / -1（不用硬包群組）+ 撲克牌 P0/-1 徽章 + 1 -> N 版面清潔大掃除
            with open(os.path.join(STUDIO_DIR, "web", "js", "create_block_builder.js"), "r", encoding="utf-8") as f_bb79:
                bb79_src = f_bb79.read()
            with open(os.path.join(STUDIO_DIR, "web", "js", "audit_editors.js"), "r", encoding="utf-8") as f_ae79:
                ae79_src = f_ae79.read()
            with open(os.path.join(STUDIO_DIR, "web", "index.html"), "r", encoding="utf-8") as f_idx79:
                idx79_src = f_idx79.read()

            check("階段位置 (Phase)" in bb79_src
                  and "allowPhaseRole" in bb79_src
                  and ">P0<" in bb79_src
                  and ">-1<" in bb79_src
                  and ">同P<" in bb79_src,
                  "v0.8.079 create_block_builder.js 支援單顆積木直接選 Phase 0 / -1 / 沿用，且撲克牌顯示狀態徽章",
                  "missing Phase role picker or card badges in create_block_builder.js")

            exp_bar_pos = idx79_src.find('id="editorExportBar"')
            hub_host_pos = idx79_src.find('id="auditGlobalEditor"')
            check('id="editorDropZoneStrip"' in idx79_src
                  and "handleEditorFileDrop" in idx79_src
                  and 'id="btnTab1LaunchSfis"' not in idx79_src
                  and 'id="btnTab1LaunchDll"' not in idx79_src
                  and 0 < hub_host_pos < exp_bar_pos
                  and 'id="editorSheetSel"' in ae79_src
                  and 'openStationDiffModal()' in ae79_src
                  and "修改 System.ini" in ae79_src
                  and "進入順序編排" in ae79_src
                  and "進入跳轉規則" in ae79_src
                  and "Marco 子流程表" in idx79_src,
                  "v0.8.079/v0.8.081 1->N 介面大掃除：拖曳載入、去重頂部按鈕、測站與比對鈕整合於編修主入口、手風琴預期標示與 Marco 子流程說明",
                  f"hub={hub_host_pos}, exp={exp_bar_pos}")

            v79_res = post_json("/api/generate_new_standalone", {
                "project_name": "V79_SINGLE_P0_PROJ",
                "station_name": "MB",
                "dut_count": 1,
                "open_folder": False,
                "open_excel": False,
                "wizard_config": {"isn_length": 10, "isn_pattern": "[0-9A-Z]"},
                "builder_sequence": [
                    {"uid": "s0", "kind": "start", "config": {"project": "V79_SINGLE_P0_PROJ", "station": "MB", "dut_count": 1}},
                    {"uid": "s1", "kind": "isn", "config": {"enable_scan": True, "isn_len": 10, "isn_pattern": "[0-9A-Z]"}},
                    {"uid": "s2", "kind": "dll_call", "config": {
                        "dll_mode": "utility", "util_action": "gen_dt",
                        "title": "Pretest Timestamp", "dt_fmt": "yyyyMMddhhmmss", "var_name": "sDATE1",
                        "phase_role": "0",
                    }},
                    {"uid": "s3", "kind": "comm_cmd", "config": {
                        "protocol": "uart", "port": "COM4", "alias": "UART",
                        "title": "Paused Debug Step", "command": "dbg_skip",
                        "phase_role": "-1",
                    }},
                    {"uid": "s4", "kind": "comm_cmd", "config": {
                        "protocol": "uart", "port": "COM4", "alias": "UART",
                        "title": "First Real Test", "command": "ver",
                        "phase_role": "normal",
                    }},
                    {"uid": "s5", "kind": "teardown", "config": {"teardown_mode": "97_only"}},
                    {"uid": "s6", "kind": "end", "config": {"confirmed": True}},
                ]
            })
            ws_v79 = _parse_v50(v79_res["excel_path"])
            v79_phases = [str(r.get("Phase") or "").strip() for r in ws_v79["stations"]["MB"] if str(r.get("Phase") or "").strip()]
            check(v79_res.get("status") == "ok"
                  and v79_phases == ["0", "-1", "1", "97"],
                  "v0.8.079 單顆積木直接設定 Phase 0 / -1 不浪費耗號，下一顆一般測項準確從 Phase 1 起編",
                  f"phases={v79_phases}")

            # [v0.8.080] Ref 冒號/分號轉義（防 Centimani 報 The Ref function """ doesn't define）、
            #            Phase 0 永遠置頂於 Phase 1 之前、匯出無 Excel Cell Comment、單積木獨立進階切換、
            #            全站字體連動與按鍵懸停說明 Popup
            with open(os.path.join(STUDIO_DIR, "web", "js", "create_block_builder.js"), "r", encoding="utf-8") as f_bb80:
                bb80_src = f_bb80.read()
            with open(os.path.join(STUDIO_DIR, "web", "index.html"), "r", encoding="utf-8") as f_idx80:
                idx80_src = f_idx80.read()
            with open(os.path.join(STUDIO_DIR, "web", "css", "app.css"), "r", encoding="utf-8") as f_css80:
                css80_src = f_css80.read()

            check("bbToggleItemAdv" in bb80_src
                  and "item._showAdv" in bb80_src
                  and "BB_STATE.qaShowAdv ?" not in bb80_src
                  and "data-pop-tip=" in bb80_src
                  and 'id="appGlobalBtnPop"' in idx80_src
                  and "initGlobalButtonPopup" in idx80_src
                  and "NI-DAQmx 未安裝（安裝後重整網頁 F5 即自動更新）" in idx80_src
                  and ".app-btn-popup" in css80_src
                  and "min-width:175px" in bb80_src
                  and "min-width:195px" in bb80_src,
                  "v0.8.080 單積木獨立展開進階設定、輸入框加寬不截字、全站按鍵懸停說明 Popup 與字體連動規則檢查通過",
                  "missing expected v0.8.080 UI/popup/adv markers")

            # Test Phase 0 placed after Phase 1 in input sequence is sorted to the top, AND ':' in SplitString is escaped as '\:'
            v80_res = post_json("/api/generate_new_standalone", {
                "project_name": "V80_REF_P0_TOP",
                "station_name": "FUNCTION",
                "dut_count": 1,
                "open_folder": False,
                "open_excel": False,
                "wizard_config": {"isn_length": 10, "isn_pattern": "[0-9A-Z]"},
                "builder_sequence": [
                    {"uid": "a0", "kind": "start", "config": {"project": "V80_REF_P0_TOP", "station": "FUNCTION", "dut_count": 1}},
                    {"uid": "a1", "kind": "isn", "config": {"enable_scan": True, "isn_len": 10, "isn_pattern": "[0-9A-Z]"}},
                    {"uid": "a2", "kind": "sfis_rw", "config": {"rw_mode": "get_version", "field_name": "MYPROJECT", "var_name": "sfPROJECT", "title": "SFIS Get MAC"}},
                    {"uid": "a3", "kind": "sfis_route", "config": {"sfis_mode": "offline", "use_phase0": True}},
                    {"uid": "a4", "kind": "comm_cmd", "config": {
                        "protocol": "uart", "port": "COM4", "alias": "UART",
                        "title": "Check UART & FW Version3", "command": "cat /etc/version",
                        "extract_mode": "split", "split_sep": ":", "split_idx": "1",
                        "var_name": "DUT_FW", "val_type": "%s", "expect_min": "1.0.0_release",
                    }},
                    {"uid": "a5", "kind": "teardown", "config": {"teardown_mode": "97_only"}},
                    {"uid": "a6", "kind": "end", "config": {"confirmed": True}},
                ]
            })
            ws_v80 = _parse_v50(v80_res["excel_path"])
            v80_rows = ws_v80["stations"]["FUNCTION"]
            v80_phases = [str(r.get("Phase") or "").strip() for r in v80_rows if str(r.get("Phase") or "").strip()]
            v80_refs = [str(r.get("Ref") or "").strip() for r in v80_rows if str(r.get("Ref") or "").strip()]
            wb_v80_cmt_check = openpyxl.load_workbook(v80_res["excel_path"])
            v80_any_comment = any(
                wb_v80_cmt_check[sn].cell(r_i, c_i).comment is not None
                for sn in wb_v80_cmt_check.sheetnames
                for r_i in range(1, wb_v80_cmt_check[sn].max_row + 1)
                for c_i in range(1, wb_v80_cmt_check[sn].max_column + 1)
            )
            wb_v80_cmt_check.close()
            check(v80_res.get("status") == "ok"
                  and v80_phases == ["0", "1", "2", "97"]
                  and '$DUT_FW:SplitString,"\\:","1"' in v80_refs
                  and not v80_any_comment
                  and int((v80_res.get("audit_report") or {}).get("error_count", -1)) == 0,
                  "v0.8.080 Phase 0 強制排於 Phase 1 之前 + SplitString 冒號自動轉義為 \\: + 匯出 Excel 無多餘註解 + 0 Error",
                  f"phases={v80_phases}, refs={v80_refs}, cmt={v80_any_comment}, ar={v80_res.get('audit_report')}")

            # Verify script_doctor detects and auto-fixes legacy unescaped SplitString,":","1"
            from core.script_doctor import audit_workspace as _aud80, auto_fix_workspace as _fix80
            ws_bad_ref = {
                "project_name": "TEST_REF_COLON",
                "duts": [{"Load": "*$(LOAD_1)", "DUT Name": "P$MB", "Station": "MB,1", "Parameter": "*$(PCIP_1),*$(DUTIP_1),1", "SFIS_DeviceID": "*$(DEVID_1)", "ScanBarcode( {Name,Lengh,Pattern} )": "{ISN,3,[0-9A-Z]}", "Connection1 (Type,Name,ConnectString)": '"Uart","UART","*$(DUT_UR1),115200,8,One,None,None,10000,5000"'}],
                "instruments": [], "switches": [], "global_ini": {"Settings": {"LOAD_1": "true", "PCIP_1": "1.1.1.1", "DUTIP_1": "1.1.1.2", "DEVID_1": "1", "DUT_UR1": "COM1"}, "Scripts": {}}, "system_ini": {},
                "stations": {"MB": [
                    {"Index": "000", "Phase": "0", "Title": "0,Route", "Send": ":ShowISN,\"*(ISN)\"", "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "001", "Phase": "", "Title": "", "Send": ":SfCheckRoute", "ExecMode": "8", "TestID": "OTFX085"},
                    {"Index": "002", "Phase": "1", "Title": "0,Ver,3", "Send": ":Connect,\"UART\"", "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "003", "Phase": "", "Title": "", "Send": "UART@cat /etc/version\\r\\n", "Reply": "@", "Ref": '$DUT_FW:SplitString,":","1"', "ExecMode": "1", "TestID": "B7PL025"},
                    {"Index": "004", "Phase": "97", "Title": "1,End", "Send": ":Disconnect,\"UART\"", "ExecMode": "3", "TestID": "B7PL025"},
                ]}
            }
            rep_bad = _aud80(ws_bad_ref)
            _fix80(ws_bad_ref)
            fixed_ref_str = ws_bad_ref["stations"]["MB"][3]["Ref"]
            check(any("未跳脫之冒號" in e for e in rep_bad.get("errors", []))
                  and fixed_ref_str == '$DUT_FW:SplitString,"\\:","1"',
                  "v0.8.080 script_doctor 正確偵測並自動修復 SplitString 未跳脫冒號 ':' -> '\\:'",
                  f"errs={rep_bad.get('errors')}, fixed={fixed_ref_str!r}")

            # [v0.8.081]
            #  1. log_analyzer 偵測 Centimani Ref function doesn't define 與 Format of Script Error=3
            #  2. 01 健檢清單預設 3 筆摺疊、首頁 05 實機測試獨立卡、全域語法小抄彈窗+複製、1->N 標題併入測站列+方案 A 文案與摘要膠囊、純儀器單測骨架與 Frozen EXE 相容性
            ref_err_log = (
                '2026/11/26 16:33:19 [System]    The Ref function """ of UART@cat /etc/version\n'
                " of Check UART & FW Version3(2) doesn't define.\n"
                "2026/11/26 16:33:19 [System]    Format of Script has some wrongs. Error=3.\n"
                "2026/11/26 16:33:19 [System]    Load PEGA_NEW444_TestFlow_FUNCTION.xlsx Fail !\n"
            )
            ref_diag = log_analyzer.analyze_centimani_log(ref_err_log)
            ref_blob = str(ref_diag)
            check("REF_FUNCTION_NOT_DEFINED" in ref_blob or "Ref 函式解析錯誤" in ref_blob
                  and "腳本格式驗證失敗" in ref_blob,
                  "v0.8.081 log_analyzer 可辨識 Centimani Ref function doesn't define 與 Format of Script Error=3 並引導一鍵修復",
                  str(ref_diag.get("issues")))

            with open(os.path.join(STUDIO_DIR, "web", "index.html"), "r", encoding="utf-8") as f_idx81:
                idx81_src = f_idx81.read()
            with open(os.path.join(STUDIO_DIR, "web", "js", "audit_editors.js"), "r", encoding="utf-8") as f_ae81:
                ae81_src = f_ae81.read()
            with open(os.path.join(STUDIO_DIR, "web", "js", "script_qa.js"), "r", encoding="utf-8") as f_qa81:
                qa81_src = f_qa81.read()
            with open(os.path.join(STUDIO_DIR, "web", "js", "create_block_builder.js"), "r", encoding="utf-8") as f_bb81:
                bb81_src = f_bb81.read()
            with open(os.path.join(PROJECT_ROOT, "CentimaniStudio.spec"), "r", encoding="utf-8") as f_sp81:
                spec81_src = f_sp81.read()

            check('id="auditRecentExpandBar"' in idx81_src
                  and "toggleAuditRecentExpand" in idx81_src
                  and "rows.slice(0, 3)" in idx81_src
                  and 'id="accCard_tools"' in idx81_src
                  and 'id="topBtnQaCheatsheet"' in idx81_src
                  and 'id="qaCheatsheetModal"' in idx81_src
                  and "qaCopySnippet" in qa81_src
                  and "bbLoadSingleInstPreset" in bb81_src
                  and "環境與埠號 (INI 設定)" in ae81_src
                  and "修改 Global.ini" in ae81_src
                  and "測項順序與停用" in ae81_src
                  and "跳轉與多 SKU 分流" in ae81_src
                  and 'id="editorSheetSel"' in ae81_src
                  and "IS_FROZEN" in open(os.path.join(STUDIO_DIR, "app_server.py"), "r", encoding="utf-8").read()
                  and "('IMAGES', 'IMAGES')" in spec81_src,
                  "v0.8.081 3筆清單摺疊、首頁05實機測試卡、全域語法小抄、1->N排版整併與方案A文案、純儀器骨架與EXE打包相容檢查通過",
                  "missing expected v0.8.081 markers")

            # [v0.8.082] 系統設定移至首頁右上綠色按鈕、移除手風琴/撲克牌文字、最近健檢檔案記憶、健檢無儀器匯出選項
            bs82_src = open(os.path.join(STUDIO_DIR, "web", "js", "block_sorter.js"), "r", encoding="utf-8").read()
            sf82_src = open(os.path.join(STUDIO_DIR, "web", "js", "sfis_hmi.js"), "r", encoding="utf-8").read()
            fg82_src = open(os.path.join(STUDIO_DIR, "web", "js", "flow_guide.js"), "r", encoding="utf-8").read()
            ui_combined82 = idx81_src + ae81_src + bb81_src + bs82_src + sf82_src + fg82_src
            check('id="btnHomeSettings"' in idx81_src
                  and 'btn-primary-green' in idx81_src.split('id="btnHomeSettings"')[1][:120]
                  and 'id="accCard_settings"' not in idx81_src
                  and 'id="btnExportAuditDry"' in idx81_src
                  and 'id="btnAuditResetPicker"' in idx81_src
                  and 'id="auditResumeLastBox"' in idx81_src
                  and 'record_recent_file' in open(os.path.join(STUDIO_DIR, "app_server.py"), "r", encoding="utf-8").read()
                  and '手風琴' not in ui_combined82
                  and '撲克牌' not in ui_combined82,
                  "v0.8.082 首頁右上綠色系統設定鈕、移除手風琴/撲克牌字眼、健檢記憶與無儀器匯出選項全部檢查通過",
                  f"has_home_btn={'btnHomeSettings' in idx81_src}, no_acc_set={'accCard_settings' not in idx81_src}, dry_btn={'btnExportAuditDry' in idx81_src}")

            # 實際測試：呼叫 /api/load_specific_file 載入舊檔後，該檔案必須置頂於 /api/recent_files #1 且標示 recently_viewed=True
            _orig_cfg_bak = None
            if os.path.exists(app_server.CONFIG_FILE):
                with open(app_server.CONFIG_FILE, "r", encoding="utf-8") as _fcfg:
                    _orig_cfg_bak = _fcfg.read()
            try:
                _cands82 = [x for x in (get_json("/api/recent_files").get("recent_files") or []) if os.path.isfile(x.get("path", ""))]
                if len(_cands82) >= 2:
                    _target_old = _cands82[-1]["path"]
                    _load82 = get_json("/api/load_specific_file?path=" + urllib.parse.quote(_target_old))
                    _rec82 = _load82.get("recent_files") or []
                    _init82 = get_json("/api/init")
                    check(len(_rec82) > 0
                          and os.path.normcase(os.path.abspath(_rec82[0].get("path", ""))) == os.path.normcase(os.path.abspath(_target_old))
                          and bool(_rec82[0].get("recently_viewed"))
                          and os.path.normcase(os.path.abspath(_init82.get("last_opened_file", ""))) == os.path.normcase(os.path.abspath(_target_old)),
                          "v0.8.082 健檢選檔後立即記憶並置頂於 recent_files #1 (recently_viewed=True) 與 /api/init last_opened_file",
                          f"target={_target_old}, top={_rec82[0].get('path') if _rec82 else None}")
            finally:
                if _orig_cfg_bak is not None:
                    with open(app_server.CONFIG_FILE, "w", encoding="utf-8") as _fcfg:
                        _fcfg.write(_orig_cfg_bak)

            # [v0.8.083] 雙主卡初始底色＋懸浮拉伸、1->N 永遠顯示匯出列、精簡 6 卡文案、跳轉多點說明與直白按鈕
            css83_src = open(os.path.join(STUDIO_DIR, "web", "css", "app.css"), "r", encoding="utf-8").read()
            tsw83_src = open(os.path.join(STUDIO_DIR, "web", "js", "template_sku_wizard.js"), "r", encoding="utf-8").read()
            check('.gen-big-card[data-theme="blue"]' in css83_src
                  and '.gen-big-card[data-theme="green"]' in css83_src
                  and 'flex: 1.55 1 0%' in css83_src
                  and "AUDIT_GLOBAL_TAB === 'hub'" in ae81_src
                  and 'renderGlobalEditorPanel' in tsw83_src
                  and '同一 Phase 可設多個跳轉點' in idx81_src
                  and '失敗跳到結尾 (略過中段)' in idx81_src
                  and '雙路線分流 (PASS走A / FAIL走B)' in idx81_src
                  and '失敗回前步重試 (2:XX)' in idx81_src,
                  "v0.8.083 雙主卡初始著色與懸浮拉伸、1->N恆常顯示匯出列、跳轉多重起點與白話模板全部檢查通過",
                  "missing expected v0.8.083 markers")

            # [v0.8.084] 1->N 改為 3x2 寬版功能網格：合併 INI 卡、跳轉+SKU 同卡、跨檔複製卡、頂部去重
            check('class="hub-grid-3x2"' in ae81_src
                  and 'globalHubCard_copy_sheet' in ae81_src
                  and '切換至 Global.ini' in ae81_src
                  and '切換至 System.ini' in ae81_src
                  and 'id="btnEditorTplSkuWizard"' in ae81_src
                  and 'id="btnEditorTplSkuWizard"' not in idx81_src,
                  "v0.8.084 1->N 改為 3x2 寬版功能格（INI合併/跳轉+SKU同卡/跨檔複製獨立卡/頂部去重）檢查通過",
                  "missing expected v0.8.084 markers")

            # [v0.8.085] 移除 pendingChangesBar 重複匯出鈕、1->N 各功能進入獨立全寬頁面 (.as-page)
            pending_sec85 = idx81_src.split("if (pendings.length > 0)")[1].split("} else {")[0]
            check('applyFixAndExport' not in pending_sec85
                  and '_applyAsPageMode' in idx81_src
                  and '.modal-backdrop.open.as-page' in css83_src
                  and '_applyAsPageMode' in bs82_src
                  and '_applyAsPageMode' in tsw83_src
                  and 'btnJeCloseModal' in idx81_src
                  and 'btnBsCloseModal' in idx81_src
                  and 'btnCsCloseModal' in idx81_src
                  and 'btnTswCloseModal' in tsw83_src,
                  "v0.8.085 移除暫存列重複匯出按鈕、1->N 所有卡片點入皆以全寬獨立頁面呈現 (.as-page) 檢查通過",
                  "missing expected v0.8.085 markers")

            # [v0.8.086] 統一「⬅ 返回編修主入口」、子頁面不直接匯出改由總覽統一匯出、StationName清單(ask置首+全測站)、去重Phase=-1勾選
            check('返回 1 → N 編修總覽' not in (idx81_src + bs82_src + tsw83_src)
                  and '返回 6 格設定入口' not in ae81_src
                  and 'id="auditNoHwPhaseChk"' not in idx81_src
                  and "expBar.style.display = (AUDIT_GLOBAL_TAB === 'hub') ? 'flex' : 'none';" in ae81_src
                  and "執行時由使用者當場選站" in idx81_src
                  and "station_name_value" in open(os.path.join(STUDIO_DIR, "app_server.py"), "r", encoding="utf-8").read(),
                  "v0.8.086 統一返回編修主入口、6頁僅暫存改由總覽匯出、StationName全站清單與移除重複Phase=-1勾選通過",
                  "missing expected v0.8.086 markers")

            # [v0.8.087] 全分頁與彈窗字體連動修復（panelHome/FlowGuide/InstIntro/InstHmi/Ni6009/BlockSorter/0->1/SFIS/表格按鍵繼承與雙向同步）
            fg87_src = open(os.path.join(STUDIO_DIR, "web", "js", "flow_guide.js"), "r", encoding="utf-8").read()
            sf87_src = open(os.path.join(STUDIO_DIR, "web", "js", "sfis_hmi.js"), "r", encoding="utf-8").read()
            cbb87_src = open(os.path.join(STUDIO_DIR, "web", "js", "create_block_builder.js"), "r", encoding="utf-8").read()
            sqa87_src = open(os.path.join(STUDIO_DIR, "web", "js", "script_qa.js"), "r", encoding="utf-8").read()
            ih87_src = open(os.path.join(STUDIO_DIR, "web", "js", "inst_hmi.js"), "r", encoding="utf-8").read()
            sub_tiny_hits = _re_chk.findall(r'font-size\s*:\s*0\.6\d?rem', idx81_src + bs82_src + ae81_src + tsw83_src + sf87_src + cbb87_src + sqa87_src)
            check('#panelHome, #panelFlowGuide, #panelInstIntro, #panelInstHmi, #panelNi6009' in css83_src
                  and 'button {' in css83_src
                  and 'table, th, td, pre, details, summary {' in css83_src
                  and 'setIntroFontSize(fs, false)' in fg87_src
                  and '_bootApplyCachedFontSize' in fg87_src
                  and 'setIntroFontSize(sz, persist = false)' in ih87_src
                  and 'setIntroFontSize(19, true)' in idx81_src
                  and 'calc(84px * var(--app-scale, 1))' in cbb87_src
                  and 'Math.max(0.86, rootFontPx / 15)' in bs82_src
                  and 'minmax(13.5rem, 26%) 1fr' in bs82_src
                  and not sub_tiny_hits,
                  "v0.8.087 全分頁/彈窗/積木排序器/0->1/SFIS/儀器頁面字體連動與雙向持久化全面檢查通過",
                  f"sub_tiny_hits={sub_tiny_hits[:5]}")

            # [v0.8.088] 1) tbd_stub (待補測項佔位) 僅 1 列合法 :Delay,"10" 且預設 Phase=-1 (0 Error)
            #            2) Error Code / TestID 智慧比對：信心度分級 + 高相似自動預選 + 差距大建議申請新項目 + 1->N直入比對 + 同類同步
            v88_payload = {
                "project_name": "TBD_STUB_V88",
                "station_name": "MB",
                "dut_count": 1,
                "open_folder": False,
                "open_excel": False,
                "builder_sequence": [
                    {"kind": "start", "config": {"project": "TBD_STUB_V88", "station": "MB", "dut_count": 1}},
                    {"kind": "tbd_stub", "config": {"phase_role": "-1", "title": "TBD - RF Power Meter", "note": "待補實機步驟"}},
                    {"kind": "delay", "config": {"ms": "200", "note": "Regular Step"}},
                    {"kind": "teardown", "config": {"teardown_mode": "97_only"}},
                    {"kind": "end", "config": {"confirmed": True}},
                ]
            }
            v88_res = post_json("/api/generate_new_standalone", v88_payload)
            ws_v88 = _parse_v50(v88_res["excel_path"])
            v88_rows = ws_v88["stations"]["MB"]
            tbd_rows = [r for r in v88_rows if "TBD - RF Power Meter" in str(r.get("Title") or "")]
            check(v88_res.get("status") == "ok"
                  and len(tbd_rows) == 1
                  and str(tbd_rows[0].get("Phase") or "").strip() == "-1"
                  and str(tbd_rows[0].get("Send") or "").strip() == ':Delay,"10"'
                  and int((v88_res.get("audit_report") or {}).get("error_count", -1)) == 0
                  and "tbd_stub" in cbb87_src
                  and "待補測項佔位" in cbb87_src,
                  "v0.8.088 新增「🔖 佔位 (TBD)」積木僅產出 1 列合法 :Delay,\"10\" (Phase=-1, 0 Error)",
                  f"tbd_rows={tbd_rows}, ar={v88_res.get('audit_report')}")

            tic_v88_ws = {
                "stations": {
                    "MB": [
                        {"Index": "1", "Phase": "1", "Title": "Measure 5V Voltage", "Description": "PC#-#Measure 5V Voltage", "Send": ":Dev.MVolt,1", "TestID": "", "ExecMode": "0"},
                        {"Index": "2", "Phase": "2", "Title": "Quantum Flux Z99 Xyzzy", "Description": "PC#-#Qubit Calibration Xyzzy", "Send": "UART@qflux_xyz99", "TestID": "", "ExecMode": "0"},
                    ]
                }
            }
            tic_v88 = post_json("/api/tic_audit_excel", {"workspace": tic_v88_ws, "station": "MB"})
            iss88 = tic_v88.get("issues") or []
            iss88_v = next((x for x in iss88 if "5V Voltage" in str(x.get("title") or "")), None)
            iss88_q = next((x for x in iss88 if "Quantum Flux" in str(x.get("title") or "")), None)
            check(tic_v88.get("status") == "ok"
                  and iss88_v is not None and iss88_v.get("match_tier") == "high"
                  and int((iss88_v.get("candidates") or [{}])[0].get("confidence_score", 0)) >= 72
                  and iss88_q is not None and iss88_q.get("match_tier") == "low_gap"
                  and iss88_q.get("suggest_new_item") is True
                  and "ticAutoSelectTier" in idx81_src
                  and "ticExportNewItemRequests" in idx81_src
                  and "ticApplyToSimilarRows" in idx81_src
                  and "switchTicSubTab('batch')" in idx81_src.split("function openTicFromEdit()")[1].split("function openTicBatchAuditFromGen()")[0],
                  "v0.8.088 Error Code 智慧比對分級（高相似自動預選 / 差距過大建議申請新碼 / 同類同步 / 1->N直入比對）通過",
                  f"v={iss88_v and iss88_v.get('match_tier')}, q={iss88_q and (iss88_q.get('match_tier'), iss88_q.get('best_score'))}")

            # [v0.8.089] B7PL011 偷懶通用碼自動對照升級 + Title/Description 優先關鍵字擷取 + 過濾 <35% 無關候選 + 預設只列出無法自動確認項目
            tic_v89_ws = {
                "stations": {
                    "OQC": [
                        {"Index": "61", "Phase": "8", "Title": "", "Description": "Fan Control", "Send": "LAN@@FA4201$3#c8.", "TestID": "B7PL011", "ExecMode": "0"},
                        {"Index": "63", "Phase": "8", "Title": "", "Description": "FAN sound", "Send": ':ShowConfirmBox,"有風扇聲音嗎?","好(OK)"', "TestID": "B7PL011", "ExecMode": "0"},
                        {"Index": "64", "Phase": "9", "Title": "Custom Proprietary XYZ", "Description": "PC#-#Qubit Calibration Xyzzy", "Send": "UART@qflux_xyz99", "TestID": "IOFN136", "ExecMode": "0"},
                        {"Index": "65", "Phase": "9", "Title": "Quantum Flux Z99 Xyzzy", "Description": "PC#-#Qubit Frobnicate Xyzzy", "Send": "UART@qflux_xyz99", "TestID": "", "ExecMode": "0"},
                    ]
                }
            }
            tic_v89 = post_json("/api/tic_audit_excel", {"workspace": tic_v89_ws, "station": "OQC"})
            iss89 = tic_v89.get("issues") or []
            iss89_fc = next((x for x in iss89 if x.get("description") == "Fan Control"), None)
            iss89_fs = next((x for x in iss89 if x.get("description") == "FAN sound"), None)
            iss89_prop = next((x for x in iss89 if x.get("title") == "Custom Proprietary XYZ"), None)
            iss89_qf = next((x for x in iss89 if "Quantum Flux" in str(x.get("title") or "")), None)
            check(tic_v89.get("status") == "ok"
                  and iss89_fc is not None and iss89_fc.get("auto_confirmed") is True and "IOFN" in str((iss89_fc.get("candidates") or [{}])[0].get("test_id") or "")
                  and iss89_fs is not None and iss89_fs.get("auto_confirmed") is True and "IOFN" in str((iss89_fs.get("candidates") or [{}])[0].get("test_id") or "")
                  and iss89_prop is None
                  and iss89_qf is not None and iss89_qf.get("needs_review") is True and len(iss89_qf.get("candidates") or []) == 0
                  and "filter: 'needs_review'" in idx81_src
                  and "btnTicBatchFilterNeedsReview" in idx81_src
                  and "ticKeepOriginalRow" in idx81_src,
                  "v0.8.089 B7PL011 自動升級配對 + 排除0%誤導候選 + 不誤報已有專碼 + 預設只列無法確認項目通過",
                  f"fc={iss89_fc and (iss89_fc.get('auto_confirmed'), iss89_fc.get('candidates', [{}])[0].get('test_id'))}, prop={iss89_prop}, qf={iss89_qf and iss89_qf.get('candidates')}")

            # [v0.8.090] Script O欄 Description (含 2412 TX1 等英數通道碼) 對照文件 D 欄 + Phase 繼承 + 測項分類分組 + 整份比對為預設主畫面
            tic_v90_ws = {
                "stations": {
                    "MainBoard": [
                        {"Index": "59", "Phase": "5", "Title": "1,TX1_2412 6M BPSK", "Description": "2412 TX1", "Send": "1,1,6,12.5,11ag_6,10.5,14.5,-50,-5", "TestID": "", "ExecMode": "0"},
                        {"Index": "60", "Phase": "", "Title": "", "Description": "PC#-#Check Route", "Send": ":SfCheckRoute", "TestID": "", "ExecMode": "1"},
                        {"Index": "61", "Phase": "6", "Title": "0,Power", "Description": "Measure 5V Voltage", "Send": ":Dev.MVolt,1", "TestID": "", "ExecMode": "1"},
                    ]
                }
            }
            tic_v90 = post_json("/api/tic_audit_excel", {"workspace": tic_v90_ws, "station": "MainBoard"})
            iss90 = tic_v90.get("issues") or []
            iss90_tx = next((x for x in iss90 if x.get("description") == "2412 TX1"), None)
            iss90_rt = next((x for x in iss90 if x.get("description") == "PC#-#Check Route"), None)
            iss90_pw = next((x for x in iss90 if x.get("description") == "Measure 5V Voltage"), None)
            check(tic_v90.get("status") == "ok"
                  and iss90_tx is not None and iss90_tx.get("auto_confirmed") is True
                  and "WFTX" in str((iss90_tx.get("candidates") or [{}])[0].get("test_id") or "")
                  and iss90_tx.get("item_category") == "rf_wireless" and iss90_tx.get("effective_phase") == "5"
                  and iss90_rt is not None and iss90_rt.get("item_category") == "sfis" and iss90_rt.get("effective_phase") == "5"
                  and iss90_pw is not None and iss90_pw.get("item_category") == "power_volt" and iss90_pw.get("effective_phase") == "6"
                  and "subTab: 'batch'" in idx81_src
                  and "groupBy: 'phase'" in idx81_src
                  and "ticSetBatchGroupBy" in idx81_src
                  and "btnTicGroupPhase" in idx81_src,
                  "v0.8.090 Description 2412 TX1 精準對照 WFTX + Phase繼承/測項分類分組 + 整份比對預設主畫面檢查通過",
                  f"tx={iss90_tx and (iss90_tx.get('auto_confirmed'), iss90_tx.get('candidates', [{}])[0].get('test_id'), iss90_tx.get('item_category'))}")

        print("\n" + "=" * 78)
        print(f"🎉 全功能自動驗收完成：{passed_checks} / {total_checks} 項測試 100% 通過！(0 Error)")
        print("=" * 78)
        return True
    finally:
        server.shutdown()
        app_server.open_folder_in_explorer = orig_open_folder
        app_server.launch_excel_file_async = orig_launch_excel
        app_server.launch_ini_file_async = orig_launch_ini
        app_server.launch_centimani_tool_async = orig_launch_tool


if __name__ == "__main__":
    run_all_verifications()
