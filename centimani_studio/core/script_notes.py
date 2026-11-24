# -*- coding: utf-8 -*-
"""
Centimani Studio - Concise Companion Switch & Usage Note (.txt)
Produces a concise, field-focused quick reference focused on INI/Phase switches,
StationName startup mode, and missing DLL reminders.
"""
import os
import re


def generate_companion_logic_txt(workspace, excel_path, dll_chk=None, fixed_logs=None, build_ver="Build v0.8.018"):
    """
    在匯出 Excel 同目錄產出精簡版 `<檔名>_編寫與使用說明.txt`，重點說明開關怎麼切換：
    1. 基本資訊與啟動站別 (StationName 指定 vs 留空當場選站)
    2. Global.ini [Scripts] 一鍵開關用法 (*$(EN_xxx)=0 執行 / 2 跳過；*$(AULAB)=0 / 6 略過)
    3. Excel Phase=-1 暫停區塊清單 (回產線手動改回 1, 2... 即可)
    4. 缺實機 DLL 提醒 (若有)
    """
    if not excel_path:
        return ""
    out_dir = os.path.dirname(os.path.abspath(excel_path))
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(excel_path))[0]
    txt_path = os.path.join(out_dir, f"{stem}_編寫與使用說明.txt")

    ws = workspace or {}
    stations = ws.get("stations") or {}
    global_scripts = (ws.get("global_ini") or {}).get("Scripts") or {}
    system_ini = ws.get("system_ini") or {}
    dll_chk = dll_chk or {}

    all_ini_switches = []
    seen_sw = set()
    paused_phases = []

    for st_name, steps in stations.items():
        if not isinstance(steps, list):
            continue
        for r_idx, row in enumerate(steps, 2):
            p = str(row.get("Phase", "")).strip()
            t = str(row.get("Title", "")).strip()
            em = str(row.get("ExecMode", "")).strip()
            if p == "-1":
                paused_phases.append((st_name, r_idx, t))
            for text_src in (t, em, str(row.get("Validation", "")), str(row.get("Send", ""))):
                for m in re.finditer(r"\*\$\(([A-Za-z0-9_ ]+)\)", text_src):
                    vname = m.group(1).strip()
                    if vname not in seen_sw:
                        seen_sw.add(vname)
                        all_ini_switches.append(vname)

    st_list = ", ".join(stations.keys()) if stations else "(無)"
    st_mode = str(system_ini.get("StationName_Mode", "")).lower()
    st_name_val = str(system_ini.get("StationName", "")).strip()
    if st_mode == "ask" or st_name_val == "":
        st_desc = f"空白（開機時彈窗當場選擇測試站；StationList={st_list}）"
    else:
        st_desc = f"{st_name_val}（指定站別直接啟動）"

    lines = [
        f"=== {os.path.basename(excel_path)} 開關與使用說明 ({build_ver}) ===",
        f"測試站：{st_list}  ｜  System.ini StationName：{st_desc}",
        f"DebugMode={system_ini.get('DebugMode', '1')} (1=除錯 / 0=產線簽章)  ｜  SFIS_Enable={system_ini.get('SFIS_Enable', '0')} (0=單機 / 1=連SFIS)",
        "",
        "【1. Global.ini [Scripts] 一鍵開關（改 INI 即可，免改 Excel、不破 Checksum）】",
    ]

    if all_ini_switches:
        for sw in all_ini_switches:
            cur_val = str(global_scripts.get(sw, "(未設定)")).strip()
            up = sw.upper()
            if up.startswith("EN_") or up in ("RL", "TITLESTATUS", "SPT", "LOCKTEST", "DEBUG_MAC", "LEDOFF_VERIFY"):
                hint = "0=開啟執行  /  2=Skip 跳過整個測項"
            elif up in ("AULAB", "EXECMODE_N", "EXECMODEL_N", "SHOWB", "EXECUTE_F"):
                hint = "0或1=執行  /  6=Skip 略過該步驟"
            else:
                hint = "可依產線需求於 Global.ini [Scripts] 調整"
            lines.append(f"  {sw} = {cur_val:<8s}   # {hint}")
    else:
        lines.append("  （本腳本未加入 *$(EN_xxx) Title 開關）")

    lines.append("")
    lines.append("【2. Excel Phase = -1 暫停區塊（回產線手動把 -1 改回 1, 2... 即可跑）】")
    if paused_phases:
        for sn, r_idx, t in paused_phases:
            lines.append(f"  - [{sn} 第 {r_idx} 列] Phase=-1 | Title={t}")
    else:
        lines.append("  （目前無 Phase=-1 暫停區塊）")

    missing = dll_chk.get("missing_dlls") or []
    cm_dir = dll_chk.get("centimani_dir") or ""
    if not dll_chk.get("centimani_dir_exists", True):
        lines.append("")
        lines.append("【3. 實機 DLL 檢查】尚未指定 Centimani 目錄，上機前請確認 Device\\ 內 DLL 齊備。")
    elif missing:
        lines.append("")
        lines.append(f"【3. 實機 DLL 檢查】⚠️ {cm_dir}\\Device\\ 缺下列 DLL（無該硬體電腦請改用 *_DryRun.xlsx）：")
        for m in missing:
            lines.append(f"  - {m.get('inst', '')} -> 缺 {m.get('dll', '')}")

    lines.append("")
    try:
        with open(txt_path, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(lines))
        return txt_path
    except Exception:
        return ""
