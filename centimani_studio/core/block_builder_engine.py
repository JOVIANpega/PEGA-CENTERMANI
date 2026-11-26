# -*- coding: utf-8 -*-
"""
Centimani Studio - Visual Block Builder Backend Engine (0 -> 1)
Converts the ordered `builder_sequence` from the drag-and-drop block builder
into a Script-Doctor-clean Centimani workspace (stations, DUTs, Instrument, Marcos, INIs).
"""
import re
from core.golden_data import STANDARD_BLOCKS
from core.script_doctor import (
    insert_instrument_title_block,
    insert_ni6009_block,
    insert_rf_iqxel_block,
)


def _step(
    phase="",
    title="",
    marco="",
    inst="",
    sw="",
    send="",
    reply="0",
    end_prompt="",
    ref="",
    validation="",
    prompt="",
    waiting="",
    exec_mode="0",
    description="",
    test_id="B7PL025",
):
    return {
        "Index": "",
        "Phase": str(phase or ""),
        "Title": str(title or ""),
        "Marco": str(marco or ""),
        "Instrument": str(inst or ""),
        "Switch": str(sw or ""),
        "Send": str(send or ""),
        "Reply": str(reply if reply is not None else ""),
        "EndPrompt": str(end_prompt or ""),
        "Ref": str(ref or ""),
        "Validation": str(validation or ""),
        "Prompt": str(prompt or ""),
        "Waiting": str(waiting or ""),
        "ExecMode": str(exec_mode or "0"),
        "Description": str(description or ""),
        "TestID": str(test_id or "B7PL025"),
    }


def _safe_var(name, default="gVal"):
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", str(name or "").strip()).strip("_")
    return cleaned or default


def _ensure_dut_connection(ws, alias, conn_str_fn, overwrite=False):
    """Ensure every DUT slot has `alias` mounted in Connection1..10 without duplicates."""
    alias_low = str(alias or "").strip().lower()
    if not alias_low:
        return
    conn_cols = [
        "Connection1 (Type,Name,ConnectString)",
        "Connection2 (Type,Name,ConnectString)",
        "Connection3 (Type,Name,ConnectString)",
        "Connection4(Type,Name,ConnectString)",
        "Connection5(Type,Name,ConnectString)",
        "Connection6(Type,Name,ConnectString)",
        "Connection7(Type,Name,ConnectString)",
        "Connection8(Type,Name,ConnectString)",
        "Connection9(Type,Name,ConnectString)",
        "Connection10(Type,Name,ConnectString)",
    ]
    for slot_idx, dut in enumerate(ws.get("duts") or [], 1):
        already = False
        first_empty = None
        for col in conn_cols:
            val = str(dut.get(col) or "").strip()
            if not val:
                if first_empty is None:
                    first_empty = col
                continue
            m = re.match(r'^"[^"]*"\s*,\s*"([^"]+)"', val)
            if m and m.group(1).strip().lower() == alias_low:
                if overwrite:
                    dut[col] = conn_str_fn(slot_idx)
                already = True
                break
        if not already and first_empty:
            dut[first_empty] = conn_str_fn(slot_idx)


def _append_standard_block_steps(bid, blk_map, wizard_config, ws, steps, next_phase_ref):
    b = blk_map.get(bid)
    if not b:
        return
    for k, v in b.get("required_globals", {}).get("Settings", {}).items():
        ws.setdefault("global_ini", {}).setdefault("Settings", {})[k] = v
    for k, v in b.get("required_globals", {}).get("Scripts", {}).items():
        ws.setdefault("global_ini", {}).setdefault("Scripts", {})[k] = v
    for m_name, m_rows in b.get("required_marcos", {}).items():
        ws.setdefault("marcos", {})[m_name] = [dict(mr) for mr in m_rows]
    src = b.get("steps", [])
    for idx, st_row in enumerate(src):
        r = dict(st_row)
        if idx == 0:
            p_raw = str(r.get("Phase") or "").strip()
            if p_raw and p_raw.isdigit() and int(p_raw) < 95:
                r["Phase"] = str(next_phase_ref[0])
                next_phase_ref[0] += 1
        steps.append(r)


_UTILITY_SENDS = (":Delay", ":Connect", ":Disconnect", ":ObtainDevice", ":ReleaseDevice", ":ObtainSubDevice", ":ReleaseSubDevice", ":CloseMessage")


def _apply_custom_test_id(rows_slice, custom_tid):
    """Apply user-chosen 7-char TestID from Advanced Q&A to primary action rows."""
    tid = str(custom_tid or "").strip()
    if not tid or not rows_slice:
        return
    applied = False
    for r in rows_slice:
        s = str(r.get("Send") or "").strip()
        if not any(s.startswith(p) for p in _UTILITY_SENDS):
            r["TestID"] = tid
            applied = True
    if not applied:
        rows_slice[0]["TestID"] = tid


def _apply_custom_exec_mode(rows_slice, custom_em, g_scr=None, g_set=None):
    """Apply user-chosen ExecMode (e.g. '6', '2:0', '*$(AULAB)') to primary action rows."""
    em = str(custom_em or "").strip()
    if not em or not rows_slice:
        return
    ini_target = g_scr if g_scr is not None else g_set
    if ini_target is not None:
        for m in re.finditer(r"\*\$\(([^)]+)\)", em):
            vn = m.group(1).strip()
            if vn and vn not in ini_target:
                ini_target[vn] = "1"
    applied = False
    for r in rows_slice:
        s = str(r.get("Send") or "").strip()
        if not any(s.startswith(p) for p in _UTILITY_SENDS):
            r["ExecMode"] = em
            applied = True
    if not applied:
        rows_slice[0]["ExecMode"] = em


def _apply_custom_title(rows_slice, title_run_mode=None, title_retry=None, g_scr=None):
    """Apply custom Title prefix (0/1/2/*$(Var)/none) and RetryCount on the first titled row."""
    if not rows_slice:
        return
    if title_run_mode is None and title_retry is None:
        return
    for r in rows_slice:
        cur_t = str(r.get("Title") or "").strip()
        if not cur_t or cur_t.startswith("__INST_SLOT_"):
            continue
        parts = [p.strip() for p in cur_t.split(",")]
        cur_mode = "0"
        cur_name = cur_t
        cur_retry = ""
        if len(parts) >= 2 and (parts[0] in ("0", "1", "2") or parts[0].startswith("*$(")):
            cur_mode = parts[0]
            cur_name = parts[1]
            cur_retry = parts[2] if len(parts) >= 3 else ""
        elif len(parts) >= 2 and parts[-1].isdigit():
            cur_mode = ""
            cur_name = ",".join(parts[:-1])
            cur_retry = parts[-1]
        new_mode = cur_mode if title_run_mode is None else str(title_run_mode).strip()
        new_retry = cur_retry if title_retry is None else str(title_retry).strip()
        if g_scr is not None and new_mode and new_mode != "none":
            _register_ini_tokens(new_mode, g_scr, "0")
        if new_mode.lower() == "none" or new_mode == "":
            r["Title"] = f"{cur_name},{new_retry}" if (new_retry and new_retry != "0") else cur_name
        else:
            r["Title"] = f"{new_mode},{cur_name},{new_retry}" if (new_retry and new_retry != "0") else f"{new_mode},{cur_name}"
        break


def _build_single_ref_line(spec):
    vn = _safe_var(spec.get("var_name") or "gCmdOut", "gCmdOut")
    em = str(spec.get("extract_mode") or "within").strip().lower()
    chain = f"${vn}"
    if spec.get("rp_space"):
        chain += ':rpString," ",""'
    if em == "split":
        sep = str(spec.get("split_sep") or ":").replace('"', '\\"')
        idx_s = str(spec.get("split_idx") or "1").strip() or "1"
        chain += f':SplitString,"{sep}","{idx_s}"'
    elif em == "sub":
        st_i = str(spec.get("sub_start") or "0").strip() or "0"
        ln_i = str(spec.get("sub_len") or "8").strip() or "8"
        chain += f':SubString,"{st_i}","{ln_i}"'
    else:
        left_s = str(spec.get("left_delim") if spec.get("left_delim") is not None else "version=").replace('"', '\\"')
        right_s = str(spec.get("right_delim") if spec.get("right_delim") is not None else "\\r\\n").replace('"', '\\"')
        chain += f':WithinString,"{left_s}","{right_s}",""'
    if spec.get("trim"):
        chain += ":Trim"
    if spec.get("rm_mac"):
        chain += ":rmMAC"
    if spec.get("up_string"):
        chain += ":upString"
    return chain


def _register_ini_tokens(text, g_set, default_val="1"):
    for m in re.finditer(r"\*\$\(([^)]+)\)", str(text or "")):
        vn = m.group(1).strip()
        if vn and vn not in g_set:
            g_set[vn] = default_val


def _dedup_group_steps(grp_steps):
    """Keep one shared Phase/Title for a group box and strip redundant mid-group UART connects."""
    opened_uart = set()
    cleaned = []
    skip_prompt_alias = ""
    for r in grp_steps:
        s = str(r.get("Send") or "").strip()
        if skip_prompt_alias and s == f"{skip_prompt_alias}@\\r\\n":
            skip_prompt_alias = ""
            continue
        skip_prompt_alias = ""
        m_conn = re.match(r'^:Connect,"([^"]+)"$', s)
        if m_conn:
            alias = m_conn.group(1)
            if alias in opened_uart:
                skip_prompt_alias = alias
                continue
            opened_uart.add(alias)
        m_disc = re.match(r'^:Disconnect,"([^"]+)"$', s)
        if m_disc:
            opened_uart.discard(m_disc.group(1))
        cleaned.append(r)
    return cleaned


def build_workspace_from_sequence(
    ws,
    station_name,
    sequence,
    wizard_config,
    build_wizard_block_steps_fn,
    skip_teardown=False,
):
    """
    Build ordered station steps + DUT connections + instruments + INIs from `builder_sequence`.
    Returns `(ws, sku_wizard_override_or_None)`.
    """
    blk_map = {b["block_id"]: b for b in STANDARD_BLOCKS}
    steps = []
    deferred_inst_blocks = []
    extracted_sku_cfg = None
    next_phase = [1]  # phase 0 reserved for sfis_route + optional phase0 blocks
    has_phase0 = False
    active_phase_role = [""]
    g_set = ws.setdefault("global_ini", {}).setdefault("Settings", {})
    g_scr = ws.setdefault("global_ini", {}).setdefault("Scripts", {})

    def _alloc_phase(force_zero=False):
        if force_zero:
            return "0"
        ov = active_phase_role[0]
        if ov in ("0", "-1", "same"):
            active_phase_role[0] = ""
            return "" if ov == "same" else ov
        p = str(next_phase[0])
        next_phase[0] += 1
        return p

    # Separate teardown blocks and phase_role 97/98/99 groups cleanly
    normal_items = []
    teardown_items = []
    teardown_groups = []
    for it in (sequence or []):
        if not isinstance(it, dict):
            continue
        k = it.get("kind")
        if k == "teardown":
            teardown_items.append(it)
        elif k == "end":
            continue
        elif k == "group" and str((it.get("config") or {}).get("phase_role") or "normal").strip() in ("97", "97:PWROFF", "98", "99"):
            teardown_groups.append(it)
        else:
            normal_items.append(it)

    def _apply_sfis_hmi_bundle(hmi_bundle, cfg, is_route):
        from core.sfis_client import build_sfis_excel_steps
        scfg = hmi_bundle.get("config") or {}
        sys_ini = ws.setdefault("system_ini", {})
        if is_route or scfg.get("sfis_enable") is not None:
            sys_ini["SFIS_Enable"] = str(scfg.get("sfis_enable") or ("1" if cfg.get("sfis_mode") == "online" else "0"))
        if scfg.get("url"):
            sys_ini["SFIS_WebLink"] = str(scfg["url"]).strip()
        if scfg.get("tsp"):
            sys_ini["SFIS_TSP"] = str(scfg["tsp"]).strip()
        if scfg.get("op"):
            sys_ini["SFIS_LoginID"] = str(scfg["op"]).strip()
            sys_ini["SFIS_AutoLogin"] = "1"
        if scfg.get("isn"):
            sys_ini["SFIS_GetDateISN"] = str(scfg["isn"]).strip()
        if "skip_save_on_fail" in scfg:
            sys_ini["SFIS_SkipSaveResultOnFail"] = "1" if scfg.get("skip_save_on_fail") else "0"
        if scfg.get("device_id"):
            g_set["DEVID_1"] = str(scfg["device_id"]).strip()
        if is_route:
            _ensure_dut_connection(
                ws, "UART", lambda sl: f'"Uart","UART","*$(DUT_UR{sl}),115200,8,One,None,None,10000,5000"'
            )
        start_ph = 0 if is_route else int(_alloc_phase())
        need_show_isn = not has_phase0 and not any(':ShowISN' in str(s.get('Send') or '') for s in steps)
        sfis_steps = build_sfis_excel_steps(hmi_bundle["items"], start_phase=start_ph, include_show_isn=need_show_isn)
        if sfis_steps:
            steps.extend(sfis_steps)
            return True
        return False

    for item in normal_items:
        kind = str(item.get("kind") or "").strip()
        cfg = item.get("config") or {}
        step_start_idx = len(steps)
        req_role = str(cfg.get("phase_role") or "").strip()
        active_phase_role[0] = req_role if (kind not in ("start", "isn", "group", "teardown", "end", "sfis_route", "multi_sku", "inst") and req_role in ("0", "-1", "same")) else ""

        if kind == "start":
            sys_ini = ws.setdefault("system_ini", {})
            if cfg.get("debug_mode") is not None:
                sys_ini["DebugMode"] = str(cfg.get("debug_mode"))
            if cfg.get("sfis_enable") is not None:
                sys_ini["SFIS_Enable"] = str(cfg.get("sfis_enable"))
            continue

        elif kind == "isn":
            # Applied on top-level ws metadata & DUTs; optionally customize or disable ScanBarcode
            if cfg.get("enable_scan") is False:
                for dut in (ws.get("duts") or []):
                    dut["ScanBarcode( {Name,Lengh,Pattern} )"] = ""
            elif any(cfg.get(k) is not None for k in ("barcode_name", "barcode_len", "barcode_pattern", "isn_len", "isn_pattern")):
                b_name = str(cfg.get("barcode_name") or "ISN").strip() or "ISN"
                raw_len = cfg.get("barcode_len") if cfg.get("barcode_len") is not None else cfg.get("isn_len")
                raw_pat = cfg.get("barcode_pattern") if cfg.get("barcode_pattern") is not None else cfg.get("isn_pattern")
                b_len = "" if raw_len is None else str(raw_len).strip()
                b_pat = "" if raw_pat is None else str(raw_pat).strip()
                scan_expr = f"{{  {b_name},{b_len},{b_pat}  }}"
                for dut in (ws.get("duts") or []):
                    dut["ScanBarcode( {Name,Lengh,Pattern} )"] = scan_expr
            continue

        elif kind == "sfis_route":
            # Applies System.ini switches and builds Phase 0 CheckRoute (or synced SFIS HMI bundle)
            use_ph0 = bool(cfg.get("use_phase0", True))
            req_uart = bool(cfg.get("require_uart", True))
            hmi_bundle = cfg.get("sfis_hmi_bundle")
            if isinstance(hmi_bundle, dict) and (hmi_bundle.get("items") or []):
                if _apply_sfis_hmi_bundle(hmi_bundle, cfg, is_route=use_ph0):
                    if use_ph0:
                        has_phase0 = True
            else:
                mode = str(cfg.get("sfis_mode") or "offline").strip().lower()
                sys_ini = ws.setdefault("system_ini", {})
                if mode == "online":
                    sys_ini["SFIS_Enable"] = "1"
                    sys_ini["DebugMode"] = str(cfg.get("debug_mode") or "0")
                else:
                    sys_ini["SFIS_Enable"] = "0"
                    sys_ini["DebugMode"] = "1"
                if cfg.get("tsp"):
                    sys_ini["SFIS_TSP"] = str(cfg["tsp"]).strip()
                if cfg.get("weblink"):
                    sys_ini["SFIS_WebLink"] = str(cfg["weblink"]).strip()
                if cfg.get("login_id"):
                    sys_ini["SFIS_LoginID"] = str(cfg["login_id"]).strip()
                    sys_ini["SFIS_AutoLogin"] = "1"
                if cfg.get("date_isn"):
                    sys_ini["SFIS_GetDateISN"] = str(cfg["date_isn"]).strip()
                route_ph = "0" if use_ph0 else _alloc_phase()
                steps.append(_step(
                    phase=route_ph, title="0,CheckRoute", send=':ShowISN,"*(ISN)"', reply="0", exec_mode="1",
                    description="PC#-#Display ISN", test_id="B7PL025",
                ))
                if req_uart:
                    _ensure_dut_connection(
                        ws, "UART", lambda sl: f'"Uart","UART","*$(DUT_UR{sl}),115200,8,One,None,None,10000,5000"'
                    )
                    steps.append(_step(
                        send=':Disconnect,"UART"', reply="0", exec_mode="3",
                        description="PC#-#Ensure UART Closed Before Route", test_id="OTFX082",
                    ))
                steps.append(_step(
                    send=":SfCheckRoute", reply="0", waiting="2000", exec_mode="8",
                    description="SFIS#-#Check Station Route", test_id="OTFX085",
                ))
                if use_ph0:
                    has_phase0 = True

        elif kind == "fixture":
            fx_type = str(cfg.get("fixture_type") or "none").strip().lower()
            if fx_type == "none":
                continue
            delay_ms = str(cfg.get("delay_ms") or "3000").strip() or "3000"
            if fx_type == "ipower":
                ws["switches"] = ws.get("switches") or []
                ph = "" if has_phase0 else _alloc_phase(force_zero=False)
                steps.extend([
                    _step(phase=ph, title="0,Power Cold Reset", inst="POWERSWITCH", sw="IPOWER2401",
                          send=":ObtainDevice", reply="0", exec_mode="0", description="Power#-#Obtain iPower Lock"),
                    _step(send=':Dev.SwitchOFF,"1"', reply="0", exec_mode="0",
                          description="Power#-#Switch OFF Channel 1", test_id="BRME027"),
                    _step(send=f':Delay,"{delay_ms}"', reply="0", exec_mode="0",
                          description="PC#-#Wait Discharge"),
                    _step(send=':Dev.SwitchON,"1"', reply="0", exec_mode="0",
                          description="Power#-#Switch ON Channel 1", test_id="BRME027"),
                    _step(send=":ReleaseDevice", reply="0", exec_mode="3",
                          description="Power#-#Release Power Lock", test_id="BRME027"),
                ])
            else:
                g_set["PCUART_fixture_1"] = str(cfg.get("com_port") or g_set.get("PCUART_fixture_1") or "COM8").strip()
                _ensure_dut_connection(
                    ws, "UARTF", lambda sl: f'"Uart","UARTF","*$(PCUART_fixture_{sl}),9600,8,One,None,None,10000,5000"'
                )
                ph = "" if has_phase0 else _alloc_phase(force_zero=False)
                steps.extend([
                    _step(phase=ph, title="0,Fixture Down,3", send=':Connect,"UARTF"', reply="0",
                          exec_mode="1", description="Fixture#-#Connect Fixture COM", test_id="OTFX082"),
                    _step(send='UARTF@G\\r\\n', reply="", exec_mode="1",
                          description="Fixture#-#Close Pneumatic Clamp", test_id="OTFX157"),
                    _step(send=f':Delay,"{delay_ms}"', reply="0", exec_mode="1",
                          description="PC#-#Wait DUT Power Stable"),
                ])

        elif kind == "comm_cmd":
            proto = str(cfg.get("protocol") or "uart").strip().lower()
            title_lbl = str(cfg.get("title") or "Comm Command Test").strip() or "Comm Command Test"
            cmd = str(cfg.get("command") or "cat /etc/version").strip() or "cat /etc/version"
            endp = str(cfg.get("end_prompt") if cfg.get("end_prompt") is not None else ("#" if proto in ("uart", "ssh", "telnet") else ">")).strip()
            wait_ms = str(cfg.get("waiting") or "5000").strip() or "5000"
            retry = str(cfg.get("retry") or "3").strip() or "3"
            extract_mode = str(cfg.get("extract_mode") or "reply_only").strip().lower()
            reply_kw = str(cfg.get("reply_keyword") if cfg.get("reply_keyword") is not None else "PASS").strip()
            reply_mode = str(cfg.get("reply_mode") or "contains").strip().lower()
            prompt_col = str(cfg.get("prompt") or "").strip()
            baud_rate = str(cfg.get("baud_rate") or "115200").strip() or "115200"
            char_mode = str(cfg.get("char_mode") or "").strip()
            skip_connect = bool(cfg.get("skip_connect", False))
            skip_prompt_check = bool(cfg.get("skip_prompt_check", False))
            append_nl = cfg.get("append_newline")
            if append_nl is None:
                append_nl = (char_mode.lower() != "hex")
            else:
                append_nl = bool(append_nl)
            nl_suffix = "\\r\\n" if append_nl else ""
            var_name = _safe_var(cfg.get("var_name") or "gCmdOut", "gCmdOut")
            val_type = str(cfg.get("val_type") or "%s").strip()
            if val_type not in ("%s", "%f", "%d", "%x"):
                val_type = "%s"
            expect_min = str(cfg.get("expect_min") if cfg.get("expect_min") is not None else "").strip()
            expect_max = str(cfg.get("expect_max") if cfg.get("expect_max") is not None else "").strip()
            use_ini = bool(cfg.get("use_ini_var", False))

            ph = _alloc_phase()
            t_str = f"0,{title_lbl},{retry}" if retry and retry != "0" else f"0,{title_lbl}"

            connect_step = None
            prompt_step = None
            char_mode_step = None
            close_step = None

            # Determine connection alias & prefix
            if proto == "uart":
                raw_alias = str(cfg.get("alias") or "UART").strip()
                alias = _safe_var(raw_alias, "UART") if raw_alias else "UART"
                port_val = str(cfg.get("port") or g_set.get("DUT_UR1") or "COM4").strip()
                if alias == "UART":
                    ur_key = str(cfg.get("port_ini_key") or "DUT_UR").strip() or "DUT_UR"
                    g_set[f"{ur_key}1"] = port_val
                    want_ow = bool(cfg.get("port_ini_key") or (baud_rate != "115200"))
                    _ensure_dut_connection(
                        ws, "UART", lambda sl, uk=ur_key, br=baud_rate: f'"Uart","UART","*$({uk}{sl}),{br},8,One,None,None,10000,5000"',
                        overwrite=want_ow,
                    )
                else:
                    ini_ur_key = f"{alias}_UR"
                    g_set[f"{ini_ur_key}1"] = port_val
                    _ensure_dut_connection(
                        ws, alias, lambda sl, a=alias, k=ini_ur_key, br=baud_rate: f'"Uart","{a}","*$({k}{sl}),{br},8,One,None,None,10000,5000"'
                    )
                if not skip_connect:
                    connect_step = _step(phase=ph, title=t_str, send=f':Connect,"{alias}"', reply="0",
                                         exec_mode="1", description=f"PC#-#Connect {alias} Port", test_id="OTFX082")
                    if char_mode:
                        char_mode_step = _step(send=f':AddAttribute,"{alias}","CharMode","{char_mode}"', reply="0",
                                               exec_mode="1", description=f"PC#-#Set {alias} CharMode {char_mode}", test_id="OTFX082")
                    elif not skip_prompt_check:
                        prompt_step = _step(send=f"{alias}@\\r\\n", reply=f"@{endp}" if endp else "@#", end_prompt=endp or "#",
                                            waiting="5000", exec_mode="1", description=f"DUT#-#Check {alias} Prompt", test_id="OTFX079")
                send_str = f"{alias}@{cmd}{nl_suffix}"
                if bool(cfg.get("close_after", False)):
                    close_step = _step(send=f':Disconnect,"{alias}"', reply="0", exec_mode="3",
                                       description=f"PC#-#Disconnect {alias}", test_id="OTFX082")
            elif proto == "ssh":
                alias = "SSH1"
                ssh_user = str(cfg.get("ssh_user") or "root").strip() or "root"
                ssh_pass = str(cfg.get("ssh_pass") or "").strip()
                if cfg.get("dut_ip"):
                    g_set["DUTIP_1"] = str(cfg["dut_ip"]).strip()
                _ensure_dut_connection(
                    ws, "SSH1", lambda sl: f'"SSH","SSH1","*$(PCIP_{sl}),*$(DUTIP_{sl}),22,{ssh_user},{ssh_pass},5000,1000"'
                )
                if not skip_connect:
                    connect_step = _step(phase=ph, title=t_str, send=':Connect,"SSH1"', reply="0",
                                         exec_mode="1", description="PC#-#Connect SSH Console", test_id="OTFX082")
                ssh_nl = "\\n" if cfg.get("append_newline") is None else nl_suffix
                send_str = f"SSH1@{cmd}{ssh_nl}"
                if not bool(cfg.get("keep_open", False)):
                    close_step = _step(send=':Disconnect,"SSH1"', reply="0", exec_mode="3",
                                       description="PC#-#Disconnect SSH Console", test_id="OTFX082")
            elif proto == "telnet":
                alias = "TELNET1"
                t_user = str(cfg.get("ssh_user") or "root").strip() or "root"
                t_pass = str(cfg.get("ssh_pass") or "").strip()
                if cfg.get("dut_ip"):
                    g_set["DUTIP_1"] = str(cfg["dut_ip"]).strip()
                _ensure_dut_connection(
                    ws, "TELNET1", lambda sl: f'"Telnet","TELNET1","*$(PCIP_{sl}),*$(DUTIP_{sl}),23,{t_user},{t_pass},5000,1000"'
                )
                if not skip_connect:
                    connect_step = _step(phase=ph, title=t_str, send=':Connect,"TELNET1"', reply="0",
                                         exec_mode="1", description="PC#-#Connect Telnet Console", test_id="OTFX082")
                send_str = f"TELNET1@{cmd}{nl_suffix}"
                if not bool(cfg.get("keep_open", False)):
                    close_step = _step(send=':Disconnect,"TELNET1"', reply="0", exec_mode="3",
                                       description="PC#-#Disconnect Telnet Console", test_id="OTFX082")
            elif proto in ("util_cmd", "utility_cmd"):
                alias = "Utility.CMD"
                exe_p = str(cfg.get("cmd_exe") or cmd or "{0}\\SPT_repeater.exe").strip()
                exe_args = str(cfg.get("cmd_args") if cfg.get("cmd_args") is not None else "").strip()
                show_f = str(cfg.get("cmd_show") if cfg.get("cmd_show") is not None else "ON").strip()
                extra_f = str(cfg.get("cmd_extra") if cfg.get("cmd_extra") is not None else "").strip()
                _register_ini_tokens(exe_p, g_scr, "")
                _register_ini_tokens(exe_args, g_scr, "")
                if show_f or extra_f:
                    send_str = f':Utility.CMD,"{exe_p}","{exe_args}","{show_f or "ON"}","{wait_ms}","{extra_f or "0"}"'
                else:
                    send_str = f':Utility.CMD,"{exe_p}","{exe_args}"'
            else:
                # adb or cmd (Windows CmdConsole / MtCmd / STCmd / CmdConsole2)
                raw_app_alias = str(cfg.get("app_alias") or cfg.get("alias") or "CmdConsole").strip()
                alias = _safe_var(raw_app_alias, "CmdConsole") if raw_app_alias else "CmdConsole"
                cmd_conn = str(cfg.get("app_conn") or "C:\\Windows\\System32\\cmd.exe,0,5000,").strip()
                _register_ini_tokens(cmd_conn, g_set, "1")
                _ensure_dut_connection(
                    ws, alias, lambda _sl, a=alias, cc=cmd_conn: f'"APP","{a}","{cc}"',
                    overwrite=bool(cfg.get("app_conn")),
                )
                full_cmd = cmd
                if proto == "adb" and not cmd.lower().startswith("adb"):
                    full_cmd = f"adb {cmd}"
                if not skip_connect:
                    connect_step = _step(phase=ph, title=t_str, send=f':Connect,"{alias}"', reply="0",
                                         exec_mode="1", description=f"PC#-#Open Console ({alias})", test_id="B7PL025")
                send_str = f"{alias}@{full_cmd}{nl_suffix}"
                if not bool(cfg.get("keep_open", False)):
                    close_step = _step(send=f':Disconnect,"{alias}"', reply="0", exec_mode="3",
                                       description=f"PC#-#Close Console ({alias})", test_id="B7PL025")

            _register_ini_tokens(cmd, g_scr, "1")
            _register_ini_tokens(reply_kw, g_scr, "1")
            ref_expr = ""
            val_expr = ""
            multi_refs = [mr for mr in (cfg.get("multi_refs") or []) if isinstance(mr, dict) and str(mr.get("var_name") or "").strip()]
            if proto in ("util_cmd", "utility_cmd"):
                if reply_mode in ("exact", "raw"):
                    step_reply = str(cfg.get("raw_reply") if (reply_mode == "raw" and cfg.get("raw_reply") is not None) else reply_kw)
                elif extract_mode == "reply_only" and cfg.get("reply_keyword") and cfg.get("reply_keyword") != "PASS":
                    step_reply = f"@{reply_kw}"
                else:
                    step_reply = "0"
            elif reply_mode in ("exact", "raw"):
                step_reply = str(cfg.get("raw_reply") if (reply_mode == "raw" and cfg.get("raw_reply") is not None) else reply_kw)
            else:
                step_reply = f"@{reply_kw}" if (extract_mode == "reply_only" and reply_kw) else "@"
            if multi_refs:
                ref_lines = [_build_single_ref_line(mr) for mr in multi_refs]
                ref_expr = ";\n".join(ref_lines) + ";"
                if reply_mode not in ("exact", "raw") and reply_kw:
                    step_reply = f"@{reply_kw}"
            elif extract_mode != "reply_only":
                ref_expr = _build_single_ref_line(cfg)

                if expect_min != "" or expect_max != "":
                    if val_type == "%s":
                        exp_str = expect_min or expect_max
                        if use_ini and exp_str:
                            ini_k = f"{var_name}_SPEC"
                            g_scr[ini_k] = exp_str
                            exp_tok = f"*$({ini_k})"
                        else:
                            exp_tok = exp_str
                        val_expr = f"({var_name},%s,{exp_tok},{exp_tok})"
                    else:
                        lo_val = expect_min or "0"
                        hi_val = expect_max or lo_val
                        if use_ini:
                            g_scr[f"{var_name}_DL"] = lo_val
                            g_scr[f"{var_name}_UL"] = hi_val
                            lo_tok = f"*$({var_name}_DL)"
                            hi_tok = f"*$({var_name}_UL)"
                        else:
                            lo_tok, hi_tok = lo_val, hi_val
                        val_expr = f"({var_name},{val_type},{lo_tok},{hi_tok})"

            conn_action = str(cfg.get("conn_action") or "send").strip().lower()
            if conn_action == "connect_only":
                if connect_step:
                    steps.append(connect_step)
                if char_mode_step:
                    steps.append(char_mode_step)
            elif conn_action == "disconnect_only":
                steps.append(_step(
                    phase=ph, title=t_str, send=f':Disconnect,"{alias}"', reply="0",
                    exec_mode="3", description=f"PC#-#Disconnect {alias}", test_id="OTFX082",
                ))
            else:
                if connect_step:
                    steps.append(connect_step)
                if char_mode_step:
                    steps.append(char_mode_step)
                if prompt_step:
                    steps.append(prompt_step)
                steps.append(_step(
                    phase="" if connect_step else ph,
                    title="" if connect_step else t_str,
                    send=send_str,
                    reply=step_reply,
                    end_prompt=endp,
                    ref=ref_expr,
                    validation=val_expr,
                    prompt=prompt_col,
                    waiting=wait_ms,
                    exec_mode="1",
                    description=f"DUT#-#{title_lbl} ({alias})",
                    test_id="VSCH026" if val_expr else "OTFX054",
                ))
                if close_step:
                    steps.append(close_step)

        elif kind == "delay":
            ms = str(cfg.get("ms") or "1000").strip() or "1000"
            note = str(cfg.get("note") or f"Wait {ms} ms").strip()
            ph = _alloc_phase()
            steps.append(_step(
                phase=ph,
                title=f"0,Delay {ms}ms",
                send=f':Delay,"{ms}"',
                reply="0",
                exec_mode="0",
                description=f"PC#-#{note}",
                test_id="B7PL025",
            ))

        elif kind == "prompt_box":
            p_mode = str(cfg.get("prompt_mode") or "ok_only").strip().lower()
            msg = str(cfg.get("message") or "請確認測試狀態").strip()
            title_lbl = str(cfg.get("title") or "Operator Check").strip() or "Operator Check"
            ph = _alloc_phase()
            if p_mode == "input":
                var_in = _safe_var(cfg.get("var_name") or "ScanSub", "ScanSub")
                min_len = str(cfg.get("min_len") or "1").strip() or "1"
                max_len = str(cfg.get("max_len") or "32").strip() or "32"
                steps.append(_step(
                    phase=ph,
                    title=f"0,{title_lbl},3",
                    send=':Delay,"10"',
                    reply="0",
                    ref=f"${var_in};",
                    validation=f"({var_in},%len,{min_len},{max_len});",
                    prompt=msg,
                    exec_mode="1",
                    description=f"OP#-#Input {var_in}",
                    test_id="CACK180",
                ))
            elif p_mode == "yes_no":
                yes_lbl = str(cfg.get("yes_label") or "Yes").strip() or "Yes"
                no_lbl = str(cfg.get("no_label") or "No").strip() or "No"
                no_policy = str(cfg.get("no_policy") or "fail").strip().lower()
                if no_policy == "branch":
                    steps.extend([
                        _step(phase=ph, title=f"0,{title_lbl}",
                              send=f':ShowConfirmBox,"{msg}","{yes_lbl};{no_lbl}"',
                              reply=yes_lbl, exec_mode="4:1,2",
                              description=f"OP#-#Confirm ({yes_lbl}/{no_lbl})", test_id="OTFX054"),
                        _step(send=':Delay,"50"', reply="0", exec_mode="4:3,3",
                              description=f"OP#-#Confirmed {yes_lbl} (PASS)", test_id="B7PL025"),
                        _step(send=':Delay,"0"', reply="1", exec_mode="0",
                              description=f"OP#-#Operator Clicked {no_lbl} (FAIL)", test_id="B7PL025"),
                        _step(send=':Delay,"50"', reply="0", exec_mode="0",
                              description="PC#-#Confirm Complete", test_id="B7PL025"),
                    ])
                else:
                    em = "1" if no_policy == "retry" else "0"
                    t_title = f"0,{title_lbl},3" if em == "1" else f"0,{title_lbl}"
                    steps.append(_step(
                        phase=ph,
                        title=t_title,
                        send=f':ShowConfirmBox,"{msg}","{yes_lbl};{no_lbl}"',
                        reply=yes_lbl,
                        exec_mode=em,
                        description=f"OP#-#Confirm ({yes_lbl}/{no_lbl})",
                        test_id="OTFX054",
                    ))
            else:
                btn_lbl = str(cfg.get("ok_label") or "好(OK)").strip() or "好(OK)"
                steps.append(_step(
                    phase=ph,
                    title=f"0,{title_lbl},3",
                    send=f':ShowConfirmBox,"{msg}","{btn_lbl}"',
                    reply=btn_lbl,
                    exec_mode="1",
                    description="OP#-#Operator Action Confirm",
                    test_id="OTFX054",
                ))

        elif kind == "var_check":
            var_nm = _safe_var(cfg.get("var_name") or "gVal", "gVal")
            chk_mode = str(cfg.get("check_mode") or "limit").strip().lower()
            title_lbl = str(cfg.get("title") or f"Check {var_nm}").strip()
            use_ini = bool(cfg.get("use_ini_var", False))
            ph = _alloc_phase()
            if chk_mode == "validation":
                dl = str(cfg.get("dl") if cfg.get("dl") is not None else "0").strip()
                ul = str(cfg.get("ul") if cfg.get("ul") is not None else "100").strip()
                vtype = str(cfg.get("val_type") or "%f").strip()
                if vtype not in ("%f", "%d", "%s", "%SELF"):
                    vtype = "%f"
                if cfg.get("skip_validation") or (dl == "" and ul == "" and vtype != "%SELF"):
                    val_out = ""
                elif vtype == "%s":
                    exp_s = str(cfg.get("expect_str") or dl or "1").strip()
                    val_out = f"({var_nm},%s,{exp_s},{exp_s});"
                else:
                    if use_ini:
                        g_scr[f"{var_nm}_DL"] = dl
                        g_scr[f"{var_nm}_UL"] = ul
                        dl_tok = f"*$({var_nm}_DL)"
                        ul_tok = f"*$({var_nm}_UL)"
                    else:
                        _register_ini_tokens(dl, g_scr, "0")
                        _register_ini_tokens(ul, g_scr, "0")
                        dl_tok, ul_tok = dl, ul
                    val_out = f"({var_nm},{vtype},{dl_tok},{ul_tok});"
                steps.append(_step(
                    phase=ph,
                    title=f"0,{title_lbl}",
                    send=str(cfg.get("send") or ':Delay,"0"').strip() or ':Delay,"0"',
                    reply=str(cfg.get("reply") if cfg.get("reply") is not None else "0").strip(),
                    ref=str(cfg.get("ref_expr") or "").strip(),
                    validation=val_out,
                    waiting=str(cfg.get("waiting") or "").strip(),
                    exec_mode="0",
                    description=f"PC#-#Validate {var_nm}",
                    test_id="CACK182",
                ))
            elif chk_mode == "string":
                expect_s = str(cfg.get("expect_str") if cfg.get("expect_str") is not None else "PASS").strip()
                exact_m = bool(cfg.get("exact_match", False))
                if use_ini:
                    ini_k = f"{var_nm}_EXPECT"
                    g_scr[ini_k] = expect_s
                    tok = f"*$({ini_k})"
                else:
                    _register_ini_tokens(expect_s, g_scr, "0")
                    tok = expect_s
                send_v = str(cfg.get("send_expr") or f"${var_nm}").strip()
                steps.append(_step(
                    phase=ph,
                    title=f"0,{title_lbl}",
                    send=f':GetVal,"{send_v}"',
                    reply=tok if exact_m else f"@{tok}",
                    waiting=str(cfg.get("waiting") or "").strip(),
                    exec_mode="0",
                    description=f"PC#-#Compare {var_nm} == {expect_s}",
                    test_id="CACK182",
                ))
            else:
                dl = str(cfg.get("dl") if cfg.get("dl") is not None else "0").strip() or "0"
                ul = str(cfg.get("ul") if cfg.get("ul") is not None else "100").strip() or "100"
                vtype = str(cfg.get("val_type") or "%f").strip()
                if vtype not in ("%f", "%d"):
                    vtype = "%f"
                if use_ini:
                    g_scr[f"{var_nm}_DL"] = dl
                    g_scr[f"{var_nm}_UL"] = ul
                    dl_tok = f"*$({var_nm}_DL)"
                    ul_tok = f"*$({var_nm}_UL)"
                else:
                    dl_tok, ul_tok = dl, ul
                steps.append(_step(
                    phase=ph,
                    title=f"0,{title_lbl}",
                    send=f':CheckLimit,"*({var_nm})","{dl_tok}","{ul_tok}","{vtype}"',
                    reply="0",
                    exec_mode="0",
                    description=f"PC#-#Check {var_nm} ({dl}~{ul})",
                    test_id="CACK182",
                ))

        elif kind == "math_opr":
            opr_mode = str(cfg.get("opr_mode") or "set_opr_val").strip().lower()
            title_lbl = str(cfg.get("title") or "Math / Variable Operation").strip() or "Math / Variable Operation"
            var_nm = _safe_var(cfg.get("var_name") or "gCalc", "gCalc")
            val_expr = ""
            if cfg.get("validation_enabled"):
                v_var = _safe_var(cfg.get("val_var") or var_nm, var_nm)
                vtype = str(cfg.get("val_type") or "%f").strip()
                if vtype not in ("%f", "%d", "%s", "%SELF"):
                    vtype = "%f"
                dl = str(cfg.get("dl") if cfg.get("dl") is not None else "0").strip()
                ul = str(cfg.get("ul") if cfg.get("ul") is not None else dl).strip()
                if bool(cfg.get("use_ini_var", False)) and vtype in ("%f", "%d"):
                    g_scr[f"{v_var}_DL"] = dl
                    g_scr[f"{v_var}_UL"] = ul
                    dl, ul = f"*$({v_var}_DL)", f"*$({v_var}_UL)"
                else:
                    _register_ini_tokens(dl, g_scr, "0")
                    _register_ini_tokens(ul, g_scr, "0")
                val_expr = f"({v_var},{vtype},{dl},{ul});"
            ph = _alloc_phase()
            if opr_mode == "conversion":
                conv_type = str(cfg.get("conv_mode") or "H2D").strip() or "H2D"
                src_expr = str(cfg.get("src_expr") or "*(rawHex)").strip() or "*(rawHex)"
                _register_ini_tokens(src_expr, g_scr, "0")
                steps.append(_step(
                    phase=ph, title=f"0,{title_lbl}",
                    send=f':Utility.ConVersion,"{conv_type}","{src_expr}"',
                    reply="0", ref=f"${var_nm};", validation=val_expr,
                    exec_mode="0", description=f"PC#-#Convert {conv_type} -> {var_nm}", test_id="B7PL025",
                ))
            elif opr_mode == "set_cdti_val":
                lhs = str(cfg.get("var1") or f"*({var_nm})").strip()
                op = str(cfg.get("op") or ">").strip() or ">"
                rhs = str(cfg.get("var2") or "0").strip()
                tval = str(cfg.get("true_val") if cfg.get("true_val") is not None else "1").strip()
                _register_ini_tokens(lhs, g_scr, "0")
                _register_ini_tokens(rhs, g_scr, "0")
                steps.append(_step(
                    phase=ph, title=f"0,{title_lbl}",
                    send=f':SetCdtiVal,"{lhs}","{op}","{rhs}","{var_nm}","{tval}"',
                    reply=str(cfg.get("reply") if cfg.get("reply") is not None else "").strip(),
                    validation=val_expr, exec_mode="0",
                    description=f"PC#-#Condition {var_nm} = ({lhs} {op} {rhs} ? {tval})", test_id="B7PL025",
                ))
            elif opr_mode == "math":
                v1 = str(cfg.get("var1") or f"*({var_nm})").strip()
                op = str(cfg.get("op") or "+").strip() or "+"
                v2 = str(cfg.get("var2") or "1").strip()
                _register_ini_tokens(v1, g_scr, "0")
                _register_ini_tokens(v2, g_scr, "0")
                steps.append(_step(
                    phase=ph, title=f"0,{title_lbl}",
                    send=f':Utility.MATH,"{v1}","{op}","{v2}"',
                    reply="0", ref=f"${var_nm};", validation=val_expr,
                    exec_mode="0", description=f"PC#-#MATH {v1} {op} {v2} -> {var_nm}", test_id="B7PL025",
                ))
            else:
                expr = str(cfg.get("expr") or "*(A)-*(B)").strip() or "0"
                _register_ini_tokens(expr, g_scr, "0")
                var_target = f"${var_nm}" if cfg.get("prefix_dollar") else var_nm
                steps.append(_step(
                    phase=ph, title=f"0,{title_lbl}",
                    send=f':SetOprVal,"{var_target}","{expr}"',
                    reply="0", validation=val_expr,
                    exec_mode="0", description=f"PC#-#SetOprVal {var_target} = {expr}", test_id="B7PL025",
                ))

        elif kind == "inst":
            # Defer insertion so phase order matches sequence via a placeholder marker
            marker_ph = _alloc_phase()
            placeholder_id = f"__INST_SLOT_{len(deferred_inst_blocks)}__"
            steps.append(_step(
                phase=marker_ph,
                title=placeholder_id,
                send=':Delay,"0"',
                reply="0",
                exec_mode="0",
            ))
            deferred_inst_blocks.append((placeholder_id, marker_ph, cfg))

        elif kind == "multi_sku":
            if isinstance(cfg.get("sku_wizard"), dict) and cfg["sku_wizard"].get("enabled"):
                extracted_sku_cfg = cfg["sku_wizard"]

        elif kind == "sfis_rw":
            hmi_bundle = cfg.get("sfis_hmi_bundle")
            if isinstance(hmi_bundle, dict) and (hmi_bundle.get("items") or []):
                if _apply_sfis_hmi_bundle(hmi_bundle, cfg, is_route=False):
                    has_phase0 = True
            else:
                rw_mode = str(cfg.get("rw_mode") or "get_version").strip().lower()
                field_nm = str(cfg.get("field_name") or "MAC1").strip() or "MAC1"
                out_var = _safe_var(cfg.get("var_name") or f"sf_{field_nm}", "sfField")
                title_lbl = str(cfg.get("title") or f"SFIS {field_nm}").strip()
                ph = _alloc_phase()
                ref_mode = str(cfg.get("ref_slice_mode") or "raw").strip().lower()
                if ref_mode == "split":
                    s_sep = str(cfg.get("ref_split_sep") or ",").strip()
                    s_idx = str(cfg.get("ref_split_idx") or "0").strip() or "0"
                    sf_ref = f'${out_var}:SplitString,"{s_sep}","{s_idx}";'
                elif ref_mode == "sub":
                    sb_s = str(cfg.get("ref_sub_start") or "0").strip() or "0"
                    sb_l = str(cfg.get("ref_sub_len") or "12").strip() or "12"
                    sf_ref = f'${out_var}:SubString,"{sb_s}","{sb_l}";'
                elif ref_mode == "within":
                    w_l = str(cfg.get("ref_left") or "")
                    w_r = str(cfg.get("ref_right") or ";")
                    sf_ref = f'${out_var}:WithinString,"{w_l}","{w_r}","";'
                else:
                    sf_ref = f"${out_var};"

                if rw_mode == "save_link":
                    val_expr = str(cfg.get("save_value") or f"*({out_var})").strip()
                    steps.append(_step(
                        phase=ph,
                        title=f"0,{title_lbl}",
                        send=f':SfSaveLinkData,"{field_nm}","{val_expr}"',
                        reply="0",
                        waiting="2000",
                        exec_mode="8",
                        description=f"SFIS#-#SaveLinkData {field_nm}",
                        test_id="OTFX085",
                    ))
                elif rw_mode == "scan_label":
                    lbl_len = str(cfg.get("label_len") or "12").strip() or "12"
                    steps.append(_step(
                        phase=ph,
                        title=f"0,{title_lbl},3",
                        send=':Delay,"10"',
                        reply="0",
                        ref=sf_ref,
                        validation=f"({out_var},%len,{lbl_len},{lbl_len});",
                        prompt=f"請掃描 {field_nm} ({lbl_len} 碼)",
                        exec_mode="1",
                        description=f"OP#-#Scan {field_nm}",
                        test_id="CACK180",
                    ))
                elif rw_mode == "get_imac":
                    steps.append(_step(
                        phase=ph,
                        title=f"0,{title_lbl}",
                        send=':SfGetiMAC,"*(ISN)","1","1","2"',
                        reply="",
                        ref=sf_ref,
                        validation=f"({out_var},%len,12,12);",
                        waiting="2000",
                        exec_mode="8",
                        description="SFIS#-#Get iMAC",
                        test_id="OTFX085",
                    ))
                else:
                    table_nm = str(cfg.get("table_name") or "ISN_BASEINFO").strip() or "ISN_BASEINFO"
                    steps.append(_step(
                        phase=ph,
                        title=f"0,{title_lbl}",
                        send=f':SfGetVersion,"*(ISN)","{table_nm}","2","{field_nm}",""',
                        reply="",
                        ref=sf_ref,
                        validation=f"({out_var},%len,1,64);",
                        waiting="2000",
                        exec_mode="8",
                        description=f"SFIS#-#GetVersion ({table_nm} {field_nm})",
                        test_id="OTFX085",
                    ))

        elif kind == "sfis_upload":
            title_lbl = str(cfg.get("title") or "Update SFIS").strip() or "Update SFIS"
            upload_items = cfg.get("items")
            if not isinstance(upload_items, list) or not upload_items:
                upload_items = [{"field": str(cfg.get("field_name") or "SN1"), "var_name": str(cfg.get("var_name") or "gCmdOut")}]
            ph = _alloc_phase()
            for u_idx, u_it in enumerate(upload_items):
                if not isinstance(u_it, dict):
                    continue
                u_field = str(u_it.get("field") or "SN1").strip() or "SN1"
                raw_var = str(u_it.get("var_name") or "gCmdOut").strip()
                if raw_var.startswith("*(") or raw_var.startswith("*$("):
                    u_expr = raw_var
                else:
                    clean_v = _safe_var(raw_var.lstrip("$"), "gCmdOut")
                    u_expr = f"*({clean_v})"
                steps.append(_step(
                    phase=ph if u_idx == 0 else "",
                    title=f"0,{title_lbl}" if u_idx == 0 else "",
                    send=f':SfSaveLinkData,"{u_field}","{u_expr}"',
                    reply="0",
                    waiting="2000",
                    exec_mode="8",
                    description=f"SFIS#-#SaveLinkData {u_field}",
                    test_id="OTFX063",
                ))

        elif kind == "python":
            _ensure_dut_connection(
                ws, "CmdConsole", lambda _sl: '"APP","CmdConsole","C:\\Windows\\System32\\cmd.exe,0,5000,"'
            )
            local_wiz = dict(wizard_config or {})
            local_wiz["python_config"] = {
                "python_path": cfg.get("python_path") or "D:\\PythonScript",
                "script_name": cfg.get("script_name") or "my_test.py",
                "result_prefix": cfg.get("result_prefix") or "RESULT=",
                "min_val": cfg.get("min_val") if cfg.get("min_val") is not None else "0.0",
                "max_val": cfg.get("max_val") if cfg.get("max_val") is not None else "100.0",
            }
            custom = build_wizard_block_steps_fn("BLK_PYTHON_SCRIPT_CALL", blk_map.get("BLK_PYTHON_SCRIPT_CALL"), local_wiz, ws)
            if custom:
                custom[0]["Phase"] = _alloc_phase()
                steps.extend(custom)

        elif kind == "ping":
            dip = str(cfg.get("dut_ip") or g_set.get("DUTIP_1") or "192.168.11.143").strip()
            pip = str(cfg.get("pc_ip") or g_set.get("PCIP_1") or "192.168.11.3").strip()
            tmo = str(cfg.get("timeout_ms") or "5000").strip() or "5000"
            g_set["DUTIP_1"] = dip
            g_set["PCIP_1"] = pip
            g_scr["DUTIP_1"] = dip
            g_scr["PCIP_1"] = pip
            ph = _alloc_phase()
            steps.append(_step(
                phase=ph,
                title="0,LAN Ping Test,5",
                send=f':Utility.Ping,"{dip}","{tmo}","{pip}"',
                reply="0",
                ref="$PingRes_1",
                exec_mode="1",
                description=f"PC#-#Ping {dip}",
                test_id="IOPI113",
            ))

        elif kind == "ext_file":
            fmode = str(cfg.get("file_mode") or "rini").strip().lower()
            fpath = str(cfg.get("file_path") or ".\\System\\config.ini").strip()
            out_v = _safe_var(cfg.get("var_name") or "gExtVal", "gExtVal")
            ph = _alloc_phase()
            if fmode == "rtxt":
                steps.append(_step(
                    phase=ph,
                    title=f"0,Read TXT ({out_v})",
                    send=f':Utility.Rtxt,"{fpath}","-1"',
                    reply="0",
                    ref=f"${out_v}",
                    exec_mode="1",
                    description="PC#-#Read External TXT",
                    test_id="IPPR005",
                ))
            else:
                sec_nm = str(cfg.get("section") or "Scripts").strip() or "Scripts"
                key_nm = str(cfg.get("key") or "TargetKey").strip() or "TargetKey"
                steps.append(_step(
                    phase=ph,
                    title=f"0,Read INI ({key_nm})",
                    send=f':Utility.Rini,"{fpath}","{sec_nm}","{key_nm}"',
                    reply="0",
                    ref=f"${out_v}",
                    exec_mode="1",
                    description=f"PC#-#Read INI [{sec_nm}] {key_nm}",
                    test_id="IPPR005",
                ))

        elif kind == "set_val":
            vname = _safe_var(cfg.get("var_name") or "gTag", "gTag")
            vexpr = str(cfg.get("value_expr") or "*(ISN)").strip()
            title_lbl = str(cfg.get("title") or f"Set {vname}").strip()
            steps.append(_step(
                phase=_alloc_phase(),
                title=f"0,{title_lbl}",
                send=f':SetVal,"${vname}","{vexpr}"',
                reply="0",
                exec_mode="0",
                description=f"PC#-#Set ${vname} = {vexpr}",
                test_id="OTFX054",
            ))

        elif kind == "add_attr":
            target_obj = str(cfg.get("target") or "UART").strip() or "UART"
            attr_k = str(cfg.get("attr_key") or "COM").strip() or "COM"
            attr_v = str(cfg.get("attr_val") or "*(comPort)").strip()
            title_lbl = str(cfg.get("title") or f"Bind {target_obj} {attr_k}").strip()
            steps.append(_step(
                phase=_alloc_phase(),
                title=f"0,{title_lbl}",
                send=f':AddAttribute,"{target_obj}","{attr_k}","{attr_v}"',
                reply="0",
                exec_mode="0",
                description=f"PC#-#AddAttribute {target_obj}.{attr_k}",
                test_id="OTFX15D",
            ))

        elif kind in ("usb_fw", "subdev_finalgo", "sfis_bypass", "stream_flash"):
            bid_map = {
                "usb_fw": "BLK_USB_FW_UPGRADE_COM",
                "subdev_finalgo": "BLK_SUBDEV_DEVUART_FINALGO",
                "sfis_bypass": "BLK_SFIS_ENABLED_BRANCH",
                "stream_flash": "BLK_FW_STREAM_PROMPT_FLASH",
            }
            if kind == "sfis_bypass":
                _ensure_dut_connection(
                    ws, "UART", lambda sl: f'"Uart","UART","*$(DUT_UR{sl}),115200,8,One,None,None,10000,5000"'
                )
            _append_standard_block_steps(bid_map[kind], blk_map, wizard_config, ws, steps, next_phase)

        elif kind == "dll_call":
            dmode = str(cfg.get("dll_mode") or "custom_dll").strip().lower()
            title_lbl = str(cfg.get("title") or "DLL / Utility Step").strip() or "DLL / Utility Step"
            ph = _alloc_phase()
            if dmode == "utility":
                uact = str(cfg.get("util_action") or "gen_dt").strip().lower()
                if uact == "get_com":
                    port_id = str(cfg.get("port_id") or "*$(PortID)").strip() or "*$(PortID)"
                    _register_ini_tokens(port_id, g_scr, "Port_#0001.Hub_#0001")
                    com_idx = str(cfg.get("com_idx") or "1").strip() or "1"
                    tgt_alias = _safe_var(cfg.get("target_alias") or "UART", "UART")
                    if tgt_alias != "UART":
                        _ensure_dut_connection(
                            ws, tgt_alias, lambda sl, a=tgt_alias: f'"Uart","{a}","*$({a}_UR{sl}),115200,8,One,None,None,10000,5000"'
                        )
                    steps.extend([
                        _step(phase=ph, title=f"0,{title_lbl}", send=f':Utility.GetCOM,"{port_id}","{com_idx}"', reply="0",
                              ref="$comPort", exec_mode="2:0", description="PC#-#Get Dynamic COM", test_id="NBOT043"),
                        _step(send=f':AddAttribute,"{tgt_alias}","COM","*(comPort)"', reply="0", waiting="500",
                              exec_mode="0", description=f"PC#-#Bind {tgt_alias} COM", test_id="NBOT043"),
                        _step(send=f':Parameter,"{tgt_alias}"', reply="*(comPort)", exec_mode="0",
                              description=f"PC#-#Verify {tgt_alias} Param", test_id="NBOT043"),
                        _step(send=f':Connect,"{tgt_alias}"', reply="0", waiting="500", exec_mode="2:1",
                              description=f"PC#-#Open {tgt_alias}", test_id="OTFX117"),
                    ])
                elif uact == "get_chain_com":
                    port_id = str(cfg.get("port_id") or "*$(PortID)").strip() or "*$(PortID)"
                    _register_ini_tokens(port_id, g_scr, "Port_#0001.Hub_#0001")
                    com_idx = str(cfg.get("com_idx") or "1").strip() or "1"
                    out_v = _safe_var(cfg.get("var_name") or "comPort", "comPort")
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}",
                        send=f':Utility.GetChainCOM,"{port_id}","{com_idx}"',
                        reply="0", ref=f"${out_v}", exec_mode="0",
                        description="PC#-#Get Chain COM Port", test_id="NBOT043",
                    ))
                elif uact == "cfile":
                    src_p = str(cfg.get("src_path") or ".\\capture\\shot.bmp").strip()
                    dst_p = str(cfg.get("dst_path") or ".\\Record\\shot.bmp").strip()
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':Utility.CFile,"{src_p}","{dst_p}"',
                        reply="0", exec_mode="1", description=f"PC#-#Copy File ({title_lbl})", test_id="IOCD041",
                    ))
                elif uact == "fchksum":
                    fdir = str(cfg.get("file_dir") or ".\\API").strip()
                    fname = str(cfg.get("file_name") or "sample.ini").strip()
                    exp_md5 = str(cfg.get("expect_md5") or "*$(sampleMD5)").strip()
                    _register_ini_tokens(exp_md5, g_scr, "")
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':Utility.fChkSum,"MD5","{fdir}","{fname}"',
                        reply="0", ref="$fMD5", validation=f"(fMD5,%s,{exp_md5},)", exec_mode="1",
                        description=f"PC#-#Check MD5 ({fname})", test_id="OTFX076",
                    ))
                elif uact == "show_img":
                    img_f = str(cfg.get("img_file") or "Loimage.gif").strip()
                    wait_ms = str(cfg.get("waiting") or "").strip()
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':ShowImageMessage,"{img_f}","0"',
                        reply="0", waiting=wait_ms, exec_mode="1",
                        description=f"PC#-#Show Image ({img_f})", test_id="B7PL025",
                    ))
                elif uact == "close_msg":
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=":CloseMessage",
                        reply="0", exec_mode="0", description="PC#-#Close Prompt / Image Message", test_id="B7PL025",
                    ))
                elif uact == "chk_len":
                    src_var = str(cfg.get("src_expr") or "*(rawData)").strip() or "*(rawData)"
                    exp_len = str(cfg.get("expect_len") if cfg.get("expect_len") is not None else "70").strip()
                    wait_ms = str(cfg.get("waiting") or "").strip()
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':Utility.ChkLEN,"{src_var}","{exp_len}"',
                        reply="0", waiting=wait_ms, exec_mode="0",
                        description=f"PC#-#Check String Length == {exp_len}", test_id="OTKS001",
                    ))
                elif uact == "sf_enabled":
                    out_v = _safe_var(cfg.get("var_name") or "gSFIS", "gSFIS")
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=":SfEnabled",
                        reply="@", ref=out_v, exec_mode="0",
                        description="PC#-#Check SFIS Enabled Status", test_id="B7PL025",
                    ))
                elif uact == "cmd":
                    exe_p = str(cfg.get("cmd_exe") or "{0}\\SPT_repeater.exe").strip()
                    exe_args = str(cfg.get("cmd_args") or "").strip()
                    show_f = str(cfg.get("cmd_show") if cfg.get("cmd_show") is not None else "ON").strip()
                    wait_ms = str(cfg.get("waiting") or "10000").strip() or "10000"
                    extra_f = str(cfg.get("cmd_extra") if cfg.get("cmd_extra") is not None else "5").strip()
                    _register_ini_tokens(exe_p, g_scr, "")
                    _register_ini_tokens(exe_args, g_scr, "")
                    send_u = f':Utility.CMD,"{exe_p}","{exe_args}","{show_f or "ON"}","{wait_ms}","{extra_f or "0"}"' if (show_f or extra_f) else f':Utility.CMD,"{exe_p}","{exe_args}"'
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=send_u,
                        reply=str(cfg.get("reply") if cfg.get("reply") is not None else "0").strip(),
                        ref=str(cfg.get("ref") or "").strip(), waiting=wait_ms, exec_mode="1",
                        description=f"PC#-#Utility.CMD ({exe_p})", test_id="OTFX054",
                    ))
                elif uact == "kill_pro":
                    proc_nm = str(cfg.get("proc_name") or "adb.exe").strip() or "adb.exe"
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':Utility.KillPro,"{proc_nm}"',
                        reply="0", exec_mode="0", description=f"PC#-#Kill Process ({proc_nm})", test_id="B7PL025",
                    ))
                elif uact == "string_scan":
                    src_p = str(cfg.get("src_path") or ".\\log.txt").strip()
                    s_key = str(cfg.get("scan_key") or "PASS").strip()
                    out_v = _safe_var(cfg.get("var_name") or "sScanOut", "sScanOut")
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':Utility.StringScan,"{src_p}","{s_key}"',
                        reply="0", ref=f"${out_v}", exec_mode="1", description=f"PC#-#StringScan ({s_key})", test_id="B7PL025",
                    ))
                elif uact == "wini":
                    ini_p = str(cfg.get("ini_file") or ".\\Config\\custom.ini").strip()
                    sec_n = str(cfg.get("ini_section") or "Settings").strip()
                    key_n = str(cfg.get("ini_key") or "Key1").strip()
                    val_n = str(cfg.get("ini_val") or "1").strip()
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':Utility.wIni,"{ini_p}","{sec_n}","{key_n}","{val_n}"',
                        reply="0", exec_mode="0", description=f"PC#-#Write INI {sec_n}/{key_n}", test_id="B7PL025",
                    ))
                elif uact == "conversion":
                    conv_mode = str(cfg.get("conv_mode") or "H2D").strip() or "H2D"
                    src_expr = str(cfg.get("src_expr") or "*(rawHex)").strip() or "*(rawHex)"
                    out_v = _safe_var(cfg.get("var_name") or "gDecVal", "gDecVal")
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':Utility.ConVersion,"{conv_mode}","{src_expr}"',
                        reply="0", ref=f"${out_v}", validation=str(cfg.get("validation") or "").strip(),
                        exec_mode="0", description=f"PC#-#ConVersion {conv_mode} -> {out_v}", test_id="B7PL025",
                    ))
                elif uact == "set_opr_val":
                    out_v = _safe_var(cfg.get("var_name") or "gCalc", "gCalc")
                    expr = str(cfg.get("expr") or "*(A)-*(B)").strip() or "0"
                    _register_ini_tokens(expr, g_scr, "0")
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':SetOprVal,"{out_v}","{expr}"',
                        reply="0", validation=str(cfg.get("validation") or "").strip(),
                        exec_mode="0", description=f"PC#-#SetOprVal {out_v}={expr}", test_id="B7PL025",
                    ))
                elif uact == "set_cdti_val":
                    lhs = str(cfg.get("var1") or "*(A)").strip()
                    op = str(cfg.get("op") or ">").strip()
                    rhs = str(cfg.get("var2") or "0").strip()
                    dst_v = _safe_var(cfg.get("var_name") or "gCond", "gCond")
                    tval = str(cfg.get("true_val") if cfg.get("true_val") is not None else "1").strip()
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':SetCdtiVal,"{lhs}","{op}","{rhs}","{dst_v}","{tval}"',
                        reply=str(cfg.get("reply") if cfg.get("reply") is not None else "").strip(),
                        validation=str(cfg.get("validation") or "").strip(),
                        exec_mode="0", description=f"PC#-#SetCdtiVal {dst_v}", test_id="B7PL025",
                    ))
                elif uact == "util_math":
                    v1 = str(cfg.get("var1") or "*(A)").strip()
                    op = str(cfg.get("op") or "+").strip()
                    v2 = str(cfg.get("var2") or "1").strip()
                    out_v = _safe_var(cfg.get("var_name") or "gMath", "gMath")
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':Utility.MATH,"{v1}","{op}","{v2}"',
                        reply="0", ref=f"${out_v}", validation=str(cfg.get("validation") or "").strip(),
                        exec_mode="0", description=f"PC#-#MATH {v1} {op} {v2}", test_id="B7PL025",
                    ))
                elif uact == "get_yr":
                    out_v = _safe_var(cfg.get("var_name") or "currYR", "currYR")
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=":GetYR",
                        reply="@", ref=f"${out_v}", exec_mode="0", description="PC#-#Get Year", test_id="B7PL025",
                    ))
                else:
                    # gen_dt default
                    dt_fmt = str(cfg.get("dt_fmt") or "yyyyMMddhhmmss").strip() or "yyyyMMddhhmmss"
                    out_v = _safe_var(cfg.get("var_name") or "sDATE1", "sDATE1")
                    steps.append(_step(
                        phase=ph, title=f"0,{title_lbl}", send=f':Utility.GenDT,"{dt_fmt}"',
                        reply="0", ref=f"${out_v}", exec_mode="0", description="PC#-#Get Current DTS", test_id="NBOT001",
                    ))
            else:
                dll_file = str(cfg.get("dll_file") or "AutLabs.dll").strip() or "AutLabs.dll"
                dll_alias = _safe_var(cfg.get("dll_alias") or "autLabs", "autLabs")
                init_arg = str(cfg.get("init_arg") or "").strip()
                send_cmd = str(cfg.get("send_cmd") or f":{dll_alias}.Active,\"*(ISN)\",\"1\",\"Step\"").strip()
                reply_s = str(cfg.get("reply") if cfg.get("reply") is not None else "0").strip()
                ref_s = str(cfg.get("ref") or "").strip()
                val_s = str(cfg.get("validation") or "").strip()
                wait_s = str(cfg.get("waiting") or "").strip()
                _register_ini_tokens(init_arg, g_set, "1")
                _register_ini_tokens(send_cmd, g_scr, "1")
                _register_ini_tokens(reply_s, g_scr, "1")
                _ensure_dut_connection(
                    ws, dll_alias, lambda _sl, df=dll_file, da=dll_alias, ia=init_arg: f'"DLL:{df}","{da}","{ia}"'
                )
                steps.append(_step(
                    phase=ph, title=f"0,{title_lbl}", send=send_cmd, reply=reply_s,
                    ref=ref_s, validation=val_s, waiting=wait_s, exec_mode="1",
                    description=f"APP#-#{title_lbl}", test_id="IPIO01C" if "%SELF" in val_s else "B7PL025",
                ))

        elif kind == "group":
            children = [c for c in (cfg.get("children") or []) if isinstance(c, dict)]
            if children:
                tmp_ws = {
                    "project_name": ws.get("project_name"),
                    "duts": ws.setdefault("duts", []),
                    "instruments": ws.setdefault("instruments", []),
                    "switches": ws.setdefault("switches", []),
                    "marcos": ws.setdefault("marcos", {}),
                    "global_ini": ws.setdefault("global_ini", {}),
                    "system_ini": ws.setdefault("system_ini", {}),
                    "stations": {},
                }
                _, grp_sku = build_workspace_from_sequence(
                    tmp_ws, station_name, children, wizard_config, build_wizard_block_steps_fn, skip_teardown=True
                )
                if grp_sku and not extracted_sku_cfg:
                    extracted_sku_cfg = grp_sku
                raw_grp_steps = _dedup_group_steps(tmp_ws.get("stations", {}).get(station_name) or [])
                if raw_grp_steps:
                    g_role = str(cfg.get("phase_role") or "normal").strip()
                    same_phase = bool(cfg.get("same_phase", False))
                    g_title = str(cfg.get("title") or "Custom Group").strip() or "Custom Group"
                    g_t_mode = str(cfg.get("title_run_mode") if cfg.get("title_run_mode") is not None else "0").strip() or "0"
                    g_retry = str(cfg.get("retry") or "0").strip()
                    if g_t_mode != "none":
                        _register_ini_tokens(g_t_mode, g_scr, "0")
                        g_title_str = f"{g_t_mode},{g_title},{g_retry}" if g_retry and g_retry != "0" else f"{g_t_mode},{g_title}"
                    else:
                        g_title_str = f"{g_title},{g_retry}" if g_retry and g_retry != "0" else g_title
                    if same_phase:
                        g_ph = ""
                    elif g_role == "0":
                        g_ph = "0"
                        has_phase0 = True
                    elif g_role == "-1":
                        g_ph = "-1"
                    else:
                        g_ph = _alloc_phase()
                    for g_i, gr in enumerate(raw_grp_steps):
                        gr["Phase"] = g_ph if g_i == 0 else ""
                        gr["Title"] = g_title_str if g_i == 0 else ""
                    steps.extend(raw_grp_steps)

        active_phase_role[0] = ""
        # Every action block (except start / end / isn / delay / inst / multi_sku / disabled fixture) supports optional post-block Delay row
        skip_post_delay = (
            kind in ("start", "end", "isn", "delay", "inst", "multi_sku")
            or (kind == "fixture" and str(cfg.get("fixture_type") or "none").strip().lower() == "none")
        )
        if kind not in ("start", "isn", "group", "teardown", "end", "sfis_route", "multi_sku", "inst") and len(steps) > step_start_idx:
            if req_role in ("0", "-1", "same"):
                steps[step_start_idx]["Phase"] = "" if req_role == "same" else req_role
                if req_role == "0":
                    has_phase0 = True
        if kind != "inst" and cfg.get("test_id"):
            _apply_custom_test_id(steps[step_start_idx:], cfg.get("test_id"))
        if kind != "inst" and cfg.get("exec_mode"):
            _apply_custom_exec_mode(steps[step_start_idx:], cfg.get("exec_mode"), g_scr=g_scr, g_set=g_set)
        if kind not in ("inst", "group") and (cfg.get("title_run_mode") is not None or cfg.get("title_retry") is not None):
            _apply_custom_title(steps[step_start_idx:], cfg.get("title_run_mode"), cfg.get("title_retry"), g_scr=g_scr)
        if not skip_post_delay and cfg.get("post_delay_enabled"):
            try:
                sec = float(cfg.get("post_delay_sec") if cfg.get("post_delay_sec") is not None else 0.5)
            except (ValueError, TypeError):
                sec = 0.5
            if sec > 0:
                ms_val = max(1, int(round(sec * 1000)))
                steps.append(_step(
                    send=f':Delay,"{ms_val}"',
                    reply="0",
                    exec_mode="0",
                    description=f"PC#-#Post-Block Delay ({sec:g}s)",
                    test_id="B7PL025",
                ))

    # Append Teardown block(s) + custom Phase 97 / 97:PWROFF / 98 / 99 groups at the end unless running inside a group box
    if not skip_teardown:
        td_by_role = {}
        for tg in teardown_groups:
            tcfg = tg.get("config") or {}
            role = str(tcfg.get("phase_role") or "97").strip()
            tchs = [c for c in (tcfg.get("children") or []) if isinstance(c, dict)]
            if tchs:
                tmp_td = {
                    "project_name": ws.get("project_name"),
                    "duts": ws.setdefault("duts", []),
                    "instruments": ws.setdefault("instruments", []),
                    "switches": ws.setdefault("switches", []),
                    "marcos": ws.setdefault("marcos", {}),
                    "global_ini": ws.setdefault("global_ini", {}),
                    "system_ini": ws.setdefault("system_ini", {}),
                    "stations": {},
                }
                build_workspace_from_sequence(tmp_td, station_name, tchs, wizard_config, build_wizard_block_steps_fn, skip_teardown=True)
                raw_td = _dedup_group_steps(tmp_td.get("stations", {}).get(station_name) or [])
                if raw_td:
                    def_t = {"97:PWROFF": "PWROFF", "97": "DISCONNECTION", "98": "PASS_DISCONNECTION", "99": "FAIL_DISCONNECTION"}.get(role, "DISCONNECTION")
                    g_t = str(tcfg.get("title") or def_t).strip() or def_t
                    t_mode = str(tcfg.get("title_run_mode") if tcfg.get("title_run_mode") is not None else "none").strip()
                    t_retry = str(tcfg.get("retry") or "").strip()
                    if t_mode and t_mode != "none":
                        _register_ini_tokens(t_mode, g_scr, "0")
                        g_title_s = f"{t_mode},{g_t},{t_retry}" if (t_retry and t_retry != "0") else f"{t_mode},{g_t}"
                    else:
                        g_title_s = f"{g_t},{t_retry}" if (t_retry and t_retry != "0") else g_t
                    for gi, gr in enumerate(raw_td):
                        gr["Phase"] = role if gi == 0 else ""
                        gr["Title"] = g_title_s if gi == 0 else ""
                    td_by_role.setdefault(role, []).extend(raw_td)

        td_cfg = (teardown_items[-1].get("config") or {}) if teardown_items else {}
        td_mode = str(td_cfg.get("teardown_mode") or "97_only").strip().lower()
        if "97:PWROFF" in td_by_role:
            steps.extend(td_by_role["97:PWROFF"])
        if "97" in td_by_role:
            steps.extend(td_by_role["97"])
        else:
            for r in (blk_map.get("BLK_PHASE97_TEARDOWN", {}).get("steps") or []):
                steps.append(dict(r))

        if "98" in td_by_role or "99" in td_by_role:
            if "98" in td_by_role:
                steps.extend(td_by_role["98"])
            if "99" in td_by_role:
                steps.extend(td_by_role["99"])
        elif td_mode == "97_98_99":
            for r in (blk_map.get("BLK_PHASE98_99_BRANCH_TEARDOWN", {}).get("steps") or []):
                steps.append(dict(r))

    ws["stations"] = {station_name: steps}

    # Replace deferred instrument placeholders with real instrument blocks in-place
    for placeholder_id, marker_ph, icfg in deferred_inst_blocks:
        cur_steps = ws["stations"][station_name]
        p_idx = next((i for i, r in enumerate(cur_steps) if r.get("Title") == placeholder_id), -1)
        if p_idx < 0:
            continue
        # Remove placeholder and find insertion index (block index just before p_idx)
        cur_steps.pop(p_idx)
        inst_type = str(icfg.get("inst_mode") or "catalog").strip().lower()
        # Find block index after which to insert
        from core.script_doctor import _build_title_blocks
        blks = _build_title_blocks(cur_steps)
        after_blk = -1
        for bi, blk in enumerate(blks):
            if blk["steps"][-1]["global_idx"] < p_idx:
                after_blk = bi
        before_inst_len = len(cur_steps)
        if inst_type == "multi_queue" and isinstance(icfg.get("inst_queue"), list) and icfg.get("inst_queue"):
            cur_after = after_blk
            for q_it in icfg["inst_queue"]:
                if not isinstance(q_it, dict):
                    continue
                if isinstance(q_it.get("ni6009_block"), dict):
                    nb = q_it["ni6009_block"]
                    insert_ni6009_block(
                        ws, station_name,
                        mode=nb.get("mode", "RSE"),
                        sample_ms=str(nb.get("sample_ms", "1000")),
                        dev_id=str(nb.get("dev_id", "Dev1")),
                        title_name=str(nb.get("title_name") or q_it.get("title_name") or "Measure Voltage Test"),
                        channels=nb.get("channels") or [],
                        after_block_idx=cur_after,
                    )
                elif isinstance(q_it.get("rf_block"), dict):
                    rb = q_it["rf_block"]
                    insert_rf_iqxel_block(
                        ws, station_name,
                        inst_name=str(rb.get("inst_name") or q_it.get("inst_name") or "InstIQApiA"),
                        title_name=str(rb.get("title_name") or q_it.get("title_name") or "WIFI RF Test"),
                        settings_str=str(rb.get("settings_str") or ""),
                        tx_tests=rb.get("tx_tests") or [],
                        rx_tests=rb.get("rx_tests") or [],
                        after_block_idx=cur_after,
                    )
                else:
                    q_inst = str(q_it.get("inst_name") or "PPH1503").strip() or "PPH1503"
                    insert_instrument_title_block(
                        ws, station_name, q_inst,
                        str(q_it.get("title_name") or f"{q_inst} Test").strip(),
                        after_block_idx=cur_after,
                        dl_val=str(q_it.get("dl_val") or "").strip(),
                        ul_val=str(q_it.get("ul_val") or "").strip(),
                        custom_steps=q_it.get("custom_steps"),
                        globals_patch=q_it.get("globals_patch"),
                    )
                cur_after += 1
        elif inst_type == "ni6009":
            channels = icfg.get("channels") or [
                {"ch": 0, "name": "VCC_5V", "dl": "4.75", "ul": "5.25"},
                {"ch": 1, "name": "VCC_3V3", "dl": "3.15", "ul": "3.45"},
            ]
            insert_ni6009_block(
                ws, station_name,
                mode=icfg.get("mode", "RSE"),
                sample_ms=str(icfg.get("sample_ms", "1000")),
                dev_id=str(icfg.get("dev_id", "Dev1")),
                title_name=str(icfg.get("title_name") or "Measure Voltage Test"),
                channels=channels,
                after_block_idx=after_blk,
            )
        elif inst_type == "rf":
            insert_rf_iqxel_block(
                ws, station_name,
                inst_name=str(icfg.get("inst_name") or "InstIQApiA"),
                title_name=str(icfg.get("title_name") or "WIFI RF Test"),
                settings_str=str(icfg.get("settings_str") or ""),
                tx_tests=icfg.get("tx_tests") or [],
                rx_tests=icfg.get("rx_tests") or [],
                after_block_idx=after_blk,
            )
        else:
            inst_nm = str(icfg.get("inst_name") or "PPH1503").strip() or "PPH1503"
            c_steps = icfg.get("custom_steps")
            g_patch = icfg.get("globals_patch")
            if not c_steps:
                low_nm = inst_nm.lower()
                dl_s = str(icfg.get("dl_val") or "").strip()
                ul_s = str(icfg.get("ul_val") or "").strip()
                if "feasa" in low_nm:
                    l_ch = str(icfg.get("led_ch") or "01").strip() or "01"
                    w_dl = dl_s or "515"
                    w_ul = ul_s or "535"
                    i_dl = str(icfg.get("led_int_min") or "1000").strip() or "1000"
                    i_ul = str(icfg.get("led_int_max") or "99999").strip() or "99999"
                    c_steps = [
                        {"Send": ":ObtainDevice", "ExecMode": "0", "Description": f"PC#-#Obtain {inst_nm}", "TestID": "BRME027"},
                        {
                            "Send": f':Dev.CaptureAndRead,"{l_ch}"',
                            "Ref": "$LED_Wave;\n$LED_Int",
                            "Validation": f"(LED_Wave,%f,{w_dl},{w_ul});\n(LED_Int,%f,{i_dl},{i_ul})",
                            "ExecMode": "2:0",
                            "Description": f"LED#-#Ch{l_ch} ({w_dl}~{w_ul}nm)",
                            "TestID": "IOLE015",
                        },
                        {"Send": ":ReleaseDevice", "ExecMode": "3", "Description": f"PC#-#Release {inst_nm}", "TestID": "BRME027"},
                    ]
                elif any(k in low_nm for k in ("pph1503", "ps2005", "ipower", "ipro", "keithley2302", "chroma615")):
                    p_act = str(icfg.get("pwr_action") or "on").strip().lower()
                    p_ch = str(icfg.get("pwr_ch") or "1").strip() or "1"
                    p_volt = str(icfg.get("pwr_volt") or "12").strip() or "12"
                    p_wait = str(icfg.get("pwr_wait_ms") or "500").strip() or "500"
                    is_pph = "pph1503" in low_nm
                    is_ps2005 = "ps2005" in low_nm
                    c_steps = [{"Send": ":ObtainDevice", "ExecMode": "1", "Description": f"PC#-#Obtain {inst_nm}"}]
                    if p_act == "cycle":
                        off_cmd = ':Dev.OUTONOFF,"OFF"' if is_pph else (':Dev.OutOnOff,"OFF"' if is_ps2005 else f':Dev.SwitchOFF,"{p_ch}"')
                        on_cmd = ':Dev.OUTONOFF,"ON"' if is_pph else (':Dev.OutOnOff,"ON"' if is_ps2005 else f':Dev.SwitchON,"{p_ch}"')
                        c_steps.extend([
                            {"Send": off_cmd, "ExecMode": "1", "Description": f"Power#-#{inst_nm} OFF"},
                            {"Send": f':Delay,"{p_wait}"', "ExecMode": "0", "Description": "PC#-#Wait Power Discharge"},
                            {"Send": on_cmd, "ExecMode": "1", "Description": f"Power#-#{inst_nm} ON"},
                        ])
                    elif p_act == "off":
                        off_cmd = ':Dev.OUTONOFF,"OFF"' if is_pph else (':Dev.OutOnOff,"OFF"' if is_ps2005 else f':Dev.SwitchOFF,"{p_ch}"')
                        c_steps.append({"Send": off_cmd, "ExecMode": "1", "Description": f"Power#-#{inst_nm} Power OFF"})
                    elif p_act in ("mcurr", "mscurr"):
                        m_dl = dl_s or "50"
                        m_ul = ul_s or "800"
                        _register_ini_tokens(p_volt, g_set, "12")
                        meas_cmd = ':Dev.MSCurr' if p_act == "mscurr" else (':Dev.MCurr' if is_pph else f':Dev.Measure,"{p_ch}"')
                        c_steps.extend([
                            {"Send": f':Dev.SetON,"{p_volt}","2"' if is_pph else f':Dev.SwitchON,"{p_ch}"', "ExecMode": "1", "Description": f"Power#-#Set {p_volt}V ON"},
                            {"Send": f':Delay,"{p_wait}"', "ExecMode": "0", "Description": "PC#-#Stabilize Current"},
                            {"Send": meas_cmd, "Ref": "$gCurr", "Validation": f"(gCurr,%f,{m_dl},{m_ul})", "ExecMode": "2:0", "Description": f"Power#-#Check Current ({m_dl}~{m_ul})"},
                        ])
                    else:
                        _register_ini_tokens(p_volt, g_set, "12")
                        on_cmd = f':Dev.SetON,"{p_volt}","2"' if is_pph else (':Dev.OutOnOff,"ON"' if is_ps2005 else f':Dev.SwitchON,"{p_ch}"')
                        c_steps.append({"Send": on_cmd, "ExecMode": "1", "Description": f"Power#-#{inst_nm} Power ON"})
                    c_steps.append({"Send": ":ReleaseDevice", "ExecMode": "3", "Description": f"PC#-#Release {inst_nm}"})
                elif any(k in low_nm for k in ("agilent34401", "keithley2700", "mda2700", "gdm", "u2004a")):
                    d_ch = str(icfg.get("dmm_ch") or "1").strip() or "1"
                    d_dl = dl_s or "3.15"
                    d_ul = ul_s or "3.45"
                    is_sub_dmm = "keithley2700" in low_nm
                    if is_sub_dmm:
                        c_steps = [
                            {"Send": f':ObtainSubDevice,"{inst_nm}"', "ExecMode": "1", "Description": f"PC#-#Obtain {inst_nm}"},
                            {"Send": f':sDev.Voltage,"{d_ch}"', "Ref": "$gDmmVal", "Validation": f"(gDmmVal,%f,{d_dl},{d_ul})", "ExecMode": "2:0", "Description": f"DMM#-#Ch{d_ch} ({d_dl}~{d_ul})"},
                            {"Send": ":ReleaseSubDevice", "ExecMode": "3", "Description": f"PC#-#Release {inst_nm}"},
                        ]
                    else:
                        c_steps = [
                            {"Send": ":ObtainDevice", "ExecMode": "1", "Description": f"PC#-#Obtain {inst_nm}"},
                            {"Send": f':Dev.Measure,"{d_ch}"', "Ref": "$gDmmVal", "Validation": f"(gDmmVal,%f,{d_dl},{d_ul})", "ExecMode": "2:0", "Description": f"DMM#-#Ch{d_ch} ({d_dl}~{d_ul})"},
                            {"Send": ":ReleaseDevice", "ExecMode": "3", "Description": f"PC#-#Release {inst_nm}"},
                        ]
                elif any(k in low_nm for k in ("devuart", "scpicontroller", "transmitter", "vnxrfsw")):
                    s_cmd = str(icfg.get("subdev_cmd") or (':sDev.Announce,"SAT{1},start"' if "devuart" in low_nm else (':sDev.SetSwitch,"1"' if "vnxrfsw" in low_nm else ':sDev.OnOff,"ON"'))).strip()
                    c_steps = [
                        {"Send": f':ObtainSubDevice,"{inst_nm}"', "ExecMode": "1", "Description": f"PC#-#Obtain {inst_nm}"},
                        {"Send": s_cmd, "ExecMode": "1", "Description": f"SubDev#-#{inst_nm} Command"},
                        {"Send": ":ReleaseSubDevice", "ExecMode": "3", "Description": f"PC#-#Release {inst_nm}"},
                    ]
                elif "fc6000" in low_nm:
                    f_dl = dl_s or "10"
                    f_ul = ul_s or "100"
                    c_steps = [
                        {"Send": ":ObtainDevice", "ExecMode": "1", "Description": f"PC#-#Obtain {inst_nm}"},
                        {"Send": ':Dev.ReadFlow', "Ref": "$gFlow", "Validation": f"(gFlow,%f,{f_dl},{f_ul})", "ExecMode": "2:0", "Description": f"Flow#-#Check Flow ({f_dl}~{f_ul})"},
                        {"Send": ":ReleaseDevice", "ExecMode": "3", "Description": f"PC#-#Release {inst_nm}"},
                    ]
                elif low_nm == "rst" or low_nm.startswith("rst"):
                    c_steps = [
                        {"Send": ":ObtainDevice", "ExecMode": "1", "Description": f"PC#-#Obtain {inst_nm}"},
                        {"Send": ':Dev.Read', "Ref": "$gRstVal", "ExecMode": "2:0", "Description": f"Inst#-#Read {inst_nm}"},
                        {"Send": ":ReleaseDevice", "ExecMode": "3", "Description": f"PC#-#Release {inst_nm}"},
                    ]
            insert_instrument_title_block(
                ws, station_name, inst_nm,
                str(icfg.get("title_name") or f"{inst_nm} Test").strip(),
                after_block_idx=after_blk,
                dl_val=str(icfg.get("dl_val") or "").strip(),
                ul_val=str(icfg.get("ul_val") or "").strip(),
                custom_steps=c_steps,
                globals_patch=g_patch,
            )

        inst_role = str(icfg.get("phase_role") or "").strip()
        if inst_role in ("0", "-1", "same"):
            after_steps = ws["stations"][station_name]
            added_n = len(after_steps) - before_inst_len
            base_pos = 0 if after_blk < 0 else (blks[after_blk]["steps"][-1]["global_idx"] + 1)
            if added_n > 0:
                after_steps[base_pos]["Phase"] = "" if inst_role == "same" else inst_role
        if icfg.get("test_id"):
            after_steps = ws["stations"][station_name]
            added_n = len(after_steps) - before_inst_len
            base_pos = 0 if after_blk < 0 else (blks[after_blk]["steps"][-1]["global_idx"] + 1)
            if added_n > 0:
                _apply_custom_test_id(after_steps[base_pos:base_pos + added_n], icfg.get("test_id"))
        if icfg.get("exec_mode"):
            after_steps = ws["stations"][station_name]
            added_n = len(after_steps) - before_inst_len
            base_pos = 0 if after_blk < 0 else (blks[after_blk]["steps"][-1]["global_idx"] + 1)
            if added_n > 0:
                _apply_custom_exec_mode(after_steps[base_pos:base_pos + added_n], icfg.get("exec_mode"), g_scr=g_scr, g_set=g_set)

        if icfg.get("post_delay_enabled"):
            try:
                sec = float(icfg.get("post_delay_sec") if icfg.get("post_delay_sec") is not None else 0.5)
            except (ValueError, TypeError):
                sec = 0.5
            if sec > 0:
                ms_val = max(1, int(round(sec * 1000)))
                after_steps = ws["stations"][station_name]
                added_n = len(after_steps) - before_inst_len
                base_pos = 0 if after_blk < 0 else (blks[after_blk]["steps"][-1]["global_idx"] + 1)
                delay_insert_pos = min(len(after_steps), max(0, base_pos + max(0, added_n)))
                after_steps.insert(delay_insert_pos, _step(
                    send=f':Delay,"{ms_val}"',
                    reply="0",
                    exec_mode="0",
                    description=f"PC#-#Post-Block Delay ({sec:g}s)",
                    test_id="B7PL025",
                ))

    # Re-sequence contiguous Phases (preserving 0, -1, 97:PWROFF, 97, 98, 99)
    final_steps = ws["stations"][station_name]
    cur_p = 0
    seen_zero = False
    for st_row in final_steps:
        p_raw = str(st_row.get("Phase") or "").strip()
        if p_raw == "":
            continue
        p_head = p_raw.split(":")[0].strip()
        try:
            p_int = int(p_head)
            if p_int >= 95 or p_int < 0:
                continue
            if p_int == 0:
                seen_zero = True
                if cur_p == 0:
                    cur_p = 1
                continue
            if not seen_zero:
                seen_zero = True
                if cur_p == 0:
                    cur_p = 1
            st_row["Phase"] = str(cur_p)
            cur_p += 1
        except ValueError:
            pass

    return ws, extracted_sku_cfg
