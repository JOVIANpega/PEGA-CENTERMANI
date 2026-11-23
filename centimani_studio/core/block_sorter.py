import copy
import os
import re


def _parse_phase_int(val):
    s = str(val or "").strip()
    if not s:
        return None
    s_head = s.split(":")[0].strip()
    try:
        return int(float(s_head))
    except Exception:
        return None


def _extract_produced_vars(row):
    out = set()
    ref_str = str(row.get("Ref") or "")
    for m in re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", ref_str):
        out.add(m)
    send_str = str(row.get("Send") or "")
    for m in re.findall(r':SetVal\s*,\s*"\$([A-Za-z_][A-Za-z0-9_]*)"', send_str, flags=re.IGNORECASE):
        out.add(m)
    return out


def _extract_used_vars(row):
    out = set()
    send_str = str(row.get("Send") or "")
    val_str = str(row.get("Validation") or "")
    # Ignore :SetVal target variable when scanning Send for usages
    cleaned_send = re.sub(r':SetVal\s*,\s*"\$[A-Za-z_][A-Za-z0-9_]*"', '', send_str, flags=re.IGNORECASE)
    for text in (cleaned_send, val_str):
        # Match *(Var) or *$(Var) or $Var (excluding Global.ini *$(...))
        for m in re.findall(r"(?<!\*)\$([A-Za-z_][A-Za-z0-9_]*)", text):
            out.add(m)
        for m in re.findall(r"\*\(([A-Za-z_][A-Za-z0-9_]*)\)", text):
            if m.upper() not in ("ISN", "SN", "MAC"):
                out.add(m)
    return out


def extract_station_blocks(rows):
    """
    Group a station's rows into contiguous Phase blocks.
    A new block starts at row 0, or whenever Phase column has an explicit non-empty value
    that differs from the current block's Phase.
    Rows with empty Phase remain inside their parent Phase block.
    """
    if not rows:
        return []

    raw_blocks = []
    cur = None
    for idx, row in enumerate(rows):
        phase_str = str(row.get("Phase") or "").strip()
        title_str = str(row.get("Title") or "").strip()

        # A block starts at row 0, or whenever Phase column has a non-empty value
        # that transitions to a new Phase
        is_header = (idx == 0) or (bool(phase_str) and (cur is None or phase_str != cur.get("phase")))
        if is_header:
            if cur is not None:
                raw_blocks.append(cur)
            cur = {
                "orig_idx": len(raw_blocks),
                "start_row": idx + 2,  # 1-based Excel row (row 1 is header)
                "phase": phase_str,
                "phase_num": _parse_phase_int(phase_str),
                "title": title_str or (f"Phase {phase_str}" if phase_str else f"區塊 #{len(raw_blocks) + 1}"),
                "rows": [row],
            }
        else:
            cur["rows"].append(row)
            # If current block's title is generic or empty, and this row has a title, adopt it
            if not cur.get("title") or cur.get("title").startswith("Phase ") or cur.get("title").startswith("區塊 #"):
                if title_str:
                    cur["title"] = title_str

    if cur is not None:
        raw_blocks.append(cur)

    # Compute vars and Phase order regression flags
    prev_phase = None
    seen_teardown = False
    result = []
    for b in raw_blocks:
        produced = set()
        used = set()
        for r in b["rows"]:
            r_prod = _extract_produced_vars(r)
            r_used = _extract_used_vars(r)
            # Only count as external usage if not already produced earlier in this same block
            used |= (r_used - produced)
            produced |= r_prod

        pnum = b["phase_num"]
        is_teardown = (pnum is not None and pnum >= 95)
        is_skipped = (pnum == -1)
        out_of_order = False
        order_reason = ""
        if pnum is not None and not is_skipped:
            if seen_teardown and not is_teardown:
                out_of_order = True
                order_reason = f"Phase {pnum} 位於收尾固定區 Phase >= 95 之後"
            elif not is_teardown and prev_phase is not None and pnum < prev_phase:
                out_of_order = True
                order_reason = f"Phase {pnum} 倒退小於前方 Phase {prev_phase}"
            if is_teardown:
                seen_teardown = True
            else:
                prev_phase = pnum

        result.append({
            "orig_idx": b["orig_idx"],
            "start_row": b["start_row"],
            "phase": b["phase"],
            "phase_num": pnum,
            "title": b["title"],
            "row_count": len(b["rows"]),
            "is_teardown": is_teardown,
            "is_skipped": is_skipped,
            "is_out_of_order": out_of_order,
            "order_reason": order_reason,
            "produced_vars": sorted(produced),
            "used_vars": sorted(used),
            "_rows": b["rows"],
        })
    return result


def serialize_blocks_for_ui(blocks):
    out = []
    for b in blocks:
        item = {k: v for k, v in b.items() if k != "_rows"}
        item["steps"] = [
            {
                "Command": str(r.get("Command") or "").strip(),
                "Send": str(r.get("Send") or "").strip(),
            }
            for r in b.get("_rows", [])
        ]
        out.append(item)
    return out


def check_var_dependencies(blocks):
    """
    Check if any block references a $Var that is ONLY produced in a later block.
    Returns a list of human-readable warning strings.
    """
    all_produced = set()
    for b in blocks:
        all_produced.update(b.get("produced_vars", []))

    seen_produced = set()
    warnings = []
    for pos, b in enumerate(blocks):
        for v in b.get("used_vars", []):
            if v in all_produced and v not in seen_produced:
                # Find which later block produces it
                prod_block = next((x for x in blocks[pos + 1:] if v in x.get("produced_vars", [])), None)
                if prod_block:
                    warnings.append(
                        f"變數 ${v} 在 [{b['title']}] 被使用，但產出它的區塊 [{prod_block['title']}] 目前排在後面！"
                    )
        seen_produced.update(b.get("produced_vars", []))
    return warnings


def find_phase_order_issues(workspace):
    """
    Scan all stations for Phase order regression or normal Phase placed after Phase 97.
    Returns (issues_list, warning_strings).
    """
    issues = []
    warn_strings = []
    for st_name, rows in (workspace.get("stations") or {}).items():
        if not isinstance(rows, list):
            continue
        blocks = extract_station_blocks(rows)
        for b in blocks:
            if b["is_out_of_order"]:
                issues.append({
                    "sheet": st_name,
                    "start_row": b["start_row"],
                    "title": b["title"],
                    "phase": b["phase"],
                    "reason": b["order_reason"],
                })
                warn_strings.append(
                    f"[{st_name}] 第 {b['start_row']} 列 [{b['title']}] 的 Phase 順序異常（{b['order_reason']}），請開啟「🧱 積木排序器」拖拉調整順序或自動順編 Phase。"
                )
    return issues, warn_strings


def reorder_station_blocks(workspace, sheet_name, new_order_indices, auto_renumber_phase=True, paused_orig_indices=None):
    """
    Reorder a station's Title/Phase blocks according to new_order_indices,
    optionally pause/resume blocks (Phase = -1 <-> numeric Phase),
    re-index the Index column, optionally re-number non-teardown numeric Phases,
    highlight moved/paused/renumbered Phase blocks in light blue (_modified_cells with highlight='blue'),
    and run variable dependency checks.
    """
    stations = workspace.get("stations") or {}
    if sheet_name not in stations:
        raise ValueError(f"找不到工作表：{sheet_name}")

    rows = stations[sheet_name]
    blocks = extract_station_blocks(rows)
    if len(new_order_indices) != len(blocks) or sorted(new_order_indices) != list(range(len(blocks))):
        raise ValueError("區塊排序索引不完整或重複")

    # Record each block's original Phase and original start_row before mutation
    orig_meta = {
        b["orig_idx"]: {
            "orig_pos": b["orig_idx"],
            "orig_phase": str(b.get("phase") or "").strip(),
            "orig_start_row": b.get("start_row", 2),
            "title": b.get("title", ""),
        }
        for b in blocks
    }

    ordered_blocks = [blocks[i] for i in new_order_indices]

    # Apply pause/resume toggles if specified
    if paused_orig_indices is not None:
        paused_set = {int(x) for x in paused_orig_indices}
        used_positive = {
            b["phase_num"]
            for b in ordered_blocks
            if b["orig_idx"] not in paused_set
            and b["phase_num"] is not None
            and 0 <= b["phase_num"] < 95
        }
        for b in ordered_blocks:
            is_fixed = b.get("is_teardown") or (b["phase_num"] is not None and b["phase_num"] >= 95)
            if is_fixed:
                continue
            if b["orig_idx"] in paused_set:
                b["_rows"][0]["Phase"] = "-1"
                b["phase"] = "-1"
                b["phase_num"] = -1
                b["is_skipped"] = True
            elif b["phase_num"] == -1:
                cand = 1
                while cand in used_positive and cand < 95:
                    cand += 1
                used_positive.add(cand)
                b["_rows"][0]["Phase"] = str(cand)
                b["phase"] = str(cand)
                b["phase_num"] = cand
                b["is_skipped"] = False

    # Determine starting phase number if auto-renumbering (keep skipped Phase=-1 intact!)
    if auto_renumber_phase:
        normal_nums = [b["phase_num"] for b in ordered_blocks if b["phase_num"] is not None and 0 <= b["phase_num"] < 95]
        next_phase = min(normal_nums) if normal_nums else 1
        if next_phase > 1:
            next_phase = 1
        for b in ordered_blocks:
            if b["phase_num"] is not None and 0 <= b["phase_num"] < 95:
                b["_rows"][0]["Phase"] = str(next_phase)
                b["phase"] = str(next_phase)
                b["phase_num"] = next_phase
                next_phase += 1

    # Rebuild flattened rows, re-index 000, 001, ..., and mark modified Phase blocks in light blue
    from .golden_data import STATION_HEADERS_16
    mods = [m for m in workspace.get("_modified_cells", []) if m.get("sheet") != sheet_name]

    new_rows = []
    for new_pos, b in enumerate(ordered_blocks):
        om = orig_meta.get(b["orig_idx"], {})
        old_pos = om.get("orig_pos", new_pos)
        old_phase = om.get("orig_phase", "")
        new_phase = str(b.get("phase") or "").strip()
        is_block_modified = (old_pos != new_pos) or (old_phase != new_phase)
        block_start_excel_row = len(new_rows) + 2

        for r_off, r in enumerate(b["_rows"]):
            excel_row = len(new_rows) + 2
            new_rows.append(r)
            if is_block_modified:
                note_txt = (
                    f"[積木順序排序] 區塊「{b.get('title', '')}」"
                    f"由原第 {old_pos + 1} 順位 (Phase {old_phase or '-'}) "
                    f"調整為第 {new_pos + 1} 順位 (Phase {new_phase or '-'})"
                )
                for col_n in STATION_HEADERS_16:
                    mods.append({
                        "sheet": sheet_name,
                        "row": excel_row,
                        "col_name": col_n,
                        "old": old_phase,
                        "new": new_phase,
                        "highlight": "blue",
                        "show_comment": (r_off == 0 and col_n in ("Phase", "Title")),
                        "note": note_txt,
                    })

    workspace["_modified_cells"] = mods

    # Detect whether original Index started at 000 or 001
    start_idx = 0
    if rows:
        first_idx_s = str(rows[0].get("Index") or "").strip()
        if first_idx_s.isdigit() and int(first_idx_s) == 1:
            start_idx = 1

    for i, r in enumerate(new_rows):
        r["Index"] = f"{i + start_idx:03d}"

    stations[sheet_name] = new_rows

    # Re-extract fresh blocks and check variable dependencies
    refreshed_blocks = extract_station_blocks(new_rows)
    dep_warnings = check_var_dependencies(refreshed_blocks)
    return {
        "blocks": serialize_blocks_for_ui(refreshed_blocks),
        "dep_warnings": dep_warnings,
    }


def build_taipei_dual_station(workspace, prod_sheet, taipei_sheet=None):
    """
    同一份 Excel 雙地共存：克隆產線站別 (<prod_sheet>) 為無硬體台北除錯站 (<prod_sheet>_TAIPEI)。
    - <taipei_sheet> 不掛載於 Instrument/Switch.Mount，因此 Centimani 開機不載入儀器 DLL。
    - 將需實體連線/儀器/量測與 CheckLimit 步驟設為 ExecMode='6' (Skip) 並清空該列 Instrument/Switch；
      :Sf* 指令依規則保留 ExecMode='9' 且清空 Validation。
    - 原產線分頁 <prod_sheet> 維持 100% 完整產線流程與硬體掛載不變。
    """
    stations = workspace.setdefault("stations", {})
    if prod_sheet not in stations:
        raise ValueError(f"找不到產線測試站工作表：{prod_sheet}")

    base_name = prod_sheet[:24] if len(prod_sheet) > 24 else prod_sheet
    t_sheet = (taipei_sheet or f"{base_name}_TAIPEI")[:31]
    copied_rows = [copy.deepcopy(r) for r in stations[prod_sheet]]

    hw_prefixes = (
        ":Connect", ":Disconnect", ":ObtainDevice", ":ReleaseDevice",
        ":ObtainSubDevice", ":ReleaseSubDevice", ":Dev.", ":sDev.",
        ":Utility.Ping", ":FindIP", ":CheckLimit"
    )
    mods = [m for m in workspace.get("_modified_cells", []) if m.get("sheet") != t_sheet]
    for idx, st in enumerate(copied_rows):
        s_send = str(st.get("Send", "")).strip()
        s_inst = str(st.get("Instrument", "")).strip()
        s_sw = str(st.get("Switch", "")).strip()
        old_exec = str(st.get("ExecMode", "")).strip()

        if s_send.startswith(":Sf"):
            if old_exec not in ("8", "9"):
                st["ExecMode"] = "9"
            if str(st.get("Validation", "")).strip():
                st["Validation"] = ""
            continue

        is_hw_or_meas = (
            s_inst != "" or
            s_sw != "" or
            s_send.startswith(hw_prefixes) or
            bool(str(st.get("Validation", "")).strip()) or
            ("@" in s_send and not s_send.startswith(":"))
        )
        if is_hw_or_meas:
            st["ExecMode"] = "6"
            st["Instrument"] = ""
            st["Switch"] = ""
            mods.append({
                "sheet": t_sheet,
                "row": idx + 2,
                "col_name": "ExecMode",
                "old": old_exec,
                "new": "6",
                "highlight": "blue",
                "show_comment": True,
                "note": "【台北無硬體除錯分頁】硬體/連線/量測步驟已自動設為 ExecMode=6 (Skip) 且不掛載 DLL。",
            })

    stations[t_sheet] = copied_rows
    workspace["_modified_cells"] = mods
    return t_sheet


def write_env_switch_bats(target_dir, prod_sheet, taipei_sheet, xlsx_filename=""):
    """
    在匯出目錄產生 Windows CRLF 雙地一鍵切換批次檔：
    - 切換_台北座位除錯模式.bat (切換為 <taipei_sheet> 無硬體單槽除錯)
    - 切換_工廠產線正式模式.bat (切換回 <prod_sheet> 產線完整測試)
    """
    os.makedirs(target_dir, exist_ok=True)
    files_written = []

    def _ps_ini_block(station_target, load234_val):
        return (
            "powershell -NoProfile -Command ^\r\n"
            "  \"$sys = 'System.ini'; if (Test-Path $sys) { "
            "$c = Get-Content $sys -Raw; "
            f"$c = $c -replace '(?mi)^(StationName|Station)\\s*=.*$', ('$1=' + '{station_target}'); "
            "Set-Content $sys -Value $c -NoNewline }; "
            "$glb = 'Global.ini'; if (Test-Path $glb) { "
            "$g = Get-Content $glb -Raw; "
            "$g = $g -replace '(?mi)^LOAD_1\\s*=.*$', 'LOAD_1=true'; "
            f"$g = $g -replace '(?mi)^(LOAD_[234])\\s*=.*$', ('$1={load234_val}'); "
            "Set-Content $glb -Value $g -NoNewline }\"\r\n"
        )

    tp_bat = os.path.join(target_dir, "切換_台北座位除錯模式.bat")
    tp_content = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        f"title Centimani 環境切換 - 台北無硬體座位除錯 ({taipei_sheet})\r\n"
        "cd /d \"%~dp0\"\r\n"
        "echo ============================================================\r\n"
        f"echo  切換至【台北座位除錯模式】站別：{taipei_sheet}\r\n"
        f"echo  對應腳本：{xlsx_filename}\r\n"
        "echo  說明：僅啟用 LOAD_1、略過儀器 DLL 與治具量測 (ExecMode=6)\r\n"
        "echo ============================================================\r\n"
        + _ps_ini_block(taipei_sheet, "false")
        + "echo.\r\n"
        f"echo [完成] 已設定預設站別為 {taipei_sheet}（若使用 Centimani 主程式，請確認站別下拉選 {taipei_sheet} 與 SFIS OFF）。\r\n"
        "pause\r\n"
    )
    with open(tp_bat, "w", encoding="utf-8", newline="") as f:
        f.write(tp_content)
    files_written.append(tp_bat)

    prod_bat = os.path.join(target_dir, "切換_工廠產線正式模式.bat")
    prod_content = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        f"title Centimani 環境切換 - 工廠產線正式模式 ({prod_sheet})\r\n"
        "cd /d \"%~dp0\"\r\n"
        "echo ============================================================\r\n"
        f"echo  切換回【工廠產線正式模式】站別：{prod_sheet}\r\n"
        f"echo  對應腳本：{xlsx_filename}\r\n"
        "echo  說明：還原產線測試站與硬體儀器完整掛載\r\n"
        "echo ============================================================\r\n"
        + _ps_ini_block(prod_sheet, "true")
        + "echo.\r\n"
        f"echo [完成] 已還原產線正式站別 {prod_sheet}（上機前請確認實體儀器與 SFIS 連線正常）。\r\n"
        "pause\r\n"
    )
    with open(prod_bat, "w", encoding="utf-8", newline="") as f:
        f.write(prod_content)
    files_written.append(prod_bat)

    return files_written


def _normalize_title_label(raw_title):
    s = str(raw_title or "").strip()
    parts = [p.strip() for p in s.split(",")]
    if len(parts) >= 2:
        return parts[1]
    return s


def diff_station_sheets(workspace, sheet_a, sheet_b):
    """
    同檔雙分頁差異比對（例如比對 MB 與 MB_TAIPEI），確保在台北除錯修改邏輯後，
    能立即找出漏同步回產線分頁的區塊與測項步驟差異。
    """
    stations = workspace.get("stations") or {}
    if sheet_a not in stations or sheet_b not in stations:
        raise ValueError(f"找不到欲比對的測試站分頁：{sheet_a} 或 {sheet_b}")

    blocks_a = extract_station_blocks(stations[sheet_a])
    blocks_b = extract_station_blocks(stations[sheet_b])

    map_a = {}
    order_a = []
    for idx, b in enumerate(blocks_a):
        key = _normalize_title_label(b.get("title") or b.get("title_raw")) or f"BLOCK_{idx+1}"
        if key in map_a:
            key = f"{key}#{idx+1}"
        map_a[key] = b
        order_a.append(key)

    map_b = {}
    order_b = []
    for idx, b in enumerate(blocks_b):
        key = _normalize_title_label(b.get("title") or b.get("title_raw")) or f"BLOCK_{idx+1}"
        if key in map_b:
            key = f"{key}#{idx+1}"
        map_b[key] = b
        order_b.append(key)

    only_in_a = []
    only_in_b = []
    block_diffs = []

    for k in order_a:
        if k not in map_b:
            ba = map_a[k]
            only_in_a.append({
                "title": k,
                "phase": ba.get("phase", ""),
                "step_count": ba.get("step_count", 0),
                "start_row": ba.get("start_row", 0),
            })

    for k in order_b:
        if k not in map_a:
            bb = map_b[k]
            only_in_b.append({
                "title": k,
                "phase": bb.get("phase", ""),
                "step_count": bb.get("step_count", 0),
                "start_row": bb.get("start_row", 0),
            })

    for k in order_a:
        if k not in map_b:
            continue
        ba = map_a[k]
        bb = map_b[k]
        rows_a = ba.get("_rows", [])
        rows_b = bb.get("_rows", [])
        step_changes = []
        max_len = max(len(rows_a), len(rows_b))
        for si in range(max_len):
            ra = rows_a[si] if si < len(rows_a) else {}
            rb = rows_b[si] if si < len(rows_b) else {}
            diffs_in_row = []
            for col in ("Phase", "Send", "Ref", "Validation", "ExecMode", "Waiting", "Description"):
                va = str(ra.get(col, "") or "").strip()
                vb = str(rb.get(col, "") or "").strip()
                if va != vb:
                    diffs_in_row.append({"col": col, "val_a": va, "val_b": vb})
            if diffs_in_row:
                step_changes.append({
                    "step_offset": si + 1,
                    "send_a": str(ra.get("Send", "") or ""),
                    "send_b": str(rb.get("Send", "") or ""),
                    "fields": diffs_in_row,
                })
        if step_changes or str(ba.get("phase", "")) != str(bb.get("phase", "")):
            block_diffs.append({
                "title": k,
                "phase_a": ba.get("phase", ""),
                "phase_b": bb.get("phase", ""),
                "step_count_a": len(rows_a),
                "step_count_b": len(rows_b),
                "step_changes": step_changes,
            })

    summary = (
        f"比對 {sheet_a} ({len(blocks_a)} 區塊) vs {sheet_b} ({len(blocks_b)} 區塊)："
        f"僅 {sheet_a} 有 {len(only_in_a)} 塊、僅 {sheet_b} 有 {len(only_in_b)} 塊、步驟內容有差異 {len(block_diffs)} 塊"
    )
    return {
        "sheet_a": sheet_a,
        "sheet_b": sheet_b,
        "only_in_a": only_in_a,
        "only_in_b": only_in_b,
        "block_diffs": block_diffs,
        "summary": summary,
    }
