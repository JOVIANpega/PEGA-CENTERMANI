# -*- coding: utf-8 -*-
"""
Centimani Studio - Bi-Directional 16-Column Excel Engine V2.1
Supports both:
1. Generating brand-new 16-Column Mother Excel from selected Lego blocks.
2. In-Place Non-Destructive Patching of existing Excel files (preserving all Marco 11-col sheets,
   PathLoss, and Connection1..10 columns while highlighting repaired cells in yellow with notes).
"""
import os
import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter
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

FILL_HEADER = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
FILL_PHASE0 = PatternFill(start_color="F2F8FD", end_color="F2F8FD", fill_type="solid")
FILL_PHASE97 = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
FILL_SKIP = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
FILL_FIXED_CELL = PatternFill(start_color="FEF08A", end_color="FEF08A", fill_type="solid")

BORDER_THIN = Border(
    left=Side(style="thin", color="64748B"),
    right=Side(style="thin", color="64748B"),
    top=Side(style="thin", color="64748B"),
    bottom=Side(style="thin", color="64748B")
)

ALIGN_LEFT = Alignment(wrap_text=True, vertical="center", horizontal="left")
ALIGN_CENTER = Alignment(wrap_text=True, vertical="center", horizontal="center")


def apply_sheet_formatting(ws, is_station=False, fixed_cell_map=None):
    """Applies Calibri 11, wrap_text=True, borders, auto-fit column widths, and yellow highlights for fixed cells."""
    fixed_cell_map = fixed_cell_map or {}
    ws.row_dimensions[1].height = 28
    center_cols = {1, 2, 8, 9, 13, 14, 16} if is_station else {1}

    # Bounded column count prevents openpyxl from hanging on sparse/unbounded sheets (e.g. max_col=16384)
    max_c = min(ws.max_column or 1, 16 if is_station else 30)

    curr_phase_str = ""
    for r_idx, row in enumerate(ws.iter_rows(max_col=max_c), start=1):
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
                cell.font = FONT_SKIP if curr_phase_str.startswith("-") else FONT_BODY
                cell.alignment = ALIGN_CENTER if c_idx in center_cols else ALIGN_LEFT
                if is_station:
                    if curr_phase_str.startswith("-"):
                        cell.fill = FILL_SKIP
                    elif curr_phase_str == "0":
                        cell.fill = FILL_PHASE0
                    elif curr_phase_str == "97":
                        cell.fill = FILL_PHASE97

                # Highlight modified cells in bright yellow (#FEF08A) with Comment
                if (r_idx, c_idx) in fixed_cell_map:
                    note_txt = fixed_cell_map[(r_idx, c_idx)]
                    cell.fill = FILL_FIXED_CELL
                    cell.font = FONT_FIXED
                    cmt = Comment(f"[Centimani Studio 自動修正]\n{note_txt}", "ScriptDoctor")
                    cmt.width = 320
                    cmt.height = 120
                    cell.comment = cmt

    # Auto-adjust column widths based on text length (bounded by max_c)
    for col_idx in range(1, max_c + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for r in range(1, min(ws.max_row + 1, 250)):
            cell_val = ws.cell(row=r, column=col_idx).value
            val_str = str(cell_val or "")
            for line in val_str.split("\n"):
                if len(line) > max_len:
                    max_len = len(line)
        col_w = max(max_len + 4, 11)
        if col_w > 46:
            col_w = 46
        ws.column_dimensions[col_letter].width = col_w


def export_workspace_to_excel(workspace, output_excel_path, active_sheet=None):
    """
    Exports the workspace JSON into a standard 16-column Centimani .xlsx workbook.
    If `source_file` exists, patches the original workbook in-place so all Marco sheets (11-col),
    PathLoss sheets, and Connection1..10 columns are 100% preserved!
    """
    os.makedirs(os.path.dirname(output_excel_path), exist_ok=True)
    source_file = workspace.get("source_file", "")

    # Build lookup of modified cells per sheet: sheet_name -> {(row_idx, col_idx): note}
    col_name_to_idx = {h: i + 1 for i, h in enumerate(STATION_HEADERS_16)}
    sheet_fixed_map = {}
    for mc in workspace.get("_modified_cells", []):
        if mc.get("col_name") == "Index":
            continue  # Don't yellow-highlight every re-indexed row
        s_name = mc.get("sheet", "")
        r_num = mc.get("row", 0)
        c_idx = col_name_to_idx.get(mc.get("col_name", ""), 0)
        if s_name and r_num and c_idx:
            sheet_fixed_map.setdefault(s_name, {})[(r_num, c_idx)] = mc.get("note", "")

    if source_file and os.path.exists(source_file):
        # IN-PLACE NON-DESTRUCTIVE PATCH MODE
        wb = openpyxl.load_workbook(source_file)

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
            for r in range(2, ws_inst.max_row + 1):
                n_val = str(ws_inst.cell(row=r, column=name_col).value or "").strip().lower() if name_col else ""
                d_val = str(ws_inst.cell(row=r, column=dll_col).value or "").strip().lower() if dll_col else ""
                match_item = inst_map.get(n_val) or inst_map.get(d_val)
                if match_item:
                    if n_val:
                        seen_keys.add(n_val)
                    if d_val:
                        seen_keys.add(d_val)
                    if ver_col and match_item.get("Version"):
                        ws_inst.cell(row=r, column=ver_col, value=match_item.get("Version"))
                    if mount_col and match_item.get("Mount") is not None:
                        m_str = str(match_item.get("Mount", "")).strip()
                        if m_str:
                            ws_inst.cell(row=r, column=mount_col, value=m_str)
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
                for r in range(2, ws_sw.max_row + 1):
                    n_val = str(ws_sw.cell(row=r, column=name_col).value or "").strip().lower() if name_col else ""
                    d_val = str(ws_sw.cell(row=r, column=dll_col).value or "").strip().lower() if dll_col else ""
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

        for st_name, steps in workspace.get("stations", {}).items():
            if st_name in wb.sheetnames:
                ws_st = wb[st_name]
                # Clear existing rows
                ws_st.delete_rows(1, ws_st.max_row + 10)
            else:
                ws_st = wb.create_sheet(title=st_name)

            total_steps = len(steps)
            st_headers = [f"Index_{total_steps:03d}"] + STATION_HEADERS_16[1:]
            ws_st.append(st_headers)

            for idx, step in enumerate(steps):
                step["Index"] = f"{idx:03d}"
                row_vals = []
                for h in STATION_HEADERS_16:
                    val = step.get(h, "")
                    row_vals.append(val if (val is not None and str(val) != "") else None)
                ws_st.append(row_vals)

            apply_sheet_formatting(ws_st, is_station=True, fixed_cell_map=sheet_fixed_map.get(st_name, {}))

        # Format other sheets cleanly with Calibri 11 + wrap_text without losing any columns
        for s_other in wb.sheetnames:
            if s_other not in workspace.get("stations", {}):
                apply_sheet_formatting(wb[s_other], is_station=False)

        if active_sheet and active_sheet in wb.sheetnames:
            wb.active = wb[active_sheet]

        wb.save(output_excel_path)
        return output_excel_path

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

    # 2. DUTs
    ws_duts = wb.create_sheet(title="DUTs")
    ws_duts.append(DUTS_HEADERS_10)
    for d in workspace.get("duts", []):
        ws_duts.append([d.get(h, "") or None for h in DUTS_HEADERS_10])
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
    for st_name, steps in workspace.get("stations", {}).items():
        ws_st = wb.create_sheet(title=st_name)
        total_steps = len(steps)
        st_headers = [f"Index_{total_steps:03d}"] + STATION_HEADERS_16[1:]
        ws_st.append(st_headers)

        for idx, step in enumerate(steps):
            step["Index"] = f"{idx:03d}"
            row_vals = []
            for h in STATION_HEADERS_16:
                val = step.get(h, "")
                row_vals.append(val if (val is not None and str(val) != "") else None)
            ws_st.append(row_vals)
        apply_sheet_formatting(ws_st, is_station=True, fixed_cell_map=sheet_fixed_map.get(st_name, {}))

    # 6. Marco Sheets (11 columns: Index_NN + Send..TestID)
    for m_name, m_steps in workspace.get("marcos", {}).items():
        if not isinstance(m_steps, list):
            continue
        ws_m = wb.create_sheet(title=m_name)
        m_headers = [f"Index_{len(m_steps)}"] + MARCO_HEADERS_11[1:]
        ws_m.append(m_headers)
        for idx, step in enumerate(m_steps):
            step["Index"] = f"{idx:02d}"
            row_vals = []
            for h in MARCO_HEADERS_11:
                val = step.get(h, "")
                row_vals.append(val if (val is not None and str(val) != "") else None)
            ws_m.append(row_vals)
        apply_sheet_formatting(ws_m, is_station=False, fixed_cell_map=sheet_fixed_map.get(m_name, {}))

    if active_sheet and active_sheet in wb.sheetnames:
        wb.active = wb[active_sheet]

    # 防禦性存檔：若檔案被 Excel 鎖定引發 PermissionError，自動以時間戳備援檔名保存
    actual_output_path = output_excel_path
    try:
        wb.save(output_excel_path)
    except (PermissionError, IOError) as pe:
        import datetime
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
        wb = openpyxl.load_workbook(xlsx_path, data_only=True)
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
        rows = list(wb[sheet_name].iter_rows(max_col=20, values_only=True))
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
        rows = list(wb[s_name].iter_rows(max_col=17, values_only=True))
        if not rows:
            continue
        headers = [str(c).strip() if c is not None else "" for c in rows[0][:17]]

        if "Phase" in headers:
            # 16-Column Station Sheet
            if first_station is None:
                first_station = s_name
            step_list = []
            for r in rows[1:]:
                if not any(r[:16]):
                    continue
                r_pad = list(r[:16]) + [None] * max(0, 16 - len(r[:16]))
                step_item = {}
                for c_i, h_key in enumerate(STATION_HEADERS_16):
                    v = r_pad[c_i]
                    step_item[h_key] = str(v).strip() if v is not None else ""
                step_list.append(step_item)
            ws_data["stations"][s_name] = step_list
        elif "Send" in headers:
            # 11-Column Marco Sheet
            ws_data["marcos"][s_name] = len(rows) - 1

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
                        if k_s in ("SFIS_Enable", "SFIS_LinkIPLAS", "SFIS_WebLink", "SFIS_TSP", "iPLAS_Enable", "iPLAS_Site", "iPLAS_ProjectName", "TestItemCodeFile"):
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
