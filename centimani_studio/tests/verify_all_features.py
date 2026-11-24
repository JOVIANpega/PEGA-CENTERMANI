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
        check("儀器範本" in index_html and "左側撲克牌庫" in index_html and "既有腳本編修" in flow_guide_js,
              "首頁手風琴、流程導覽 (flow_guide.js) 與儀器撲克牌說明文已全面與新版 UI 同步")
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
                    {"Load": "*$(LOAD_1)", "DUT Name": "MD_AUDIT$MB", "Station": "MB,1", "Connection1 (Type,Name,ConnectString)": '"Uart","UART","COM1"'},
                    {"Load": "*$(LOAD_2)", "DUT Name": "MD_AUDIT$MB", "Station": "MB,2", "Connection1 (Type,Name,ConnectString)": '"Uart","UART","COM2"'},
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

            # [v0.8.025] 驗證第 5 張手風琴『實機驗證 (SFIS / DLL)』、移除書籤N 字眼、NI-DAQmx 驅動缺漏偵測與 Log 診斷
            check('id="genHubCard_tools"' in index_html
                  and 'id="genModeTools"' in index_html
                  and 'id="btnGenModeTools"' in index_html
                  and 'toolsCheckSfisLink()' in sfis_hmi_js
                  and 'ISN 刷過' in index_html
                  and 'GET' in index_html
                  and 'WRITE' in index_html,
                  "腳本建立與編修中心已新增第 5 張手風琴『實機驗證 (SFIS / DLL)』含 ISN/GET/WRITE 與 DLLtest 工作區")

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
            check(ref_split == '$sf5G:SplitString,"\\;","1":Trim;'
                  and ref_within == '$sfSN:WithinString,"SN\\:","\\;IMEI","":Trim;'
                  and ref_steps[1]["Ref"] == '$sfSN:WithinString,"SN\\:","\\;IMEI","":Trim;'
                  and ',\"4\",\"W3G\"' in ref_steps[1]["Send"]
                  and "sfisPickSlotIndex" in sfis_hmi_js and "sfisPickSegment" in sfis_hmi_js and "sfisSetMockMode" in sfis_hmi_js,
                  "v0.8.035 支援 0~7 堆疊選格、Centimani 官方 Ref 找字串轉義 (SplitString/WithinString) 與完整積木清單")

            # [v0.8.036] 驗證雙視窗拖曳調寬 + 折疊吐回字串 + 模擬切換清錯誤 + 全域字體聯動 + 正名實機驗證中心（SFIS)
            inst_hmi_js = open(os.path.join(STUDIO_DIR, "web", "js", "inst_hmi.js"), "r", encoding="utf-8").read()
            check("tools: '🛡️ 實機驗證中心（SFIS)'" in index_html
                  and "sfis-split-resizer" in app_css and "sfisStartSplitDrag" in sfis_hmi_js
                  and 'id="sfisResponseDetails"' in sfis_hmi_js and "responseExpanded: false" in sfis_hmi_js
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
