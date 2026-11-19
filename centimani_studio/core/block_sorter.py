import re


def _parse_phase_int(val):
    s = str(val or "").strip()
    if not s:
        return None
    try:
        return int(float(s))
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
    Group a station's rows into contiguous Title/Phase blocks.
    A new block starts whenever a row has a non-empty Title or non-empty Phase
    (or at row 0).
    """
    if not rows:
        return []

    raw_blocks = []
    cur = None
    for idx, row in enumerate(rows):
        phase_str = str(row.get("Phase") or "").strip()
        title_str = str(row.get("Title") or "").strip()
        is_header = (idx == 0) or bool(title_str) or bool(phase_str)
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
        is_teardown = (pnum is not None and pnum >= 97)
        out_of_order = False
        order_reason = ""
        if pnum is not None:
            if seen_teardown and not is_teardown:
                out_of_order = True
                order_reason = f"Phase {pnum} 位於收尾區 Phase 97 之後"
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
            "is_out_of_order": out_of_order,
            "order_reason": order_reason,
            "produced_vars": sorted(produced),
            "used_vars": sorted(used),
            "_rows": b["rows"],
        })
    return result


def serialize_blocks_for_ui(blocks):
    return [{k: v for k, v in b.items() if k != "_rows"} for b in blocks]


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


def reorder_station_blocks(workspace, sheet_name, new_order_indices, auto_renumber_phase=True):
    """
    Reorder a station's Title/Phase blocks according to new_order_indices,
    re-index the Index column, optionally re-number non-teardown numeric Phases,
    and run variable dependency checks.
    """
    stations = workspace.get("stations") or {}
    if sheet_name not in stations:
        raise ValueError(f"找不到工作表：{sheet_name}")

    rows = stations[sheet_name]
    blocks = extract_station_blocks(rows)
    if len(new_order_indices) != len(blocks) or sorted(new_order_indices) != list(range(len(blocks))):
        raise ValueError("區塊排序索引不完整或重複")

    ordered_blocks = [blocks[i] for i in new_order_indices]

    # Determine starting phase number if auto-renumbering
    if auto_renumber_phase:
        normal_nums = [b["phase_num"] for b in blocks if b["phase_num"] is not None and not b["is_teardown"]]
        next_phase = min(normal_nums) if normal_nums else 1
        if next_phase > 1:
            next_phase = 1
        for b in ordered_blocks:
            if b["phase_num"] is not None and not b["is_teardown"]:
                b["_rows"][0]["Phase"] = str(next_phase)
                b["phase"] = str(next_phase)
                b["phase_num"] = next_phase
                next_phase += 1

    # Rebuild flattened rows and re-index 000, 001, ... (preserving 3-digit padding)
    new_rows = []
    for b in ordered_blocks:
        for r in b["_rows"]:
            new_rows.append(r)

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
