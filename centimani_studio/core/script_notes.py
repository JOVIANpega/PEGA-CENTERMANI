# -*- coding: utf-8 -*-
"""
Centimani Studio - Companion Script Logic & Usage Guide (.txt) Generator
Generates a human-readable engineering & production-switching manual alongside exported Excel files.
"""
import os
import re
import datetime


def generate_companion_logic_txt(workspace, excel_path, dll_chk=None, fixed_logs=None, build_ver="Build v0.8.011"):
    """
    在匯出 Excel 同目錄下產出 `<檔名>_編寫與使用說明.txt`，記錄：
    1. 本次編寫／異動摘要
    2. Excel 結構設計邏輯（Phase / Title / Instrument 單次宣告 / $全域變數）
    3. Global.ini 一鍵開關速查（免改 Excel 現場切換 0=開 / 2或6=停）
    4. 台北座位（無硬體 Debug）vs 工廠產線（實機）應變 SOP ＋ 缺 DLL 檢查清單
    """
    if not excel_path:
        return ""
    out_dir = os.path.dirname(os.path.abspath(excel_path))
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(excel_path))[0]
    txt_path = os.path.join(out_dir, f"{stem}_編寫與使用說明.txt")

    ws = workspace or {}
    proj = str(ws.get("project_name", "Centimani") or "Centimani")
    stations = ws.get("stations") or {}
    instruments = ws.get("instruments") or []
    global_scripts = (ws.get("global_ini") or {}).get("Scripts") or {}
    system_ini = ws.get("system_ini") or {}
    dll_chk = dll_chk or {}
    fixed_logs = fixed_logs or []

    lines = []
    lines.append("=" * 78)
    lines.append(f"Centimani TestFlow 編寫邏輯與產線應變使用指南 ({build_ver})")
    lines.append("=" * 78)
    lines.append(f"產生時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"專案名稱：{proj}")
    lines.append(f"對應 Excel：{os.path.basename(excel_path)}")
    lines.append(f"所在目錄：{out_dir}")
    lines.append("")

    # 1. Summary
    lines.append("【一、 本次編輯／產出摘要】")
    lines.append(f"  - 包含測試站分頁：{', '.join(stations.keys()) if stations else '(無)'}")
    mounted_insts = [i for i in instruments if str(i.get("Mount", "")).strip()]
    lines.append(f"  - 已掛載儀器數量：{len(mounted_insts)} 台")
    for mi in mounted_insts:
        lines.append(
            f"      * {mi.get('Name', '')} (Mount={mi.get('Mount', '')}, "
            f"DLL={mi.get('ControlDLL', '')}, Functions={mi.get('Functions', '')})"
        )
    if fixed_logs:
        lines.append(f"  - 本次自動修復／精簡異動（共 {len(fixed_logs)} 項）：")
        for lg in fixed_logs[:20]:
            lines.append(f"      * {lg}")
        if len(fixed_logs) > 20:
            lines.append(f"      ... 其餘 {len(fixed_logs) - 20} 項略")
    lines.append("")

    # 2. Excel structure & authoring conventions
    lines.append("【二、 Excel 編寫結構與實戰設計邏輯】")
    lines.append("  1. Phase -> Title -> Step 單次宣告階層：")
    lines.append("     - Phase 欄僅在該階段第 1 列寫入（0=前置, 1~96=正式測項, -1=整批暫停, 97=斷電收尾）。")
    lines.append("     - 同一 Phase 下可包含多個各自獨立的 Title 子區塊，各自擁有重試與區域變數作用域。")
    lines.append("  2. Instrument 單次綁定規範：")
    lines.append("     - 僅於每個儀器區塊首列（或切換功能時）寫一次 Functions 名稱；同區塊後續 :Delay / :Dev.* / :ReleaseDevice 一律留空。")
    lines.append("     - 每次 :ObtainDevice 必須配對 :ReleaseDevice 且設 ExecMode=3 (Continue)，避免死鎖。")
    lines.append("")

    all_ini_switches = []
    seen_sw = set()
    global_vars_used = set()

    for st_name, steps in stations.items():
        if not isinstance(steps, list):
            continue
        lines.append(f"  [測試站：{st_name}] 共 {len(steps)} 列步驟")
        cur_p = "-"
        for r_idx, row in enumerate(steps, 2):
            p = str(row.get("Phase", "")).strip()
            t = str(row.get("Title", "")).strip()
            ins = str(row.get("Instrument", "")).strip()
            em = str(row.get("ExecMode", "")).strip()
            ref = str(row.get("Ref", "")).strip()
            if p:
                cur_p = p
            if p or t or ins:
                tag_skip = " [⏸️ 暫停不測]" if (cur_p == "-1" or t.startswith("2,")) else ""
                lines.append(
                    f"      L{r_idx:03d} | Phase={p or '(同上)':8s} | Title={t or '(同上)':30s} "
                    f"| Inst={ins or '-':12s} | Exec={em or '-'}{tag_skip}"
                )
            for text_src in (t, em, str(row.get("Validation", "")), str(row.get("Send", ""))):
                for m in re.finditer(r"\*\$\(([A-Za-z0-9_ ]+)\)", text_src):
                    vname = m.group(1).strip()
                    if vname not in seen_sw:
                        seen_sw.add(vname)
                        all_ini_switches.append(vname)
            for m in re.finditer(r"\$([A-Za-z_][A-Za-z0-9_]*)", ref):
                global_vars_used.add("$" + m.group(1))
        lines.append("")

    if global_vars_used:
        lines.append(f"  - 本腳本建立之跨 Title 全域變數：{', '.join(sorted(global_vars_used))}")
        lines.append("")

    # 3. Global.ini One-Click Switch Cheat Sheet
    lines.append("【三、 Global.ini [Scripts] 一鍵開關速查表（免改 Excel、不破 Checksum）】")
    if all_ini_switches:
        for sw in all_ini_switches:
            cur_val = str(global_scripts.get(sw, "(未設定)")).strip()
            if sw.upper().startswith("EN_") or sw.upper() in ("RL", "TITLESTATUS", "SPT", "LOCKTEST", "DEBUG_MAC", "LEDOFF_VERIFY"):
                hint = "0=正常執行測項 / 2=Skip 跳過此 Title 區塊"
            elif sw.upper() in ("AULAB", "EXECMODE_N", "EXECMODEL_N", "SHOWB", "EXECUTE_F"):
                hint = "0或1=執行 / 3=強制繼續 / 6=Skip 略過該步驟"
            else:
                hint = "請依測試需求於 Global.ini [Scripts] 調整"
            lines.append(f"  - {sw} = {cur_val:<8s}   # {hint}")
    else:
        lines.append("  - 本次尚未加入 *$(EN_xxx) 動態開關（若想在 Global.ini 控制測試有無，可勾選「加入 Global.ini 一鍵開關」或將 Title 改為 *$(EN_名稱),標題,3）。")
    lines.append("")

    # 4. Taipei vs Production Line SOP & Missing DLL
    lines.append("【四、 台北座位（無硬體／除錯）vs 產線上機（實機）切換 SOP 與缺 DLL 提醒】")
    lines.append(f"  - System.ini DebugMode = {system_ini.get('DebugMode', '1')} (1=免檢查 Checksum 方便除錯 / 0=產線嚴格簽章)")
    lines.append(f"  - System.ini SFIS_Enable = {system_ini.get('SFIS_Enable', '0')} (0=台北單機免 SFIS / 1=產線連 SFIS 過站)")

    cm_dir = dll_chk.get("centimani_dir") or ""
    missing = dll_chk.get("missing_dlls") or []
    if not dll_chk.get("centimani_dir_exists", True):
        lines.append("  - DLL 檢查：尚未指定本機 Centimani 主程式目錄，請於上機前確認 Device\\ 內 DLL 齊備。")
    elif missing:
        lines.append(f"  - ⚠️ 本機 ({cm_dir}\\Device\\) 缺少以下 DLL（在無這些硬體的電腦開啟將報錯）：")
        for m in missing:
            lines.append(f"      * {m.get('inst', '')} -> 缺 {m.get('dll', '')}")
    else:
        lines.append(f"  - ✅ DLL 檢查通過：目前目錄 ({cm_dir}\\Device\\) 已具備本腳本所需 DLL。")

    lines.append("")
    lines.append("  📌 不同現場快速切換建議：")
    lines.append("     1) 若電腦有 DLL 但暫時不測某功能：直接改 Global.ini [Scripts] 內的 EN_xxx=2（產線改回 0），免改 Excel。")
    lines.append("     2) 若台北電腦完全沒接實體儀器（或缺上述 DLL）：開機時 Centimani 會先讀 Instrument 表的 Mount 欄並報錯；")
    lines.append("        請暫時清空該儀器 Mount（或改跑本工具產出之 *_DryRun.xlsx 無硬體試跑版），到產線再切換回正式版。")
    lines.append("     3) 同檔雙站進階技巧：亦可在同一個 Excel 複製一份站別分頁（如 MB_TAIPEI），只把產線儀器 Mount 寫在 MB，")
    lines.append("        台北端跑 MB_TAIPEI 即完全不載入無硬體之產線儀器，達成同一包程式跨地即時運行。")
    lines.append("")

    try:
        with open(txt_path, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(lines))
        return txt_path
    except Exception:
        return ""
