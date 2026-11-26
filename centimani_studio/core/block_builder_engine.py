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


def _ensure_dut_connection(ws, alias, conn_str_fn):
    """Ensure every DUT slot has `alias` mounted in Connection1..5 without duplicates."""
    alias_low = str(alias or "").strip().lower()
    if not alias_low:
        return
    conn_cols = [
        "Connection1 (Type,Name,ConnectString)",
        "Connection2 (Type,Name,ConnectString)",
        "Connection3 (Type,Name,ConnectString)",
        "Connection4(Type,Name,ConnectString)",
        "Connection5(Type,Name,ConnectString)",
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


def build_workspace_from_sequence(
    ws,
    station_name,
    sequence,
    wizard_config,
    build_wizard_block_steps_fn,
):
    """
    Build ordered station steps + DUT connections + instruments + INIs from `builder_sequence`.
    Returns `(ws, sku_wizard_override_or_None)`.
    """
    blk_map = {b["block_id"]: b for b in STANDARD_BLOCKS}
    steps = []
    deferred_inst_blocks = []
    extracted_sku_cfg = None
    next_phase = [1]  # phase 0 reserved for sfis_route + optional phase0 fixture
    has_phase0 = False
    g_set = ws.setdefault("global_ini", {}).setdefault("Settings", {})
    g_scr = ws.setdefault("global_ini", {}).setdefault("Scripts", {})

    def _alloc_phase(force_zero=False):
        if force_zero:
            return "0"
        p = str(next_phase[0])
        next_phase[0] += 1
        return p

    # Separate teardown items to always stay at the very end cleanly
    normal_items = [it for it in (sequence or []) if isinstance(it, dict) and it.get("kind") != "teardown"]
    teardown_items = [it for it in (sequence or []) if isinstance(it, dict) and it.get("kind") == "teardown"]

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

        if kind == "isn":
            # Applied on top-level ws metadata & DUTs; no station rows needed
            continue

        elif kind == "sfis_route":
            # Applies System.ini switches and builds Phase 0 CheckRoute (or synced SFIS HMI bundle)
            hmi_bundle = cfg.get("sfis_hmi_bundle")
            if isinstance(hmi_bundle, dict) and (hmi_bundle.get("items") or []):
                if _apply_sfis_hmi_bundle(hmi_bundle, cfg, is_route=True):
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
                _ensure_dut_connection(
                    ws, "UART", lambda sl: f'"Uart","UART","*$(DUT_UR{sl}),115200,8,One,None,None,10000,5000"'
                )
                steps.extend([
                    _step(phase="0", title="0,CheckRoute", send=':ShowISN,"*(ISN)"', reply="0", exec_mode="1",
                          description="PC#-#Display ISN", test_id="B7PL025"),
                    _step(send=':Disconnect,"UART"', reply="0", exec_mode="3",
                          description="PC#-#Ensure UART Closed Before Route", test_id="OTFX082"),
                    _step(send=":SfCheckRoute", reply="0", waiting="2000", exec_mode="8",
                          description="SFIS#-#Check Station Route", test_id="OTFX085"),
                ])
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
            reply_kw = str(cfg.get("reply_keyword") or "PASS").strip()
            var_name = _safe_var(cfg.get("var_name") or "gCmdOut", "gCmdOut")
            val_type = str(cfg.get("val_type") or "%s").strip()
            if val_type not in ("%s", "%f", "%d", "%x"):
                val_type = "%s"
            expect_min = str(cfg.get("expect_min") if cfg.get("expect_min") is not None else "").strip()
            expect_max = str(cfg.get("expect_max") if cfg.get("expect_max") is not None else "").strip()
            use_ini = bool(cfg.get("use_ini_var", False))

            ph = _alloc_phase()
            t_str = f"0,{title_lbl},{retry}" if retry and retry != "0" else f"0,{title_lbl}"

            # Determine connection alias & prefix
            if proto == "uart":
                alias = "UART"
                g_set["DUT_UR1"] = str(cfg.get("port") or g_set.get("DUT_UR1") or "COM4").strip()
                _ensure_dut_connection(
                    ws, "UART", lambda sl: f'"Uart","UART","*$(DUT_UR{sl}),115200,8,One,None,None,10000,5000"'
                )
                connect_step = _step(phase=ph, title=t_str, send=':Connect,"UART"', reply="0",
                                     exec_mode="1", description="PC#-#Connect UART Port", test_id="OTFX082")
                prompt_step = _step(send="UART@\\r\\n", reply=f"@{endp}" if endp else "@#", end_prompt=endp or "#",
                                    waiting="5000", exec_mode="1", description="DUT#-#Check Console Prompt", test_id="OTFX079")
                send_str = f"UART@{cmd}\\r\\n"
                close_step = None
            elif proto == "ssh":
                alias = "SSH1"
                ssh_user = str(cfg.get("ssh_user") or "root").strip() or "root"
                ssh_pass = str(cfg.get("ssh_pass") or "").strip()
                if cfg.get("dut_ip"):
                    g_set["DUTIP_1"] = str(cfg["dut_ip"]).strip()
                _ensure_dut_connection(
                    ws, "SSH1", lambda sl: f'"SSH","SSH1","*$(PCIP_{sl}),*$(DUTIP_{sl}),22,{ssh_user},{ssh_pass},5000,1000"'
                )
                connect_step = _step(phase=ph, title=t_str, send=':Connect,"SSH1"', reply="0",
                                     exec_mode="1", description="PC#-#Connect SSH Console", test_id="OTFX082")
                prompt_step = None
                send_str = f"SSH1@{cmd}\\n"
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
                connect_step = _step(phase=ph, title=t_str, send=':Connect,"TELNET1"', reply="0",
                                     exec_mode="1", description="PC#-#Connect Telnet Console", test_id="OTFX082")
                prompt_step = None
                send_str = f"TELNET1@{cmd}\\r\\n"
                close_step = _step(send=':Disconnect,"TELNET1"', reply="0", exec_mode="3",
                                   description="PC#-#Disconnect Telnet Console", test_id="OTFX082")
            else:
                # adb or cmd (Windows CmdConsole)
                alias = "CmdConsole"
                _ensure_dut_connection(
                    ws, "CmdConsole", lambda _sl: '"APP","CmdConsole","C:\\Windows\\System32\\cmd.exe,0,5000,"'
                )
                full_cmd = cmd
                if proto == "adb" and not cmd.lower().startswith("adb"):
                    full_cmd = f"adb {cmd}"
                connect_step = _step(phase=ph, title=t_str, send=':Connect,"CmdConsole"', reply="0",
                                     exec_mode="1", description=f"PC#-#Open Console ({proto.upper()})", test_id="B7PL025")
                prompt_step = None
                send_str = f"CmdConsole@{full_cmd}\\r\\n"
                close_step = _step(send=':Disconnect,"CmdConsole"', reply="0", exec_mode="3",
                                   description="PC#-#Close Console", test_id="B7PL025")

            ref_expr = ""
            val_expr = ""
            step_reply = f"@{reply_kw}" if (extract_mode == "reply_only" and reply_kw) else "@"
            if extract_mode != "reply_only":
                if extract_mode == "split":
                    sep = str(cfg.get("split_sep") or ":").replace('"', '\\"')
                    idx_s = str(cfg.get("split_idx") or "1").strip() or "1"
                    ref_expr = f'${var_name}:SplitString,"{sep}","{idx_s}"'
                elif extract_mode == "sub":
                    st_i = str(cfg.get("sub_start") or "0").strip() or "0"
                    ln_i = str(cfg.get("sub_len") or "8").strip() or "8"
                    ref_expr = f'${var_name}:SubString,"{st_i}","{ln_i}"'
                else:
                    # default: within
                    left_s = str(cfg.get("left_delim") if cfg.get("left_delim") is not None else "version=").replace('"', '\\"')
                    right_s = str(cfg.get("right_delim") if cfg.get("right_delim") is not None else "\\r\\n").replace('"', '\\"')
                    ref_expr = f'${var_name}:WithinString,"{left_s}","{right_s}",""'

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

            steps.append(connect_step)
            if prompt_step:
                steps.append(prompt_step)
            steps.append(_step(
                send=send_str,
                reply=step_reply,
                end_prompt=endp,
                ref=ref_expr,
                validation=val_expr,
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
            if chk_mode == "string":
                expect_s = str(cfg.get("expect_str") or "PASS").strip() or "PASS"
                if use_ini:
                    ini_k = f"{var_nm}_EXPECT"
                    g_scr[ini_k] = expect_s
                    tok = f"*$({ini_k})"
                else:
                    tok = expect_s
                steps.append(_step(
                    phase=ph,
                    title=f"0,{title_lbl}",
                    send=f':GetVal,"${var_nm}"',
                    reply=f"@{tok}",
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

        # Every action block (except isn / delay / multi_sku / disabled fixture) supports optional post-block Delay row
        skip_post_delay = (
            kind in ("isn", "delay", "inst", "multi_sku")
            or (kind == "fixture" and str(cfg.get("fixture_type") or "none").strip().lower() == "none")
        )
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

    # Append Teardown block(s) at the end (always 97, optionally 98/99)
    if teardown_items:
        td_cfg = teardown_items[-1].get("config") or {}
        td_mode = str(td_cfg.get("teardown_mode") or "97_only").strip().lower()
        for r in (blk_map.get("BLK_PHASE97_TEARDOWN", {}).get("steps") or []):
            steps.append(dict(r))
        if td_mode == "97_98_99":
            for r in (blk_map.get("BLK_PHASE98_99_BRANCH_TEARDOWN", {}).get("steps") or []):
                steps.append(dict(r))
    else:
        for r in (blk_map.get("BLK_PHASE97_TEARDOWN", {}).get("steps") or []):
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
                    elif p_act == "mcurr":
                        m_dl = dl_s or "50"
                        m_ul = ul_s or "800"
                        c_steps.extend([
                            {"Send": f':Dev.SetON,"{p_volt}","2"' if is_pph else f':Dev.SwitchON,"{p_ch}"', "ExecMode": "1", "Description": f"Power#-#Set {p_volt}V ON"},
                            {"Send": f':Delay,"{p_wait}"', "ExecMode": "0", "Description": "PC#-#Stabilize Current"},
                            {"Send": ':Dev.MCurr' if is_pph else f':Dev.Measure,"{p_ch}"', "Ref": "$gCurr", "Validation": f"(gCurr,%f,{m_dl},{m_ul})", "ExecMode": "2:0", "Description": f"Power#-#Check Current ({m_dl}~{m_ul})"},
                        ])
                    else:
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
                elif any(k in low_nm for k in ("devuart", "scpicontroller", "transmitter")):
                    s_cmd = str(icfg.get("subdev_cmd") or (':sDev.Announce,"SAT{1},start"' if "devuart" in low_nm else ':sDev.OnOff,"ON"')).strip()
                    c_steps = [
                        {"Send": f':ObtainSubDevice,"{inst_nm}"', "ExecMode": "1", "Description": f"PC#-#Obtain {inst_nm}"},
                        {"Send": s_cmd, "ExecMode": "1", "Description": f"SubDev#-#{inst_nm} Command"},
                        {"Send": ":ReleaseSubDevice", "ExecMode": "3", "Description": f"PC#-#Release {inst_nm}"},
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

    # Re-sequence contiguous Phases (0, 1, 2... up to 96) preserving 97/98/99
    final_steps = ws["stations"][station_name]
    cur_p = 0
    seen_zero = False
    for st_row in final_steps:
        p_raw = str(st_row.get("Phase") or "").strip()
        if p_raw == "":
            continue
        try:
            p_int = int(p_raw)
            if p_int >= 95 or p_int == -1:
                continue
            if p_int == 0 and not seen_zero:
                seen_zero = True
                cur_p = 1
                continue
            if not seen_zero:
                seen_zero = True
            st_row["Phase"] = str(cur_p)
            cur_p += 1
        except ValueError:
            pass

    return ws, extracted_sku_cfg
