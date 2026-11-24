# -*- coding: utf-8 -*-
"""
Centimani Studio - Concise Companion Switch & Usage Note (.txt)
Produces a concise, field-focused quick reference focused on INI/Phase switches,
StationName startup mode, and missing DLL reminders.
"""
import os
import re


def generate_companion_logic_txt(workspace, excel_path, dll_chk=None, fixed_logs=None, build_ver="Build v0.8.039"):
    """
    在匯出 Excel 同目錄產出白話版 `<檔名>_編寫與使用說明.txt`（不寫艱澀術語、不顯示空區塊）：
    1. 怎麼直接開始執行（站別 / 試跑或產線模式）
    2. Global.ini [Scripts] 跳過開關（僅在有加入 *$(EN_xxx) 時顯示）
    3. Phase = -1 暫停測項怎麼恢復（僅在有設 Phase=-1 時顯示）
    4. 實機缺 DLL 提醒（僅在缺 DLL 時顯示，同款多機合併為同一支 DLL）
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
        st_desc = f"開機當場自己選站（可選：{st_list}）"
    else:
        st_desc = f"{st_name_val}（已固定，打開主程式就直接跑這站）"

    dbg_label = "除錯試跑模式 (DebugMode=1)" if str(system_ini.get("DebugMode", "1")).strip() == "1" else "產線正式模式 (DebugMode=0)"
    sfis_label = "單機不連 SFIS (SFIS_Enable=0)" if str(system_ini.get("SFIS_Enable", "0")).strip() == "0" else "已連線 SFIS (SFIS_Enable=1)"

    lines = [
        f"=== {os.path.basename(excel_path)} 操作說明 ({build_ver}) ===",
        "1. 怎麼執行：打開同資料夾旁的 CentimaniSystem.exe 即可開始測試。",
        f"2. 測試站別：{st_desc}",
        f"3. 目前模式：{dbg_label} ｜ {sfis_label}",
    ]

    if all_ini_switches:
        lines.extend([
            "",
            "【想跳過特定測項？（不用改 Excel，直接改 Global.ini [Scripts] 就好）】",
            "用記事本打開同資料夾的 Global.ini，找到 [Scripts] 下面改數字、存檔即可：",
        ])
        for sw in all_ini_switches:
            cur_val = str(global_scripts.get(sw, "(未設定)")).strip()
            up = sw.upper()
            if up.startswith("EN_") or up in ("RL", "TITLESTATUS", "SPT", "LOCKTEST", "DEBUG_MAC", "LEDOFF_VERIFY"):
                hint = "0=要測  /  改成 2=跳過整個測項"
            elif up in ("AULAB", "EXECMODE_N", "EXECMODEL_N", "SHOWB", "EXECUTE_F"):
                hint = "0=要測  /  改成 6=略過這一步"
            else:
                hint = "可依產線需要修改數字"
            lines.append(f"  {sw} = {cur_val:<6s} -> {hint}")

    paused_mounts = ws.get("_paused_mounts") or []
    if paused_phases:
        lines.extend([
            "",
            "【目前暫時跳過的無儀器測項（接好實機後再打開）】",
            "以下測項目前設成 Phase = -1，沒接儀器也能先跑主程式確認流程：",
        ])
        for sn, r_idx, t in paused_phases:
            lines.append(f"  - [{sn} 第 {r_idx} 列] {t}")
        lines.append("回產線接好實機後，打開 Excel 做這 2 步就恢復測試：")
        lines.append("  1) 把上面列的 Phase 從 -1 改回 1, 2, 3...")
        if paused_mounts:
            pm_txt = "、".join(f"{p.get('device')} 填回 {p.get('sheet')}" for p in paused_mounts)
            lines.append(f"  2) 到「Instrument」分頁，將 Mount 欄補回（{pm_txt}）")

    missing = dll_chk.get("missing_dlls") or []
    cm_dir = dll_chk.get("centimani_dir") or ""
    if not dll_chk.get("centimani_dir_exists", True):
        lines.extend([
            "",
            "【實機 DLL 檢查提醒】尚未指定 Centimani 主程式路徑，上產線前請確認 Device\\ 內 DLL 齊備。",
        ])
    elif missing:
        lines.extend([
            "",
            f"【實機 DLL 檢查提醒】目前 {cm_dir}\\Device\\ 缺少以下 DLL（同款多台儀器如 NI6008 / NI6008-2 共用同一支 DLL）：",
        ])
        for m in missing:
            lines.append(f"  - {m.get('dll', '')} （{m.get('inst', '')} 需要，缺這支上機開檔會報錯）")
        lines.append("  提示：若只是在無儀器電腦先看流程，請改開 *_DryRun.xlsx。")

    missing_drivers = dll_chk.get("missing_drivers") or []
    if missing_drivers:
        lines.extend([
            "",
            "【系統驅動程式提醒】",
        ])
        for md in missing_drivers:
            lines.append(f"  - {md}")

    lines.append("")
    try:
        with open(txt_path, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(lines))
        return txt_path
    except Exception:
        return ""
