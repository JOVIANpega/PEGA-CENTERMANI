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


def _analyze_block_jump_flow(st_name, blk, warnings):
    """
    分析單一 Title 區塊內的跳轉控制流 (Control Flow)：
    1. 偵測因 4:P,F 跳轉而永遠走不到的「死步 (Unreachable Step)」。
    2. 偵測「分支貫穿 (Fall-through)」：當 4:P,F 分成 PASS(P) 與 FAIL(F) 兩條路徑 (P < F) 時，
       若 PASS 分支最後一步 (F - 1) 沒有設 4:N,N (例如跳至末行 :Delay) 跳過 FAIL 分支，
       執行完 PASS 分支後會直接掉進 FAIL 分支。
    """
    b_steps = blk.get("steps", [])
    b_len = len(b_steps)
    if b_len <= 1:
        return

    adj = {i: [] for i in range(b_len)}
    branch_splits = []
    for i, item in enumerate(b_steps):
        s_mode = str(item["step"].get("ExecMode", "")).strip()
        if s_mode.startswith("4:") and "," in s_mode:
            parts = s_mode[2:].split(",")
            if len(parts) == 2:
                try:
                    p_st, f_st = int(parts[0].strip()), int(parts[1].strip())
                    if 0 <= p_st < b_len:
                        adj[i].append(p_st)
                    if 0 <= f_st < b_len and f_st != p_st:
                        adj[i].append(f_st)
                    if i < p_st < f_st < b_len:
                        branch_splits.append((i, p_st, f_st, item["row_num"]))
                    continue
                except ValueError:
                    pass
        if i + 1 < b_len:
            adj[i].append(i + 1)

    visited = {0}
    queue = [0]
    while queue:
        cur = queue.pop(0)
        for nxt in adj.get(cur, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)

    for i, item in enumerate(b_steps):
        if i not in visited:
            s_mode = str(item["step"].get("ExecMode", "")).strip()
            if s_mode != "6":
                warnings.append(
                    f"[{st_name} 第 {item['row_num']} 列] 跳轉死步警告：Title '{blk['title']}' 的第 {i} 步"
                    f" ({str(item['step'].get('Send', ''))[:30]}) 被前方 4:P,F 跳過且無任何路徑可到達"
                )

    for src_off, p_st, f_st, src_row in branch_splits:
        if f_st >= b_len - 1:
            # FAIL jumps directly to the last convergence/exit step of the block (Guard pattern)
            continue
        end_of_pass = f_st - 1
        if end_of_pass >= p_st:
            end_mode = str(b_steps[end_of_pass]["step"].get("ExecMode", "")).strip()
            has_skip_out = False
            if end_mode.startswith("4:") and "," in end_mode:
                try:
                    ep, ef = [int(x.strip()) for x in end_mode[2:].split(",", 1)]
                    if ep >= f_st and ef >= f_st:
                        has_skip_out = True
                except ValueError:
                    pass
            if not has_skip_out:
                end_row = b_steps[end_of_pass]["row_num"]
                warnings.append(
                    f"[{st_name} 第 {end_row} 列] 分支貫穿警告：第 {src_row} 列使用 4:{p_st},{f_st} 分流，"
                    f"但 PASS 分支末行（第 {end_row} 列）未設 4:N,N 跳過 FAIL 分支（步號 {f_st}），執行完會直接掉入 FAIL 分支"
                )


def _build_jump_summary(st_name, sheet_type, blk, block_retry_count):
    """
    將含有 2:XX 或 4:P,F 的 Title 區塊翻譯為白話流程摘要，並判斷狀態 (ok / warning / error) 與一鍵推薦修法。
    """
    b_steps = blk.get("steps", [])
    b_len = len(b_steps)
    if b_len == 0:
        return None

    narratives = []
    status = "ok"
    quick_fix = None
    has_jump = False

    def _step_brief(off_idx):
        if 0 <= off_idx < b_len:
            cmd = str(b_steps[off_idx]["step"].get("Send", "")).strip() or "(無指令)"
            return f"步 {off_idx:02d} ({cmd[:22]})"
        return f"步 {off_idx:02d} (⚠️越界)"

    for i, item in enumerate(b_steps):
        s_mode = str(item["step"].get("ExecMode", "")).strip()
        s_send = str(item["step"].get("Send", "")).strip() or "(無指令)"
        r_num = item["row_num"]

        if s_mode.startswith("2:"):
            has_jump = True
            try:
                r_pt = int(s_mode[2:].strip())
                if r_pt < 0 or r_pt > i or (i == 0 and r_pt > 0):
                    status = "error"
                    rec_mode, rec_reason = _infer_smart_retry_target(b_steps, i)
                    narratives.append(f"❌ 步 {i:02d} ({s_send[:22]})：失敗跳回步 {r_pt:02d}【越界錯誤，區塊僅 {b_len} 步】")
                    if not quick_fix:
                        quick_fix = {
                            "global_idx": item["global_idx"], "row_num": r_num, "field": "ExecMode",
                            "old": s_mode, "new": rec_mode, "label": f"一鍵修正第 {r_num} 列為 {rec_mode}（{rec_reason}）"
                        }
                else:
                    if block_retry_count == 0 and status == "ok":
                        status = "warning"
                    if block_retry_count is None:
                        retry_txt = "沿用預設重試設定"
                    elif block_retry_count > 0:
                        retry_txt = f"Title 重試上限 {block_retry_count} 次"
                    else:
                        retry_txt = "⚠️ Title RetryCount 明確設為 0"
                    narratives.append(f"↩ 步 {i:02d} ({s_send[:22]})：失敗時跳回 {_step_brief(r_pt)} 重試（{retry_txt}）")
            except ValueError:
                status = "error"
                narratives.append(f"❌ 步 {i:02d} ({s_send[:22]})：ExecMode '{s_mode}' 格式非整數")

        elif s_mode.startswith("4:") and "," in s_mode:
            has_jump = True
            parts = s_mode[2:].split(",")
            if len(parts) == 2:
                try:
                    p_st, f_st = int(parts[0].strip()), int(parts[1].strip())
                    if p_st <= i or f_st <= i:
                        status = "error"
                        rec_mode, rec_reason = _infer_smart_cond_target(b_steps, i, p_st, f_st)
                        narratives.append(f"❌ 步 {i:02d} ({s_send[:22]})：寫成 {s_mode} 往回跳【無窮迴圈風險】")
                        if not quick_fix:
                            quick_fix = {
                                "global_idx": item["global_idx"], "row_num": r_num, "field": "ExecMode",
                                "old": s_mode, "new": rec_mode, "label": f"一鍵修正第 {r_num} 列為 {rec_mode}"
                            }
                    elif p_st >= b_len or f_st >= b_len:
                        if status == "ok":
                            status = "warning"
                        rec_mode, rec_reason = _infer_smart_cond_target(b_steps, i, p_st, f_st)
                        narratives.append(
                            f"⚠️ 步 {i:02d} ({s_send[:22]})：跳轉 {s_mode} 超過區塊末行（步 {b_len - 1:02d}），建議收斂為 {rec_mode}"
                        )
                        if not quick_fix:
                            quick_fix = {
                                "global_idx": item["global_idx"], "row_num": r_num, "field": "ExecMode",
                                "old": s_mode, "new": rec_mode, "label": f"一鍵收斂第 {r_num} 列為 {rec_mode}"
                            }
                    elif p_st == f_st:
                        narratives.append(f"⏭ 步 {i:02d} ({s_send[:22]})：無論 PASS/FAIL 皆跳至 {_step_brief(p_st)} 匯流")
                    else:
                        narratives.append(
                            f"🔀 步 {i:02d} ({s_send[:22]})：PASS 走 {_step_brief(p_st)}，FAIL 跳 {_step_brief(f_st)}"
                        )
                        # Check fall-through (only when FAIL branch is NOT the final exit step of the block)
                        end_of_pass = f_st - 1
                        if i < p_st < f_st < b_len - 1 and end_of_pass >= p_st:
                            end_mode = str(b_steps[end_of_pass]["step"].get("ExecMode", "")).strip()
                            has_skip_out = False
                            if end_mode.startswith("4:") and "," in end_mode:
                                try:
                                    ep, ef = [int(x.strip()) for x in end_mode[2:].split(",", 1)]
                                    if ep >= f_st and ef >= f_st:
                                        has_skip_out = True
                                except ValueError:
                                    pass
                            if not has_skip_out:
                                if status == "ok":
                                    status = "warning"
                                end_item = b_steps[end_of_pass]
                                last_off = b_len - 1
                                narratives.append(
                                    f"⚠️ 分支貫穿風險：PASS 分支末行（步 {end_of_pass:02d} / 第 {end_item['row_num']} 列）"
                                    f"跑完未跳過 FAIL 分支，會直接掉入 {_step_brief(f_st)}"
                                )
                                if not quick_fix and end_of_pass < last_off:
                                    quick_fix = {
                                        "global_idx": end_item["global_idx"], "row_num": end_item["row_num"],
                                        "field": "ExecMode", "old": end_mode, "new": f"4:{last_off},{last_off}",
                                        "label": f"一鍵在步 {end_of_pass:02d} 補上 4:{last_off},{last_off}（跳至末行收尾）"
                                    }
                except ValueError:
                    status = "error"
                    narratives.append(f"❌ 步 {i:02d} ({s_send[:22]})：ExecMode '{s_mode}' 步號非整數")

    if not has_jump:
        return None

    tree_lines = []
    i = 0
    while i < b_len:
        s_mode = str(b_steps[i]["step"].get("ExecMode", "")).strip()
        s_send = (str(b_steps[i]["step"].get("Send", "")).strip() or "(無指令)")[:24]
        if s_mode.startswith("4:") and "," in s_mode:
            try:
                p_st, f_st = [int(x.strip()) for x in s_mode[2:].split(",", 1)]
                if p_st == f_st:
                    tgt = f"步 {p_st:02d}" + (" (⚠️越界)" if p_st >= b_len or p_st <= i else "")
                    tree_lines.append(f"[步 {i:02d}] {s_send}  ⏭ 無條件跳至 {tgt}")
                    i += 1
                    continue
                if i < p_st < f_st < b_len:
                    tree_lines.append(f"[步 {i:02d}] {s_send}")
                    p_end = f_st - 1
                    p_range = f"步 {p_st:02d}..{p_end:02d}" if p_end > p_st else f"步 {p_st:02d}"
                    p_end_mode = str(b_steps[p_end]["step"].get("ExecMode", "")).strip()
                    p_tail = ""
                    if p_end_mode.startswith("4:") and "," in p_end_mode:
                        p_tail = f" ──▶ ⏭ 跳至 ({p_end_mode})"
                    elif f_st < b_len - 1:
                        p_tail = " ──▶ ⚠️ 未跳出(貫穿)"
                    tree_lines.append(f"  ├─ PASS ──▶ [{p_range}]{p_tail}")
                    f_send = (str(b_steps[f_st]["step"].get("Send", "")).strip() or "(無指令)")[:20]
                    f_tag = " (末行收尾)" if f_st == b_len - 1 else ""
                    tree_lines.append(f"  └─ FAIL ──▶ [步 {f_st:02d}] {f_send}{f_tag}")
                    i = f_st
                    continue
                tree_lines.append(f"[步 {i:02d}] {s_send}  🔀 P→步{p_st:02d} / F→步{f_st:02d}")
                i += 1
                continue
            except ValueError:
                pass
        elif s_mode.startswith("2:"):
            tree_lines.append(f"[步 {i:02d}] {s_send}  ↩ 失敗跳回 {s_mode}")
            i += 1
            continue
        tree_lines.append(f"[步 {i:02d}] {s_send}")
        i += 1

    return {
        "sheet": st_name,
        "sheet_type": sheet_type,
        "title": blk.get("title", ""),
        "row_start": b_steps[0]["row_num"],
        "total_steps": b_len,
        "status": status,
        "narratives": narratives,
        "tree_text": "\n".join(tree_lines),
        "quick_fix": quick_fix
    }


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
    jump_summaries = []
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
            _analyze_block_jump_flow(st_name, blk, warnings)
            title_parts = [p.strip() for p in str(blk.get("title", "")).split(",")]
            block_retry_count = None
            if len(title_parts) >= 3 and title_parts[2] != "":
                try:
                    block_retry_count = int(title_parts[2])
                except ValueError:
                    block_retry_count = None
            block_has_retry2_warned = False
            js = _build_jump_summary(st_name, "Station", blk, block_retry_count)
            if js:
                jump_summaries.append(js)

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
                        if block_retry_count == 0 and not block_has_retry2_warned:
                            block_has_retry2_warned = True
                            warnings.append(
                                f"[{st_name} 第 {r_num} 列] 步驟使用 ExecMode '{s_mode}' 重試，"
                                f"但所屬 Title '{blk['title']}' 將 RetryCount 明確設為 0，失敗時將不會重複執行"
                            )
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
                                is_backward = (p_st <= offset or f_st <= offset)
                                is_over = (p_st >= b_len or f_st >= b_len)
                                if is_backward or is_over:
                                    rec_mode, rec_reason = _infer_smart_cond_target(b_steps, offset, p_st, f_st)
                                    if is_backward:
                                        errors.append(
                                            f"[{st_name} 第 {r_num} 列] ExecMode '{s_mode}' 違反『不可往回跳 (<= 當前步號 {offset})』規定！"
                                        )
                                        issue_msg = f"[{st_name} 第 {r_num} 列] 條件跳轉 '{s_mode}' 往回跳（有無限迴圈風險，當前步號 {offset}）"
                                    else:
                                        warnings.append(
                                            f"[{st_name} 第 {r_num} 列] ExecMode '{s_mode}' 跳轉目標超過當前 Title 區塊總步數 ({b_len}) 👉 推薦改為 '{rec_mode}'"
                                        )
                                        issue_msg = f"[{st_name} 第 {r_num} 列] 條件跳轉 '{s_mode}' 超過區塊步數（本區塊最後一步為步號 {b_len - 1}）"
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
                                        "issue_title": issue_msg,
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

                # Rule 7: :ObtainDevice / :ReleaseDevice pairing & ExecMode=3 (no false-positive Skip on re-entrant/multi-instrument Obtain)
                if ":ObtainDevice" in s_send or ":ObtainSubDevice" in s_send:
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

                # Rule 11: CmdConsole@ external .py existence & DUTs Parameter {N} index check
                if s_mode != "6":
                    duts_rows = workspace.get("duts", [])
                    max_dut_params = 0
                    for dr in duts_rows:
                        p_str = str(dr.get("Parameter", "")).strip()
                        if p_str:
                            max_dut_params = max(max_dut_params, len([x for x in p_str.split(",") if x.strip() != ""]))
                    if max_dut_params > 0:
                        for m_p in re.finditer(r"\{(\d+)\}", f"{s_send} {s_ref}"):
                            p_idx = int(m_p.group(1))
                            if p_idx >= max_dut_params:
                                warnings.append(
                                    f"[{st_name} 第 {r_num} 列] 引用了 DUTs Parameter '{{{p_idx}}}'，但 DUTs 僅定義了 {max_dut_params} 個參數 (0~{max_dut_params - 1})"
                                )
                    if "cmdconsole@" in s_send.lower() and ".py" in s_send.lower() and src_file and os.path.exists(src_file):
                        m_py = re.search(r"([A-Za-z0-9_.\-]+\.py)", s_send, re.IGNORECASE)
                        if m_py:
                            py_name = m_py.group(1)
                            f_dir = os.path.dirname(os.path.abspath(src_file))
                            parent_dir = os.path.dirname(f_dir)
                            found_py = any(
                                os.path.exists(os.path.join(d, py_name))
                                for d in (f_dir, parent_dir, os.path.join(f_dir, "Tools"), os.path.join(parent_dir, "Tools"))
                            )
                            if not found_py:
                                suggestions.append(
                                    f"[{st_name} 第 {r_num} 列] CmdConsole@ 呼叫外部腳本 '{py_name}'（未在同層或 Tools 目錄找到，請確認實際執行路徑是否正確）"
                                )

        if obtain_lock_open:
            warnings.append(f"[{st_name}] 腳本結束前仍有 :ObtainDevice (第 {obtain_lock_row} 列) 未呼叫 :ReleaseDevice 釋放")
        if not has_phase_97:
            warnings.append(f"[{st_name}] 缺少 Phase 97 (End Test 強制收尾階段)，建議加入斷電與治具復位步驟")

    # Also audit Marco sheets for jump logic & build summaries
    for m_name, m_steps in workspace.get("marcos", {}).items():
        if not isinstance(m_steps, list):
            continue
        m_blocks = _build_title_blocks(m_steps)
        for blk in m_blocks:
            _analyze_block_jump_flow(m_name, blk, warnings)
            t_parts = [p.strip() for p in str(blk.get("title", "")).split(",")]
            try:
                r_cnt = int(t_parts[2]) if len(t_parts) >= 3 and t_parts[2] != "" else None
            except ValueError:
                r_cnt = None
            js = _build_jump_summary(m_name, "Marco", blk, r_cnt)
            if js:
                jump_summaries.append(js)

    # Separate mechanical auto-fixable warnings from manual-review warnings
    auto_fix_keywords = (
        "TestID ",
        "Index 序號",
        "ExecMode 為空白",
        ":ReleaseDevice 的 ExecMode",
        "跨 Title 引用了變數",
        "尚未在 Global.ini 的",
        "表頭為 'Index_",
        "避免重複 Phase",
        "未呼叫 :ReleaseDevice",
        "缺少 Phase 97"
    )
    auto_fix_warnings = [w for w in warnings if any(k in w for k in auto_fix_keywords)]
    manual_warnings = [w for w in warnings if not any(k in w for k in auto_fix_keywords)]

    # Build per-sheet health statistics for multi-sheet dashboard filtering
    sheet_stats = []
    all_sheet_items = [("Station", s) for s in workspace.get("stations", {}).keys()] + [
        ("Marco", m) for m, v in workspace.get("marcos", {}).items() if isinstance(v, list)
    ]
    for s_type, s_name in all_sheet_items:
        prefix = f"[{s_name}"
        s_errs = sum(1 for e in errors if e.startswith(prefix))
        s_warns = sum(1 for w in manual_warnings if w.startswith(prefix))
        s_auto = sum(1 for w in auto_fix_warnings if w.startswith(prefix))
        s_jumps = [j for j in jump_summaries if j["sheet"] == s_name]
        s_j_issues = sum(1 for j in s_jumps if j["status"] in ("error", "warning"))
        sheet_stats.append({
            "sheet": s_name,
            "sheet_type": s_type,
            "errors": s_errs,
            "warnings": s_warns,
            "auto_fix_count": s_auto,
            "jump_blocks": len(s_jumps),
            "jump_issues": s_j_issues
        })

    return {
        "passed": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "manual_warning_count": len(manual_warnings),
        "auto_fix_warning_count": len(auto_fix_warnings),
        "suggestion_count": len(suggestions),
        "choice_card_count": len(choice_cards),
        "errors": errors,
        "warnings": warnings,
        "manual_warnings": manual_warnings,
        "auto_fix_warnings": auto_fix_warnings,
        "suggestions": suggestions,
        "choice_cards": choice_cards,
        "jump_summaries": jump_summaries,
        "sheet_stats": sheet_stats
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
    modified_cells = list(workspace.get("_modified_cells", []))  # [{"sheet": st_name, "row": r_num, "col_name": "ExecMode", "old": ..., "new": ..., "note": ...}]

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
        used_phases = set()
        for s in steps:
            sp = str(s.get("Phase", "")).strip()
            if sp.isdigit() and 1 <= int(sp) <= 96:
                used_phases.add(int(sp))
        seen_phases_fix = set()

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

                # Fix duplicate Phase (1..96) automatically
                s_phase = str(step.get("Phase", "")).strip()
                if s_phase.isdigit() and 1 <= int(s_phase) <= 96:
                    p_int = int(s_phase)
                    if p_int in seen_phases_fix:
                        cand = p_int + 1
                        while cand in used_phases and cand <= 96:
                            cand += 1
                        if cand <= 96:
                            used_phases.add(cand)
                            seen_phases_fix.add(cand)
                            step["Phase"] = str(cand)
                            fixed_logs.append(f"[{st_name} 第 {r_num} 列] 重複之 Phase '{s_phase}' 已自動順延為 '{cand}'")
                            modified_cells.append({
                                "sheet": st_name, "row": r_num, "col_name": "Phase",
                                "old": s_phase, "new": str(cand),
                                "note": f"原 Phase '{s_phase}' 與前段重複，已自動順延為 '{cand}'"
                            })
                    else:
                        seen_phases_fix.add(p_int)

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

    # Auto-fix missing Phase 97 & unclosed :ReleaseDevice at end of each station sheet
    for st_name in list(workspace.get("stations", {}).keys()):
        st_steps = workspace["stations"][st_name]
        has_p97 = any(str(s.get("Phase", "")).strip() == "97" for s in st_steps)
        if not has_p97:
            added_p97 = apply_safety_ending_fix(workspace, st_name, "phase97")
            if added_p97 > 0:
                fixed_logs.append(f"[{st_name}] 已自動補齊無治具 Phase 97 安全收尾步驟 ({added_p97} 列)")
        else:
            added_rel = apply_safety_ending_fix(workspace, st_name, "release")
            if added_rel > 0:
                fixed_logs.append(f"[{st_name}] 已自動補齊遺漏之 :ReleaseDevice (ExecMode=3)")
        for i, s in enumerate(st_steps):
            s["Index"] = f"{i:03d}"

    return fixed_logs


def apply_safety_ending_fix(workspace, sheet_name, fix_kind):
    """
    一鍵補齊工作表安全收尾步驟，並將新增列關鍵欄位寫入 _modified_cells 供匯出時整列高亮黃底：
    - fix_kind == "release": 補上 :ReleaseDevice (ExecMode=3)
    - fix_kind == "phase97": 補上無治具標準 Phase 97 (:CloseMessage + 自動偵測 :Disconnect + 必要時 :ReleaseDevice)
    """
    stations = workspace.get("stations", {})
    if sheet_name not in stations:
        return 0

    steps = stations[sheet_name]
    mods = workspace.setdefault("_modified_cells", [])

    def _make_row(phase="", title="", send="", exec_mode="3", desc=""):
        return {
            "Index": "", "Phase": phase, "Title": title, "Marco": "",
            "Instrument": "", "Switch": "", "Send": send, "Reply": "",
            "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "",
            "Waiting": "", "ExecMode": exec_mode, "Description": desc,
            "TestID": "B7PL025"
        }

    def _mark_row_highlighted(row_num, note_text):
        for col_n in ("Phase", "Title", "Send", "ExecMode", "Description", "TestID"):
            mods.append({
                "sheet": sheet_name, "row": row_num, "col_name": col_n,
                "old": "", "new": "ADDED", "note": note_text
            })

    # Detect open :ObtainDevice and used comm interfaces (e.g. UART@, IcatchUART@, LinuxUART@)
    obtain_open = False
    comm_ifaces = []
    for s in steps:
        cmd = str(s.get("Send", "")).strip()
        if ":ObtainDevice" in cmd:
            obtain_open = True
        elif ":ReleaseDevice" in cmd or ":ReleaseSubDevice" in cmd:
            obtain_open = False
        if "@" in cmd and not cmd.startswith(":"):
            iface = cmd.split("@", 1)[0].strip()
            if iface and iface not in comm_ifaces and len(comm_ifaces) < 3:
                comm_ifaces.append(iface)

    new_rows = []
    if fix_kind == "release":
        if obtain_open:
            new_rows.append((
                _make_row(send=":ReleaseDevice", exec_mode="3", desc="PC#-#Auto ReleaseDevice Safety"),
                "系統自動補齊 :ReleaseDevice (ExecMode=3)，確保儀器獨佔鎖定必釋放"
            ))
    elif fix_kind == "phase97":
        has_p97 = any(str(s.get("Phase", "")).strip() == "97" for s in steps)
        if not has_p97:
            new_rows.append((
                _make_row(phase="97", title="1,Disconnect", send=":CloseMessage", exec_mode="3", desc="PC#-#Close Prompt Message"),
                "系統自動補齊無治具 Phase 97 收尾：關閉提示訊息"
            ))
            for iface in comm_ifaces:
                new_rows.append((
                    _make_row(send=f':Disconnect,"{iface}"', exec_mode="3", desc=f"PC#-#Disconnect {iface}"),
                    f"系統自動補齊無治具 Phase 97 收尾：斷開 {iface} 連線"
                ))
            if obtain_open:
                new_rows.append((
                    _make_row(send=":ReleaseDevice", exec_mode="3", desc="PC#-#Auto ReleaseDevice Safety"),
                    "系統自動補齊 :ReleaseDevice (ExecMode=3)，釋放未關閉之裝置鎖"
                ))

    if not new_rows:
        return 0

    # Insert before Phase 98/99 if present, otherwise append at end of sheet
    insert_idx = len(steps)
    for idx, s in enumerate(steps):
        if str(s.get("Phase", "")).strip() in ("98", "99"):
            insert_idx = idx
            break

    for offset, (row_dict, note_txt) in enumerate(new_rows):
        pos = insert_idx + offset
        steps.insert(pos, row_dict)
        _mark_row_highlighted(pos + 2, note_txt)

    return len(new_rows)


def insert_instrument_title_block(workspace, sheet_name, inst_name, title_name, after_block_idx=-1, dl_val="", ul_val="", custom_steps=None, globals_patch=None):
    """
    在既有測試站工作表中，以「獨立新 Title 區塊」插入指定儀器範本（嚴格插在既有 Title 區塊之後、Phase 97 之前），
    同步補齊 Instrument 分頁與 Mount 掛載，並將整個新區塊寫入 _modified_cells 亮黃底提醒。
    """
    from .golden_data import get_golden_mother

    stations = workspace.get("stations", {})
    if sheet_name not in stations:
        return 0
    steps = stations[sheet_name]

    if globals_patch and isinstance(globals_patch, dict):
        g_ini = workspace.setdefault("global_ini", {})
        for sec, kv in globals_patch.items():
            if isinstance(kv, dict):
                g_ini.setdefault(sec, {}).update({str(k): str(v) for k, v in kv.items()})

    # 1. Lookup instrument metadata from full catalog (34 instruments)
    catalog = get_golden_mother().get("instruments", [])
    inst_meta = next((i for i in catalog if i.get("Name") == inst_name), None)
    if not inst_meta:
        inst_meta = {"Name": inst_name, "ControlDLL": f"{inst_name}.dll", "Settings": "", "Functions": inst_name, "Version": "1.0.0.0", "Switch": "", "Desc": inst_name}

    # Ensure instrument exists and is mounted to this station
    ws_insts = workspace.setdefault("instruments", [])
    existing = next((i for i in ws_insts if str(i.get("Name", "")).strip() == inst_name), None)
    if existing:
        cur_m = str(existing.get("Mount", "")).strip()
        m_list = [x.strip() for x in cur_m.split(",") if x.strip()]
        if sheet_name not in m_list:
            m_list.append(sheet_name)
            existing["Mount"] = ",".join(m_list)
    else:
        new_inst = dict(inst_meta)
        new_inst["Mount"] = sheet_name
        ws_insts.append(new_inst)

    # 2. Determine next unused Phase (1..96)
    used_p = set()
    for s in steps:
        sp = str(s.get("Phase", "")).strip()
        if sp.isdigit() and 1 <= int(sp) <= 96:
            used_p.add(int(sp))
    next_p = 1
    while next_p in used_p and next_p <= 96:
        next_p += 1

    # 3. Determine insertion index: after chosen block, strictly before Phase 97/98/99
    blocks = _build_title_blocks(steps)
    p97_idx = len(steps)
    for idx, s in enumerate(steps):
        if str(s.get("Phase", "")).strip() in ("97", "98", "99"):
            p97_idx = idx
            break

    if 0 <= after_block_idx < len(blocks):
        last_step_in_blk = blocks[after_block_idx]["steps"][-1]["global_idx"]
        insert_idx = min(last_step_in_blk + 1, p97_idx)
    else:
        insert_idx = p97_idx

    # 4. Build independent Title block rows according to instrument function
    funcs = str(inst_meta.get("Functions", "")).upper()
    clean_title = (title_name or f"{inst_name} Test").strip()
    t_header = f"0,{clean_title},3"

    def _row(phase="", title="", inst="", send="", ref="", val="", exec_mode="1", desc="", tid="B7PL025"):
        return {
            "Index": "", "Phase": phase, "Title": title, "Marco": "",
            "Instrument": inst, "Switch": "", "Send": send, "Reply": "0" if (send.startswith(":Dev") or send in (":ObtainDevice", ":ReleaseDevice")) else "",
            "EndPrompt": "", "Ref": ref, "Validation": val, "Prompt": "",
            "Waiting": "", "ExecMode": exec_mode, "Description": desc, "TestID": tid
        }

    if custom_steps and isinstance(custom_steps, list):
        block_rows = []
        for idx_cs, cs in enumerate(custom_steps):
            block_rows.append(_row(
                phase=str(next_p) if idx_cs == 0 else "",
                title=t_header if idx_cs == 0 else "",
                inst=str(cs.get("Instrument", inst_name)),
                send=str(cs.get("Send", "")),
                ref=str(cs.get("Ref", "")),
                val=str(cs.get("Validation", "")),
                exec_mode=str(cs.get("ExecMode", "1")),
                desc=str(cs.get("Description", clean_title)),
                tid=str(cs.get("TestID", "B7PL025"))
            ))
    else:
        inst_col = "LED_Test" if "LED_TEST" in funcs else inst_name
        block_rows = [
            _row(phase=str(next_p), title=t_header, inst=inst_col, send=":ObtainDevice", exec_mode="0" if "LED_TEST" in funcs else "1", desc=f"PC#-#Obtain {inst_name}", tid="BRME027" if "LED_TEST" in funcs else "B7PL025")
        ]
        if "LED_TEST" in funcs:
            w_min = str(dl_val).strip() or "515"
            w_max = str(ul_val).strip() or "535"
            block_rows.append(_row(
                inst="LED_Test",
                send=':Dev.CaptureAndRead,"01"',
                ref="$LED_Wave;\n$LED_Int",
                val=f"(LED_Wave,%f,{w_min},{w_max});\n(LED_Int,%f,1000,99999)",
                exec_mode="2:0",
                desc=f"LED#-#{clean_title} ({w_min}~{w_max}nm)",
                tid="IOLE015"
            ))
        elif "POWERSWITCH" in funcs:
            block_rows.append(_row(inst=inst_name, send=':Dev.SwitchOFF,"1"', exec_mode="1", desc=f"PC#-#{inst_name} Power OFF"))
            block_rows.append(_row(send=':Delay,"500"', exec_mode="0", desc="PC#-#Wait 500ms"))
            block_rows.append(_row(inst=inst_name, send=':Dev.SwitchON,"1"', exec_mode="1", desc=f"PC#-#{inst_name} Power ON"))
        elif any(k in funcs for k in ("VOLTAGE", "DC", "DMM", "DAQ", "PMETER")):
            dl = str(dl_val).strip() or "0.0"
            ul = str(ul_val).strip() or "5.0"
            key_base = clean_title.replace(",", "_")
            block_rows.append(_row(inst=inst_name, send=':Dev.Measure,"1"', val=f"({key_base}_CH1,%f,{dl},{ul})", exec_mode="2:0", desc=f"DUT#-#{clean_title} Ch1 ({dl}~{ul})"))
            block_rows.append(_row(inst=inst_name, send=':Dev.Measure,"2"', val=f"({key_base}_CH2,%f,{dl},{ul})", exec_mode="2:0", desc=f"DUT#-#{clean_title} Ch2 ({dl}~{ul})"))
        else:
            val_str = f"({clean_title.replace(',', '_')},%f,{dl_val},{ul_val})" if (dl_val or ul_val) else ""
            block_rows.append(_row(inst=inst_name, send=f':Dev.Run,""', val=val_str, exec_mode="2:0", desc=f"DUT#-#{clean_title}"))

        block_rows.append(
            _row(inst=inst_col, send=":ReleaseDevice", exec_mode="3", desc=f"PC#-#Release {inst_name}", tid="BRME027" if "LED_TEST" in funcs else "B7PL025")
        )

    # 5. Insert rows & highlight entire block in _modified_cells
    mods = workspace.setdefault("_modified_cells", [])
    note_txt = f"新增獨立儀器範本區塊 ({inst_name} / {clean_title})"
    for off, r_dict in enumerate(block_rows):
        pos = insert_idx + off
        steps.insert(pos, r_dict)
        r_num = pos + 2
        for col_n in ("Phase", "Title", "Instrument", "Send", "Ref", "Validation", "ExecMode", "Description", "TestID"):
            mods.append({
                "sheet": sheet_name, "row": r_num, "col_name": col_n,
                "old": "", "new": "INSERTED", "note": note_txt
            })

    for idx, s in enumerate(steps):
        s["Index"] = f"{idx:03d}"

    return len(block_rows)


def insert_rf_iqxel_block(workspace, sheet_name, inst_name="InstIQApiA", title_name="WIFI RF Test", settings_str="", tx_tests=None, rx_tests=None, after_block_idx=-1):
    """
    依 IQxel / MT8870A RF 人機介面設定，插入標準 WIFI Tx MCS / WIFI Rx MCS 主站呼叫列，
    並自動補齊 11 欄 Marco 子工作表 (WIFI Tx MCS 21 步 / WIFI Rx MCS 22 步) 與 Instrument 掛載。
    """
    from .golden_data import get_golden_mother, STANDARD_BLOCKS

    stations = workspace.get("stations", {})
    if sheet_name not in stations:
        return 0
    tx_tests = tx_tests or []
    rx_tests = rx_tests or []
    if not tx_tests and not rx_tests:
        return 0

    steps = stations[sheet_name]

    # 1. Ensure RF instrument is in Instrument and mounted to sheet_name
    catalog = get_golden_mother().get("instruments", [])
    inst_meta = next((i for i in catalog if i.get("Name") == inst_name), None) or {
        "Mount": sheet_name, "Name": inst_name, "Sub": "", "ControlDLL": "InstIQApi_A.dll",
        "Settings": "192.168.100.254,1,2,1,60000,PathLoss.ini",
        "Functions": "MeasWIFI,MeasCW,GenWIFI,GenBT,MeasBT", "Version": "1.0.0.4", "Switch": "", "Desc": "LitePoint IQxel RF Tester"
    }
    ws_insts = workspace.setdefault("instruments", [])
    existing = next((i for i in ws_insts if str(i.get("Name", "")).strip() == inst_name), None)
    if existing:
        cur_m = str(existing.get("Mount", "")).strip()
        m_list = [x.strip() for x in cur_m.split(",") if x.strip()]
        if sheet_name not in m_list:
            m_list.append(sheet_name)
            existing["Mount"] = ",".join(m_list)
        if settings_str.strip():
            existing["Settings"] = settings_str.strip()
    else:
        new_inst = dict(inst_meta)
        new_inst["Mount"] = sheet_name
        if settings_str.strip():
            new_inst["Settings"] = settings_str.strip()
        ws_insts.append(new_inst)

    # 2. Ensure WIFI Tx MCS / WIFI Rx MCS Marco sub-sheets exist
    rf_blk = next((b for b in STANDARD_BLOCKS if b.get("block_id") == "BLK_WIFI_RF_IQXEL"), None)
    if rf_blk and rf_blk.get("required_marcos"):
        ws_marcos = workspace.setdefault("marcos", {})
        for m_name, m_rows in rf_blk["required_marcos"].items():
            if m_name not in ws_marcos or not ws_marcos[m_name]:
                ws_marcos[m_name] = [dict(r) for r in m_rows]

    # 3. Next unused Phase (1..96) & insertion index before Phase 97
    used_p = {int(str(s.get("Phase", "")).strip()) for s in steps if str(s.get("Phase", "")).strip().isdigit() and 1 <= int(str(s.get("Phase", "")).strip()) <= 96}
    next_p = 1
    while next_p in used_p and next_p <= 96:
        next_p += 1

    blocks = _build_title_blocks(steps)
    p97_idx = len(steps)
    for idx, s in enumerate(steps):
        if str(s.get("Phase", "")).strip() in ("97", "98", "99"):
            p97_idx = idx
            break
    if 0 <= after_block_idx < len(blocks):
        insert_idx = min(blocks[after_block_idx]["steps"][-1]["global_idx"] + 1, p97_idx)
    else:
        insert_idx = p97_idx

    block_rows = []
    for t in tx_tests:
        ch = str(t.get("channel", "6")).strip()
        bw = str(t.get("bw", "20")).strip()
        mcs = str(t.get("mcs", "7")).strip()
        ant = str(t.get("antenna", "1")).strip()
        tpwr = str(t.get("target_pwr", "15")).strip()
        pmin = str(t.get("pwr_min", "13")).strip()
        pmax = str(t.get("pwr_max", "17")).strip()
        emin = str(t.get("evm_min", "-50")).strip()
        emax = str(t.get("evm_max", "-28")).strip()
        lbl = f"WIFI TX_CH{ch} MCS{mcs}_BW{bw}"
        block_rows.append({
            "Index": "", "Phase": str(next_p) if not block_rows else "",
            "Title": f"0,{lbl}", "Marco": "WIFI Tx MCS",
            "Instrument": "MeasWIFI", "Switch": "",
            "Send": f"{ch},{bw},{mcs},{ant},{tpwr},{pmin},{pmax},{emin},{emax},{lbl}",
            "Reply": "", "EndPrompt": "", "Ref": "", "Validation": "",
            "Prompt": "", "Waiting": "", "ExecMode": "1",
            "Description": f"RF#-#{lbl} ({pmin}~{pmax}dBm)", "TestID": "WFOT036"
        })

    for r in rx_tests:
        ch = str(r.get("channel", "6")).strip()
        bw = str(r.get("bw", "20")).strip()
        mcs = str(r.get("mcs", "7")).strip()
        ant = str(r.get("antenna", "1")).strip()
        rlvl = str(r.get("rx_level", "-59")).strip()
        lbl = f"WIFI RX_CH{ch} MCS{mcs}_BW{bw}"
        block_rows.append({
            "Index": "", "Phase": str(next_p) if not block_rows else "",
            "Title": f"0,{lbl}", "Marco": "WIFI Rx MCS",
            "Instrument": "GenWIFI", "Switch": "",
            "Send": f"{ch},{bw},{mcs},{ant},{rlvl},{lbl}",
            "Reply": "", "EndPrompt": "", "Ref": "", "Validation": "",
            "Prompt": "", "Waiting": "", "ExecMode": "1",
            "Description": f"RF#-#{lbl} ({rlvl}dBm)", "TestID": "WFOT036"
        })

    mods = workspace.setdefault("_modified_cells", [])
    note_txt = f"透過 {inst_name} RF 人機介面插入 ({len(tx_tests)} Tx / {len(rx_tests)} Rx，已同步補齊 Marco)"
    for off, r_dict in enumerate(block_rows):
        pos = insert_idx + off
        steps.insert(pos, r_dict)
        r_num = pos + 2
        for col_n in ("Phase", "Title", "Marco", "Instrument", "Send", "ExecMode", "Description", "TestID"):
            mods.append({
                "sheet": sheet_name, "row": r_num, "col_name": col_n,
                "old": "", "new": "INSERTED", "note": note_txt
            })

    for idx, s in enumerate(steps):
        s["Index"] = f"{idx:03d}"

    return len(block_rows)


def insert_ni6009_block(workspace, sheet_name, mode="RSE", sample_ms="1000", dev_id="Dev1", title_name="Measure Voltage Test", channels=None, after_block_idx=-1):
    """
    依 NI-6009 人機介面設定，插入標準 :Dev.VOLTAGE + :CheckLimit 獨立 Title 區塊，
    同步掛載 NI6008-1 至 Instrument 分頁、寫入 Global.ini [Settings] DAQ_1，並整塊亮黃底標記。
    """
    from .golden_data import get_golden_mother

    stations = workspace.get("stations", {})
    if sheet_name not in stations or not channels:
        return 0
    steps = stations[sheet_name]

    # 1. Ensure NI6008-1 is in Instrument and mounted to sheet_name
    catalog = get_golden_mother().get("instruments", [])
    inst_meta = next((i for i in catalog if i.get("Name") == "NI6008-1"), None) or {
        "Mount": sheet_name, "Name": "NI6008-1", "Sub": "", "ControlDLL": "DaqUSBNi.dll",
        "Settings": "*$(DAQ_1)", "Functions": "Voltage", "Version": "1.0.2.1", "Switch": "", "Desc": "DAQ device NI6008/6009"
    }
    ws_insts = workspace.setdefault("instruments", [])
    existing = next((i for i in ws_insts if str(i.get("Name", "")).strip() == "NI6008-1"), None)
    if existing:
        cur_m = str(existing.get("Mount", "")).strip()
        m_list = [x.strip() for x in cur_m.split(",") if x.strip()]
        if sheet_name not in m_list:
            m_list.append(sheet_name)
            existing["Mount"] = ",".join(m_list)
    else:
        new_inst = dict(inst_meta)
        new_inst["Mount"] = sheet_name
        ws_insts.append(new_inst)

    workspace.setdefault("global_ini", {}).setdefault("Settings", {})["DAQ_1"] = str(dev_id or "Dev1").strip()

    # 2. Next unused Phase (1..96) & insertion index before Phase 97
    used_p = {int(str(s.get("Phase", "")).strip()) for s in steps if str(s.get("Phase", "")).strip().isdigit() and 1 <= int(str(s.get("Phase", "")).strip()) <= 96}
    next_p = 1
    while next_p in used_p and next_p <= 96:
        next_p += 1

    blocks = _build_title_blocks(steps)
    p97_idx = len(steps)
    for idx, s in enumerate(steps):
        if str(s.get("Phase", "")).strip() in ("97", "98", "99"):
            p97_idx = idx
            break
    if 0 <= after_block_idx < len(blocks):
        insert_idx = min(blocks[after_block_idx]["steps"][-1]["global_idx"] + 1, p97_idx)
    else:
        insert_idx = p97_idx

    clean_title = (title_name or "Measure Voltage Test").strip()
    ch_nums = ",".join(str(c["ch"]) for c in channels)
    ref_lines = ";\n".join(f"${c['name']}" for c in channels)
    ch_desc = ", ".join(f"AI{c['ch']}({c['name']})" for c in channels)

    def _row(phase="", title="", inst="", send="", ref="", exec_mode="0", desc="", tid="B7PL025"):
        return {
            "Index": "", "Phase": phase, "Title": title, "Marco": "",
            "Instrument": inst, "Switch": "", "Send": send, "Reply": "0",
            "EndPrompt": "", "Ref": ref, "Validation": "", "Prompt": "",
            "Waiting": "", "ExecMode": exec_mode, "Description": desc, "TestID": tid
        }

    block_rows = [
        _row(phase=str(next_p), title=f"0,{clean_title},3", inst="Voltage", send=":ObtainDevice", exec_mode="0", desc="INST#-#Obtain NI6009 Lock"),
        _row(inst="Voltage", send=':Delay,"1500"', exec_mode="0", desc="PC#-#Wait Voltage Stabilize"),
        _row(inst="Voltage", send=f':Dev.VOLTAGE,"{mode},{sample_ms},{ch_nums}"', ref=ref_lines, exec_mode="0", desc=f"INST#-#Read {ch_desc}", tid="BRPW033"),
        _row(inst="Voltage", send=":ReleaseDevice", exec_mode="3", desc="INST#-#Release NI6009 Lock", tid="BRME027"),
    ]
    for c in channels:
        nm = str(c["name"]).strip()
        dl = str(c["dl"]).strip()
        ul = str(c["ul"]).strip()
        block_rows.append(
            _row(send=f':CheckLimit,"*({nm})","{dl}","{ul}","%f"', exec_mode="2:0", desc=f"DUT#-#Check {nm} ({dl}V~{ul}V)", tid="BRPW024")
        )

    mods = workspace.setdefault("_modified_cells", [])
    note_txt = f"透過 NI-6009 人機介面插入 ({mode}, {len(channels)} 通道)"
    for off, r_dict in enumerate(block_rows):
        pos = insert_idx + off
        steps.insert(pos, r_dict)
        r_num = pos + 2
        for col_n in ("Phase", "Title", "Instrument", "Send", "Ref", "ExecMode", "Description", "TestID"):
            mods.append({
                "sheet": sheet_name, "row": r_num, "col_name": col_n,
                "old": "", "new": "INSERTED", "note": note_txt
            })

    for idx, s in enumerate(steps):
        s["Index"] = f"{idx:03d}"

    return len(block_rows)


def insert_rf_iqxel_block(workspace, sheet_name, inst_name="InstIQApiA", title_name="WIFI RF Test", settings_str="", tx_tests=None, rx_tests=None, after_block_idx=-1):
    """
    依 IQxel / MT8870A RF 人機介面設定，插入標準 WIFI Tx MCS / WIFI Rx MCS 主站呼叫列，
    並自動補齊 11 欄 Marco 子工作表 (WIFI Tx MCS 21 步 / WIFI Rx MCS 22 步) 與 Instrument 掛載。
    """
    from .golden_data import get_golden_mother, STANDARD_BLOCKS

    stations = workspace.get("stations", {})
    if sheet_name not in stations:
        return 0
    tx_tests = tx_tests or []
    rx_tests = rx_tests or []
    if not tx_tests and not rx_tests:
        return 0

    steps = stations[sheet_name]

    # 1. Ensure RF instrument is in Instrument and mounted to sheet_name
    catalog = get_golden_mother().get("instruments", [])
    inst_meta = next((i for i in catalog if i.get("Name") == inst_name), None) or {
        "Mount": sheet_name, "Name": inst_name, "Sub": "", "ControlDLL": "InstIQApi_A.dll",
        "Settings": "192.168.100.254,1,2,1,60000,PathLoss.ini",
        "Functions": "MeasWIFI,MeasCW,GenWIFI,GenBT,MeasBT", "Version": "1.0.0.4", "Switch": "", "Desc": "LitePoint IQxel RF Tester"
    }
    ws_insts = workspace.setdefault("instruments", [])
    existing = next((i for i in ws_insts if str(i.get("Name", "")).strip() == inst_name), None)
    if existing:
        cur_m = str(existing.get("Mount", "")).strip()
        m_list = [x.strip() for x in cur_m.split(",") if x.strip()]
        if sheet_name not in m_list:
            m_list.append(sheet_name)
            existing["Mount"] = ",".join(m_list)
        if settings_str.strip():
            existing["Settings"] = settings_str.strip()
    else:
        new_inst = dict(inst_meta)
        new_inst["Mount"] = sheet_name
        if settings_str.strip():
            new_inst["Settings"] = settings_str.strip()
        ws_insts.append(new_inst)

    # 2. Ensure WIFI Tx MCS / WIFI Rx MCS Marco sub-sheets exist
    rf_blk = next((b for b in STANDARD_BLOCKS if b.get("block_id") == "BLK_WIFI_RF_IQXEL"), None)
    if rf_blk and rf_blk.get("required_marcos"):
        ws_marcos = workspace.setdefault("marcos", {})
        for m_name, m_rows in rf_blk["required_marcos"].items():
            if m_name not in ws_marcos or not ws_marcos[m_name]:
                ws_marcos[m_name] = [dict(r) for r in m_rows]

    # 3. Next unused Phase (1..96) & insertion index before Phase 97
    used_p = {int(str(s.get("Phase", "")).strip()) for s in steps if str(s.get("Phase", "")).strip().isdigit() and 1 <= int(str(s.get("Phase", "")).strip()) <= 96}
    next_p = 1
    while next_p in used_p and next_p <= 96:
        next_p += 1

    blocks = _build_title_blocks(steps)
    p97_idx = len(steps)
    for idx, s in enumerate(steps):
        if str(s.get("Phase", "")).strip() in ("97", "98", "99"):
            p97_idx = idx
            break
    if 0 <= after_block_idx < len(blocks):
        insert_idx = min(blocks[after_block_idx]["steps"][-1]["global_idx"] + 1, p97_idx)
    else:
        insert_idx = p97_idx

    block_rows = []
    for t in tx_tests:
        ch = str(t.get("channel", "6")).strip()
        bw = str(t.get("bw", "20")).strip()
        mcs = str(t.get("mcs", "7")).strip()
        ant = str(t.get("antenna", "1")).strip()
        tpwr = str(t.get("target_pwr", "15")).strip()
        pmin = str(t.get("pwr_min", "13")).strip()
        pmax = str(t.get("pwr_max", "17")).strip()
        emin = str(t.get("evm_min", "-50")).strip()
        emax = str(t.get("evm_max", "-28")).strip()
        lbl = f"WIFI TX_CH{ch} MCS{mcs}_BW{bw}"
        block_rows.append({
            "Index": "", "Phase": str(next_p) if not block_rows else "",
            "Title": f"0,{lbl}", "Marco": "WIFI Tx MCS",
            "Instrument": "MeasWIFI", "Switch": "",
            "Send": f"{ch},{bw},{mcs},{ant},{tpwr},{pmin},{pmax},{emin},{emax},{lbl}",
            "Reply": "", "EndPrompt": "", "Ref": "", "Validation": "",
            "Prompt": "", "Waiting": "", "ExecMode": "1",
            "Description": f"RF#-#{lbl} ({pmin}~{pmax}dBm)", "TestID": "WFOT036"
        })

    for r in rx_tests:
        ch = str(r.get("channel", "6")).strip()
        bw = str(r.get("bw", "20")).strip()
        mcs = str(r.get("mcs", "7")).strip()
        ant = str(r.get("antenna", "1")).strip()
        rlvl = str(r.get("rx_level", "-59")).strip()
        lbl = f"WIFI RX_CH{ch} MCS{mcs}_BW{bw}"
        block_rows.append({
            "Index": "", "Phase": str(next_p) if not block_rows else "",
            "Title": f"0,{lbl}", "Marco": "WIFI Rx MCS",
            "Instrument": "GenWIFI", "Switch": "",
            "Send": f"{ch},{bw},{mcs},{ant},{rlvl},{lbl}",
            "Reply": "", "EndPrompt": "", "Ref": "", "Validation": "",
            "Prompt": "", "Waiting": "", "ExecMode": "1",
            "Description": f"RF#-#{lbl} ({rlvl}dBm)", "TestID": "WFOT036"
        })

    mods = workspace.setdefault("_modified_cells", [])
    note_txt = f"透過 {inst_name} RF 人機介面插入 ({len(tx_tests)} Tx / {len(rx_tests)} Rx，已同步補齊 Marco)"
    for off, r_dict in enumerate(block_rows):
        pos = insert_idx + off
        steps.insert(pos, r_dict)
        r_num = pos + 2
        for col_n in ("Phase", "Title", "Marco", "Instrument", "Send", "ExecMode", "Description", "TestID"):
            mods.append({
                "sheet": sheet_name, "row": r_num, "col_name": col_n,
                "old": "", "new": "INSERTED", "note": note_txt
            })

    for idx, s in enumerate(steps):
        s["Index"] = f"{idx:03d}"

    return len(block_rows)



def update_comm_settings(workspace, dut_ur1="", dut_ip1="", dut_login="", convert_uart_to_ssh=False, target_sheet=""):
    """
    更新 Global.ini 的 UART COM Port (DUT_UR1) 與 DUT IP (DUTIP_1 / DUT_Login)，
    並可選擇將指定測試站（或全部站別）的 UART 指令步驟轉換為 SSH (CmdConsole@ssh)。
    """
    settings = workspace.setdefault("global_ini", {}).setdefault("Settings", {})
    if dut_ur1.strip():
        settings["DUT_UR1"] = dut_ur1.strip()
    if dut_ip1.strip():
        settings["DUTIP_1"] = dut_ip1.strip()
    if dut_login.strip():
        settings["DUT_Login"] = dut_login.strip()

    converted = 0
    if convert_uart_to_ssh:
        login_user = settings.get("DUT_Login", "root") or "root"
        mods = workspace.setdefault("_modified_cells", [])
        stations = workspace.get("stations", {})
        sheets = [target_sheet] if (target_sheet and target_sheet in stations) else list(stations.keys())
        for s_name in sheets:
            for idx, step in enumerate(stations[s_name]):
                send_val = str(step.get("Send", "")).strip()
                r_num = idx + 2
                if send_val.startswith(':Connect,"UART"') or send_val.startswith(':Connect,"UART,'):
                    old_v = send_val
                    step["Send"] = ':Connect,"CmdConsole"'
                    mods.append({"sheet": s_name, "row": r_num, "col_name": "Send", "old": old_v, "new": step["Send"], "note": "UART 連線轉換為 CmdConsole (SSH)"})
                    converted += 1
                elif send_val.startswith(':Disconnect,"UART"'):
                    old_v = send_val
                    step["Send"] = ':Disconnect,"CmdConsole"'
                    mods.append({"sheet": s_name, "row": r_num, "col_name": "Send", "old": old_v, "new": step["Send"], "note": "UART 斷線轉換為 CmdConsole"})
                    converted += 1
                elif send_val.startswith("UART@"):
                    old_v = send_val
                    raw_cmd = send_val[len("UART@"):].replace("\\r\\n", "").replace("\\n", "").strip()
                    step["Send"] = f'CmdConsole@ssh {login_user}@*$(DUTIP_1) "{raw_cmd}"\\r\\n'
                    mods.append({"sheet": s_name, "row": r_num, "col_name": "Send", "old": old_v, "new": step["Send"], "note": "UART@ 指令轉換為 SSH 連線"})
                    converted += 1
    return converted
