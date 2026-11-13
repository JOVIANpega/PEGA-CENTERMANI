# -*- coding: utf-8 -*-
"""
Centimani Studio - 10-Point Deep Logic & Optimization Auditor (Script Doctor V2.1)
Includes Smart Step-Target Inference & Interactive Choice Cards for Zero-Burden Fixing.
"""
import os
import re
from .golden_data import get_valid_test_ids

VALID_EXEC_PREFIXES = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}


def _build_title_blocks(steps):
    """Groups a station sheet's steps into Title blocks with 0-indexed relative step offsets."""
    blocks = []
    curr_block = None
    for idx, step in enumerate(steps):
        s_title = str(step.get("Title", "")).strip()
        if s_title != "" or curr_block is None:
            curr_block = {
                "title": s_title or "Untitled",
                "start_idx": idx,
                "steps": []
            }
            blocks.append(curr_block)
        offset = len(curr_block["steps"])
        curr_block["steps"].append({
            "global_idx": idx,
            "row_num": idx + 2,
            "offset": offset,
            "step": step
        })
    return blocks


def _infer_smart_retry_target(block_steps, curr_offset):
    """
    Infers the most likely intended retry target (0..curr_offset-1) when ExecMode 2:X is out of bounds.
    - If curr_offset == 0: returns ("1", "當前已是區塊第 0 步，建議改為 '1' (單步直接重試)")
    - If previous step (curr_offset - 1) is a setup/write command (e.g. setenv, Delay, send command):
      recommends 2:{curr_offset-1}.
    - Otherwise recommends 2:0.
    """
    if curr_offset == 0:
        return "1", "當前已是本區塊第 0 步，改為 '1' (單步原地重試)"

    curr_send = str(block_steps[curr_offset]["step"].get("Send", "")).strip().lower()
    prev_step = block_steps[curr_offset - 1]
    prev_send = str(prev_step["step"].get("Send", "")).strip()

    # Check if previous step is a paired write/setup command (e.g. fw_setenv before fw_printenv, or Delay before check)
    if ("printenv" in curr_send and "setenv" in prev_send.lower()) or (curr_offset >= 1 and not prev_send.startswith(":SfEnabled")):
        rec_mode = f"2:{curr_offset - 1}"
        return rec_mode, f"退回上一步 [步號 {curr_offset - 1}] ({prev_send[:32]}) 重新執行"

    return "2:0", f"退回本區塊最開頭 [步號 0] ({str(block_steps[0]['step'].get('Send', ''))[:32]})"


def _infer_smart_cond_target(block_steps, curr_offset, p_step, f_step):
    """
    Infers the most likely intended 4:Pass,Fail target when p_step or f_step is out of bounds or backward.
    - If curr_offset is ALREADY the last step of the Title block (curr_offset == len(block_steps) - 1),
      there is no later step to jump to -> recommend '0' (for :Delay) or '1' (for normal commands).
    - Often ':Delay,\"000\"' with '4:17,17' is an unconditional jump to the end of the Title block!
    """
    last_offset = len(block_steps) - 1
    curr_send = str(block_steps[curr_offset]["step"].get("Send", "")).strip()
    if curr_offset >= last_offset:
        rec = "0" if curr_send.startswith(":Delay") else "1"
        return rec, f"當前已是本區塊最後一步 [步號 {curr_offset}]，無後續步驟可跳轉，改為 '{rec}'"

    if p_step == f_step and p_step > last_offset:
        return f"4:{last_offset},{last_offset}", f"無條件跳至本區塊結尾 [步號 {last_offset}] ({str(block_steps[last_offset]['step'].get('Send', ''))[:28]})"

    new_p = min(max(p_step, curr_offset + 1), last_offset)
    new_f = min(max(f_step, curr_offset + 1), last_offset)
    return f"4:{new_p},{new_f}", f"修正跳轉至有效範圍 [Pass->步號 {new_p}, Fail->步號 {new_f}]"


def audit_workspace(workspace):
    """
    Runs the 10-Point Logic & Optimization Audit on a workspace dict.
    Also produces `choice_cards` for interactive 1-click resolution of ambiguous logic errors,
    and `auto_fixable_count` for mechanical issues that can be fixed automatically.
    """
    errors = []
    warnings = []
    suggestions = []
    choice_cards = []
    valid_tids = get_valid_test_ids()

    # Collect defined instruments, switches, and globals
    inst_names = {str(r.get("Name", "")).strip() for r in workspace.get("instruments", []) if r.get("Name")}
    sw_names = {str(r.get("Name", "")).strip() for r in workspace.get("switches", []) if r.get("Name")}
    marco_names = set(workspace.get("marcos", {}).keys()) | set(workspace.get("stations", {}).keys())

    g_ini = workspace.get("global_ini", {})
    settings_vars = set(g_ini.get("Settings", {}).keys())
    scripts_vars = set(g_ini.get("Scripts", {}).keys())

    # Rule 5A: Check DUTs & Instrument *$(VAR) against Global.ini [Settings]
    for sec_label, rows in [("DUTs", workspace.get("duts", [])), ("Instrument", workspace.get("instruments", []))]:
        for idx, r in enumerate(rows, start=2):
            row_text = " ".join([str(v) for v in r.values() if v])
            for m in re.finditer(r"\*\$\(([^)]+)\)", row_text):
                vname = m.group(1).strip()
                if vname not in settings_vars:
                    warnings.append(
                        f"[{sec_label} 第 {idx} 列] 變數 *$({vname}) 尚未在 Global.ini 的 [Settings] 區段宣告（系統將自動補入 [Settings]）"
                    )

    # Rule 5B: Check Instrument ControlDLL version against disk PE FileVersion
    src_file = workspace.get("source_file", "")
    base_search_dirs = []
    if src_file and os.path.exists(src_file):
        f_dir = os.path.dirname(os.path.abspath(src_file))
        base_search_dirs.extend([
            os.path.join(f_dir, "Device"), os.path.join(f_dir, "API"),
            os.path.join(os.path.dirname(f_dir), "Device"), os.path.join(os.path.dirname(f_dir), "API")
        ])
    base_search_dirs.extend([
        os.path.join(r"D:\PYTHON\自動化編寫EXCEL\Centimani_1.5.3_sample", "Device"),
        os.path.join(r"D:\PYTHON\自動化編寫EXCEL\Centimani_1.5.3_sample", "API")
    ])

    try:
        import win32api
        def _get_dll_ver(dll_name):
            if not dll_name:
                return None
            clean_name = os.path.basename(dll_name).strip()
            for s_dir in base_search_dirs:
                cand = os.path.join(s_dir, clean_name)
                if os.path.exists(cand):
                    try:
                        info = win32api.GetFileVersionInfo(cand, "\\")
                        ms, ls = info["FileVersionMS"], info["FileVersionLS"]
                        return f"{ms>>16}.{ms&0xFFFF}.{ls>>16}.{ls&0xFFFF}"
                    except Exception:
                        pass
            return None

        for idx, inst_row in enumerate(workspace.get("instruments", []), start=2):
            c_dll = inst_row.get("ControlDLL", "")
            pe_ver = _get_dll_ver(c_dll)
            if pe_ver:
                declared_ver = str(inst_row.get("Version", "")).strip()
                if declared_ver != pe_ver:
                    errors.append(
                        f"[Instrument 第 {idx} 列] 儀器 {inst_row.get('Name','')} 的 ControlDLL ({c_dll}) 版本 '{declared_ver}' 與實體 DLL 版本 '{pe_ver}' 不符！(Centimani 將報 Version mismatch，存檔時將自動校正為 {pe_ver})"
                    )
    except Exception:
        pass

    # Audit each Station Sheet
    for st_name, steps in workspace.get("stations", {}).items():
        if not steps:
            continue

        blocks = _build_title_blocks(steps)

        # Pre-scan all defined $global vars across the entire sheet so we know if a local var was defined earlier
        defined_local_by_title = {}  # var_name -> list of (title_name, row_num, global_idx)
        defined_global_vars = {"$ISN", "$sfisLANMAC", "$sfisWIFIMAC", "$sf69PN"}

        for b_idx, blk in enumerate(blocks):
            for item in blk["steps"]:
                s_ref = str(item["step"].get("Ref", "")).strip()
                s_send = str(item["step"].get("Send", "")).strip()
                if s_ref:
                    for part in s_ref.split(";"):
                        v_raw = part.split(":")[0].strip()
                        if not v_raw:
                            continue
                        if v_raw.startswith("$"):
                            defined_global_vars.add(v_raw[1:])
                        else:
                            defined_local_by_title.setdefault(v_raw, []).append((b_idx, item["row_num"], item["global_idx"]))
                if s_send.startswith((":SetVal", ":SetOprVal", ":SetCdtiVal")):
                    m_set = re.search(r'"(\$?[A-Za-z0-9_]+)"', s_send)
                    if m_set:
                        vn = m_set.group(1)
                        if vn.startswith("$"):
                            defined_global_vars.add(vn[1:])
                        else:
                            defined_local_by_title.setdefault(vn, []).append((b_idx, item["row_num"], item["global_idx"]))

        has_phase_97 = False
        seen_phases = {}
        prev_phase_val = None
        obtain_lock_open = False
        obtain_lock_row = None
        ni6008_single_Check_streak = 0

        for b_idx, blk in enumerate(blocks):
            b_steps = blk["steps"]
            b_len = len(b_steps)

            # Local vars defined so far within THIS Title block
            curr_block_locals = set()

            for item in b_steps:
                idx = item["global_idx"]
                r_num = item["row_num"]
                offset = item["offset"]
                step = item["step"]

                s_idx = str(step.get("Index", "")).strip()
                s_phase = str(step.get("Phase", "")).strip()
                s_title = str(step.get("Title", "")).strip()
                s_marco = str(step.get("Marco", "")).strip()
                s_inst = str(step.get("Instrument", "")).strip()
                s_sw = str(step.get("Switch", "")).strip()
                s_send = str(step.get("Send", "")).strip()
                s_endp = str(step.get("EndPrompt", "")).strip()
                s_ref = str(step.get("Ref", "")).strip()
                s_val = str(step.get("Validation", "")).strip()
                s_wait = str(step.get("Waiting", "")).strip()
                s_mode = str(step.get("ExecMode", "")).strip()
                s_tid = str(step.get("TestID", "")).strip()

                # Rule 2: Index continuity
                expected_idx = f"{idx:03d}"
                if s_idx != expected_idx and s_idx != str(idx):
                    warnings.append(f"[{st_name} 第 {r_num} 列] Index 序號 '{s_idx}' 不連續（應為 '{expected_idx}'，可自動重編）")

                # Rule 8: Phase lifecycle
                if s_phase != "":
                    p_num_str = s_phase.split(":")[0].strip()
                    try:
                        p_int = int(float(p_num_str))
                        if p_int == 97:
                            has_phase_97 = True
                        if 1 <= p_int <= 96:
                            if p_int in seen_phases and p_int != prev_phase_val:
                                warnings.append(
                                    f"[{st_name} 第 {r_num} 列] Phase '{p_int}' 與第 {seen_phases[p_int]} 列重複（官方建議 1~96 避免重複 Phase）"
                                )
                            seen_phases[p_int] = r_num
                        prev_phase_val = p_int
                    except ValueError:
                        errors.append(f"[{st_name} 第 {r_num} 列] Phase 欄位值 '{s_phase}' 非有效整數！")

                # Rule 1: TestID validation
                if not s_tid:
                    errors.append(f"[{st_name} 第 {r_num} 列] 缺少第 16 欄 TestID（系統可自動補齊合法 7 碼代碼）")
                elif len(s_tid) != 7 and "," not in s_tid and ";" not in s_tid:
                    warnings.append(f"[{st_name} 第 {r_num} 列] TestID '{s_tid}' 長度非標準 7 碼")
                elif valid_tids and s_tid not in valid_tids and "," not in s_tid and ";" not in s_tid:
                    warnings.append(f"[{st_name} 第 {r_num} 列] TestID '{s_tid}' 未出現在 Test Item Code V2.04 標準表中")

                # Rule 3: ExecMode relative step bounds + interactive choice card generation
                if s_mode == "":
                    warnings.append(f"[{st_name} 第 {r_num} 列] ExecMode 為空白（建議明確填寫 0 或 1）")
                else:
                    mode_head = s_mode.split(":")[0].strip()
                    if mode_head not in VALID_EXEC_PREFIXES:
                        errors.append(f"[{st_name} 第 {r_num} 列] ExecMode '{s_mode}' 主代碼無效（僅支援 0~9）")
                    elif mode_head == "2":
                        if ":" not in s_mode:
                            errors.append(f"[{st_name} 第 {r_num} 列] ExecMode '2' 缺少冒號與 RetryPoint（格式應為 2:0）")
                        else:
                            try:
                                r_pt = int(s_mode.split(":", 1)[1].strip())
                                if r_pt < 0 or r_pt > offset or (offset == 0 and r_pt >= 0 and r_pt > 0):
                                    rec_mode, rec_reason = _infer_smart_retry_target(b_steps, offset)
                                    errors.append(
                                        f"[{st_name} 第 {r_num} 列] ExecMode '{s_mode}' 重試步號 ({r_pt}) 越界！"
                                        f"（當前位於 Title '{blk['title']}' 的第 {offset} 步，區塊共 {b_len} 步 👉 推薦改為 '{rec_mode}'：{rec_reason}）"
                                    )
                                    # Build interactive choice card
                                    options = [
                                        {"value": rec_mode, "label": f"【智慧推薦】改為 {rec_mode} — {rec_reason}", "recommended": True}
                                    ]
                                    if rec_mode != "2:0" and offset > 0:
                                        options.append({
                                            "value": "2:0",
                                            "label": f"改為 2:0 — 退回本區塊第 0 步 ({str(b_steps[0]['step'].get('Send', ''))[:35]})",
                                            "recommended": False
                                        })
                                    if rec_mode != "1":
                                        options.append({
                                            "value": "1",
                                            "label": "改為 1 — 僅單步原地重試本行指令",
                                            "recommended": False
                                        })
                                    # Also list all valid prior steps in this Title block
                                    step_choices = []
                                    for prev_item in b_steps[:offset + 1]:
                                        p_off = prev_item["offset"]
                                        p_send = str(prev_item["step"].get("Send", "")).strip()
                                        p_desc = str(prev_item["step"].get("Description", "")).strip()
                                        step_choices.append({
                                            "offset": p_off,
                                            "row_num": prev_item["row_num"],
                                            "mode_val": f"2:{p_off}" if p_off < offset else "1",
                                            "text": f"[步號 {p_off} / 第 {prev_item['row_num']} 列] {p_send[:40]} ({p_desc[:24]})"
                                        })
                                    choice_cards.append({
                                        "card_id": f"{st_name}_{idx}_exec2",
                                        "sheet": st_name,
                                        "global_idx": idx,
                                        "row_num": r_num,
                                        "title_block": blk["title"],
                                        "current_offset": offset,
                                        "block_total_steps": b_len,
                                        "send_cmd": s_send,
                                        "description": str(step.get("Description", "")),
                                        "field": "ExecMode",
                                        "current_value": s_mode,
                                        "recommended_value": rec_mode,
                                        "issue_title": f"[{st_name} 第 {r_num} 列] 重試步號 '{s_mode}' 越界（本區塊共 {b_len} 步，目前在第 {offset} 步）",
                                        "options": options,
                                        "block_steps": step_choices
                                    })
                            except ValueError:
                                errors.append(f"[{st_name} 第 {r_num} 列] ExecMode '{s_mode}' 重試點非整數！")
                    elif mode_head == "4":
                        parts = s_mode.split(":", 1)[1].split(",") if ":" in s_mode else []
                        if len(parts) != 2:
                            errors.append(f"[{st_name} 第 {r_num} 列] ExecMode '{s_mode}' 格式錯誤（應為 4:PassStep,FailStep）")
                        else:
                            try:
                                p_st, f_st = int(parts[0].strip()), int(parts[1].strip())
                                if p_st <= offset or f_st <= offset:
                                    rec_mode, rec_reason = _infer_smart_cond_target(b_steps, offset, p_st, f_st)
                                    errors.append(
                                        f"[{st_name} 第 {r_num} 列] ExecMode '{s_mode}' 違反『不可往回跳 (<= 當前步號 {offset})』規定！"
                                    )
                                elif p_st >= b_len or f_st >= b_len:
                                    rec_mode, rec_reason = _infer_smart_cond_target(b_steps, offset, p_st, f_st)
                                    warnings.append(
                                        f"[{st_name} 第 {r_num} 列] ExecMode '{s_mode}' 跳轉目標超過當前 Title 區塊總步數 ({b_len}) 👉 推薦改為 '{rec_mode}'"
                                    )
                                    options = [
                                        {"value": rec_mode, "label": f"【智慧推薦】改為 {rec_mode} — {rec_reason}", "recommended": True},
                                        {"value": "0", "label": "改為 0 — 不跳轉，依序往下執行", "recommended": False}
                                    ]
                                    step_choices = []
                                    for sub_item in b_steps:
                                        p_off = sub_item["offset"]
                                        p_send = str(sub_item["step"].get("Send", "")).strip()
                                        p_desc = str(sub_item["step"].get("Description", "")).strip()
                                        step_choices.append({
                                            "offset": p_off,
                                            "row_num": sub_item["row_num"],
                                            "mode_val": f"4:{p_off},{p_off}",
                                            "text": f"[步號 {p_off} / 第 {sub_item['row_num']} 列] {p_send[:40]} ({p_desc[:24]})"
                                        })
                                    choice_cards.append({
                                        "card_id": f"{st_name}_{idx}_exec4",
                                        "sheet": st_name,
                                        "global_idx": idx,
                                        "row_num": r_num,
                                        "title_block": blk["title"],
                                        "current_offset": offset,
                                        "block_total_steps": b_len,
                                        "send_cmd": s_send,
                                        "description": str(step.get("Description", "")),
                                        "field": "ExecMode",
                                        "current_value": s_mode,
                                        "recommended_value": rec_mode,
                                        "issue_title": f"[{st_name} 第 {r_num} 列] 條件跳轉 '{s_mode}' 超過區塊步數（本區塊最後一步為步號 {b_len - 1}）",
                                        "options": options,
                                        "block_steps": step_choices
                                    })
                            except ValueError:
                                errors.append(f"[{st_name} 第 {r_num} 列] ExecMode '{s_mode}' 跳轉步號非整數！")

                # Rule 4: Local vs Global ($) Ref variable lifecycle across Title blocks
                if s_ref:
                    for part in s_ref.split(";"):
                        v_raw = part.split(":")[0].strip()
                        if v_raw and not v_raw.startswith("$"):
                            curr_block_locals.add(v_raw)
                if s_send.startswith((":SetVal", ":SetOprVal", ":SetCdtiVal")):
                    m_set = re.search(r'"([A-Za-z0-9_]+)"', s_send)
                    if m_set:
                        curr_block_locals.add(m_set.group(1))

                row_all_str = f"{s_send} {s_val} {s_sw} {s_inst}"
                for m_var in re.finditer(r"(?<!\*)\*\(([^)$]+)\)", row_all_str):
                    used_v = m_var.group(1).strip()
                    if used_v in ["ISN", "60ISN", "SAGCSN", "SSN", "lbMAC", "cDT"]:
                        continue
                    if used_v not in curr_block_locals and used_v not in defined_global_vars:
                        prev_defs = defined_local_by_title.get(used_v, [])
                        earlier_defs = [d for d in prev_defs if d[0] < b_idx]
                        if earlier_defs:
                            def_row = earlier_defs[0][1]
                            warnings.append(
                                f"[{st_name} 第 {r_num} 列] 跨 Title 引用了變數 *({used_v})，但第 {def_row} 列定義時未加 '$' 前綴（離開該 Title 會被清空，系統可自動升級為 ${used_v}）"
                            )

                # Rule 5B: Station *$(VAR) in Global.ini [Scripts]
                for m_gvar in re.finditer(r"\*\$\(([^)]+)\)", row_all_str):
                    gv = m_gvar.group(1).strip()
                    if gv not in scripts_vars:
                        if gv in settings_vars:
                            errors.append(
                                f"[{st_name} 第 {r_num} 列] 站位引用了 *$({gv})，但該變數只定義在 Global.ini [Settings] 而未定義於 [Scripts]！（系統可自動同步至 [Scripts]）"
                            )
                        else:
                            warnings.append(
                                f"[{st_name} 第 {r_num} 列] 測試步驟引用了未在 Global.ini [Scripts] 宣告的變數 *$({gv})（系統可自動補入 [Scripts]）"
                            )

                # Rule 7: :ObtainDevice / :ReleaseDevice pairing & ExecMode=3
                if ":ObtainDevice" in s_send or ":ObtainSubDevice" in s_send:
                    if obtain_lock_open:
                        warnings.append(
                            f"[{st_name} 第 {r_num} 列] 重複呼叫 :ObtainDevice（前一次於第 {obtain_lock_row} 列尚未 ReleaseDevice）"
                        )
                        choice_cards.append({
                            "card_id": f"{st_name}_{idx}_obtain",
                            "sheet": st_name,
                            "global_idx": idx,
                            "row_num": r_num,
                            "title_block": blk["title"],
                            "current_offset": offset,
                            "block_total_steps": b_len,
                            "send_cmd": s_send,
                            "description": str(step.get("Description", "")),
                            "field": "ExecMode",
                            "current_value": s_mode,
                            "recommended_value": "6",
                            "issue_title": f"[{st_name} 第 {r_num} 列] 重複呼叫 :ObtainDevice（第 {obtain_lock_row} 列已取得裝置鎖尚未釋放）",
                            "options": [
                                {"value": "6", "label": "【推薦】將此列重複的 :ObtainDevice 設為 ExecMode = 6 (Skip 略過)", "recommended": True},
                                {"value": s_mode, "label": f"維持原狀 (ExecMode = {s_mode})", "recommended": False}
                            ],
                            "block_steps": []
                        })
                    obtain_lock_open = True
                    obtain_lock_row = r_num
                elif ":ReleaseDevice" in s_send or ":ReleaseSubDevice" in s_send:
                    obtain_lock_open = False
                    if s_mode not in ["3", "6"]:
                        warnings.append(
                            f"[{st_name} 第 {r_num} 列] :ReleaseDevice 的 ExecMode 應設為 '3' (Continue)，目前為 '{s_mode}'（系統可自動改為 3）"
                        )

                # Rule 10: Cycle time optimization suggestions
                if "@" in s_send and not s_send.startswith(":") and s_endp == "" and s_wait not in ["", "0"]:
                    suggestions.append(
                        f"[{st_name} 第 {r_num} 列] 序列埠/命令列指令 '{s_send[:28]}...' 未設定 EndPrompt（如 # 或 >），設定後可縮短等待時間"
                    )
                if ":CheckLimit" in s_send:
                    ni6008_single_Check_streak += 1
                    if ni6008_single_Check_streak == 6:
                        suggestions.append(
                            f"[{st_name} 第 {r_num} 列] 連續多步單獨呼叫 :CheckLimit，建議可收納為共用 Marco 分頁以精簡主表"
                        )
                else:
                    ni6008_single_Check_streak = 0

        if obtain_lock_open:
            warnings.append(f"[{st_name}] 腳本結束前仍有 :ObtainDevice (第 {obtain_lock_row} 列) 未呼叫 :ReleaseDevice 釋放")
        if not has_phase_97:
            warnings.append(f"[{st_name}] 缺少 Phase 97 (End Test 強制收尾階段)，建議加入斷電與治具復位步驟")

    return {
        "passed": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "suggestion_count": len(suggestions),
        "choice_card_count": len(choice_cards),
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
        "choice_cards": choice_cards
    }


def auto_fix_workspace(workspace, user_choices=None):
    """
    One-Click Smart Repair Engine (V2.1):
    1. Re-indexes all steps sequentially (000, 001, ...) and updates Index_N header.
    2. Fills any empty TestID with valid 7-character code ('B7PL025').
    3. Upgrades cross-Title Ref variables to global '$VAR' automatically.
    4. Applies smart target inference (or user_choices from choice cards) to out-of-range ExecMode '2:X' and '4:P,F'.
    5. Sets :ReleaseDevice ExecMode to '3' (even if it was '0' or '6' at the end of a test).
    6. Syncs all *$(VAR) into the correct Global.ini section ([Settings] vs [Scripts]).
    Returns (fixed_logs, modified_cells) where modified_cells is a list of dicts for Excel highlighting.
    """
    user_choices = user_choices or {}
    fixed_logs = []
    modified_cells = []  # [{"sheet": st_name, "row": r_num, "col_name": "ExecMode", "old": ..., "new": ..., "note": ...}]

    g_ini = workspace.setdefault("global_ini", {"Settings": {}, "Scripts": {}})
    settings_dict = g_ini.setdefault("Settings", {})
    scripts_dict = g_ini.setdefault("Scripts", {})

    # 1. Sync DUTs & Instrument *$(VAR) to [Settings]
    for sec_key in ["duts", "instruments"]:
        for row in workspace.get(sec_key, []):
            row_text = " ".join([str(v) for v in row.values() if v])
            for m in re.finditer(r"\*\$\(([^)]+)\)", row_text):
                vname = m.group(1).strip()
                if vname not in settings_dict:
                    settings_dict[vname] = scripts_dict.get(vname, "192.168.1.10" if "IP" in vname else "COM1")
                    fixed_logs.append(f"已自動將環境表變數 *$({vname}) 補齊至 Global.ini [Settings] 區段")

    # 1-0. Auto-fix DUTs duplicate DUT Name & Connection Names (Resolves Centimani '已經加入含有相同索引鍵的項目')
    duts = workspace.get("duts", [])
    if len(duts) > 1:
        seen_dut_names = set()
        seen_conn_names = set()
        for idx, d in enumerate(duts, start=1):
            d_name = str(d.get("DUT Name", "")).strip()
            if not d_name or d_name in seen_dut_names:
                base = d_name.split("_")[0] if "_" in d_name else (d_name or "DUT")
                new_d_name = f"{base}_{idx}"
                d["DUT Name"] = new_d_name
                fixed_logs.append(f"[DUTs 表] 第 {idx} 列 DUT Name 重複或空白，已自動更名為唯一識別名 '{new_d_name}'")
            seen_dut_names.add(d.get("DUT Name"))

            # Update Station column to MB,1 / MB,2 / MB,3 / MB,4
            st_val = str(d.get("Station", "")).strip()
            if "," in st_val:
                st_prefix = st_val.split(",")[0].strip()
                d["Station"] = f"{st_prefix},{idx}"

            # Make connection names unique across slots (e.g. UART_1, UART_2, CmdConsole_1)
            # and remove duplicate Utility connections
            for c_col in [f"Connection{i} (Type,Name,ConnectString)" for i in range(1, 5)] + ["Connection4(Type,Name,ConnectString)"]:
                if c_col in d and d[c_col]:
                    raw_c = str(d[c_col]).strip()
                    if "UtilityLibrary.dll" in raw_c:
                        # Centimani loads Utility automatically; duplicate declaration in DUTs causes duplicate key crash
                        d[c_col] = ""
                        fixed_logs.append(f"[DUTs 表] 第 {idx} 列已自動移除多餘的 UtilityLibrary 宣告（Centimani 內建加載，宣告會造成索引鍵衝突）")
                        continue
                    # Check connection name in "Type","Name","ConnectString"
                    parts = [p.strip().strip('"') for p in raw_c.split(",")]
                    if len(parts) >= 2:
                        c_type = parts[0]
                        c_name = parts[1]
                        c_conn = ",".join(parts[2:])
                        if c_name in seen_conn_names:
                            new_c_name = f"{c_name}_{idx}"
                            d[c_col] = f'"{c_type}","{new_c_name}","{c_conn}"'
                            fixed_logs.append(f"[DUTs 表] 第 {idx} 列連線名稱 '{c_name}' 重複，已自動更名為 '{new_c_name}' 避免 Centimani 索引鍵衝突")
                            seen_conn_names.add(new_c_name)
                        else:
                            seen_conn_names.add(c_name)

    # 1A. Auto-verify & correct DLL versions in Instrument & Switch tables against disk PE FileVersion
    src_file = workspace.get("source_file", "")
    base_search_dirs = []
    if src_file and os.path.exists(src_file):
        f_dir = os.path.dirname(os.path.abspath(src_file))
        base_search_dirs.extend([
            os.path.join(f_dir, "Device"), os.path.join(f_dir, "API"),
            os.path.join(os.path.dirname(f_dir), "Device"), os.path.join(os.path.dirname(f_dir), "API")
        ])
    # Also add standard project sample paths
    base_search_dirs.extend([
        os.path.join(r"D:\PYTHON\自動化編寫EXCEL\Centimani_1.5.3_sample", "Device"),
        os.path.join(r"D:\PYTHON\自動化編寫EXCEL\Centimani_1.5.3_sample", "API")
    ])

    try:
        import win32api
        def _get_dll_ver(dll_name):
            if not dll_name:
                return None
            clean_name = os.path.basename(dll_name).strip()
            for s_dir in base_search_dirs:
                cand = os.path.join(s_dir, clean_name)
                if os.path.exists(cand):
                    try:
                        info = win32api.GetFileVersionInfo(cand, "\\")
                        ms, ls = info["FileVersionMS"], info["FileVersionLS"]
                        return f"{ms>>16}.{ms&0xFFFF}.{ls>>16}.{ls&0xFFFF}"
                    except Exception:
                        pass
            return None

        for inst_row in workspace.get("instruments", []):
            c_dll = inst_row.get("ControlDLL", "")
            pe_ver = _get_dll_ver(c_dll)
            if pe_ver:
                old_ver = str(inst_row.get("Version", "")).strip()
                if old_ver != pe_ver:
                    inst_row["Version"] = pe_ver
                    fixed_logs.append(f"[Instrument 表] 自動校正 {c_dll} 版本號為實體 DLL 檔案版本 '{pe_ver}' (原為 '{old_ver}')")
                    modified_cells.append({
                        "sheet": "Instrument", "row": 2, "col_name": "Version",
                        "old": old_ver, "new": pe_ver, "note": f"實體 DLL 檔案版本為 {pe_ver}，校正以避免 Centimani 報 Version mismatch"
                    })

        for sw_row in workspace.get("switches", []):
            c_dll = sw_row.get("ControlDLL", "")
            pe_ver = _get_dll_ver(c_dll)
            if pe_ver:
                old_ver = str(sw_row.get("Version", "")).strip()
                if old_ver != pe_ver:
                    sw_row["Version"] = pe_ver
                    fixed_logs.append(f"[Switch 表] 自動校正 {c_dll} 版本號為實體 DLL 檔案版本 '{pe_ver}' (原為 '{old_ver}')")
                    modified_cells.append({
                        "sheet": "Switch", "row": 2, "col_name": "Version",
                        "old": old_ver, "new": pe_ver, "note": f"實體 DLL 檔案版本為 {pe_ver}，校正以避免 Centimani 報 Version mismatch"
                    })
    except Exception:
        pass

    # 1B. Auto-sync Instrument 'Mount' column for newly generated mother templates
    if not workspace.get("source_file"):
        used_funcs_by_station = {}
        for st_name, steps in workspace.get("stations", {}).items():
            for st_row in steps:
                fn = str(st_row.get("Instrument", "")).strip()
                if fn:
                    used_funcs_by_station.setdefault(fn.upper(), set()).add(st_name)
        mounted_funcs = set()
        for inst_row in workspace.get("instruments", []):
            inst_funcs = [f.strip().upper() for f in str(inst_row.get("Functions", "")).split(",") if f.strip()]
            matched_stations = set()
            for fn in inst_funcs:
                if fn in used_funcs_by_station and fn not in mounted_funcs:
                    matched_stations |= used_funcs_by_station[fn]
                    mounted_funcs.add(fn)
            inst_row["Mount"] = ",".join(sorted(matched_stations)) if matched_stations else ""

    # 2. Repair each Station Sheet
    for st_name, steps in workspace.get("stations", {}).items():
        if not steps:
            continue

        blocks = _build_title_blocks(steps)

        # Find all *(VAR) referenced across the sheet
        all_used_vars = set()
        for step in steps:
            row_text = " ".join([str(v) for v in step.values() if v])
            for m in re.finditer(r"(?<!\*)\*\(([^)$]+)\)", row_text):
                all_used_vars.add(m.group(1).strip())

        obtain_lock_open = False

        for b_idx, blk in enumerate(blocks):
            b_steps = blk["steps"]
            b_len = len(b_steps)

            for item in b_steps:
                idx = item["global_idx"]
                r_num = item["row_num"]
                offset = item["offset"]
                step = item["step"]

                # Re-index
                new_idx = f"{idx:03d}"
                old_idx = str(step.get("Index", "")).strip()
                if old_idx != new_idx:
                    step["Index"] = new_idx
                    modified_cells.append({
                        "sheet": st_name, "row": r_num, "col_name": "Index",
                        "old": old_idx, "new": new_idx, "note": f"自動重編連續序號 {new_idx}"
                    })

                # Fix missing TestID
                tid = str(step.get("TestID", "")).strip()
                if not tid:
                    step["TestID"] = "B7PL025"
                    fixed_logs.append(f"[{st_name} 第 {r_num} 列] 已自動補齊空白 TestID 為 'B7PL025'")
                    modified_cells.append({
                        "sheet": st_name, "row": r_num, "col_name": "TestID",
                        "old": "", "new": "B7PL025", "note": "補齊空白 TestID 為標準代碼 B7PL025"
                    })

                s_send = str(step.get("Send", "")).strip()
                s_mode = str(step.get("ExecMode", "")).strip()

                # Check if user explicitly picked an option on a Choice Card
                for c_suffix in ["exec2", "exec4", "obtain"]:
                    cid = f"{st_name}_{idx}_{c_suffix}"
                    if cid in user_choices:
                        chosen_val = str(user_choices[cid]).strip()
                        if chosen_val and chosen_val != s_mode:
                            step["ExecMode"] = chosen_val
                            fixed_logs.append(f"[{st_name} 第 {r_num} 列] 已依您的點選將 ExecMode 由 '{s_mode}' 改為 '{chosen_val}'")
                            modified_cells.append({
                                "sheet": st_name, "row": r_num, "col_name": "ExecMode",
                                "old": s_mode, "new": chosen_val, "note": f"原為 '{s_mode}'，已修正為 '{chosen_val}'"
                            })
                            s_mode = chosen_val

                # Fix :ObtainDevice / :ReleaseDevice pairing & ExecMode -> 3
                if ":ObtainDevice" in s_send or ":ObtainSubDevice" in s_send:
                    if obtain_lock_open and s_mode != "6":
                        step["ExecMode"] = "6"
                        fixed_logs.append(f"[{st_name} 第 {r_num} 列] 重複呼叫 :ObtainDevice（前次未釋放），已設為 ExecMode='6' (Skip)")
                        modified_cells.append({
                            "sheet": st_name, "row": r_num, "col_name": "ExecMode",
                            "old": s_mode, "new": "6", "note": f"前次 :ObtainDevice 尚未釋放，將重複借鎖改為 6 (Skip)"
                        })
                        s_mode = "6"
                    else:
                        obtain_lock_open = True
                elif ":ReleaseDevice" in s_send or ":ReleaseSubDevice" in s_send:
                    obtain_lock_open = False
                    if s_mode != "3":
                        step["ExecMode"] = "3"
                        fixed_logs.append(f"[{st_name} 第 {r_num} 列] 已將 :ReleaseDevice 的 ExecMode 由 '{s_mode}' 修正為 '3' (確保必釋放鎖定)")
                        modified_cells.append({
                            "sheet": st_name, "row": r_num, "col_name": "ExecMode",
                            "old": s_mode, "new": "3", "note": f"原為 '{s_mode}'，修正 :ReleaseDevice 為 '3' (Continue)"
                        })
                        s_mode = "3"

                # Smart Fix ExecMode 2:X out of bounds
                if s_mode.startswith("2:"):
                    try:
                        r_pt = int(s_mode[2:].strip())
                        if r_pt < 0 or r_pt > offset or (offset == 0 and r_pt >= 0):
                            rec_mode, rec_reason = _infer_smart_retry_target(b_steps, offset)
                            step["ExecMode"] = rec_mode
                            fixed_logs.append(f"[{st_name} 第 {r_num} 列] 智慧修正越界 ExecMode '{s_mode}' -> '{rec_mode}' ({rec_reason})")
                            modified_cells.append({
                                "sheet": st_name, "row": r_num, "col_name": "ExecMode",
                                "old": s_mode, "new": rec_mode, "note": f"原 '{s_mode}' 越界，智慧修正為 '{rec_mode}' ({rec_reason})"
                            })
                    except ValueError:
                        pass

                # Smart Fix ExecMode 4:P,F out of bounds
                elif s_mode.startswith("4:"):
                    parts = s_mode[2:].split(",")
                    if len(parts) == 2:
                        try:
                            p_st, f_st = int(parts[0].strip()), int(parts[1].strip())
                            if p_st <= offset or f_st <= offset or p_st >= b_len or f_st >= b_len:
                                rec_mode, rec_reason = _infer_smart_cond_target(b_steps, offset, p_st, f_st)
                                step["ExecMode"] = rec_mode
                                fixed_logs.append(f"[{st_name} 第 {r_num} 列] 智慧修正跳轉 ExecMode '{s_mode}' -> '{rec_mode}' ({rec_reason})")
                                modified_cells.append({
                                    "sheet": st_name, "row": r_num, "col_name": "ExecMode",
                                    "old": s_mode, "new": rec_mode, "note": f"原 '{s_mode}' 超出區塊範圍，修正為 '{rec_mode}' ({rec_reason})"
                                })
                        except ValueError:
                            pass

                # Upgrade Ref local variables to $ global if referenced in other Title blocks
                s_ref = str(step.get("Ref", "")).strip()
                if s_ref:
                    new_ref_parts = []
                    changed_ref = False
                    for part in s_ref.split(";"):
                        p_str = part.strip()
                        if not p_str:
                            continue
                        v_head = p_str.split(":")[0].strip()
                        if not v_head.startswith("$") and v_head in all_used_vars:
                            p_str = "$" + p_str
                            changed_ref = True
                        new_ref_parts.append(p_str)
                    if changed_ref:
                        new_ref_val = ";\n".join(new_ref_parts)
                        step["Ref"] = new_ref_val
                        fixed_logs.append(f"[{st_name} 第 {r_num} 列] 已將跨 Title 使用的 Ref 變數升級為 '$' 全域變數 ({new_ref_val})")
                        modified_cells.append({
                            "sheet": st_name, "row": r_num, "col_name": "Ref",
                            "old": s_ref, "new": new_ref_val, "note": "跨 Title 引用之變數自動加上 '$' 升級為全域變數"
                        })

                # Also check :SetVal,"VAR" without $ if used across Title blocks
                if s_send.startswith((":SetVal", ":SetOprVal", ":SetCdtiVal")):
                    m_set = re.search(r'(:Set(?:Opr|Cdti)?Val\s*,\s*")([A-Za-z0-9_]+)(")', s_send)
                    if m_set and m_set.group(2) in all_used_vars:
                        v_local = m_set.group(2)
                        new_send = s_send[:m_set.start(2)] + "$" + v_local + s_send[m_set.end(2):]
                        step["Send"] = new_send
                        fixed_logs.append(f"[{st_name} 第 {r_num} 列] 已將 :SetVal 變數 '{v_local}' 升級為 '${v_local}' 全域變數")
                        modified_cells.append({
                            "sheet": st_name, "row": r_num, "col_name": "Send",
                            "old": s_send, "new": new_send, "note": f"跨 Title 使用之變數升級為 ${v_local}"
                        })

                # Sync Station *$(VAR) to Global.ini [Scripts]
                row_text = " ".join([str(v) for v in step.values() if v])
                for m in re.finditer(r"\*\$\(([^)]+)\)", row_text):
                    vname = m.group(1).strip()
                    if vname not in scripts_dict:
                        scripts_dict[vname] = settings_dict.get(vname, "192.168.1.10" if "IP" in vname else "DEFAULT_VAL")
                        fixed_logs.append(f"[{st_name} 第 {r_num} 列] 已自動將站位變數 *$({vname}) 補齊至 Global.ini [Scripts] 區段")

    workspace["_modified_cells"] = modified_cells
    return fixed_logs
