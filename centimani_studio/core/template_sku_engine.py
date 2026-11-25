# -*- coding: utf-8 -*-
"""
Centimani Studio - Template Block Dependency Bundler & Guided SKU Wizard Engine
Supports:
1. Discovering mature production templates under SCRIPTS/perter_SCRIPT_11102026 (and custom .xlsx).
2. Inspecting Title/Phase blocks together with all 5 hidden dependencies:
   Marco sheets, Instrument / Sub=1 / Switch bindings, DUTs Connections & {N} Parameters,
   Global.ini [Settings]/[Scripts] & companion .txt/.ini files, and cross-step $Var producer edges.
3. Generating Centimani-compliant SFIS SKU Lookup, Multi-SKU Branching (BRANCH_RULES / EXTERNAL_TXT /
   DUT_COMPARE), and Hardware-Derivative Section Guards (4:1,<end>) for 2..N SKUs with 0 Doctor errors.
4. Safely merging transplanted blocks & SKU logic into EITHER an existing workspace (1 -> N) OR
   a brand-new 0 -> 1 standalone workspace through one shared engine.
"""
import copy
import os
import re
import glob

from .excel_engine import import_excel_to_workspace, list_excel_sheet_names
from .block_sorter import _extract_produced_vars, _extract_used_vars

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

DEFAULT_CONN_TEMPLATES = {
    "UART": '"Uart","UART","*$(DUT_UR1),115200,8,One,None,None,10000,5000"',
    "LinuxUART": '"Uart","LinuxUART","*$(DUT_UR1),115200,8,One,None,None,10000,5000"',
    "LUART": '"Uart","LUART","*$(FIXUART_1),9600,8,One,None,None,10000,5000"',
    "IcatchUART": '"Uart","IcatchUART","*$(DUT_UR2),115200,8,One,None,None,10000,5000"',
    "UARTF": '"Uart","UARTF","*$(PCUART_fixture_1),9600,8,One,None,None,10000,5000"',
    "CmdConsole": '"APP","CmdConsole","C:\\Windows\\System32\\cmd.exe,0,5000,"',
    "STCmd": '"APP","STCmd","*$(FlashTool),0,10000,"',
}


def _parse_int_phase(val):
    s = str(val or "").strip()
    if not s:
        return None
    s_head = s.split(":")[0].strip()
    try:
        return int(float(s_head))
    except Exception:
        return None


def _shift_jump_execmode(exec_mode, delta):
    """Shifts Title-local 0-based jump offsets (2:S and 4:P,F) by delta."""
    s = str(exec_mode or "").strip()
    if not delta:
        return s
    if s.startswith("4:") and "," in s:
        parts = s[2:].split(",", 1)
        try:
            p_st = int(parts[0].strip()) + delta
            f_st = int(parts[1].strip()) + delta
            return f"4:{p_st},{f_st}"
        except ValueError:
            return s
    if s.startswith("2:"):
        try:
            target = int(s[2:].strip()) + delta
            return f"2:{target}"
        except ValueError:
            return s
    return s


def _sanitize_var_name(name, default="sfSKUCode"):
    cleaned = re.sub(r"[^A-Za-z0-9_]", "", str(name or "").strip().lstrip("$"))
    return cleaned or default


def _split_station_into_title_blocks(st_name, steps):
    """
    Splits a Station's step list into Centimani Title blocks (the exact scope of 4:P,F and 2:S jumps).
    Tracks last explicit numeric/string Phase across Title blocks inside the same Phase.
    """
    blocks = []
    curr = None
    last_phase = "0"
    for idx, step in enumerate(steps or []):
        s_phase = str(step.get("Phase") or "").strip()
        s_title = str(step.get("Title") or "").strip()
        if s_phase:
            last_phase = s_phase
        is_start = (idx == 0) or bool(s_title) or (bool(s_phase) and curr is not None)
        if is_start:
            eff_phase = s_phase or last_phase
            if not s_title and curr is not None and not s_phase:
                curr["steps"].append(copy.deepcopy(step))
                continue
            title_clean = s_title.split(",", 1)[1].strip() if "," in s_title else (s_title or f"Phase {eff_phase}")
            curr = {
                "block_idx": len(blocks),
                "block_key": f"{st_name}::{len(blocks)}",
                "station": st_name,
                "phase": s_phase,
                "effective_phase": eff_phase,
                "effective_phase_num": _parse_int_phase(eff_phase),
                "title": s_title,
                "title_label": title_clean,
                "steps": [],
            }
            blocks.append(curr)
        if curr is not None:
            curr["steps"].append(copy.deepcopy(step))
    return blocks


def list_perter_templates(search_root=None):
    """
    Scans SCRIPTS/perter_SCRIPT_11102026 (or custom root) and returns primary production templates
    grouped by station folder so the shared wizard can offer one-click selection.
    """
    root_dir = search_root or os.path.join(PROJECT_ROOT, "SCRIPTS", "perter_SCRIPT_11102026")
    if not os.path.exists(root_dir):
        return {"root": root_dir, "exists": False, "templates": []}

    templates = []
    for cur_root, _dirs, files in os.walk(root_dir):
        rel_dir = os.path.relpath(cur_root, root_dir)
        top_folder = rel_dir.split(os.sep)[0] if rel_dir != "." else "ROOT"
        lower_rel = rel_dir.lower()
        is_secondary_dir = any(tag in lower_rel for tag in ("grr", "current", "mp3", "centimani_olympus_testflow"))
        txt_files = sorted([f for f in files if f.lower().endswith(".txt") and not f.startswith("~$")])
        has_global = any(f.lower() == "global.ini" for f in files)
        has_system = any(f.lower() == "system.ini" for f in files)

        for fname in sorted(files):
            low = fname.lower()
            if not low.endswith(".xlsx") or fname.startswith("~$") or "test item code" in low:
                continue
            full_path = os.path.join(cur_root, fname)
            is_backup = low.startswith("old_") or is_secondary_dir
            try:
                sheets = list_excel_sheet_names(full_path)
            except Exception:
                sheets = []
            station_sheets = [
                s for s in sheets
                if s.lower() not in ("properties", "duts", "switch", "instrument", "pathloss")
            ]
            templates.append({
                "id": os.path.relpath(full_path, root_dir).replace("\\", "/"),
                "station_folder": top_folder,
                "rel_folder": rel_dir.replace("\\", "/"),
                "name": fname,
                "path": full_path,
                "size_kb": round(os.path.getsize(full_path) / 1024.0, 1),
                "sheets": sheets,
                "station_sheets": station_sheets,
                "has_global_ini": has_global,
                "has_system_ini": has_system,
                "companion_txt_files": txt_files,
                "is_primary": not is_backup,
            })

    templates.sort(key=lambda t: (0 if t["is_primary"] else 1, t["station_folder"], t["rel_folder"], t["name"]))
    return {"root": root_dir, "exists": True, "templates": templates}


def _scan_text_companion_refs(steps):
    refs = []
    for st in steps:
        send = str(st.get("Send") or "")
        m = re.search(r':Utility\.R(?:txt|ini)\s*,\s*"([^"]+)"', send, re.IGNORECASE)
        if m:
            raw_p = m.group(1).strip()
            refs.append(os.path.basename(raw_p.replace("\\", "/")))
    return list(dict.fromkeys(refs))


def _scan_step_connections(steps):
    conns = []
    for st in steps:
        send = str(st.get("Send") or "")
        if "@" in send and not send.lstrip().startswith(":"):
            alias = send.split("@", 1)[0].strip()
            if alias and re.match(r"^[A-Za-z0-9_\-]+$", alias):
                conns.append(alias)
        for m in re.finditer(r':(?:Connect|Disconnect|AddAttribute)\s*,\s*"([^"]+)"', send, re.IGNORECASE):
            conns.append(m.group(1).strip())
    return list(dict.fromkeys(conns))


def _scan_param_indices(steps):
    idxs = set()
    for st in steps:
        for col in ("Send", "Reply", "Validation", "Switch"):
            val = str(st.get(col) or "")
            for m in re.finditer(r"\{(\d+)\}", val):
                idxs.add(int(m.group(1)))
    return sorted(idxs)


def _scan_ini_vars(rows_iterable):
    out = set()
    for row in rows_iterable:
        text = " ".join(str(v) for v in row.values() if v is not None)
        for m in re.finditer(r"\*\$\(([^)]+)\)", text):
            out.add(m.group(1).strip())
    return sorted(out)


def _scan_sfis_calls(steps):
    calls = []
    for st in steps:
        send = str(st.get("Send") or "").strip()
        if not send.lower().startswith(":sf"):
            continue
        cmd = send.split(",", 1)[0].strip()
        parts = [p.strip().strip('"') for p in send.split(",")]
        calls.append({
            "cmd": cmd,
            "table": parts[2] if len(parts) > 2 else "",
            "field": parts[4] if len(parts) > 4 else "",
            "ref": str(st.get("Ref") or "").strip(),
            "exec_mode": str(st.get("ExecMode") or "").strip(),
        })
    return calls


def _read_companion_file(xlsx_dir, fname):
    for cand in (
        os.path.join(xlsx_dir, fname),
        os.path.join(xlsx_dir, "System", fname),
    ):
        if os.path.exists(cand) and os.path.isfile(cand):
            try:
                content = open(cand, "r", encoding="utf-8", errors="ignore").read()
                return {"filename": fname, "source_path": cand, "content": content[:8000]}
            except Exception:
                pass
    return None


def inspect_template_bundle(xlsx_path, sheet_name=None):
    """
    Parses a source template Excel + sibling Global.ini + companion .txt/.ini files and returns
    every selectable block alongside its full 5-layer dependency graph for UI & transplant.
    """
    if not xlsx_path or not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"找不到來源範本 Excel：{xlsx_path}")

    ws = import_excel_to_workspace(xlsx_path)
    xlsx_dir = os.path.dirname(os.path.abspath(xlsx_path))
    g_settings = ws.get("global_ini", {}).get("Settings", {})
    g_scripts = ws.get("global_ini", {}).get("Scripts", {})
    marcos_map = ws.get("marcos", {})
    inst_rows = ws.get("instruments", [])
    sw_rows = ws.get("switches", [])
    dut_rows = ws.get("duts", [])

    # Map instrument Name (lowercase) -> row, and Function (uppercase) -> list of matching inst rows
    inst_by_name = {str(r.get("Name") or "").strip().lower(): r for r in inst_rows if str(r.get("Name") or "").strip()}
    inst_by_func = {}
    for r in inst_rows:
        for fn in str(r.get("Functions") or "").split(","):
            fn_up = fn.strip().upper()
            if fn_up:
                inst_by_func.setdefault(fn_up, []).append(r)
    sw_by_name = {str(r.get("Name") or "").strip().lower(): r for r in sw_rows if str(r.get("Name") or "").strip()}

    # Build source DUT connection alias -> connect string lookup from slot 1
    src_conn_map = {}
    if dut_rows:
        for col, val in dut_rows[0].items():
            if col.startswith("Connection") and val:
                parts = [p.strip().strip('"') for p in str(val).split(",")]
                if len(parts) >= 2 and parts[1]:
                    src_conn_map[parts[1]] = str(val)

    station_names = list(ws.get("stations", {}).keys())
    target_stations = [sheet_name] if (sheet_name and sheet_name in ws.get("stations", {})) else station_names

    stations_out = {}
    all_companion_files = {}
    sku_hints = {
        "has_custitem": False,
        "has_iteminfo_mo": False,
        "has_custinfo": False,
        "has_country_code": False,
        "has_set_model_name": False,
        "txt_files": [],
    }

    for st_name in target_stations:
        raw_blocks = _split_station_into_title_blocks(st_name, ws["stations"].get(st_name, []))
        # Track producer -> block_key inside this station for upstream dependency hints
        var_producers = {}
        blk_list = []

        for blk in raw_blocks:
            steps = blk["steps"]
            used_marcos = []
            for s in steps:
                mn = str(s.get("Marco") or "").strip()
                if mn and mn not in used_marcos:
                    used_marcos.append(mn)

            all_related_steps = list(steps)
            for mn in used_marcos:
                all_related_steps.extend(marcos_map.get(mn, []))

            # 1. Resolve instruments & Sub=1 devices
            matched_insts = []
            seen_inst_names = set()
            for s in all_related_steps:
                fn = str(s.get("Instrument") or "").strip()
                sw = str(s.get("Switch") or "").strip().split(",")[0].strip()
                send = str(s.get("Send") or "").strip()
                if sw and sw.lower() in inst_by_name:
                    ir = inst_by_name[sw.lower()]
                    nm = str(ir.get("Name") or "").strip()
                    if nm and nm not in seen_inst_names:
                        seen_inst_names.add(nm)
                        matched_insts.append({
                            "name": nm,
                            "func": fn or ir.get("Functions", ""),
                            "sub": str(ir.get("Sub") or ""),
                            "dll": str(ir.get("ControlDLL") or ""),
                            "settings": str(ir.get("Settings") or ""),
                        })
                elif fn and fn.upper() in inst_by_func:
                    ir = inst_by_func[fn.upper()][0]
                    nm = str(ir.get("Name") or "").strip()
                    if nm and nm not in seen_inst_names:
                        seen_inst_names.add(nm)
                        matched_insts.append({
                            "name": nm,
                            "func": fn,
                            "sub": str(ir.get("Sub") or ""),
                            "dll": str(ir.get("ControlDLL") or ""),
                            "settings": str(ir.get("Settings") or ""),
                        })
                m_sub = re.match(r'^:ObtainSubDevice\s*,\s*"([^"]+)"', send, re.IGNORECASE)
                if m_sub:
                    snm = m_sub.group(1).strip()
                    ir = inst_by_name.get(snm.lower())
                    nm = str(ir.get("Name") if ir else snm).strip()
                    if nm and nm not in seen_inst_names:
                        seen_inst_names.add(nm)
                        matched_insts.append({
                            "name": nm,
                            "func": ir.get("Functions", "") if ir else "SubDevice",
                            "sub": "1",
                            "dll": str(ir.get("ControlDLL") or "") if ir else "",
                            "settings": str(ir.get("Settings") or "") if ir else "",
                        })

            # 2. Switches
            matched_switches = []
            for s in all_related_steps:
                sw = str(s.get("Switch") or "").strip().split(",")[0].strip()
                if sw and sw.lower() in sw_by_name and sw not in matched_switches:
                    matched_switches.append(sw)

            # 3. Connections & Parameter {N}
            conns = _scan_step_connections(all_related_steps)
            conn_details = {c: src_conn_map.get(c, DEFAULT_CONN_TEMPLATES.get(c, "")) for c in conns}
            param_slots = _scan_param_indices(all_related_steps)

            # 4. *$(VAR) separated into Settings vs Scripts
            inst_rows_for_vars = [inst_by_name[i["name"].lower()] for i in matched_insts if i["name"].lower() in inst_by_name]
            dut_rows_for_vars = [{"c": v} for v in conn_details.values() if v]
            setting_vars = {}
            for vn in _scan_ini_vars(inst_rows_for_vars + dut_rows_for_vars):
                setting_vars[vn] = str(g_settings.get(vn, g_scripts.get(vn, "1")))
            script_vars = {}
            for vn in _scan_ini_vars(all_related_steps):
                if vn in g_settings and vn not in g_scripts:
                    setting_vars[vn] = str(g_settings[vn])
                else:
                    script_vars[vn] = str(g_scripts.get(vn, ""))

            # 5. Companion .txt / .ini files
            comp_refs = _scan_text_companion_refs(all_related_steps)
            for cf in comp_refs:
                if cf not in all_companion_files:
                    meta = _read_companion_file(xlsx_dir, cf)
                    if meta:
                        all_companion_files[cf] = meta
                        if cf.lower().endswith(".txt") and cf not in sku_hints["txt_files"]:
                            sku_hints["txt_files"].append(cf)

            # 6. SFIS & SKU hints
            sfis_calls = _scan_sfis_calls(all_related_steps)
            for sc in sfis_calls:
                tbl = sc["table"].upper()
                if "CUSTITEM" in tbl:
                    sku_hints["has_custitem"] = True
                elif "ITEMINFO" in tbl:
                    sku_hints["has_iteminfo_mo"] = True
                elif "CUSTINFO" in tbl or "CUSTINFO" in sc["field"].upper():
                    sku_hints["has_custinfo"] = True
                if sc["field"].upper() == "SNE" or "country" in str(sc["ref"]).lower():
                    sku_hints["has_country_code"] = True
            for s in all_related_steps:
                snd = str(s.get("Send") or "")
                if snd.lower().startswith(":setmodelname"):
                    sku_hints["has_set_model_name"] = True

            # 7. Producer / Consumer $Var linkage
            prod = set()
            used = set()
            for r in steps:
                r_p = _extract_produced_vars(r)
                r_u = _extract_used_vars(r)
                used |= (r_u - prod)
                prod |= r_p
            upstream = []
            for u_var in sorted(used):
                pk = var_producers.get(u_var)
                if pk and pk not in upstream:
                    upstream.append(pk)
            for p_var in prod:
                var_producers[p_var] = blk["block_key"]

            p_num = blk["effective_phase_num"]
            blk_list.append({
                "block_key": blk["block_key"],
                "block_idx": blk["block_idx"],
                "station": st_name,
                "phase": blk["phase"],
                "effective_phase": blk["effective_phase"],
                "effective_phase_num": p_num,
                "title": blk["title"],
                "title_label": blk["title_label"],
                "step_count": len(steps),
                "is_teardown": (p_num is not None and p_num >= 95),
                "is_paused": (p_num == -1),
                "marcos": used_marcos,
                "instruments": matched_insts,
                "switches": matched_switches,
                "connections": conn_details,
                "param_slots": param_slots,
                "ini_vars": {"Settings": setting_vars, "Scripts": script_vars},
                "companion_files": comp_refs,
                "sfis_calls": sfis_calls,
                "produced_vars": sorted(prod),
                "used_vars": sorted(used),
                "upstream_block_keys": upstream,
                "preview_steps": [
                    {
                        "Send": str(s.get("Send") or ""),
                        "Reply": str(s.get("Reply") or ""),
                        "Ref": str(s.get("Ref") or ""),
                        "ExecMode": str(s.get("ExecMode") or ""),
                        "Description": str(s.get("Description") or ""),
                    }
                    for s in steps[:5]
                ],
            })
        stations_out[st_name] = blk_list

    return {
        "source_path": os.path.abspath(xlsx_path),
        "file_name": os.path.basename(xlsx_path),
        "project_name": ws.get("project_name", ""),
        "station_names": station_names,
        "stations": stations_out,
        "companion_files": all_companion_files,
        "global_ini": {"Settings": g_settings, "Scripts": g_scripts},
        "sku_hints": sku_hints,
    }


def _make_step(phase="", title="", marco="", instrument="", switch="", send="",
               reply="", end_prompt="", ref="", validation="", prompt="",
               waiting="", exec_mode="0", description="", test_id="B7PL025"):
    return {
        "Index": "",
        "Phase": str(phase) if phase is not None else "",
        "Title": str(title or ""),
        "Marco": str(marco or ""),
        "Instrument": str(instrument or ""),
        "Switch": str(switch or ""),
        "Send": str(send or ""),
        "Reply": str(reply) if reply is not None else "",
        "EndPrompt": str(end_prompt or ""),
        "Ref": str(ref or ""),
        "Validation": str(validation or ""),
        "Prompt": str(prompt or ""),
        "Waiting": str(waiting or ""),
        "ExecMode": str(exec_mode) if exec_mode is not None else "0",
        "Description": str(description or ""),
        "TestID": str(test_id or "B7PL025"),
    }


def _build_sfis_fetch_send(source_mode, isn_var, cust_field):
    mode = str(source_mode or "CUSTITEM").strip().upper()
    isn = str(isn_var or "*(ISN)").strip() or "*(ISN)"
    cf = str(cust_field or "").strip()
    if mode == "CUSTITEM":
        return f':SfGetVersion,"{isn}","CUSTITEM","2","",""'
    if mode == "ISN_ITEMINFO":
        return f':SfGetVersion,"{isn}","ISN_ITEMINFO","2","",""'
    if mode == "ITEM_CUSTINFO_N":
        fld = cf or "CUSTINFO06"
        return f':SfGetVersion,"{isn}","ITEM_CUSTINFO_N","2","{fld}",""'
    if mode == "ISN_BASEINFO":
        fld = cf or "SNE"
        return f':SfGetVersion,"{isn}","ISN_BASEINFO","2","{fld}",""'
    return f':SfGetVersion,"{isn}","{mode}","2","{cf}",""'


def _safe_within_string_ref(var_name, prefix_kw):
    """Builds Centimani-compatible Ref extraction without :Trim (which older Centimani builds reject)."""
    v = _sanitize_var_name(var_name, "gDUTVal")
    pk = str(prefix_kw or "").strip()
    if pk:
        # Escape colon if present as in Centimani FWDL/LOCK templates
        pk_esc = pk.replace(":", "\\:") if "\\:" not in pk else pk
        return f'${v}:rpString," ","":WithinString,"{pk_esc}","\\n",""'
    return f"${v}"


def build_sku_wizard_steps(sku_spec, start_phase=1):
    """
    Generates Centimani-compliant SFIS SKU Lookup, Multi-SKU Routing (BRANCH_RULES / EXTERNAL_TXT /
    DUT_COMPARE), companion .txt files, and Global.ini [Scripts] variables from the 5 guided questions.
    Guarantees 0 Script Doctor warnings/errors by explicitly closing every 4:P,F PASS tail.
    """
    cfg = sku_spec if isinstance(sku_spec, dict) else {}
    if not cfg.get("enabled"):
        return {"steps": [], "companion_files": {}, "global_scripts": {}, "summary": []}

    source_mode = str(cfg.get("source_mode") or "CUSTITEM").strip().upper()
    isn_var = str(cfg.get("isn_var") or "*(ISN)").strip() or "*(ISN)"
    cust_field = str(cfg.get("cust_field") or "CUSTINFO06").strip()
    default_var_map = {
        "CUSTITEM": "sfSKUCode",
        "ISN_ITEMINFO": "sf69MO",
        "ITEM_CUSTINFO_N": "sfCustData",
        "ISN_BASEINFO": "sfCC",
        "MANUAL_ONLY": "sfSKUCode",
    }
    res_var = _sanitize_var_name(cfg.get("result_var") or default_var_map.get(source_mode, "sfSKUCode"))
    compare_mode = str(cfg.get("compare_mode") or "BRANCH_RULES").strip().upper()
    offline_wrap = bool(cfg.get("offline_wrap", True)) and source_mode != "MANUAL_ONLY"
    offline_default = str(cfg.get("offline_default_sku") or "FULL").strip() or "FULL"
    no_match_policy = str(cfg.get("no_match_policy") or "FAIL").strip().upper()
    toggle_var = re.sub(r"[^A-Za-z0-9_]", "", str(cfg.get("toggle_var") or "").strip())
    dut_conn = str(cfg.get("dut_conn") or "UART").strip() or "UART"
    end_prompt = str(cfg.get("end_prompt") or "/#").strip()

    raw_branches = [b for b in (cfg.get("sku_branches") or []) if isinstance(b, dict) and str(b.get("code") or "").strip()]
    if not raw_branches and compare_mode == "BRANCH_RULES":
        raw_branches = [{"code": offline_default, "label": "Default SKU"}]

    global_scripts = {}
    companion_files = {}
    summary = []

    if toggle_var:
        title_prefix = f"*$({toggle_var})"
        global_scripts[toggle_var] = "0"
    else:
        title_prefix = "0"

    default_ini_key = "SFIS_SKU_DEFAULT"
    if offline_wrap or source_mode == "MANUAL_ONLY":
        global_scripts[default_ini_key] = offline_default

    title_name = str(cfg.get("title_name") or "SFIS SKU Dynamic Routing").strip()
    title_str = f"{title_prefix},{title_name}"

    steps = []
    # Step 0..N loader for EXTERNAL_TXT
    txt_var = ""
    if compare_mode == "EXTERNAL_TXT":
        txt_fname = os.path.basename(str(cfg.get("txt_filename") or "69MO.txt").strip() or "69MO.txt")
        if not txt_fname.lower().endswith(".txt"):
            txt_fname += ".txt"
        txt_var = _sanitize_var_name(os.path.splitext(txt_fname)[0], "skuList")
        txt_content = str(cfg.get("txt_content") or f"A={offline_default}").strip() + "\n"
        companion_files[txt_fname] = txt_content
        steps.append(_make_step(
            send=f':Utility.Rtxt,".\\System\\{txt_fname}","-1"',
            reply="0",
            ref=f"${txt_var}",
            exec_mode="1",
            description=f"PC#-#Read {txt_fname}",
            test_id="IPPR005",
        ))
        summary.append(f"產生外部名單檔 `.\\System\\{txt_fname}` 並於流程開頭載入至 `$({txt_var})`")

    # Fetch SFIS or Offline Fallback block:
    # - When offline_wrap=True:
    #   [s0] :SfEnabled (Reply=1, EM=4:s1,s3)
    #   [s1] :SfGetVersion -> $res_var (EM=8)
    #   [s2] :Delay,"0" (Reply=0, EM=4:s4,s4)     <-- jumps OVER offline fallback so script_doctor sees 0 fall-through warnings
    #   [s3] :SetVal,"$res_var","*$(SFIS_SKU_DEFAULT)" (Reply=0, EM=0)
    #   [s4] ... downstream compare / branches start here!
    if source_mode == "MANUAL_ONLY":
        steps.append(_make_step(
            send=f':SetVal,"${res_var}","*$({default_ini_key})"',
            reply="0",
            exec_mode="0",
            description=f"PC#-#Set Default SKU ${res_var}",
            test_id="B7PL025",
        ))
        summary.append(f"設定預設 SKU `*$(SFIS_SKU_DEFAULT)={offline_default}` 至 `${res_var}`")
    elif offline_wrap:
        s0 = len(steps)
        s1, s2, s3, s4 = s0 + 1, s0 + 2, s0 + 3, s0 + 4
        steps.append(_make_step(
            send=":SfEnabled",
            reply="1",
            exec_mode=f"4:{s1},{s3}",
            description="PC#-#Check SFIS Enabled",
            test_id="B7PL025",
        ))
        steps.append(_make_step(
            send=_build_sfis_fetch_send(source_mode, isn_var, cust_field),
            ref=f"${res_var}",
            waiting="2000",
            exec_mode="8",
            description=f"PC#-#Get SFIS {source_mode}",
            test_id="OTFX085",
        ))
        steps.append(_make_step(
            send=':Delay,"0"',
            reply="0",
            exec_mode=f"4:{s4},{s4}",
            description="PC#-#Online Fetch Complete Skip Fallback",
            test_id="B7PL025",
        ))
        steps.append(_make_step(
            send=f':SetVal,"${res_var}","*$({default_ini_key})"',
            reply="0",
            exec_mode="0",
            description="PC#-#Offline Fallback Default SKU",
            test_id="B7PL025",
        ))
        summary.append(f"SFIS 查詢 `{source_mode}` → `${res_var}`（自動包 `:SfEnabled` 離線退回 `{offline_default}`）")
    else:
        steps.append(_make_step(
            send=_build_sfis_fetch_send(source_mode, isn_var, cust_field),
            ref=f"${res_var}",
            waiting="2000",
            exec_mode="8",
            description=f"PC#-#Get SFIS {source_mode}",
            test_id="OTFX085",
        ))
        summary.append(f"SFIS 查詢 `{source_mode}` → `${res_var}`")

    # Downstream comparison modes:
    if compare_mode == "DUT_COMPARE":
        dut_cmd = str(cfg.get("dut_query_cmd") or "mfg wifi get-country-code").strip()
        dut_prefix = str(cfg.get("dut_prefix_kw") or "countrycodeis").strip()
        ref_expr = _safe_within_string_ref("gDUT_SKU_Val", dut_prefix)
        steps.append(_make_step(
            send=f"{dut_conn}@{dut_cmd}\\r\\n",
            reply="@PASS" if "wifi" in dut_cmd.lower() else "@",
            end_prompt=end_prompt,
            ref=ref_expr,
            waiting="5000",
            exec_mode="2:0" if len(steps) == 0 else "1",
            description="DUT#-#Read DUT Attribute Value",
            test_id="CACK205",
        ))
        steps.append(_make_step(
            send=f':GetVal,"${res_var}"',
            reply="@*(gDUT_SKU_Val)",
            exec_mode="8" if not offline_wrap else "1",
            description=f"DUT#-#Compare ${res_var} vs DUT",
            test_id="CACK205",
        ))
        summary.append(f"DUT 指令 `{dut_conn}@{dut_cmd}` 取值並比對 `${res_var}`")

    elif compare_mode == "EXTERNAL_TXT":
        # Replicate FWDL R285-R288 / OTA R90-R93 pattern:
        # Match *(txt_var) against @*(res_var): PASS -> Variant A, MISS -> Variant B
        v_a = raw_branches[0] if raw_branches else {"code": "A", "expected_hw": "11"}
        v_b = raw_branches[1] if len(raw_branches) > 1 else {"code": "B", "expected_hw": "10"}
        dut_cmd = str(cfg.get("dut_query_cmd") or "mfg get-hw-version").strip()
        dut_prefix = str(cfg.get("dut_prefix_kw") or "HardwareVersion:").strip()
        chk_idx = len(steps)
        va_idx = chk_idx + 1
        vb_idx = chk_idx + 2
        fail_idx = chk_idx + 3
        done_idx = chk_idx + 4
        hw_a = str(v_a.get("expected_hw") or v_a.get("code") or "11").strip()
        hw_b = str(v_b.get("expected_hw") or v_b.get("code") or "10").strip()
        steps.append(_make_step(
            send=f':GetVal,"*({txt_var})"',
            reply=f"@*({res_var})",
            exec_mode=f"4:{va_idx},{vb_idx}",
            description=f"PC#-#Match {txt_var} List vs ${res_var}",
            test_id="CACK182",
        ))
        for label, hw_val in ((v_a.get("label") or hw_a, hw_a), (v_b.get("label") or hw_b, hw_b)):
            steps.append(_make_step(
                send=f"{dut_conn}@{dut_cmd}\\n",
                reply="@" if not dut_prefix else f"@{dut_prefix.split(':')[0]}",
                end_prompt=end_prompt,
                ref=_safe_within_string_ref("gHW", dut_prefix),
                validation=f"(gHW,%s,{hw_val},);",
                waiting="3000",
                exec_mode=f"4:{done_idx},{fail_idx}",
                description=f"DUT#-#Check Spec ({label}={hw_val})",
                test_id="OVTA033",
            ))
        steps.append(_make_step(
            send=':Delay,"000"',
            reply="1",
            exec_mode="0",
            description="PC#-#Force FAIL on Spec Mismatch",
            test_id="B7PL025",
        ))
        steps.append(_make_step(
            send=':Delay,"100"',
            reply="0",
            exec_mode="0",
            description="PC#-#SKU List Routing Done",
            test_id="B7PL025",
        ))
        summary.append(f"名單 `{txt_var}` 命中→驗證 `{hw_a}` / 未命中→驗證 `{hw_b}`（不符自動強制 FAIL）")

    else:
        # BRANCH_RULES: 2, 3, or N explicit SKUs!
        # Pre-compute each branch's action rows so we know exact start offsets before writing 4:P,F
        branch_specs = []
        dut_cmd = str(cfg.get("dut_query_cmd") or "").strip()
        dut_prefix = str(cfg.get("dut_prefix_kw") or "").strip()
        can_any_action_fail = False

        for br in raw_branches:
            code = str(br.get("code") or "").strip()
            label = str(br.get("label") or code).strip()
            iplas_model = str(br.get("iplas_model") or "").strip()
            dut_write = str(br.get("dut_write_cmd") or "").strip()
            exp_hw = str(br.get("expected_hw") or "").strip()
            for gk, gv in (br.get("globals_override") or {}).items():
                if str(gk).strip():
                    global_scripts[str(gk).strip()] = str(gv)

            act_rows = []
            if iplas_model:
                act_rows.append(_make_step(
                    send=f':SetModelName,"{iplas_model}"',
                    reply="0",
                    exec_mode="0",
                    description=f"PC#-#Set iPLAS Model ({code}->{iplas_model})",
                    test_id="B7PL025",
                ))
            if dut_write:
                act_rows.append(_make_step(
                    send=f"{dut_conn}@{dut_write}\\r\\n",
                    reply="@PASS" if "pass" in dut_write.lower() else "@",
                    end_prompt=end_prompt,
                    waiting="2000",
                    exec_mode="1",
                    description=f"DUT#-#Apply SKU Command ({code})",
                    test_id="OTFX054",
                ))
                can_any_action_fail = True
            if exp_hw:
                q_cmd = dut_cmd or "mfg get-hw-version"
                q_pfx = dut_prefix or "HardwareVersion:"
                act_rows.append(_make_step(
                    send=f"{dut_conn}@{q_cmd}\\n",
                    reply="@",
                    end_prompt=end_prompt,
                    ref=_safe_within_string_ref("gSKUSpec", q_pfx),
                    validation=f"(gSKUSpec,%s,{exp_hw},);",
                    waiting="3000",
                    exec_mode="1",
                    description=f"DUT#-#Verify Spec ({label}={exp_hw})",
                    test_id="OVTA033",
                ))
                can_any_action_fail = True
            if not act_rows:
                # Emit clean marker step so every branch has a valid action slot for 4:P,F
                act_rows.append(_make_step(
                    send=f':SetVal,"$gActiveSKU","{code}"',
                    reply="0",
                    exec_mode="0",
                    description=f"PC#-#Select SKU Profile ({label})",
                    test_id="B7PL025",
                ))
            branch_specs.append({"code": code, "label": label, "act_rows": act_rows})

        base_idx = len(steps)
        cursor = base_idx
        for bs in branch_specs:
            bs["chk_idx"] = cursor
            bs["act_start"] = cursor + 1
            bs["act_end"] = cursor + len(bs["act_rows"])
            cursor = bs["act_end"] + 1

        need_fail_node = (no_match_policy == "FAIL") or can_any_action_fail
        fail_idx = cursor if need_fail_node else None
        done_idx = (cursor + 1) if need_fail_node else cursor

        for idx_b, bs in enumerate(branch_specs):
            next_chk = branch_specs[idx_b + 1]["chk_idx"] if idx_b + 1 < len(branch_specs) else (
                fail_idx if (no_match_policy == "FAIL" and fail_idx is not None) else done_idx
            )
            steps.append(_make_step(
                send=f':GetVal,"${res_var}"',
                reply=f"@{bs['code']}",
                exec_mode=f"4:{bs['act_start']},{next_chk}",
                description=f"PC#-#Check SKU == {bs['code']} ({bs['label']})",
                test_id="CACK182",
            ))
            for a_i, ar in enumerate(bs["act_rows"]):
                if a_i == len(bs["act_rows"]) - 1:
                    f_target = fail_idx if fail_idx is not None else done_idx
                    ar["ExecMode"] = f"4:{done_idx},{f_target}"
                steps.append(ar)

        if need_fail_node:
            steps.append(_make_step(
                send=':Delay,"000"',
                reply="1",
                exec_mode="0",
                description="PC#-#SKU Mismatch or Check Failed",
                test_id="B7PL025",
            ))
        steps.append(_make_step(
            send=':Delay,"100"',
            reply="0",
            exec_mode="0",
            description="PC#-#SKU Routing Complete",
            test_id="B7PL025",
        ))
        summary.append(
            f"建立 {len(branch_specs)} 組 SKU 分支判斷（"
            + " / ".join(b["code"] for b in branch_specs)
            + ("，未匹配強制 FAIL" if no_match_policy == "FAIL" else "，未匹配走預設繼續")
            + "）"
        )

    if steps:
        steps[0]["Phase"] = str(start_phase)
        steps[0]["Title"] = title_str

    return {
        "steps": steps,
        "companion_files": companion_files,
        "global_scripts": global_scripts,
        "result_var": res_var,
        "summary": summary,
    }


def wrap_block_with_sku_guard(block_steps, sku_var="sfSKUCode", allowed_skus=None, section_title=""):
    """
    Prepends a zero-delay Centimani SKU gate (:GetVal,"$sku_var", Reply=@A||@B, ExecMode=4:1,end)
    at step 0 of a Title block and shifts all internal 2:S / 4:P,F offsets by +1,
    cleanly skipping the entire test section for derivative SKUs without failing.
    """
    skus = [str(x).strip() for x in (allowed_skus or []) if str(x).strip()]
    if not block_steps or not skus:
        return copy.deepcopy(block_steps)

    var_clean = _sanitize_var_name(sku_var, "sfSKUCode")
    orig = copy.deepcopy(block_steps)
    orig_phase = orig[0].get("Phase", "")
    orig_title = orig[0].get("Title", "")
    orig[0]["Phase"] = ""
    orig[0]["Title"] = ""

    # Shift any internal Title-local jump offsets inside existing rows by +1
    for st in orig:
        st["ExecMode"] = _shift_jump_execmode(st.get("ExecMode", ""), 1)

    # Ensure safe PASS convergence step at end so 4:1,end exits cleanly
    last_send = str(orig[-1].get("Send") or "").strip().lower()
    last_reply = str(orig[-1].get("Reply") or "").strip()
    if not (last_send.startswith(":delay") and last_reply in ("0", "")):
        orig.append(_make_step(
            send=':Delay,"100"',
            reply="0",
            exec_mode="0",
            description="PC#-#SKU Section Guard Exit",
            test_id="B7PL025",
        ))

    end_idx = len(orig)  # after prepending guard at index 0, last row sits at index len(orig)
    reply_expr = "||".join(f"@{c}" for c in skus)
    lbl = section_title or orig_title or "Section"
    guard_step = _make_step(
        phase=orig_phase,
        title=orig_title,
        send=f':GetVal,"${var_clean}"',
        reply=reply_expr,
        exec_mode=f"4:1,{end_idx}",
        description=f"PC#-#Enable Section [{lbl}] for ({','.join(skus)})",
        test_id="OTFX076",
    )
    return [guard_step] + orig


def _extract_conn_alias_from_str(conn_str):
    parts = [p.strip().strip('"') for p in str(conn_str or "").split(",")]
    return parts[1] if len(parts) >= 2 else ""


def _merge_dut_connections(ws, needed_conns):
    """Appends missing Connection<N> entries onto every DUT slot row cleanly without overwriting."""
    duts = ws.get("duts", [])
    if not duts or not needed_conns:
        return []
    added = []
    for alias, conn_template in needed_conns.items():
        if not alias or not conn_template:
            continue
        # Check if alias already present on slot 0
        existing_aliases = {
            _extract_conn_alias_from_str(v).lower()
            for k, v in duts[0].items()
            if k.startswith("Connection") and v
        }
        if alias.lower() in existing_aliases:
            continue
        # Find first free Connection slot on slot 0
        chosen_col = None
        for idx in range(1, 11):
            c_candidates = [k for k in duts[0].keys() if re.match(rf"^Connection{idx}\b", k)]
            if not c_candidates:
                col_key = f"Connection{idx} (Type,Name,ConnectString)" if idx <= 3 else f"Connection{idx}(Type,Name,ConnectString)"
                chosen_col = col_key
                break
            col_key = c_candidates[0]
            if not str(duts[0].get(col_key) or "").strip():
                chosen_col = col_key
                break
        if not chosen_col:
            continue
        for slot_i, d_row in enumerate(duts):
            val_slot = str(conn_template)
            # Increment slot numbers in *$(VAR_1) -> *$(VAR_<slot>) if needed
            if slot_i > 0:
                val_slot = re.sub(r"\*\$\(([A-Za-z0-9_]+?)_1\)", rf"*$(\1_{slot_i + 1})", val_slot)
            d_row[chosen_col] = val_slot
        added.append(alias)
    return added


def _ensure_dut_parameters(ws, needed_param_slots):
    if not needed_param_slots or not ws.get("duts"):
        return 0
    max_needed = max(needed_param_slots)
    expanded = 0
    for slot_i, d_row in enumerate(ws["duts"]):
        cur = str(d_row.get("Parameter") or "").strip()
        parts = [p.strip() for p in cur.split(",")] if cur else []
        while len(parts) <= max_needed:
            idx_p = len(parts)
            parts.append(str(slot_i + 1) if idx_p == 2 else f"PARAM_{idx_p}")
            expanded += 1
        d_row["Parameter"] = ",".join(parts)
    return expanded


def _rewrite_steps_for_remaps(steps, inst_remap, conn_remap, mark_paused=False):
    out = copy.deepcopy(steps)
    for i, st in enumerate(out):
        if mark_paused and i == 0:
            st["Phase"] = "-1"
        sw = str(st.get("Switch") or "").strip()
        if sw and sw in inst_remap and inst_remap[sw] not in ("", "__PAUSE__"):
            st["Switch"] = inst_remap[sw]
        send = str(st.get("Send") or "")
        for old_inst, new_inst in (inst_remap or {}).items():
            if new_inst and new_inst not in ("__PAUSE__", old_inst):
                send = re.sub(
                    rf'^(:ObtainSubDevice\s*,\s*"){re.escape(old_inst)}"',
                    rf'\1{new_inst}"',
                    send,
                    flags=re.IGNORECASE,
                )
        for old_c, new_c in (conn_remap or {}).items():
            if new_c and new_c != old_c:
                if "@" in send and not send.lstrip().startswith(":"):
                    head, tail = send.split("@", 1)
                    if head.strip() == old_c:
                        send = f"{new_c}@{tail}"
                send = re.sub(
                    rf'^(:(?:Connect|Disconnect|AddAttribute)\s*,\s*"){re.escape(old_c)}"',
                    rf'\1{new_c}"',
                    send,
                    flags=re.IGNORECASE,
                )
        st["Send"] = send
    return out


def _insert_blocks_into_station(existing_steps, new_blocks_steps, insert_mode="before_teardown"):
    """Inserts block step lists cleanly into target station steps at the chosen anchor."""
    steps = copy.deepcopy(existing_steps or [])
    if not new_blocks_steps:
        return steps

    flat_new = [copy.deepcopy(r) for blk in new_blocks_steps for r in blk]
    if not steps:
        return flat_new

    if insert_mode == "after_pretest":
        # Find end of Phase 0 (first row whose non-empty Phase >= 1)
        ins_at = len(steps)
        for i, r in enumerate(steps):
            pn = _parse_int_phase(r.get("Phase"))
            if i > 0 and pn is not None and (pn >= 1 or pn == -1):
                ins_at = i
                break
        return steps[:ins_at] + flat_new + steps[ins_at:]

    # Default: before_teardown (right before Phase >= 95)
    ins_at = len(steps)
    for i, r in enumerate(steps):
        pn = _parse_int_phase(r.get("Phase"))
        if pn is not None and pn >= 95:
            ins_at = i
            break
    return steps[:ins_at] + flat_new + steps[ins_at:]


def _renumber_station_phases(steps):
    """Ensures non-paused, non-teardown Phases are strictly contiguous 0, 1, 2..."""
    if not steps:
        return steps
    if str(steps[0].get("Phase") or "").strip() == "":
        steps[0]["Phase"] = "0"
    next_phase = 0
    for st in steps:
        p_str = str(st.get("Phase") or "").strip()
        if p_str != "":
            pn = _parse_int_phase(p_str)
            if pn is not None and 0 <= pn < 95:
                st["Phase"] = str(next_phase)
                next_phase += 1
    return steps


def write_companion_files_to_dir(companion_files, target_dir):
    """Writes companion .txt/.ini files (e.g. 69MO.txt, 90MO.txt) cleanly to target output folder."""
    written = []
    if not target_dir or not companion_files:
        return written
    os.makedirs(target_dir, exist_ok=True)
    for fname, content in companion_files.items():
        safe_name = os.path.basename(str(fname or "").strip())
        if not safe_name:
            continue
        txt = content.get("content", "") if isinstance(content, dict) else str(content)
        out_p = os.path.join(target_dir, safe_name)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(txt)
        written.append(out_p)
    return written


def apply_bundle_and_sku_to_workspace(target_ws, target_station, bundle_spec=None, sku_spec=None, output_dir=None):
    """
    Shared core applicator for BOTH '01 / EDIT' and '02 / CREATE':
    - Transplants chosen template blocks + tweaked Instruments / Marcos / DUTs Connections / Global.ini / .txt
    - Generates SFIS SKU Lookup & Multi-SKU routing blocks from the 5 guided questions
    - Applies hardware-derivative Section Guards (4:1,end) to matching blocks
    Returns (updated_ws, summary_dict).
    """
    ws = copy.deepcopy(target_ws or {})
    st_name = str(target_station or ws.get("station_name") or "MB").strip() or "MB"
    b_spec = bundle_spec if isinstance(bundle_spec, dict) else {}
    s_spec = sku_spec if isinstance(sku_spec, dict) else {}

    existing_steps = list(ws.get("stations", {}).get(st_name, []))
    g_settings = ws.setdefault("global_ini", {}).setdefault("Settings", {})
    g_scripts = ws.setdefault("global_ini", {}).setdefault("Scripts", {})
    comp_map = ws.setdefault("_companion_files", {})

    summary = {
        "target_station": st_name,
        "transplanted_blocks": [],
        "marcos_added": [],
        "instruments_added": [],
        "connections_added": [],
        "ini_vars_added": [],
        "companion_files": [],
        "sku_steps_added": 0,
        "sku_summary": [],
        "guarded_sections": [],
    }

    transplanted_list = []  # [(title_label, steps, meta_block_key)]
    inst_remap = b_spec.get("inst_remap") or {}
    conn_remap = b_spec.get("conn_remap") or {}
    paused_keys = set(b_spec.get("paused_block_keys") or [])
    marco_conflict = str(b_spec.get("marco_conflict") or "skip").strip().lower()
    selected_keys = list(b_spec.get("selected_block_keys") or [])
    src_xlsx = str(b_spec.get("source_xlsx") or "").strip()

    if selected_keys and src_xlsx and os.path.exists(src_xlsx):
        src_ws = import_excel_to_workspace(src_xlsx)
        src_dir = os.path.dirname(os.path.abspath(src_xlsx))
        src_inst_by_name = {
            str(r.get("Name") or "").strip().lower(): r
            for r in src_ws.get("instruments", [])
            if str(r.get("Name") or "").strip()
        }
        src_inst_by_func = {}
        for r in src_ws.get("instruments", []):
            for fn in str(r.get("Functions") or "").split(","):
                fn_up = fn.strip().upper()
                if fn_up:
                    src_inst_by_func.setdefault(fn_up, []).append(r)
        src_sw_by_name = {
            str(r.get("Name") or "").strip().lower(): r
            for r in src_ws.get("switches", [])
            if str(r.get("Name") or "").strip()
        }
        src_conn_map = {}
        if src_ws.get("duts"):
            for col, val in src_ws["duts"][0].items():
                if col.startswith("Connection") and val:
                    al = _extract_conn_alias_from_str(val)
                    if al:
                        src_conn_map[al] = str(val)

        # Build key -> raw Title block lookup across stations
        raw_lookup = {}
        for s_nm, s_rows in src_ws.get("stations", {}).items():
            for blk in _split_station_into_title_blocks(s_nm, s_rows):
                raw_lookup[blk["block_key"]] = blk

        needed_conns = {}
        needed_params = []
        existing_inst_names = {str(r.get("Name") or "").strip().lower(): r for r in ws.get("instruments", [])}
        existing_sw_names = {str(r.get("Name") or "").strip().lower() for r in ws.get("switches", [])}

        for b_key in selected_keys:
            blk = raw_lookup.get(b_key)
            if not blk:
                continue
            is_paused = (b_key in paused_keys)
            # Check if any instrument inside this block was mapped to __PAUSE__
            blk_all_rows = list(blk["steps"])
            blk_marcos = []
            for r in blk["steps"]:
                mn = str(r.get("Marco") or "").strip()
                if mn and mn not in blk_marcos:
                    blk_marcos.append(mn)
            for mn in blk_marcos:
                blk_all_rows.extend(src_ws.get("marcos", {}).get(mn, []))

            for r in blk_all_rows:
                sw = str(r.get("Switch") or "").strip().split(",")[0].strip()
                if sw and inst_remap.get(sw) == "__PAUSE__":
                    is_paused = True

            rewritten_steps = _rewrite_steps_for_remaps(blk["steps"], inst_remap, conn_remap, mark_paused=is_paused)
            # Normalize Title prefix cleanly
            if rewritten_steps and not str(rewritten_steps[0].get("Phase") or "").strip():
                rewritten_steps[0]["Phase"] = blk.get("effective_phase") or "1"

            transplanted_list.append({
                "block_key": b_key,
                "title": blk["title"],
                "title_label": blk["title_label"],
                "steps": rewritten_steps,
                "is_teardown": (blk.get("effective_phase_num") is not None and blk.get("effective_phase_num") >= 95),
            })
            summary["transplanted_blocks"].append(f"[{blk['title_label']}] ({len(rewritten_steps)} 步)")

            # Merge Marcos
            for mn in blk_marcos:
                src_m_rows = src_ws.get("marcos", {}).get(mn)
                if not src_m_rows:
                    continue
                m_rewritten = _rewrite_steps_for_remaps(src_m_rows, inst_remap, conn_remap, mark_paused=False)
                tgt_marcos = ws.setdefault("marcos", {})
                final_mn = mn
                if mn in tgt_marcos:
                    if marco_conflict == "skip":
                        continue
                    elif marco_conflict == "rename":
                        for sfx in range(1, 50):
                            cand = f"{mn}_{sfx}"[:31]
                            if cand not in tgt_marcos:
                                final_mn = cand
                                break
                        for sr in rewritten_steps:
                            if str(sr.get("Marco") or "").strip() == mn:
                                sr["Marco"] = final_mn
                tgt_marcos[final_mn] = m_rewritten
                if final_mn not in summary["marcos_added"]:
                    summary["marcos_added"].append(final_mn)

            # Merge Instruments / Sub=1 / Switches
            for r in blk_all_rows:
                sw = str(r.get("Switch") or "").strip().split(",")[0].strip()
                fn = str(r.get("Instrument") or "").strip()
                send = str(r.get("Send") or "").strip()
                cand_rows = []
                if sw:
                    remapped_sw = inst_remap.get(sw, sw)
                    if remapped_sw != "__PAUSE__":
                        if remapped_sw.lower() in src_inst_by_name:
                            cand_rows.append(src_inst_by_name[remapped_sw.lower()])
                        elif sw.lower() in src_inst_by_name and remapped_sw == sw:
                            cand_rows.append(src_inst_by_name[sw.lower()])
                        if remapped_sw.lower() in src_sw_by_name and remapped_sw.lower() not in existing_sw_names:
                            sw_cp = copy.deepcopy(src_sw_by_name[remapped_sw.lower()])
                            sw_cp["Mount"] = st_name
                            ws.setdefault("switches", []).append(sw_cp)
                            existing_sw_names.add(remapped_sw.lower())
                elif fn and fn.upper() in src_inst_by_func:
                    cand_rows.append(src_inst_by_func[fn.upper()][0])
                m_sub = re.match(r'^:ObtainSubDevice\s*,\s*"([^"]+)"', send, re.IGNORECASE)
                if m_sub:
                    snm = m_sub.group(1).strip()
                    snm_t = inst_remap.get(snm, snm)
                    if snm_t != "__PAUSE__" and snm_t.lower() in src_inst_by_name:
                        cand_rows.append(src_inst_by_name[snm_t.lower()])

                for ir in cand_rows:
                    nm = str(ir.get("Name") or "").strip()
                    if not nm:
                        continue
                    if nm.lower() in existing_inst_names:
                        existing_inst_names[nm.lower()]["Mount"] = st_name
                    else:
                        ir_cp = copy.deepcopy(ir)
                        ir_cp["Mount"] = st_name
                        ws.setdefault("instruments", []).append(ir_cp)
                        existing_inst_names[nm.lower()] = ir_cp
                        summary["instruments_added"].append(nm)

            # Collect Connections & Parameters
            for c_al in _scan_step_connections(blk_all_rows):
                target_al = conn_remap.get(c_al, c_al)
                if target_al not in needed_conns:
                    needed_conns[target_al] = src_conn_map.get(c_al) or DEFAULT_CONN_TEMPLATES.get(target_al, "")
            needed_params.extend(_scan_param_indices(blk_all_rows))

            # Companion .txt / .ini files
            for cf in _scan_text_companion_refs(blk_all_rows):
                meta = _read_companion_file(src_dir, cf)
                if meta and cf not in comp_map:
                    comp_map[cf] = meta["content"]
                    if cf not in summary["companion_files"]:
                        summary["companion_files"].append(cf)

        summary["connections_added"] = _merge_dut_connections(ws, needed_conns)
        _ensure_dut_parameters(ws, needed_params)

        # Merge Global.ini values from source + user overrides
        src_g = src_ws.get("global_ini", {})
        all_t_rows = [r for tb in transplanted_list for r in tb["steps"]]
        for vn in _scan_ini_vars(all_t_rows):
            if vn not in g_scripts and vn in src_g.get("Scripts", {}):
                g_scripts[vn] = src_g["Scripts"][vn]
                summary["ini_vars_added"].append(f"Scripts.{vn}")
        # Only pull Settings vars referenced by instruments/connections added for this transplant
        added_inst_set = {nm.lower() for nm in summary["instruments_added"]}
        touched_insts = [ir for ir in ws.get("instruments", []) if str(ir.get("Name") or "").strip().lower() in added_inst_set]
        for ir in touched_insts:
            for vn in _scan_ini_vars([ir]):
                if vn not in g_settings and vn in src_g.get("Settings", {}):
                    g_settings[vn] = src_g["Settings"][vn]
                    summary["ini_vars_added"].append(f"Settings.{vn}")

    # User explicit INI overrides from Step 2 tweaks
    ini_ov = b_spec.get("ini_overrides") or {}
    for k, v in (ini_ov.get("Settings") or {}).items():
        if str(k).strip():
            g_settings[str(k).strip()] = str(v)
    for k, v in (ini_ov.get("Scripts") or {}).items():
        if str(k).strip():
            g_scripts[str(k).strip()] = str(v)

    # User edited companion files
    for cf_name, cf_txt in (b_spec.get("companion_overrides") or {}).items():
        if str(cf_name).strip():
            comp_map[str(cf_name).strip()] = str(cf_txt)
            if cf_name not in summary["companion_files"]:
                summary["companion_files"].append(cf_name)

    # Build Guided SKU Wizard steps (Section ②)
    sku_res = build_sku_wizard_steps(s_spec, start_phase=1)
    for cf_name, cf_txt in sku_res.get("companion_files", {}).items():
        comp_map[cf_name] = cf_txt
        if cf_name not in summary["companion_files"]:
            summary["companion_files"].append(cf_name)
    for k, v in sku_res.get("global_scripts", {}).items():
        g_scripts[k] = v
        if f"Scripts.{k}" not in summary["ini_vars_added"]:
            summary["ini_vars_added"].append(f"Scripts.{k}")

    sku_steps = sku_res.get("steps", [])
    summary["sku_steps_added"] = len(sku_steps)
    summary["sku_summary"] = sku_res.get("summary", [])

    # Apply Hardware-Derivative Section Guards on matching transplanted or existing Title blocks
    guards = [g for g in (s_spec.get("section_guards") or []) if isinstance(g, dict) and g.get("allowed_skus")]
    sku_var_name = sku_res.get("result_var") or _sanitize_var_name(s_spec.get("result_var") or "sfSKUCode")

    if guards:
        # 1) Guard transplanted blocks matching block_key or title substring
        for tb in transplanted_list:
            for gd in guards:
                t_key = str(gd.get("target_block_key") or "").strip()
                s_title = str(gd.get("section_title") or "").strip().lower()
                if (t_key and t_key == tb["block_key"]) or (s_title and s_title in tb["title"].lower()):
                    tb["steps"] = wrap_block_with_sku_guard(
                        tb["steps"], sku_var=sku_var_name,
                        allowed_skus=gd["allowed_skus"], section_title=tb["title_label"]
                    )
                    summary["guarded_sections"].append(f"{tb['title_label']} -> {','.join(gd['allowed_skus'])}")
                    break

        # 2) Guard existing station blocks (or blocks assembled in 0->1 wizard!) matching section_title
        existing_blks = _split_station_into_title_blocks(st_name, existing_steps)
        rebuilt_existing = []
        for eb in existing_blks:
            eb_steps = eb["steps"]
            for gd in guards:
                s_title = str(gd.get("section_title") or "").strip().lower()
                if s_title and s_title in eb["title"].lower() and not eb["title"].lower().startswith("0,sfis sku"):
                    eb_steps = wrap_block_with_sku_guard(
                        eb_steps, sku_var=sku_var_name,
                        allowed_skus=gd["allowed_skus"], section_title=eb["title_label"]
                    )
                    lbl = f"{eb['title_label']} -> {','.join(gd['allowed_skus'])}"
                    if lbl not in summary["guarded_sections"]:
                        summary["guarded_sections"].append(lbl)
                    break
            rebuilt_existing.extend(eb_steps)
        existing_steps = rebuilt_existing

        # 3) If user specified a guard for a standalone section not yet present in transplanted/existing, emit clean gated shell
        applied_titles = {x.split(" -> ")[0].lower() for x in summary["guarded_sections"]}
        for gd in guards:
            s_title = str(gd.get("section_title") or "").strip()
            if s_title and s_title.lower() not in applied_titles and not str(gd.get("target_block_key") or "").strip():
                shell_steps = [
                    _make_step(phase="1", title=f"0,{s_title}", send=':Delay,"100"', reply="0",
                               exec_mode="0", description=f"DUT#-#Execute {s_title}", test_id="B7PL025"),
                ]
                guarded = wrap_block_with_sku_guard(
                    shell_steps, sku_var=sku_var_name,
                    allowed_skus=gd["allowed_skus"], section_title=s_title
                )
                transplanted_list.append({
                    "block_key": f"GUARD::{s_title}",
                    "title": guarded[0]["Title"],
                    "title_label": s_title,
                    "steps": guarded,
                    "is_teardown": False,
                })
                summary["guarded_sections"].append(f"{s_title} -> {','.join(gd['allowed_skus'])}")

    # Insert SKU routing steps right after Pretest/CheckRoute so all downstream Guards see $sku_var
    if sku_steps:
        existing_steps = _insert_blocks_into_station(existing_steps, [sku_steps], insert_mode="after_pretest")

    # Insert transplanted blocks at user's chosen insertion mode (separating normal vs teardown if needed)
    normal_transplanted = [tb["steps"] for tb in transplanted_list if not tb.get("is_teardown")]
    teardown_transplanted = [tb["steps"] for tb in transplanted_list if tb.get("is_teardown")]
    ins_mode = str(b_spec.get("insert_position") or "before_teardown").strip()
    if normal_transplanted:
        existing_steps = _insert_blocks_into_station(existing_steps, normal_transplanted, insert_mode=ins_mode)
    if teardown_transplanted:
        existing_steps.extend([r for blk in teardown_transplanted for r in blk])

    # Renumber contiguous non-paused, non-teardown Phases cleanly
    _renumber_station_phases(existing_steps)
    ws.setdefault("stations", {})[st_name] = existing_steps

    if output_dir and comp_map:
        write_companion_files_to_dir(comp_map, output_dir)

    return ws, summary
