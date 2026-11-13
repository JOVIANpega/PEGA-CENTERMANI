# -*- coding: utf-8 -*-
"""
Centimani Studio V2.4 - Local Web Server & API Engine
1. Full-window browser launch with Chrome/Edge --start-maximized.
2. In-Place Repair: Saves directly to the ORIGINAL folder as *_FIXED.xlsx, preserving System.ini & Global.ini,
   and computes 64-char official Checksum automatically into the sibling System.ini!
3. Clean Tab/Bookmark switching: only the active tab is shown, never cluttering the screen.
"""
import os
import sys
import json
import cgi
import shutil
import tempfile
import webbrowser
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SCRIPTS_ROOT = os.path.join(PROJECT_ROOT, "SCRIPTS")
OUTPUT_ROOT = os.path.join(BASE_DIR, "output_system")

sys.path.insert(0, BASE_DIR)
from core.golden_data import (
    STANDARD_BLOCKS,
    get_golden_mother,
    search_test_ids,
    set_tic_catalog_path,
    get_active_tic_info
)
from core.excel_engine import (
    export_workspace_to_excel,
    import_excel_to_workspace
)
from core.ini_engine import sync_and_generate_inis
from core.script_doctor import audit_workspace, auto_fix_workspace
from core.checksum_signer import generate_official_checksum
from core.log_analyzer import analyze_centimani_log
from desktop_app import convert_workspace_to_dry_run


CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


def get_last_opened_dir():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                d = data.get("last_dir", "")
                if d and os.path.exists(d):
                    return d
    except Exception:
        pass
    return PROJECT_ROOT


def set_last_opened_dir(folder_path):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_dir": folder_path}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def pick_file_native(file_types=None, title="選擇要檢查與修復的 Centimani Excel 腳本"):
    import tkinter as tk
    from tkinter import filedialog
    init_dir = get_last_opened_dir()
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)
    types = file_types or [("Excel 活頁簿", "*.xlsx *.XLSX")]
    file_path = filedialog.askopenfilename(
        title=title,
        initialdir=init_dir,
        filetypes=types
    )
    root.destroy()
    if file_path:
        set_last_opened_dir(os.path.dirname(os.path.abspath(file_path)))
    return file_path


def open_folder_in_explorer(folder_path):
    try:
        if not os.path.exists(folder_path):
            return
        norm_path = os.path.normpath(folder_path)
        import ctypes, threading, time
        try:
            ctypes.windll.user32.AllowSetForegroundWindow(-1)
        except Exception:
            pass
        subprocess.Popen(["explorer", norm_path])

        def _bring_to_center_front():
            time.sleep(0.55)
            try:
                user32 = ctypes.windll.user32
                folder_name = os.path.basename(norm_path).lower()
                parent_name = os.path.basename(os.path.dirname(norm_path)).lower()
                matched_hwnds = []

                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                def _cb(hwnd, lparam):
                    if user32.IsWindowVisible(hwnd):
                        buf_cls = ctypes.create_unicode_buffer(64)
                        user32.GetClassNameW(hwnd, buf_cls, 64)
                        if buf_cls.value == "CabinetWClass":
                            buf_txt = ctypes.create_unicode_buffer(256)
                            user32.GetWindowTextW(hwnd, buf_txt, 256)
                            title_l = buf_txt.value.lower()
                            if folder_name in title_l or (parent_name and parent_name in title_l):
                                matched_hwnds.append(hwnd)
                    return True

                user32.EnumWindows(WNDENUMPROC(_cb), 0)
                if matched_hwnds:
                    hwnd = matched_hwnds[0]
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    sw = user32.GetSystemMetrics(0)
                    sh = user32.GetSystemMetrics(1)
                    w, h = min(980, int(sw * 0.72)), min(640, int(sh * 0.72))
                    x, y = max(0, (sw - w) // 2), max(0, (sh - h) // 2)
                    user32.MoveWindow(hwnd, x, y, w, h, True)
                    # Toggle TopMost briefly to bypass Windows foreground lock safely
                    user32.SetWindowPos(hwnd, -1, x, y, w, h, 0x0001 | 0x0040)
                    user32.SetWindowPos(hwnd, -2, x, y, w, h, 0x0001 | 0x0040)
                    user32.SetForegroundWindow(hwnd)
            except Exception:
                pass

        threading.Thread(target=_bring_to_center_front, daemon=True).start()
    except Exception:
        pass


def extract_isn_info(ws):
    """Extracts the configured ISN barcode digit length and rule from DUTs ScanBarcode."""
    import re
    for dut in ws.get("duts", []):
        for k, v in dut.items():
            if "ScanBarcode" in str(k) and v:
                raw = str(v).strip()
                m = re.search(r"\{ISN\s*,\s*(\d+)\s*,\s*([^}]+)\}", raw, re.IGNORECASE)
                if m:
                    return {"isn_length": int(m.group(1)), "scan_rule": raw}
                m2 = re.search(r"\{[^,]+\s*,\s*(\d+)\s*,", raw)
                if m2:
                    return {"isn_length": int(m2.group(1)), "scan_rule": raw}
    return {"isn_length": None, "scan_rule": ""}


def build_wizard_block_steps(bid, block_def, wizard_config, ws):
    """Builds customized steps for configurable wizard blocks (Voltage rails, FW via UART/ADB/SSH, Python, Ping)."""
    if not wizard_config:
        return None

    if bid == "BLK_VOLT_NI6008_BATCH":
        rails = wizard_config.get("volt_rails") or []
        if not rails:
            return None
        channels = [str(r.get("channel", i)).strip() for i, r in enumerate(rails)]
        names = []
        for i, r in enumerate(rails):
            nm = str(r.get("name", f"V_CH{i}")).strip().replace(" ", "_") or f"V_CH{i}"
            names.append(nm)
        ref_str = ";\n".join(f"${nm}" for nm in names)
        ch_desc = ", ".join(f"AI{ch}({nm})" for ch, nm in zip(channels, names))
        steps = [
            {"Phase": "1", "Title": "0,Measure Voltage Test,3", "Marco": "", "Instrument": "Voltage", "Switch": "", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "INST#-#Obtain NI6008 Lock", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "Voltage", "Switch": "", "Send": f':Dev.VOLTAGE,"RSE,1000,{",".join(channels)}"', "Reply": "0", "EndPrompt": "", "Ref": ref_str, "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": f"INST#-#Read {ch_desc}", "TestID": "BRPW033"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "Voltage", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "INST#-#Release NI6008 Lock", "TestID": "BRME027"},
        ]
        for r, nm in zip(rails, names):
            vmin = str(r.get("min", "0")).strip() or "0"
            vmax = str(r.get("max", "5")).strip() or "5"
            tid = str(r.get("test_id", "BRPW024")).strip() or "BRPW024"
            steps.append({
                "Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "",
                "Send": f':CheckLimit,"*({nm})","{vmin}","{vmax}","%f"',
                "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "",
                "ExecMode": "2:0", "Description": f"DUT#-#Check {nm} ({vmin}V~{vmax}V)", "TestID": tid
            })
        return steps

    if bid == "BLK_UART_BOOT_FW":
        fw = wizard_config.get("fw_config") or {}
        if not fw:
            return None
        mode = str(fw.get("mode", "uart")).lower()
        fw_ver = str(fw.get("fw_version", "1.0.0_release")).strip() or "1.0.0_release"
        cmd = str(fw.get("command", "cat /etc/version")).strip() or "cat /etc/version"
        ws["global_ini"]["Scripts"]["FW_VERSION"] = fw_ver
        if mode == "uart":
            port = str(fw.get("port", "COM4")).strip() or "COM4"
            ws["global_ini"]["Settings"]["DUT_UR1"] = port
            return [
                {"Phase": "4", "Title": "0,Check UART & FW Version,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"UART"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Connect UART Port", "TestID": "OTFX082"},
                {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": "UART@\\r\\n", "Reply": "@#", "EndPrompt": "#", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "5000", "ExecMode": "1", "Description": "DUT#-#Check Console Prompt", "TestID": "OTFX079"},
                {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f"UART@{cmd}\\r\\n", "Reply": "@", "EndPrompt": "#", "Ref": '$DUT_FW:WithinString,"version=","\\r\\n","":Trim', "Validation": "(DUT_FW,%s,*$(FW_VERSION),*$(FW_VERSION))", "Prompt": "", "Waiting": "5000", "ExecMode": "1", "Description": "DUT#-#Verify Firmware Version (UART)", "TestID": "VSCH026"},
            ]
        elif mode == "adb":
            return [
                {"Phase": "4", "Title": "0,Check ADB & FW Version,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"CmdConsole"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Open CMD Console for ADB", "TestID": "B7PL025"},
                {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f"CmdConsole@{cmd}\\r\\n", "Reply": "@", "EndPrompt": ">", "Ref": '$DUT_FW:WithinString,"version=","\\n","":Trim', "Validation": "(DUT_FW,%s,*$(FW_VERSION),*$(FW_VERSION))", "Prompt": "", "Waiting": "8000", "ExecMode": "1", "Description": "DUT#-#Verify Firmware Version (ADB)", "TestID": "VSCH026"},
                {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Disconnect,"CmdConsole"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Close CMD Console", "TestID": "B7PL025"},
            ]
        elif mode == "ssh":
            return [
                {"Phase": "4", "Title": "0,Check SSH & FW Version,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"CmdConsole"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Open CMD Console for SSH", "TestID": "B7PL025"},
                {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f"CmdConsole@{cmd}\\r\\n", "Reply": "@", "EndPrompt": ">", "Ref": '$DUT_FW:WithinString,"version=","\\n","":Trim', "Validation": "(DUT_FW,%s,*$(FW_VERSION),*$(FW_VERSION))", "Prompt": "", "Waiting": "8000", "ExecMode": "1", "Description": "DUT#-#Verify Firmware Version (SSH)", "TestID": "VSCH026"},
                {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Disconnect,"CmdConsole"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Close CMD Console", "TestID": "B7PL025"},
            ]

    if bid == "BLK_PYTHON_SCRIPT_CALL":
        py = wizard_config.get("python_config") or {}
        if not py:
            return None
        py_path = str(py.get("python_path", "D:\\PythonScript")).strip() or "D:\\PythonScript"
        script_name = str(py.get("script_name", "my_test.py")).strip() or "my_test.py"
        prefix = str(py.get("result_prefix", "RESULT=")).strip() or "RESULT="
        pmin = str(py.get("min_val", "0.0")).strip() or "0.0"
        pmax = str(py.get("max_val", "100.0")).strip() or "100.0"
        ws["global_ini"]["Scripts"]["PythonPath"] = py_path
        return [
            {"Phase": "6", "Title": "0,Run External Python Script,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"CmdConsole"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Open Windows CMD Console", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f'CmdConsole@cd *$(PythonPath)&&cmd /c python.exe {script_name} "*(ISN)"\\r\\n', "Reply": "@Command pass", "EndPrompt": ">", "Ref": f'$PyVal:WithinString,"{prefix}","\\n","":Trim', "Validation": f"(PyVal,%f,{pmin},{pmax})", "Prompt": "", "Waiting": "10000", "ExecMode": "1", "Description": f"PC#-#Execute {script_name} & Validate Output", "TestID": "OTFX054"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Disconnect,"CmdConsole"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Close Windows CMD Console", "TestID": "B7PL025"},
        ]

    if bid == "BLK_UTILITY_PING_LAN":
        pg = wizard_config.get("ping_config") or {}
        targets = pg.get("targets") or []
        if targets:
            steps = []
            for idx, t in enumerate(targets):
                lbl = str(t.get("label", f"Ping_{idx+1}")).strip() or f"Ping_{idx+1}"
                dip = str(t.get("dut_ip", "192.168.11.143")).strip() or "192.168.11.143"
                pip = str(t.get("pc_ip", "192.168.11.3")).strip() or "192.168.11.3"
                tmo = str(t.get("timeout_ms", "5000")).strip() or "5000"
                if idx == 0:
                    ws["global_ini"]["Settings"]["DUTIP_1"] = dip
                    ws["global_ini"]["Settings"]["PCIP_1"] = pip
                    ws["global_ini"]["Scripts"]["DUTIP_1"] = dip
                    ws["global_ini"]["Scripts"]["PCIP_1"] = pip
                steps.append({
                    "Phase": "7" if idx == 0 else "",
                    "Title": "0,LAN Ping Test,5" if idx == 0 else "",
                    "Marco": "", "Instrument": "", "Switch": "",
                    "Send": f':Utility.Ping,"{dip}","{tmo}","{pip}"',
                    "Reply": "0", "EndPrompt": "", "Ref": f"$PingRes_{idx+1}",
                    "Validation": "", "Prompt": "", "Waiting": "",
                    "ExecMode": "1", "Description": f"PC#-#Ping {lbl} ({dip})", "TestID": "IOPI113"
                })
            return steps
        elif pg:
            dut_ip = str(pg.get("dut_ip", "192.168.11.143")).strip() or "192.168.11.143"
            pc_ip = str(pg.get("pc_ip", "192.168.11.3")).strip() or "192.168.11.3"
            ws["global_ini"]["Settings"]["DUTIP_1"] = dut_ip
            ws["global_ini"]["Settings"]["PCIP_1"] = pc_ip
            ws["global_ini"]["Scripts"]["DUTIP_1"] = dut_ip
            ws["global_ini"]["Scripts"]["PCIP_1"] = pc_ip
        return None

    if bid == "BLK_WIFI_RF_IQXEL":
        wf = wizard_config.get("wifi_config") or {}
        if not wf:
            return None
        iq_ip = str(wf.get("iqxel_ip", "192.168.100.254")).strip() or "192.168.100.254"
        for inst in ws.get("instruments", []):
            if "InstIQApi" in str(inst.get("Name", "")):
                parts = str(inst.get("Settings", "")).split(",")
                if parts:
                    parts[0] = iq_ip
                    inst["Settings"] = ",".join(parts)
        tx_tests = wf.get("tx_tests") or []
        rx_tests = wf.get("rx_tests") or []
        if not tx_tests and not rx_tests:
            return None
        steps = []
        for idx, t in enumerate(tx_tests):
            ch = str(t.get("channel", "3")).strip() or "3"
            bw = str(t.get("bw", "20")).strip() or "20"
            mcs = str(t.get("mcs", "7")).strip() or "7"
            ant = str(t.get("antenna", "1")).strip() or "1"
            tpwr = str(t.get("target_pwr", "15")).strip() or "15"
            pmin = str(t.get("pwr_min", "13")).strip() or "13"
            pmax = str(t.get("pwr_max", "17")).strip() or "17"
            emin = str(t.get("evm_min", "-50")).strip() or "-50"
            emax = str(t.get("evm_max", "-28")).strip() or "-28"
            lbl = f"WIFI TX{ant}_CH{ch} MCS{mcs}_BW{bw}"
            steps.append({
                "Phase": "9" if len(steps) == 0 else "",
                "Title": f"0,{lbl}",
                "Marco": "WIFI Tx MCS",
                "Instrument": "MeasWIFI", "Switch": "",
                "Send": f"{ch},{bw},{mcs},{ant},{tpwr},{pmin},{pmax},{emin},{emax},{lbl}",
                "Reply": "", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "",
                "ExecMode": "1", "Description": f"RF#-#{lbl}", "TestID": "WFOT036"
            })
        for idx, r in enumerate(rx_tests):
            ch = str(r.get("channel", "5")).strip() or "5"
            bw = str(r.get("bw", "40")).strip() or "40"
            mcs = str(r.get("mcs", "7")).strip() or "7"
            ant = str(r.get("antenna", "1")).strip() or "1"
            rxlvl = str(r.get("rx_level", "-59")).strip() or "-59"
            lbl = f"WIFI RX{ant}_CH{ch} MCS{mcs}_BW{bw}"
            steps.append({
                "Phase": "9" if len(steps) == 0 else "",
                "Title": f"0,{lbl}",
                "Marco": "WIFI Rx MCS",
                "Instrument": "GenWIFI", "Switch": "",
                "Send": f"{ch},{bw},{mcs},{ant},{rxlvl},{lbl}",
                "Reply": "", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "",
                "ExecMode": "1", "Description": f"RF#-#{lbl}", "TestID": "WFOT036"
            })
        return steps

    if bid == "BLK_FIXTURE_ACTION":
        fx = wizard_config.get("fixture_config") or {}
        if not fx:
            return None
        port = str(fx.get("port", "COM5")).strip() or "COM5"
        wait_ms = str(fx.get("wait_ms", "3000")).strip() or "3000"
        ws["global_ini"]["Settings"]["PCUART_fixture_1"] = port
        return [
            {"Phase": "", "Title": "0,Fixture Down,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"UARTF"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Fixture#-#Connect Fixture UART", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": "UARTF@G\\r\\n", "Reply": "", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Fixture#-#Pneumatic Fixture Down", "TestID": "OTFX157"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f':Delay,"{wait_ms}"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": f"PC#-#Wait Power Rail Stable ({wait_ms}ms)", "TestID": "B7PL025"},
        ]

    if bid == "BLK_POWER_ON_IPOWER":
        pw = wizard_config.get("ipower_config") or {}
        if not pw:
            return None
        delay_ms = str(pw.get("delay_ms", "2000")).strip() or "2000"
        return [
            {"Phase": "", "Title": "0,Power ON Sequence,3", "Marco": "", "Instrument": "POWERSWITCH", "Switch": "", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Power#-#Obtain iPower Lock", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "POWERSWITCH", "Switch": "", "Send": ':Dev.Switch,"1,0"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Power#-#Turn OFF Channel 1", "TestID": "BRPW011"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f':Delay,"{delay_ms}"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": f"PC#-#Wait Discharge ({delay_ms}ms)", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "POWERSWITCH", "Switch": "", "Send": ':Dev.Switch,"1,1"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Power#-#Turn ON Channel 1", "TestID": "BRPW011"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "POWERSWITCH", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "Power#-#Release iPower Lock", "TestID": "BRME027"},
        ]

    if bid == "BLK_VOLT_DIFF_SINGLE":
        vd = wizard_config.get("diff_volt_config") or {}
        if not vd:
            return None
        ch = str(vd.get("channel", "0")).strip() or "0"
        nm = str(vd.get("name", "VCC_12V")).strip().replace(" ", "_") or "VCC_12V"
        vmin = str(vd.get("min", "11.40")).strip() or "11.40"
        vmax = str(vd.get("max", "12.60")).strip() or "12.60"
        return [
            {"Phase": "2", "Title": f"0,Measure {nm},3", "Marco": "", "Instrument": "Voltage", "Switch": "", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "INST#-#Obtain NI6008 Lock", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "Voltage", "Switch": "", "Send": f':Dev.VOLTAGE,"DIFF,2000,{ch}"', "Reply": "0", "EndPrompt": "", "Ref": f"${nm}", "Validation": f"({nm},%f,{vmin},{vmax})", "Prompt": "", "Waiting": "", "ExecMode": "2:0", "Description": f"DUT#-#Measure {nm} ({vmin}V~{vmax}V)", "TestID": "BRPW024"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "Voltage", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "INST#-#Release NI6008 Lock", "TestID": "BRME027"},
        ]

    if bid == "BLK_LED_FEASA":
        ld = wizard_config.get("led_config") or {}
        if not ld:
            return None
        port = str(ld.get("port", "COM17")).strip() or "COM17"
        ch = str(ld.get("channel", "01")).strip() or "01"
        wmin = str(ld.get("wave_min", "515")).strip() or "515"
        wmax = str(ld.get("wave_max", "535")).strip() or "535"
        imin = str(ld.get("int_min", "1000")).strip() or "1000"
        imax = str(ld.get("int_max", "99999")).strip() or "99999"
        ws["global_ini"]["Settings"]["LED_AZ1"] = port
        return [
            {"Phase": "8", "Title": "0,Check LED Color & Intensity,3", "Marco": "", "Instrument": "LED_Test", "Switch": "", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "LED#-#Obtain Feasa LED Lock", "TestID": "BRME027"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "LED_Test", "Switch": "", "Send": f':Dev.CaptureAndRead,"{ch}"', "Reply": "0", "EndPrompt": "", "Ref": "$LED_Wave;\n$LED_Int", "Validation": f"(LED_Wave,%f,{wmin},{wmax});\n(LED_Int,%f,{imin},{imax})", "Prompt": "", "Waiting": "", "ExecMode": "2:0", "Description": f"LED#-#Verify Ch{ch} Wavelength({wmin}~{wmax}) & Intensity", "TestID": "IOLE015"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "LED_Test", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "LED#-#Release Feasa LED Lock", "TestID": "BRME027"},
        ]

    if bid == "BLK_SFIS_MAC_69PN":
        sf = wizard_config.get("sfis_config") or {}
        fields = sf.get("fields") or []
        if not fields:
            return None
        steps = []
        for idx, f in enumerate(fields):
            fn = str(f.get("field_name", "MAC1")).strip() or "MAC1"
            vn = str(f.get("var_name", f"sf{fn}")).strip() or f"sf{fn}"
            lmin = str(f.get("len_min", "")).strip()
            lmax = str(f.get("len_max", "")).strip()
            val_str = f"({vn},%len,{lmin},{lmax})" if (lmin and lmax) else ""
            steps.append({
                "Phase": "5" if idx == 0 else "",
                "Title": "0,GET_SFIS_INFO,3" if idx == 0 else "",
                "Marco": "", "Instrument": "", "Switch": "",
                "Send": f':SfGetVersion,"*(ISN)","ISN_BASEINFO","2","{fn}",""',
                "Reply": "", "EndPrompt": "", "Ref": f"${vn}", "Validation": val_str,
                "Prompt": "", "Waiting": "", "ExecMode": "9",
                "Description": f"PC#-#Get {fn} from SFIS", "TestID": "OTFX133" if "MAC" in fn.upper() else "OTFX085"
            })
        return steps

    return None


class StudioRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ["/", "/index.html"]:
            html_path = os.path.join(BASE_DIR, "web", "index.html")
            with open(html_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif parsed.path == "/api/init":
            self._send_json({
                "blocks": STANDARD_BLOCKS,
                "last_dir": get_last_opened_dir(),
                "tic_info": get_active_tic_info()
            })
        elif parsed.path == "/api/pick_tic_file":
            tic_types = [("Test Item Code Excel", "*.xlsx;*.xlsm"), ("所有檔案", "*.*")]
            selected_path = pick_file_native(file_types=tic_types, title="選擇 Test Item Code Excel 檔案")
            if not selected_path:
                self._send_json({"status": "cancel"})
                return
            info = set_tic_catalog_path(selected_path)
            self._send_json({
                "status": "ok",
                "tic_info": info
            })
        elif parsed.path == "/api/pick_file":
            selected_path = pick_file_native()
            if not selected_path:
                self._send_json({"status": "cancel"})
                return
            ws = import_excel_to_workspace(selected_path)
            rep = audit_workspace(ws)
            self._send_json({
                "status": "ok",
                "file_path": selected_path,
                "workspace": ws,
                "report": rep,
                "isn_info": extract_isn_info(ws)
            })
        elif parsed.path == "/api/pick_log_file":
            log_types = [("Centimani 日誌與報告", "*.log;*.txt;*.csv;*.LOG;*.TXT;*.CSV"), ("所有檔案", "*.*")]
            selected_path = pick_file_native(file_types=log_types, title="選擇要分析的 Centimani 日誌檔案 (Log / CSV)")
            if not selected_path:
                self._send_json({"status": "cancel"})
                return
            try:
                # Read file contents safely with encoding fallback
                content = ""
                for enc in ["utf-8", "big5", "cp950", "gbk", "latin-1"]:
                    try:
                        with open(selected_path, "r", encoding=enc) as f:
                            content = f.read()
                        break
                    except Exception:
                        pass
                res = analyze_centimani_log(content, file_path=selected_path)
                self._send_json({
                    "status": "ok",
                    "file_path": selected_path,
                    "file_size_kb": round(os.path.getsize(selected_path) / 1024, 2),
                    "log_snippet": content[:1200] if len(content) > 1200 else content,
                    "result": res
                })
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)
        elif parsed.path == "/api/search_test_id":
            qs = parse_qs(parsed.query)
            q = qs.get("q", [""])[0]
            limit = int(qs.get("limit", ["30"])[0])
            generic_only = qs.get("generic_only", ["0"])[0] in ("1", "true", "True")
            items = search_test_ids(q, limit=limit, generic_only=generic_only)
            self._send_json({"status": "ok", "items": items})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/upload_and_audit":
            # Handles multipart file upload from web browser
            ctype, pdict = cgi.parse_header(self.headers.get("content-type", ""))
            if ctype == "multipart/form-data":
                pdict["boundary"] = bytes(pdict["boundary"], "utf-8")
                fields = cgi.parse_multipart(self.rfile, pdict)
                file_items = fields.get("excel_file", [])
                if not file_items:
                    self._send_json({"status": "error", "message": "未收到上傳的 Excel 檔案"}, 400)
                    return
                file_bytes = file_items[0]
                # Save to a temporary or scratch file to inspect
                scratch_dir = os.path.join(BASE_DIR, "uploaded_temp")
                os.makedirs(scratch_dir, exist_ok=True)
                temp_path = os.path.join(scratch_dir, "temp_uploaded.xlsx")
                with open(temp_path, "wb") as f:
                    f.write(file_bytes)

                ws = import_excel_to_workspace(temp_path)
                rep = audit_workspace(ws)
                self._send_json({
                    "status": "ok",
                    "file_path": temp_path,
                    "workspace": ws,
                    "report": rep,
                    "isn_info": extract_isn_info(ws)
                })
            else:
                self._send_json({"status": "error", "message": "Invalid content-type"}, 400)
            return

        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        payload = json.loads(raw_body) if raw_body else {}

        try:
            if parsed.path == "/api/analyze_log":
                log_content = payload.get("log_text", "")
                file_path = payload.get("file_path", "")
                if file_path and os.path.exists(file_path):
                    for enc in ["utf-8", "big5", "cp950", "gbk", "latin-1"]:
                        try:
                            with open(file_path, "r", encoding=enc) as f:
                                log_content = f.read()
                            break
                        except Exception:
                            pass
                result = analyze_centimani_log(log_content, file_path=file_path)
                self._send_json({
                    "status": "ok",
                    "result": result
                })
                return

            if parsed.path == "/api/fix_and_export_in_place":
                ws = payload.get("workspace", {})
                user_choices = payload.get("user_choices", {})
                dry_run = payload.get("dry_run", False)

                src_file = ws.get("source_file", "")
                if not src_file or not os.path.exists(src_file):
                    # Fallback to scratch or prompt
                    src_file = os.path.join(OUTPUT_ROOT, "Fixed_Script", "TestFlow.xlsx")

                orig_dir = os.path.dirname(os.path.abspath(src_file))
                base_name = os.path.splitext(os.path.basename(src_file))[0]
                # Strip previous suffixes if present
                for sfx in ["_Fixed", "_FIXED", "_DryRun", "temp_uploaded"]:
                    base_name = base_name.replace(sfx, "")
                if not base_name:
                    base_name = "Centimani_TestFlow"

                if dry_run:
                    ws_to_export = convert_workspace_to_dry_run(ws)
                    fixed_xlsx_name = f"{base_name}_DryRun.xlsx"
                else:
                    ws_to_export = ws
                    fixed_xlsx_name = f"{base_name}_FIXED.xlsx"

                auto_fix_workspace(ws_to_export, user_choices=user_choices)

                # Export DIRECTLY to the original file directory!
                out_xlsx_path = os.path.join(orig_dir, fixed_xlsx_name)
                export_workspace_to_excel(ws_to_export, out_xlsx_path)

                # Sync and generate INIs in the original directory (preserving original SFIS keys)
                sys_ini, glb_ini = sync_and_generate_inis(ws_to_export, fixed_xlsx_name, orig_dir)

                # Compute official Checksum and write to System.ini
                chk = generate_official_checksum(out_xlsx_path, sys_ini)

                open_folder_in_explorer(orig_dir)

                self._send_json({
                    "status": "ok",
                    "output_dir": orig_dir,
                    "excel_path": out_xlsx_path,
                    "system_ini": sys_ini,
                    "global_ini": glb_ini,
                    "checksum": chk or "已自動寫入 [Checksum]",
                    "isn_info": extract_isn_info(ws_to_export)
                })

            elif parsed.path == "/api/generate_new_standalone":
                proj = payload.get("project_name", "PEGA_NEW").strip() or "PEGA_NEW"
                st = payload.get("station_name", "MB").strip() or "MB"
                dut_count = int(payload.get("dut_count", 1))
                block_ids = payload.get("block_ids", [])
                dry_run = payload.get("dry_run", False)
                testid_overrides = payload.get("testid_overrides", {}) or {}
                wizard_config = payload.get("wizard_config", {}) or {}

                effective_dut_count = 1 if dry_run else max(1, min(4, dut_count))
                ws = get_golden_mother(proj, st)
                ws["duts"] = ws["duts"][:effective_dut_count]
                isn_len = int(wizard_config.get("isn_length", 3) or 3)
                isn_pat = str(wizard_config.get("isn_pattern", "[0-9A-Z]") or "[0-9A-Z]").strip()
                for dut_row in ws["duts"]:
                    dut_row["ScanBarcode( {Name,Lengh,Pattern} )"] = f"{{ISN,{isn_len},{isn_pat}}}"
                for slot in range(1, 5):
                    if slot <= effective_dut_count:
                        ws["global_ini"]["Settings"][f"LOAD_{slot}"] = "true"
                    else:
                        for suffix in [f"LOAD_{slot}", f"PCIP_{slot}", f"DUTIP_{slot}", f"DUT_UR{slot}", f"PCUART_fixture_{slot}", f"DEVID_{slot}"]:
                            ws["global_ini"]["Settings"].pop(suffix, None)

                blk_order = {b["block_id"]: idx for idx, b in enumerate(STANDARD_BLOCKS)}
                blk_map = {b["block_id"]: b for b in STANDARD_BLOCKS}
                # Sort selected block_ids strictly by official pipeline order
                # Ensuring BLK_PRETEST_ROUTE (Phase 0) is first, test blocks in sequence, and BLK_PHASE97_TEARDOWN is always last
                sorted_block_ids = sorted(block_ids, key=lambda bid: blk_order.get(bid, 999))
                steps = []
                for bid in sorted_block_ids:
                    b = blk_map.get(bid)
                    if not b:
                        continue
                    for k, v in b.get("required_globals", {}).get("Settings", {}).items():
                        ws["global_ini"]["Settings"][k] = v
                    for k, v in b.get("required_globals", {}).get("Scripts", {}).items():
                        ws["global_ini"]["Scripts"][k] = v
                    for m_name, m_rows in b.get("required_marcos", {}).items():
                        ws.setdefault("marcos", {})[m_name] = [dict(mr) for mr in m_rows]
                    custom_steps = build_wizard_block_steps(bid, b, wizard_config, ws)
                    source_steps = custom_steps if custom_steps is not None else b.get("steps", [])
                    for st_idx, st_row in enumerate(source_steps):
                        row_copy = dict(st_row)
                        ov = testid_overrides.get(f"{bid}::{st_idx}")
                        if ov:
                            if ov.get("test_id"):
                                row_copy["TestID"] = ov["test_id"]
                            if ov.get("description"):
                                row_copy["Description"] = ov["description"]
                        steps.append(row_copy)

                # Keep only instruments actually referenced by selected blocks (cleaner mother workbook)
                used_inst_funcs = {str(s.get("Instrument", "")).strip().upper() for s in steps if str(s.get("Instrument", "")).strip()}
                if used_inst_funcs:
                    filtered_insts = []
                    seen_funcs = set()
                    for inst in ws.get("instruments", []):
                        inst_funcs = [f.strip().upper() for f in str(inst.get("Functions", "")).split(",") if f.strip()]
                        matched = [fn for fn in inst_funcs if fn in used_inst_funcs and fn not in seen_funcs]
                        if matched:
                            seen_funcs.update(matched)
                            filtered_insts.append(inst)
                    ws["instruments"] = filtered_insts

                # Ensure non-teardown Phases are strictly contiguous (0, 1, 2, 3...) with no gaps
                next_phase = 0
                for st_row in steps:
                    p_str = str(st_row.get("Phase", "")).strip()
                    if p_str != "":
                        try:
                            p_val = int(p_str)
                            if 0 <= p_val < 97:
                                st_row["Phase"] = str(next_phase)
                                next_phase += 1
                        except ValueError:
                            pass

                ws["stations"] = {st: steps}
                auto_fix_workspace(ws)

                if dry_run:
                    ws = convert_workspace_to_dry_run(ws)
                    xlsx_name = f"{proj}_TestFlow_{st}_DryRun.xlsx"
                    folder_label = f"{proj}_{st}_無硬體試跑版"
                else:
                    xlsx_name = f"{proj}_TestFlow_{st}.xlsx"
                    folder_label = f"{proj}_{st}"

                target_dir = os.path.join(OUTPUT_ROOT, folder_label, "System")
                os.makedirs(target_dir, exist_ok=True)
                for old_f in os.listdir(target_dir):
                    try:
                        os.remove(os.path.join(target_dir, old_f))
                    except Exception:
                        pass

                out_xlsx = os.path.join(target_dir, xlsx_name)
                export_workspace_to_excel(ws, out_xlsx)
                sys_ini, glb_ini = sync_and_generate_inis(ws, xlsx_name, target_dir)
                chk = "已自動寫入 [Checksum]"

                open_folder_in_explorer(target_dir)

                self._send_json({
                    "status": "ok",
                    "output_dir": target_dir,
                    "excel_path": out_xlsx,
                    "system_ini": sys_ini,
                    "global_ini": glb_ini,
                    "checksum": chk or "已自動寫入 [Checksum]",
                    "isn_info": extract_isn_info(ws)
                })
            else:
                self._send_json({"status": "error", "message": "Unknown endpoint"}, 404)
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)


def launch_fullscreen_browser(url):
    """Launches the default or installed browser in maximized/fullscreen mode."""
    # Try Chrome or Edge with --start-maximized
    browser_candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe")
    ]
    for exe in browser_candidates:
        if os.path.exists(exe):
            subprocess.Popen([exe, "--start-maximized", "--app=" + url if "chrome" in exe.lower() else url])
            return
    webbrowser.open(url)


def run_server(port=8765):
    server = HTTPServer(("127.0.0.1", port), StudioRequestHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"Centimani Studio V2.4 Server running at {url}")
    launch_fullscreen_browser(url)
    server.serve_forever()


if __name__ == "__main__":
    run_server(port=8765)
