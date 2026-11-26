# -*- coding: utf-8 -*-
"""
Centimani Studio - Bi-Directional 16-Column Excel Engine V2.1
Supports both:
1. Generating brand-new 16-Column Mother Excel from selected Lego blocks.
2. In-Place Non-Destructive Patching of existing Excel files (preserving all Marco 11-col sheets,
   PathLoss, and Connection1..10 columns while highlighting repaired cells in yellow with notes).
"""
import os
import io
import re
import shutil
import zipfile
import datetime
from copy import copy as _copy_style
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from .golden_data import (
    STATION_HEADERS_16,
    MARCO_HEADERS_11,
    DUTS_HEADERS_10,
    SWITCH_HEADERS_7,
    INSTRUMENT_HEADERS_9,
    get_golden_mother
)

FONT_BODY = Font(name="Calibri", size=11, bold=False, color="000000")
FONT_HEADER = Font(name="Calibri", size=11, bold=True, color="000000")
FONT_SKIP = Font(name="Calibri", size=11, italic=True, color="7F7F7F")
FONT_FIXED = Font(name="Calibri", size=11, bold=True, color="7F1D1D")
FONT_REORDERED = Font(name="Calibri", size=11, bold=False, color="0F172A")
FONT_SFIS_PINK = Font(name="Calibri", size=11, bold=True, color="BE185D")
FONT_PHASE98 = Font(name="Calibri", size=11, bold=True, color="15803D")
FONT_PHASE99 = Font(name="Calibri", size=11, bold=True, color="9F1239")

FILL_HEADER = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
FILL_PHASE0 = PatternFill(start_color="F2F8FD", end_color="F2F8FD", fill_type="solid")
FILL_PHASE97 = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
FILL_PHASE98 = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
FILL_PHASE99 = PatternFill(start_color="FFE4E6", end_color="FFE4E6", fill_type="solid")
FILL_SKIP = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
FILL_FIXED_CELL = PatternFill(start_color="FEF08A", end_color="FEF08A", fill_type="solid")
FILL_REORDERED_CELL = PatternFill(start_color="E8F4FD", end_color="E8F4FD", fill_type="solid")

BRANCH_DARK_HEXES = [
    "1E3A8A",  # 深寶藍 Navy Blue (配純白字)
    "14532D",  # 深森綠 Deep Emerald (配純白字)
    "7F1D1D",  # 深酒紅 Deep Burgundy (配純白字)
    "4C1D95",  # 深靛紫 Deep Royal Purple (配純白字)
    "134E4A",  # 深青墨 Deep Dark Teal (配純白字)
]
BRANCH_PASTEL_HEXES = BRANCH_DARK_HEXES  # 相容別名
GUARD_PASTEL_HEXES = ["E0F7FA", "CCFBF1"]  # 條件略過區交替柔青水藍


def _parse_cond4_pair(exec_mode):
    s = str(exec_mode or "").strip()
    if s.startswith("4:") and "," in s:
        parts = s[2:].split(",", 1)
        try:
            return int(parts[0].strip()), int(parts[1].strip())
        except ValueError:
            return None
    return None


def compute_station_row_visuals(steps):
    """
    Computes unified visual styling (Title-local step index, pastel branch/guard fill,
    SFIS pink text, Phase 97/98/99 end-section colors) shared by Excel export AND UI preview.
    """
    n = len(steps or [])
    if n == 0:
        return []

    visuals = []
    # Partition into Title blocks matching Centimani 0-based Title jump scope
    blocks = []
    curr_blk = None
    curr_phase = ""
    local_offset = 0
    for idx, step in enumerate(steps):
        p_str = str(step.get("Phase") or "").strip()
        t_str = str(step.get("Title") or "").strip()
        if p_str:
            curr_phase = p_str
        if idx > 0 and t_str:
            local_offset = 0
        if idx == 0 or t_str:
            curr_blk = {"start": idx, "end": idx, "phase": curr_phase, "rows": []}
            blocks.append(curr_blk)
        curr_blk["end"] = idx
        curr_blk["rows"].append((idx, local_offset, step))

        v = {
            "local_idx": local_offset,
            "phase": curr_phase,
            "fill_hex": None,
            "font_hex": None,
            "font_bold": False,
            "role_label": "",
        }
        if curr_phase.startswith("-"):
            v["fill_hex"] = "F2F2F2"
            v["font_hex"] = "7F7F7F"
            v["role_label"] = "暫停 (Phase -1)"
        elif curr_phase.split(":")[0].strip() == "97":
            v["fill_hex"] = "FFF2CC"
            v["role_label"] = "Phase 97 必跑收尾"
        elif curr_phase == "98":
            v["fill_hex"] = "DCFCE7"
            v["font_hex"] = "15803D"
            v["font_bold"] = True
            v["role_label"] = "Phase 98 PASS"
        elif curr_phase == "99":
            v["fill_hex"] = "FFE4E6"
            v["font_hex"] = "9F1239"
            v["font_bold"] = True
            v["role_label"] = "Phase 99 FAIL"
        elif curr_phase == "0":
            v["fill_hex"] = "F2F8FD"
            v["role_label"] = "Phase 0 前置"
        visuals.append(v)
        local_offset += 1

    # Classify ExecMode = 4:P,F blocks (supports arbitrary 2..N branches + Guard 4:1,end sections)
    guard_toggle = 0
    for blk in blocks:
        ph = blk["phase"]
        if ph.startswith("-") or ph in ("97", "98", "99"):
            continue
        b_rows = blk["rows"]
        b_len = len(b_rows)
        conds = []
        for g_idx, loc_i, st in b_rows:
            pair = _parse_cond4_pair(st.get("ExecMode"))
            if pair is not None:
                conds.append((g_idx, loc_i, pair[0], pair[1], st))
        if not conds:
            continue

        # Detect Guard pattern: step 0 uses 4:1,end (or 4:1,last) skipping the section when unmatched
        if len(conds) == 1 and conds[0][1] == 0 and conds[0][2] == 1 and conds[0][3] >= b_len - 1:
            g_hex = GUARD_PASTEL_HEXES[guard_toggle % len(GUARD_PASTEL_HEXES)]
            guard_toggle += 1
            for g_idx, _loc, _st in b_rows:
                visuals[g_idx]["fill_hex"] = g_hex
                visuals[g_idx]["role_label"] = "條件略過區 (4:1,end)"
            continue

        # Multi-branch / complex 4:P,F block
        loc_to_g = {loc_i: g_idx for g_idx, loc_i, _ in b_rows}
        assigned = set()

        # 1) Identify :SfEnabled offline-bypass header if present
        for g_idx, loc_i, p_st, f_st, st in conds:
            if str(st.get("Send") or "").strip().lower().startswith(":sfenabled"):
                end_pre = min(b_len - 1, max(loc_i, f_st))
                for k in range(loc_i, end_pre + 1):
                    gi = loc_to_g.get(k)
                    if gi is not None and k not in assigned:
                        visuals[gi]["fill_hex"] = "EFF6FF"
                        visuals[gi]["role_label"] = "SFIS/離線判定"
                        assigned.add(k)

        # 2) Identify Fail-Stop rows (:Delay,"000" + Reply="1" or failure-only targets)
        fail_only_locs = set()
        pass_targets = {p for _, _, p, _, _ in conds}
        fail_targets = {f for _, _, _, f, _ in conds}
        for g_idx, loc_i, st in b_rows:
            snd = str(st.get("Send") or "").strip().lower()
            rep = str(st.get("Reply") or "").strip()
            if snd.startswith(':delay,"000"') and rep == "1":
                fail_only_locs.add(loc_i)
            elif loc_i in fail_targets and loc_i not in pass_targets and loc_i >= b_len - 3 and loc_i != b_len - 1:
                if "fail" in str(st.get("Description") or "").lower() or rep == "1":
                    fail_only_locs.add(loc_i)
        for fl in fail_only_locs:
            gi = loc_to_g.get(fl)
            if gi is not None:
                visuals[gi]["fill_hex"] = "FFE4E6"
                visuals[gi]["role_label"] = "FAIL 停損"
                assigned.add(fl)

        # 3) Identify convergence exit & post-merge shared steps (tail node jumped to by >=2 distinct branch rows)
        target_sources = {}
        for _, loc_i, p_st, f_st, _ in conds:
            if p_st > loc_i and p_st != f_st:
                target_sources.setdefault(p_st, set()).add(loc_i)
            if f_st > loc_i and f_st != p_st and f_st not in fail_only_locs:
                target_sources.setdefault(f_st, set()).add(loc_i)
        conv_locs = [k for k, srcs in target_sources.items() if len(srcs) >= 2 and k < b_len]
        conv_start = max(conv_locs) if conv_locs else None
        if conv_start is not None:
            for k in range(conv_start, b_len):
                if k not in fail_only_locs:
                    gi = loc_to_g.get(k)
                    if gi is not None:
                        visuals[gi]["fill_hex"] = "F1F5F9"
                        visuals[gi]["role_label"] = "匯合/共用指令" if k > conv_start else "匯合點"
                        assigned.add(k)

        # 4) Assign cycling dark-theme colors + crisp white bold text to each branch check + arm (supports 2..N branches!)
        branch_idx = 0
        for g_idx, loc_i, p_st, f_st, st in conds:
            if loc_i in assigned:
                continue
            b_hex = BRANCH_DARK_HEXES[branch_idx % len(BRANCH_DARK_HEXES)]
            if p_st == f_st:
                # Unconditional jump 4:N,N
                visuals[g_idx]["fill_hex"] = b_hex
                visuals[g_idx]["font_hex"] = "FFFFFF"
                visuals[g_idx]["font_bold"] = True
                visuals[g_idx]["role_label"] = f"跳轉 -> 步 {p_st}"
                assigned.add(loc_i)
                branch_idx += 1
                continue

            b_label = f"分支 #{branch_idx + 1}"
            # Include check row itself + its PASS arm up to (f_st - 1) before next check / fail / convergence
            visuals[g_idx]["fill_hex"] = b_hex
            visuals[g_idx]["font_hex"] = "FFFFFF"
            visuals[g_idx]["font_bold"] = True
            visuals[g_idx]["role_label"] = b_label
            assigned.add(loc_i)
            arm_limit = min(b_len, f_st if f_st > p_st else b_len)
            for k in range(p_st, arm_limit):
                if k in assigned:
                    break
                gk = loc_to_g.get(k)
                if gk is not None:
                    visuals[gk]["fill_hex"] = b_hex
                    visuals[gk]["font_hex"] = "FFFFFF"
                    visuals[gk]["font_bold"] = True
                    visuals[gk]["role_label"] = b_label
                    assigned.add(k)
            branch_idx += 1

    # Finally apply SFIS pink-magenta text across ALL :Sf* steps (keep crisp white if sitting on dark branch fill)
    for idx, step in enumerate(steps):
        if str(step.get("Send") or "").strip().lower().startswith(":sf"):
            v = visuals[idx]
            if not v["phase"].startswith("-"):
                if v.get("fill_hex") not in BRANCH_DARK_HEXES:
                    v["font_hex"] = "BE185D"
                v["font_bold"] = True
                if v["role_label"] and "SFIS" not in v["role_label"]:
                    v["role_label"] = f"SFIS · {v['role_label']}"
                elif not v["role_label"]:
                    v["role_label"] = "SFIS"
    return visuals

BORDER_THIN = Border(
    left=Side(style="thin", color="64748B"),
    right=Side(style="thin", color="64748B"),
    top=Side(style="thin", color="64748B"),
    bottom=Side(style="thin", color="64748B")
)

ALIGN_LEFT = Alignment(wrap_text=True, vertical="center", horizontal="left")
ALIGN_CENTER = Alignment(wrap_text=True, vertical="center", horizontal="center")


STATION_HEADER_TOOLTIPS = {
    "A1": ("TestID index 定義", "由 EditorScriptTool 自動定義\n若欄位為空白時，程序將會自動加入\nPS: 第一次生成時，請清空讓系統重新編排"),
    "B1": ("測試順序定義", "0：測試前動作\n1~96： 測試順序，可重複定義，但必需注意順序性\n97：End Test 後動作\n98：End PASS 後動作\n99：End FAIL 後動作"),
    "C1": ("該測試項名稱", "設定此測試大項名稱（格式：0/2/*$(Var),名稱,重試次數）"),
    "D1": ("Group Loop 測試定義", "可重複 Call Loop testing\n若有需一併設定 Title 名稱, 若需要帶入參數則填在Send欄位\n若無時，請清除為空白"),
    "E1": ("輸入 Instrument Function name", "輸入於 Instrument Sheet 內定義其中一 Function name\n若無時請清除為空白\n並於 Instrument Sheet 內填入該站別名"),
    "F1": ("DUT與Device/Switch的接線設定", '若有搭配 Switch 時，填入 Switch Name\n若無時，需填入 Instrument Name\n格式 : DeviceName,"DUT ChainNo:Device Route-Port"\n           SwitchName,"DUT ChainNo:Switch L1, L2, …"'),
    "G1": ("要執行的小項測試動作", "可定義執行所有動作項目\n與 Marco 引入參數設定\n相關設定請參照說明書"),
    "H1": ("動作判斷條件", "運行後判斷條件\n加上 @ 可設為 Reply 中包含關鍵字即可\n若無時 Reply 將需要完全一樣"),
    "I1": ("結束字元定義", "若有特殊結束字元時可定義於此\n若無時，請清除為空白"),
    "J1": ("儲存變數名稱", "可將 Send 後所有Reply 執行儲存為變數使用\n加上 $ 可設定為公用變數\n若無時，僅為該 Phase 內部使用"),
    "K1": ("驗證某變數的值是否有符合設定的上下限條件", "可取出 Ref 內變數進行相對判斷式定義\nFormat : (KeyName,Value type,DL,UL)\nValue type : %s(字串), %d(整數), %f(浮點數), %x(16進位整數)"),
    "L1": ("執行前判斷設定", "用來確認收到特定訊息後才執行command，\n第一字元為@表示含有即可，沒有則是全符合"),
    "M1": ("Time Out 定設定", "等待DUT回應的時間，沒設定則以 System.ini 內預設為主"),
    "N1": ("執行模式", "0 : Normal mode\n1 : Direct Retry on Fail\n2 : Retry from Retry Point   ex: 2:RetryPoint\n3 : Continue\n4 : Condition ex: 4:PassStep,FailStep\n6 : Skip\n8 : Normal mode while SFIS Enable\n9 : Direct Retry while SFIS Enable"),
    "O1": ("描述執行的command", "建議以 主體#-#動作 格式填寫"),
    "P1": ("設定 Item TestID", "需參照 TestItem list 填入對應TestID，\n該欄位除定義為 Marco 外，不可為空白"),
}


def _apply_station_header_tooltips(ws_st, preserved_dvs=None):
    """Attaches preserved DataValidations or standard 16-column Centimani header tooltips onto A1:P1."""
    if preserved_dvs:
        for dv in preserved_dvs:
            ws_st.add_data_validation(_copy_style(dv))
        return
    for cell_ref, (p_title, p_body) in STATION_HEADER_TOOLTIPS.items():
        dv = DataValidation(showInputMessage=True, promptTitle=p_title, prompt=p_body)
        ws_st.add_data_validation(dv)
        dv.add(cell_ref)


def _write_station_sheet_contents(ws_st, steps, fixed_cell_map, preserved_dvs=None):
    """Writes a 16-column Station sheet consistently across In-Place and Brand-New exports, preserving hidden rows and writing Col 17 (0-based Title LocalStepIndex)."""
    total_steps = len(steps)
    ws_st.append([f"Index_{total_steps:03d}"] + STATION_HEADERS_16[1:])
    local_offset = 0
    for idx, step in enumerate(steps):
        step["Index"] = f"{idx:03d}"
        if idx > 0 and str(step.get("Title") or "").strip():
            local_offset = 0
        row_vals = [
            step.get(h, "") if (step.get(h, "") is not None and str(step.get(h, "")) != "") else None
            for h in STATION_HEADERS_16
        ] + [local_offset]
        ws_st.append(row_vals)
        local_offset += 1
        if step.get("_hidden"):
            ws_st.row_dimensions[idx + 2].hidden = True
    row_visuals = compute_station_row_visuals(steps)
    apply_sheet_formatting(ws_st, is_station=True, fixed_cell_map=fixed_cell_map, row_visuals=row_visuals)
    _apply_station_header_tooltips(ws_st, preserved_dvs=preserved_dvs)


def _write_marco_sheet_contents(ws_m, m_steps, fixed_cell_map):
    """Writes an 11-column Marco subroutine sheet consistently, preserving hidden rows."""
    ws_m.append([f"Index_{len(m_steps)}"] + MARCO_HEADERS_11[1:])
    for idx, step in enumerate(m_steps):
        step["Index"] = f"{idx:02d}"
        row_vals = [
            step.get(h, "") if (step.get(h, "") is not None and str(step.get(h, "")) != "") else None
            for h in MARCO_HEADERS_11
        ]
        ws_m.append(row_vals)
        if step.get("_hidden"):
            ws_m.row_dimensions[idx + 2].hidden = True
    apply_sheet_formatting(ws_m, is_station=False, fixed_cell_map=fixed_cell_map)


def _read_bounded_rows(ws_sheet, max_col=17, max_empty_streak=50, hard_limit=5000, include_hidden=False):
    """
    Streams rows from a worksheet and stops early after `max_empty_streak` consecutive blank rows.
    Prevents 30~60s freezes when an Excel sheet has formatting or DataValidation dragged down to row 1,048,576.
    When `include_hidden=True`, returns `(rows, hidden_flags)` tracking `row_dimensions[r_idx].hidden`.
    """
    rows = []
    hidden_flags = []
    empty_streak = 0
    for r_idx, r in enumerate(ws_sheet.iter_rows(max_col=max_col, values_only=True), start=1):
        if r_idx > hard_limit:
            break
        if r_idx > 1 and not any(x is not None and str(x).strip() != "" for x in r[:max_col]):
            empty_streak += 1
            if empty_streak >= max_empty_streak:
                break
            continue
        empty_streak = 0
        rows.append(r)
        if include_hidden:
            dim = ws_sheet.row_dimensions.get(r_idx)
            hidden_flags.append(bool(dim and dim.hidden))
    return (rows, hidden_flags) if include_hidden else rows


def apply_sheet_formatting(ws, is_station=False, fixed_cell_map=None, row_visuals=None):
    """Applies Calibri 11, wrap_text=True, borders, auto-fit column widths, ExecMode 4:P,F pastel coding, SFIS pink font, and highlights."""
    fixed_cell_map = fixed_cell_map or {}
    row_visuals = row_visuals or []
    fill_cache = {}
    font_cache = {}
    ws.row_dimensions[1].height = 28
    center_cols = {1, 2, 8, 9, 13, 14, 16} if is_station else {1}

    # Bounded column and row counts prevent openpyxl from hanging on sparse/unbounded sheets (e.g. max_col=16384 or max_row=1048576)
    max_c = min(ws.max_column or 1, 16 if is_station else 20)
    scan_max_r = min(ws.max_row or 1, 3000)

    # Find actual last non-empty row and column so we don't format trailing empty rows/cols
    actual_max_r = 1
    actual_max_c = 1
    for r_idx, r_vals in enumerate(ws.iter_rows(max_row=scan_max_r, max_col=max_c, values_only=True), start=1):
        row_has_val = False
        for c_idx, val in enumerate(r_vals, start=1):
            if val is not None and str(val).strip() != "":
                row_has_val = True
                if c_idx > actual_max_c:
                    actual_max_c = c_idx
        if row_has_val:
            actual_max_r = r_idx

    if is_station:
        actual_max_c = 16

    curr_phase_str = ""
    for r_idx, row in enumerate(ws.iter_rows(max_row=actual_max_r, max_col=actual_max_c), start=1):
        if r_idx > 1:
            max_lines = 1
            for cell in row:
                if cell.value:
                    s_val = str(cell.value)
                    lines = max(len(s_val.split("\n")), (len(s_val) // 42) + 1)
                    if lines > max_lines:
                        max_lines = lines
            ws.row_dimensions[r_idx].height = max(22, min(max_lines * 16 + 6, 110))

            if is_station and len(row) >= 2 and row[1].value is not None and str(row[1].value).strip() != "":
                curr_phase_str = str(row[1].value).strip()

        for c_idx, cell in enumerate(row, start=1):
            cell.border = BORDER_THIN
            if r_idx == 1:
                cell.font = FONT_HEADER
                cell.fill = FILL_HEADER
                cell.alignment = ALIGN_CENTER
            else:
                step_idx = r_idx - 2
                rv = row_visuals[step_idx] if (is_station and 0 <= step_idx < len(row_visuals)) else None
                send_val = str(row[6].value or "").strip() if (is_station and len(row) >= 7) else ""

                cell.alignment = ALIGN_CENTER if c_idx in center_cols else ALIGN_LEFT
                if rv:
                    f_hex = rv.get("fill_hex")
                    if f_hex:
                        if f_hex not in fill_cache:
                            fill_cache[f_hex] = PatternFill(start_color=f_hex, end_color=f_hex, fill_type="solid")
                        cell.fill = fill_cache[f_hex]
                    t_hex = rv.get("font_hex")
                    if t_hex:
                        f_key = (t_hex, bool(rv.get("font_bold")))
                        if f_key not in font_cache:
                            font_cache[f_key] = Font(name="Calibri", size=11, bold=f_key[1], color=t_hex)
                        cell.font = font_cache[f_key]
                    else:
                        cell.font = FONT_BODY
                else:
                    cell.font = FONT_SKIP if curr_phase_str.startswith("-") else FONT_BODY
                    if is_station:
                        if curr_phase_str.startswith("-"):
                            cell.fill = FILL_SKIP
                        elif curr_phase_str == "0":
                            cell.fill = FILL_PHASE0
                        elif curr_phase_str == "97":
                            cell.fill = FILL_PHASE97
                        elif curr_phase_str == "98":
                            cell.fill = FILL_PHASE98
                            cell.font = FONT_PHASE98
                        elif curr_phase_str == "99":
                            cell.fill = FILL_PHASE99
                            cell.font = FONT_PHASE99
                        if send_val.lower().startswith(":sf") and not curr_phase_str.startswith("-"):
                            cell.font = FONT_SFIS_PINK

                # Highlight modified cells: Light Blue (#BAE6FD) for reordered Phase blocks, Bright Yellow (#FEF08A) for auto-fixed/inserted cells
                if (r_idx, c_idx) in fixed_cell_map:
                    cell_meta = fixed_cell_map[(r_idx, c_idx)]
                    if isinstance(cell_meta, dict):
                        note_txt = cell_meta.get("note", "")
                        hl_type = cell_meta.get("highlight", "yellow")
                        show_cmt = cell_meta.get("show_comment", True)
                    else:
                        note_txt = str(cell_meta or "")
                        hl_type = "yellow"
                        show_cmt = True

                    if hl_type == "blue":
                        cell.fill = FILL_REORDERED_CELL
                        cell.font = FONT_REORDERED
                    else:
                        cell.fill = FILL_FIXED_CELL
                        cell.font = FONT_FIXED

                    if show_cmt and note_txt:
                        cmt = Comment(f"[Centimani Studio 自動標註]\n{note_txt}", "ScriptDoctor")
                        cmt.width = 320
                        cmt.height = 120
                        cell.comment = cmt

    # Auto-adjust column widths based on text length (bounded by actual_max_c & actual_max_r)
    for col_idx in range(1, actual_max_c + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for r in range(1, min(actual_max_r + 1, 250)):
            cell_val = ws.cell(row=r, column=col_idx).value
            val_str = str(cell_val or "")
            for line in val_str.split("\n"):
                if len(line) > max_len:
                    max_len = len(line)
        col_w = max(max_len + 4, 11)
        if col_w > 46:
            col_w = 46
        ws.column_dimensions[col_letter].width = col_w


def _set_active_worksheet(wb, workspace, active_sheet=None):
    """
    Ensures Microsoft Excel opens directly on `active_sheet` (or the main station sheet)
    by updating wb.active, wb.views[0].activeTab, and every sheet's tabSelected flag.
    """
    target_active = active_sheet if (active_sheet and active_sheet in wb.sheetnames) else None
    if not target_active:
        for st_k in (workspace.get("stations") or {}).keys():
            if st_k in wb.sheetnames:
                target_active = st_k
                break
    if target_active and target_active in wb.sheetnames:
        active_idx = wb.sheetnames.index(target_active)
        wb.active = active_idx
        for i, ws_item in enumerate(wb.worksheets):
            try:
                if ws_item.views and ws_item.views.sheetView:
                    ws_item.views.sheetView[0].tabSelected = (i == active_idx)
            except Exception:
                pass
        try:
            if wb.views:
                wb.views[0].activeTab = active_idx
        except Exception:
            pass


def _safe_load_workbook(path, data_only=False):
    """Load workbook safely; strip out-of-range row style indices if legacy XML causes IndexError."""
    try:
        return openpyxl.load_workbook(path, data_only=data_only)
    except IndexError:
        tmp_buf = io.BytesIO()
        with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(tmp_buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.startswith("xl/worksheets/") and item.filename.endswith(".xml"):
                    text = data.decode("utf-8", errors="ignore")
                    text = re.sub(r'(<row\b[^>]*?)\s+s="\d+"([^>]*>)', r"\1\2", text)
                    data = text.encode("utf-8")
                zout.writestr(item, data)
        tmp_buf.seek(0)
        return openpyxl.load_workbook(tmp_buf, data_only=data_only)


def export_workspace_to_excel(workspace, output_excel_path, active_sheet=None):
    """
    Exports the workspace JSON into a standard 16-column Centimani .xlsx workbook.
    If `source_file` exists, patches the original workbook in-place so all Marco sheets (11-col),
    PathLoss sheets, and Connection1..10 columns are 100% preserved!
    """
    os.makedirs(os.path.dirname(output_excel_path), exist_ok=True)
    source_file = workspace.get("source_file", "")

    # Build lookup of modified cells per sheet: sheet_name -> {(row_idx, col_idx): meta_dict}
    col_name_to_idx = {h: i + 1 for i, h in enumerate(STATION_HEADERS_16)}
    marco_col_to_idx = {h: i + 1 for i, h in enumerate(MARCO_HEADERS_11)}
    marco_sheet_names = set(workspace.get("marcos", {}).keys())
    sheet_fixed_map = {}
    for mc in workspace.get("_modified_cells", []):
        hl = mc.get("highlight", "yellow")
        if mc.get("col_name") == "Index" and hl != "blue":
            continue  # Don't yellow-highlight every re-indexed row, but DO light-blue highlight reordered Phase rows
        s_name = mc.get("sheet", "")
        r_num = mc.get("row", 0)
        lookup = marco_col_to_idx if s_name in marco_sheet_names else col_name_to_idx
        c_idx = lookup.get(mc.get("col_name", ""), 0)
        if s_name and r_num and c_idx:
            s_map = sheet_fixed_map.setdefault(s_name, {})
            prev = s_map.get((r_num, c_idx))
            if prev and prev.get("highlight") == "blue" and hl != "blue":
                # Keep light-blue row background for reordered Phase block, append auto-fix note
                s_map[(r_num, c_idx)] = {
                    "note": (prev.get("note", "") + "\n" + mc.get("note", "")).strip(),
                    "highlight": "blue",
                    "show_comment": True,
                }
            else:
                s_map[(r_num, c_idx)] = {
                    "note": mc.get("note", ""),
                    "highlight": hl,
                    "show_comment": mc.get("show_comment", True),
                }

    if source_file and os.path.exists(source_file):
        # IN-PLACE NON-DESTRUCTIVE PATCH MODE
        wb = _safe_load_workbook(source_file)

        # Update Instrument sheet if workspace has updated instrument rows (Version, Mount, Settings, or newly added rows)
        if "Instrument" in wb.sheetnames and workspace.get("instruments"):
            ws_inst = wb["Instrument"]
            headers = [str(c.value).strip() if c.value is not None else "" for c in ws_inst[1]]
            mount_col = headers.index("Mount") + 1 if "Mount" in headers else None
            ver_col = headers.index("Version") + 1 if "Version" in headers else None
            name_col = headers.index("Name") + 1 if "Name" in headers else None
            dll_col = headers.index("ControlDLL") + 1 if "ControlDLL" in headers else None
            set_col = headers.index("Settings") + 1 if "Settings" in headers else None

            inst_map = {}
            for item in workspace.get("instruments", []):
                key = str(item.get("Name", "")).strip() or str(item.get("ControlDLL", "")).strip()
                if key:
                    inst_map[key.lower()] = item

            seen_keys = set()
            empty_streak = 0
            for r in range(2, ws_inst.max_row + 1):
                n_val = str(ws_inst.cell(row=r, column=name_col).value or "").strip().lower() if name_col else ""
                d_val = str(ws_inst.cell(row=r, column=dll_col).value or "").strip().lower() if dll_col else ""
                if not n_val and not d_val:
                    empty_streak += 1
                    if empty_streak >= 50:
                        break
                    continue
                empty_streak = 0
                match_item = inst_map.get(n_val) or inst_map.get(d_val)
                if match_item:
                    if n_val:
                        seen_keys.add(n_val)
                    if d_val:
                        seen_keys.add(d_val)
                    if ver_col and match_item.get("Version"):
                        ws_inst.cell(row=r, column=ver_col, value=match_item.get("Version"))
                    if mount_col and "Mount" in match_item and match_item.get("Mount") is not None:
                        m_str = str(match_item.get("Mount", "")).strip()
                        ws_inst.cell(row=r, column=mount_col).value = m_str if m_str else None
                    if set_col and match_item.get("Settings"):
                        ws_inst.cell(row=r, column=set_col, value=match_item.get("Settings"))

            # Append any newly added instruments (e.g., NI6008-1) not present in original Instrument sheet
            headers_to_use = headers if any(headers) else INSTRUMENT_HEADERS_9
            for item in workspace.get("instruments", []):
                n_key = str(item.get("Name", "")).strip().lower()
                d_key = str(item.get("ControlDLL", "")).strip().lower()
                if (n_key and n_key in seen_keys) or (d_key and d_key in seen_keys):
                    continue
                ws_inst.append([item.get(h, "") or None for h in headers_to_use])

        # Update Switch sheet if workspace has updated switch rows
        if "Switch" in wb.sheetnames and workspace.get("switches"):
            ws_sw = wb["Switch"]
            headers = [str(c.value).strip() if c.value is not None else "" for c in ws_sw[1]]
            ver_col = headers.index("Version") + 1 if "Version" in headers else None
            name_col = headers.index("Name") + 1 if "Name" in headers else None
            dll_col = headers.index("ControlDLL") + 1 if "ControlDLL" in headers else None
            if ver_col:
                sw_map = {}
                for item in workspace.get("switches", []):
                    key = item.get("Name", "").strip() or item.get("ControlDLL", "").strip()
                    if key:
                        sw_map[key.lower()] = item.get("Version", "")
                empty_streak = 0
                for r in range(2, ws_sw.max_row + 1):
                    n_val = str(ws_sw.cell(row=r, column=name_col).value or "").strip().lower() if name_col else ""
                    d_val = str(ws_sw.cell(row=r, column=dll_col).value or "").strip().lower() if dll_col else ""
                    if not n_val and not d_val:
                        empty_streak += 1
                        if empty_streak >= 50:
                            break
                        continue
                    empty_streak = 0
                    match_ver = sw_map.get(n_val) or sw_map.get(d_val)
                    if match_ver:
                        ws_sw.cell(row=r, column=ver_col, value=match_ver)

        # Update DUTs sheet if workspace has updated duts rows (fixes duplicate connection/DUT keys!)
        if "DUTs" in wb.sheetnames and workspace.get("duts"):
            ws_duts = wb["DUTs"]
            ws_duts.delete_rows(2, ws_duts.max_row + 2)
            duts_headers = [str(c.value).strip() if c.value is not None else "" for c in ws_duts[1]]
            headers_to_write = duts_headers if any(duts_headers) else DUTS_HEADERS_10
            for d in workspace.get("duts", []):
                ws_duts.append([d.get(h, "") or None for h in headers_to_write])

        # Write or update Station sheets (16 columns including TestID) in In-Place mode
        STATION_TAB_COLORS = ["2563EB", "16A34A", "D97706", "7C3AED", "0891B2", "DB2777", "DC2626", "0D9488"]
        for st_idx, (st_name, steps) in enumerate(workspace.get("stations", {}).items()):
            preserved_dvs = None
            if st_name in wb.sheetnames:
                idx_pos = wb.sheetnames.index(st_name)
                preserved_dvs = list(wb[st_name].data_validations.dataValidation)
                wb.remove(wb[st_name])
                ws_st = wb.create_sheet(title=st_name, index=idx_pos)
            else:
                ws_st = wb.create_sheet(title=st_name)
            ws_st.sheet_properties.tabColor = STATION_TAB_COLORS[st_idx % len(STATION_TAB_COLORS)]
            _write_station_sheet_contents(ws_st, steps, sheet_fixed_map.get(st_name, {}), preserved_dvs=preserved_dvs)

        # Write or update Marco sheets (11 columns: Index_NN + Send..TestID) in In-Place mode
        for m_name, m_steps in workspace.get("marcos", {}).items():
            if not isinstance(m_steps, list) or not m_steps:
                continue
            if m_name in wb.sheetnames:
                idx_pos = wb.sheetnames.index(m_name)
                wb.remove(wb[m_name])
                ws_m = wb.create_sheet(title=m_name, index=idx_pos)
            else:
                ws_m = wb.create_sheet(title=m_name)
            _write_marco_sheet_contents(ws_m, m_steps, sheet_fixed_map.get(m_name, {}))

        # Format other sheets cleanly with Calibri 11 + wrap_text without losing any columns
        for s_other in wb.sheetnames:
            if s_other not in workspace.get("stations", {}) and s_other not in workspace.get("marcos", {}):
                apply_sheet_formatting(wb[s_other], is_station=False)

        _set_active_worksheet(wb, workspace, active_sheet)

        actual_output_path = output_excel_path
        try:
            wb.save(output_excel_path)
        except (PermissionError, IOError) as pe:
            ts = datetime.datetime.now().strftime("%H%M%S")
            dir_name = os.path.dirname(output_excel_path)
            base_name = os.path.basename(output_excel_path)
            name_no_ext, ext = os.path.splitext(base_name)
            fallback_path = os.path.join(dir_name, f"{name_no_ext}_{ts}{ext}")
            print(f"[export_workspace_to_excel in-place] {output_excel_path} locked ({pe}), saving to fallback: {fallback_path}")
            wb.save(fallback_path)
            actual_output_path = fallback_path
        return actual_output_path

    # BRAND-NEW MOTHER TEMPLATE GENERATION MODE
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # 1. Properties
    ws_prop = wb.create_sheet(title="Properties")
    ws_prop.append(["Name", "Value"])
    now_ver = datetime.datetime.now().strftime("%y%m%d%H%M%S")
    for p in workspace.get("properties", []):
        p_name = p.get("Name", "")
        p_val = now_ver if p.get("Value") == "AUTO_TIMESTAMP" else p.get("Value", "")
        ws_prop.append([p_name, p_val])
    apply_sheet_formatting(ws_prop, is_station=False)

    # 2. DUTs (preserve Connection1..4 plus any extra Connection5..10 added by multi-alias UART/DLL blocks)
    ws_duts = wb.create_sheet(title="DUTs")
    duts_hdrs = list(DUTS_HEADERS_10)
    for d in workspace.get("duts", []):
        for k in d.keys():
            if k not in duts_hdrs and k.startswith("Connection") and str(d.get(k) or "").strip():
                duts_hdrs.append(k)
    ws_duts.append(duts_hdrs)
    for d in workspace.get("duts", []):
        ws_duts.append([d.get(h, "") or None for h in duts_hdrs])
    apply_sheet_formatting(ws_duts, is_station=False)

    # 3. Switch
    ws_sw = wb.create_sheet(title="Switch")
    ws_sw.append(SWITCH_HEADERS_7)
    for sw in workspace.get("switches", []):
        ws_sw.append([sw.get(h, "") or None for h in SWITCH_HEADERS_7])
    apply_sheet_formatting(ws_sw, is_station=False)

    # 4. Instrument
    ws_inst = wb.create_sheet(title="Instrument")
    ws_inst.append(INSTRUMENT_HEADERS_9)
    for inst in workspace.get("instruments", []):
        ws_inst.append([inst.get(h, "") or None for h in INSTRUMENT_HEADERS_9])
    apply_sheet_formatting(ws_inst, is_station=False)

    # 5. Station Sheets (16 columns including TestID)
    STATION_TAB_COLORS = ["2563EB", "16A34A", "D97706", "7C3AED", "0891B2", "DB2777", "DC2626", "0D9488"]
    for st_idx, (st_name, steps) in enumerate(workspace.get("stations", {}).items()):
        ws_st = wb.create_sheet(title=st_name)
        ws_st.sheet_properties.tabColor = STATION_TAB_COLORS[st_idx % len(STATION_TAB_COLORS)]
        _write_station_sheet_contents(ws_st, steps, sheet_fixed_map.get(st_name, {}))

    # 6. Marco Sheets (11 columns: Index_NN + Send..TestID)
    for m_name, m_steps in workspace.get("marcos", {}).items():
        if not isinstance(m_steps, list):
            continue
        ws_m = wb.create_sheet(title=m_name)
        _write_marco_sheet_contents(ws_m, m_steps, sheet_fixed_map.get(m_name, {}))

    _set_active_worksheet(wb, workspace, active_sheet)

    # 防禦性存檔：若檔案被 Excel 鎖定引發 PermissionError，自動以時間戳備援檔名保存
    actual_output_path = output_excel_path
    try:
        wb.save(output_excel_path)
    except (PermissionError, IOError) as pe:
        ts = datetime.datetime.now().strftime("%H%M%S")
        dir_name = os.path.dirname(output_excel_path)
        base_name = os.path.basename(output_excel_path)
        name_no_ext, ext = os.path.splitext(base_name)
        fallback_path = os.path.join(dir_name, f"{name_no_ext}_{ts}{ext}")
        print(f"[export_workspace_to_excel] {output_excel_path} locked ({pe}), saving to fallback: {fallback_path}")
        wb.save(fallback_path)
        actual_output_path = fallback_path

    return actual_output_path


def import_excel_to_workspace(xlsx_path):
    """
    Reads any existing Centimani .xlsx script (and sibling Global.ini / System.ini if present)
    into a workspace dictionary. Strictly separates 16-column Station Sheets from 11-column Marco Sheets!
    """
    folder = os.path.dirname(xlsx_path)
    fname = os.path.basename(xlsx_path)
    proj_guess = fname.split("_")[0] if "_" in fname else os.path.splitext(fname)[0]

    ws_data = get_golden_mother(project_name=proj_guess, station_name="MB")
    ws_data["source_file"] = xlsx_path
    ws_data["stations"] = {}
    ws_data["marcos"] = {}

    try:
        wb = _safe_load_workbook(xlsx_path, data_only=True)
    except Exception:
        wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)

    # 1. Read Properties
    if "Properties" in wb.sheetnames:
        props = []
        for r_idx, r in enumerate(wb["Properties"].iter_rows(values_only=True)):
            if r_idx == 0 or not any(r):
                continue
            props.append({
                "Name": str(r[0]).strip() if r[0] is not None else "",
                "Value": str(r[1]).strip() if len(r) > 1 and r[1] is not None else ""
            })
        if props:
            ws_data["properties"] = props

    # 2. Read DUTs / Switch / Instrument (preserving all columns present in the sheet)
    def read_table_sheet(sheet_name, default_headers):
        if sheet_name not in wb.sheetnames:
            return []
        rows = _read_bounded_rows(wb[sheet_name], max_col=20, max_empty_streak=30, hard_limit=1000)
        if not rows:
            return []
        raw_h = [str(c).strip() if c is not None else f"Col_{i}" for i, c in enumerate(rows[0])]
        headers_to_use = raw_h if any(raw_h) else default_headers
        result = []
        for r in rows[1:]:
            if not any(r):
                continue
            item = {}
            for i, h in enumerate(headers_to_use):
                val = r[i] if i < len(r) else None
                item[h] = str(val).strip() if val is not None else ""
            result.append(item)
        return result

    if "DUTs" in wb.sheetnames:
        ws_data["duts"] = read_table_sheet("DUTs", DUTS_HEADERS_10)
    if "Switch" in wb.sheetnames:
        ws_data["switches"] = read_table_sheet("Switch", SWITCH_HEADERS_7)
    if "Instrument" in wb.sheetnames:
        ws_data["instruments"] = read_table_sheet("Instrument", INSTRUMENT_HEADERS_9)

    # 3. Read Station Sheets (16-col, has 'Phase') vs Marco Sheets (11-col, has 'Send' but no 'Phase')
    first_station = None
    for s_name in wb.sheetnames:
        if s_name in ["Properties", "DUTs", "Switch", "Instrument", "PathLoss"]:
            continue
        rows, hidden_flags = _read_bounded_rows(wb[s_name], max_col=17, max_empty_streak=50, hard_limit=5000, include_hidden=True)
        if not rows:
            continue
        headers = [str(c).strip() if c is not None else "" for c in rows[0][:17]]
        headers_low = [h.lower() for h in headers]

        if "phase" in headers_low:
            # 16-Column Station Sheet (case-insensitive to preserve legacy lowercase 'phase' sheets)
            if first_station is None:
                first_station = s_name
            step_list = []
            for r, is_hid in zip(rows[1:], hidden_flags[1:]):
                if not any(r[:16]):
                    continue
                r_pad = list(r[:16]) + [None] * max(0, 16 - len(r[:16]))
                step_item = {}
                for c_i, h_key in enumerate(STATION_HEADERS_16):
                    v = r_pad[c_i]
                    step_item[h_key] = str(v).strip() if v is not None else ""
                if is_hid:
                    step_item["_hidden"] = True
                step_list.append(step_item)
            ws_data["stations"][s_name] = step_list
        elif "send" in headers_low:
            # 11-Column Marco Sheet (parse full steps list for auditing, jump editing, and dry-run)
            m_list = []
            for r, is_hid in zip(rows[1:], hidden_flags[1:]):
                if not any(r[:11]):
                    continue
                r_pad = list(r[:11]) + [None] * max(0, 11 - len(r[:11]))
                m_item = {}
                for c_i, h_key in enumerate(MARCO_HEADERS_11):
                    v = r_pad[c_i]
                    m_item[h_key] = str(v).strip() if v is not None else ""
                if is_hid:
                    m_item["_hidden"] = True
                m_list.append(m_item)
            ws_data["marcos"][s_name] = m_list

    if first_station:
        ws_data["station_name"] = first_station

    wb.close()

    # 4. Read sibling Global.ini if available
    for g_cand in [os.path.join(folder, "Global.ini"), os.path.join(folder, "0_Global.ini"), os.path.join(folder, "System", "Global.ini")]:
        if os.path.exists(g_cand):
            curr_sec = None
            with open(g_cand, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("//") or s.startswith(";"):
                        continue
                    if s.startswith("[") and s.endswith("]"):
                        curr_sec = s[1:-1].strip()
                        ws_data["global_ini"].setdefault(curr_sec, {})
                    elif "=" in s and curr_sec in ["Settings", "Scripts"]:
                        k, v = s.split("=", 1)
                        ws_data["global_ini"][curr_sec][k.strip()] = v.strip()
            break

    # 5. Read sibling System.ini SFIS/iPLAS keys if available
    for s_cand in [os.path.join(folder, "System.ini"), os.path.join(folder, "System", "System.ini")]:
        if os.path.exists(s_cand):
            with open(s_cand, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("//") or s.startswith(";") or s.startswith("["):
                        continue
                    if "=" in s:
                        k, v = s.split("=", 1)
                        k_s = k.strip()
                        if k_s in (
                            "SFIS_Enable", "SFIS_AutoLogin", "SFIS_SkipSaveResultOnFail",
                            "SFIS_LoginID", "SFIS_GetDateISN", "SFIS_LinkIPLAS",
                            "SFIS_WebLink", "SFIS_TSP", "StationName",
                            "iPLAS_Enable", "iPLAS_Site", "iPLAS_ProjectName", "TestItemCodeFile",
                        ):
                            ws_data.setdefault("system_ini", {})[k_s] = v.strip()
            break

    return ws_data


def extract_blocks_from_excel(xlsx_path):
    """
    Parses an existing Centimani .xlsx script and groups each Phase / Title block
    into reusable 16-column Lego blocks that can be added to the studio library.
    """
    ws_data = import_excel_to_workspace(xlsx_path)
    fname = os.path.basename(xlsx_path)
    extracted = []

    for st_name, steps in ws_data.get("stations", {}).items():
        curr_blk = None
        for step in steps:
            s_phase = step.get("Phase", "")
            s_title = step.get("Title", "")
            if s_title or s_phase or curr_blk is None:
                title_clean = s_title.split(",")[1] if "," in s_title else (s_title or f"Phase_{s_phase}")
                curr_blk = {
                    "block_id": f"EXT_{st_name}_{len(extracted)+1:03d}",
                    "category": f"📥 萃取自 {fname[:18]} ({st_name})",
                    "name": f"[P{s_phase or '-'}] {title_clean}",
                    "description": f"萃取自 {fname} -> [{st_name}] 工作表 ({s_title})",
                    "default_phase": s_phase,
                    "required_globals": {"Settings": {}, "Scripts": {}},
                    "steps": []
                }
                extracted.append(curr_blk)
            curr_blk["steps"].append(step)

    return extracted


def list_excel_sheet_names(xlsx_path):
    """Returns all worksheet names in an Excel file quickly using read_only mode."""
    if not xlsx_path or not os.path.exists(xlsx_path):
        return []
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


def _resolve_target_sheet_name(existing_names, desired_name, overwrite=False):
    """Resolves a safe worksheet name (<=31 chars) when copying into a workbook."""
    base = (desired_name or "CopiedSheet").strip()[:31]
    if overwrite or base not in existing_names:
        return base
    for i in range(1, 100):
        suffix = f"_{i}"
        cand = base[: 31 - len(suffix)] + suffix
        if cand not in existing_names:
            return cand
    return base[:27] + "_new"


def _copy_sheet_openpyxl(source_excel_path, source_sheet_name, target_excel_path, target_sheet_name, overwrite=False):
    """Fallback pure-Python deep copy preserving styles, column widths, row heights, merges, and freeze panes."""
    src_wb = openpyxl.load_workbook(source_excel_path, data_only=False)
    dst_wb = openpyxl.load_workbook(target_excel_path, data_only=False)
    try:
        if source_sheet_name not in src_wb.sheetnames:
            raise ValueError(f"來源檔案找不到工作表：{source_sheet_name}")
        src_ws = src_wb[source_sheet_name]
        final_name = _resolve_target_sheet_name(dst_wb.sheetnames, target_sheet_name or source_sheet_name, overwrite=overwrite)

        if overwrite and final_name in dst_wb.sheetnames:
            idx_pos = dst_wb.sheetnames.index(final_name)
            dst_wb.remove(dst_wb[final_name])
            dst_ws = dst_wb.create_sheet(title=final_name, index=idx_pos)
        else:
            dst_ws = dst_wb.create_sheet(title=final_name)

        max_r = min(src_ws.max_row or 1, 15000)
        max_c = min(src_ws.max_column or 1, 100)
        for r in range(1, max_r + 1):
            for c in range(1, max_c + 1):
                s_cell = src_ws.cell(row=r, column=c)
                d_cell = dst_ws.cell(row=r, column=c, value=s_cell.value)
                if s_cell.has_style:
                    d_cell.font = _copy_style(s_cell.font)
                    d_cell.fill = _copy_style(s_cell.fill)
                    d_cell.border = _copy_style(s_cell.border)
                    d_cell.alignment = _copy_style(s_cell.alignment)
                    d_cell.number_format = s_cell.number_format
                if s_cell.comment:
                    d_cell.comment = Comment(s_cell.comment.text, s_cell.comment.author)

        for col_letter, dim in src_ws.column_dimensions.items():
            d_dim = dst_ws.column_dimensions[col_letter]
            if dim.width is not None:
                d_dim.width = dim.width
            d_dim.hidden = dim.hidden

        for r_idx, dim in src_ws.row_dimensions.items():
            d_dim = dst_ws.row_dimensions[r_idx]
            if dim.height is not None:
                d_dim.height = dim.height
            d_dim.hidden = dim.hidden

        for m_range in src_ws.merged_cells.ranges:
            dst_ws.merge_cells(str(m_range))

        dst_ws.freeze_panes = src_ws.freeze_panes
        if src_ws.sheet_properties.tabColor is not None:
            dst_ws.sheet_properties.tabColor = _copy_style(src_ws.sheet_properties.tabColor)

        _set_active_worksheet(dst_wb, None, active_sheet=final_name)
        dst_wb.save(target_excel_path)
        return final_name
    finally:
        src_wb.close()
        dst_wb.close()


def copy_sheet_between_excels(
    source_excel_path,
    source_sheet_name,
    target_excel_path,
    target_sheet_name=None,
    overwrite=False,
    use_excel_com=True,
    create_backup=True,
):
    """
    Copies an entire worksheet from source_excel_path into target_excel_path
    while preserving full formatting (widths, borders, fills, merges, formulas).
    Uses native Excel COM (win32com) when available, with openpyxl deep-copy fallback.
    """
    src_abs = os.path.abspath(source_excel_path)
    dst_abs = os.path.abspath(target_excel_path)
    if not os.path.exists(src_abs):
        raise FileNotFoundError(f"找不到來源 Excel：{src_abs}")
    if not os.path.exists(dst_abs):
        raise FileNotFoundError(f"找不到目標 Excel：{dst_abs}")

    if create_backup:
        bak_path = dst_abs + ".bak"
        shutil.copy2(dst_abs, bak_path)

    desired = (target_sheet_name or source_sheet_name).strip()
    if use_excel_com:
        excel = None
        src_wb = None
        dst_wb = None
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            excel.ScreenUpdating = False

            src_wb = excel.Workbooks.Open(src_abs, ReadOnly=True)
            dst_wb = excel.Workbooks.Open(dst_abs)

            src_names = [s.Name for s in src_wb.Sheets]
            if source_sheet_name not in src_names:
                raise ValueError(f"來源檔案找不到工作表：{source_sheet_name}")

            dst_names = [s.Name for s in dst_wb.Sheets]
            final_name = _resolve_target_sheet_name(dst_names, desired, overwrite=overwrite)
            if overwrite and final_name in dst_names and len(dst_names) > 1:
                dst_wb.Sheets(final_name).Delete()

            src_ws = src_wb.Sheets(source_sheet_name)
            src_ws.Copy(After=dst_wb.Sheets(dst_wb.Sheets.Count))
            copied_ws = dst_wb.Sheets(dst_wb.Sheets.Count)
            copied_ws.Name = final_name
            copied_ws.Activate()
            dst_wb.Save()
            return {
                "status": "ok",
                "target_excel_path": dst_abs,
                "copied_sheet": final_name,
                "engine": "excel_com",
            }
        except Exception:
            pass
        finally:
            try:
                if src_wb is not None:
                    src_wb.Close(SaveChanges=False)
            except Exception:
                pass
            try:
                if dst_wb is not None:
                    dst_wb.Close(SaveChanges=False)
            except Exception:
                pass
            try:
                if excel is not None:
                    excel.Quit()
            except Exception:
                pass
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass

    final_name = _copy_sheet_openpyxl(src_abs, source_sheet_name, dst_abs, desired, overwrite=overwrite)
    return {
        "status": "ok",
        "target_excel_path": dst_abs,
        "copied_sheet": final_name,
        "engine": "openpyxl",
    }
