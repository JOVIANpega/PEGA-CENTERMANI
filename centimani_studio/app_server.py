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
import re
import json
import shutil
import tempfile
import webbrowser
import subprocess
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote


def _parse_multipart_form(headers, rfile):
    """Python 3.10 ~ 3.13+ compatible multipart/form-data parser (replaces removed 'cgi' module)."""
    ctype = headers.get("Content-Type") or headers.get("content-type") or ""
    if "multipart/form-data" not in ctype.lower():
        return None
    m = re.search(r'boundary=(?:"([^"]+)"|([^;\s]+))', ctype, re.I)
    if not m:
        return {}
    boundary = (m.group(1) or m.group(2)).encode("utf-8")
    length = int(headers.get("Content-Length") or headers.get("content-length") or 0)
    if length <= 0:
        return {}
    raw_data = rfile.read(length)
    delimiter = b"--" + boundary
    parts = raw_data.split(delimiter)
    fields = {}
    for part in parts[1:]:
        if part.startswith(b"--") or not part.strip():
            continue
        if part.startswith(b"\r\n"):
            part = part[2:]
        elif part.startswith(b"\n"):
            part = part[1:]
        if b"\r\n\r\n" in part:
            hdr_bytes, body = part.split(b"\r\n\r\n", 1)
            if body.endswith(b"\r\n"):
                body = body[:-2]
        elif b"\n\n" in part:
            hdr_bytes, body = part.split(b"\n\n", 1)
            if body.endswith(b"\n"):
                body = body[:-1]
        else:
            continue
        hdr_text = hdr_bytes.decode("utf-8", errors="ignore")
        nm = re.search(r'name="([^"]+)"', hdr_text, re.I)
        if nm:
            field_key = nm.group(1)
            fields.setdefault(field_key, []).append(body)
            fn_m = re.search(r'filename="([^"]+)"', hdr_text, re.I)
            if fn_m:
                fields[f"{field_key}__filename"] = os.path.basename(fn_m.group(1).replace("\\", "/"))
    return fields

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
from core.script_doctor import audit_workspace, auto_fix_workspace, apply_safety_ending_fix, insert_instrument_title_block, insert_ni6009_block, insert_rf_iqxel_block, update_comm_settings
from core.checksum_signer import generate_official_checksum
from core.log_analyzer import analyze_centimani_log
from desktop_app import convert_workspace_to_dry_run


CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


DEFAULT_SETTINGS = {
    "auto_fullscreen": True,
    "show_flow_guide": True,
    "show_top_refresh": True,
    "auto_open_folder": True,
    "auto_checksum": True,
    "tic_generic_only": False,
    "intro_font_size": 15,
    "skip_guides": {},
    "centimani_dir": ""
}


def get_app_settings():
    res = dict(DEFAULT_SETTINGS)
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    res.update(data)
    except Exception:
        pass
    return res


def save_app_settings(patch):
    cur = get_app_settings()
    if isinstance(patch, dict):
        cur.update(patch)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cur, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return cur


def get_last_opened_dir():
    d = get_app_settings().get("last_dir", "")
    if d and os.path.exists(d):
        return d
    if os.path.exists(SCRIPTS_ROOT):
        return SCRIPTS_ROOT
    return PROJECT_ROOT


def set_last_opened_dir(folder_path):
    save_app_settings({"last_dir": folder_path})


def get_recent_excel_files(limit=24):
    """取得最近目錄與預設專案資料夾內的 TestFlow Excel 檔案列表，自動排除代碼表與暫存檔"""
    import datetime
    search_dirs = []
    last_d = get_last_opened_dir()
    if last_d and os.path.exists(last_d):
        search_dirs.append(last_d)
    for sub_folder in ("TEST_SECRIPT", "TEMP_SCRIPT"):
        cand_d = os.path.join(PROJECT_ROOT, sub_folder)
        if os.path.exists(cand_d) and cand_d not in search_dirs:
            search_dirs.append(cand_d)
    if os.path.exists(SCRIPTS_ROOT) and SCRIPTS_ROOT not in search_dirs:
        search_dirs.append(SCRIPTS_ROOT)

    files_list = []
    seen_paths = set()
    for d in search_dirs:
        try:
            for fname in os.listdir(d):
                low_name = fname.lower()
                if not low_name.endswith(".xlsx") or fname.startswith("~"):
                    continue
                if "test item code" in low_name or low_name.startswith("old_") or ".bak" in low_name:
                    continue
                full_p = os.path.join(d, fname)
                norm_p = os.path.normcase(os.path.abspath(full_p))
                if norm_p not in seen_paths and os.path.isfile(full_p):
                    seen_paths.add(norm_p)
                    try:
                        mtime = os.path.getmtime(full_p)
                        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%m/%d %H:%M")
                        size_kb = round(os.path.getsize(full_p) / 1024, 1)
                        files_list.append({
                            "name": fname,
                            "path": full_p,
                            "folder": os.path.basename(d),
                            "size_kb": size_kb,
                            "mtime": mtime,
                            "mtime_str": mtime_str
                        })
                    except Exception:
                        pass
        except Exception:
            pass

    files_list.sort(key=lambda x: x["mtime"], reverse=True)
    return files_list[:limit]


import threading
_PICK_LOCK = threading.Lock()
_EXCEL_LAUNCH_LOCK = threading.Lock()
_LAST_EXCEL_LAUNCH = {"path": "", "time": 0.0}


def _prepare_topmost_tk_root(tk_mod):
    """Creates a 1x1 topmost parent Tk window that forces Win32 file/folder dialogs above fullscreen Chrome."""
    import ctypes
    try:
        ctypes.windll.user32.AllowSetForegroundWindow(-1)
    except Exception:
        pass
    root = tk_mod.Tk()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"1x1+{sw // 2}+{sh // 3}")
    root.overrideredirect(True)
    try:
        root.attributes("-alpha", 0.01)
    except Exception:
        pass
    root.attributes("-topmost", True)
    root.deiconify()
    root.lift()
    root.focus_force()
    root.update()
    try:
        ctypes.windll.user32.SetForegroundWindow(root.winfo_id())
    except Exception:
        pass
    return root


_ACTIVE_PICK_PROC = None


def _run_tk_dialog(child_code, cfg_data):
    global _ACTIVE_PICK_PROC
    # 若前一個系統選檔對話框還卡在背景，先中止舊程序再開啟新對話框，避免 _PICK_LOCK 鎖死導致直接 cancel
    old_p = _ACTIVE_PICK_PROC
    if old_p is not None and old_p.poll() is None:
        try:
            old_p.terminate()
            old_p.wait(timeout=1.5)
        except Exception:
            try:
                old_p.kill()
            except Exception:
                pass
        _ACTIVE_PICK_PROC = None

    _PICK_LOCK.acquire()
    try:
        if getattr(sys, "frozen", False):
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = _prepare_topmost_tk_root(tk)
                res = ""
                if "file_types" in cfg_data:
                    ft = cfg_data.get("file_types") or [("Excel 活頁簿 (*.xlsx)", "*.xlsx"), ("所有檔案 (*.*)", "*.*")]
                    res = filedialog.askopenfilename(
                        parent=root,
                        title=cfg_data.get("title", "選擇檔案"),
                        initialdir=cfg_data.get("init_dir", ""),
                        filetypes=ft
                    )
                else:
                    res = filedialog.askdirectory(
                        parent=root,
                        title=cfg_data.get("title", "選擇資料夾"),
                        initialdir=cfg_data.get("init_dir", "")
                    )
                root.destroy()
                return (res or "").strip()
            except Exception as e:
                print(f"[_run_tk_dialog in-process error] {e}")
                return ""

        try:
            import ctypes
            try:
                ctypes.windll.user32.AllowSetForegroundWindow(-1)
            except Exception:
                pass
            sub_env = dict(os.environ)
            sub_env["PYTHONIOENCODING"] = "utf-8"
            sub_env["PYTHONUTF8"] = "1"
            proc = subprocess.Popen(
                [sys.executable, "-c", child_code, json.dumps(cfg_data, ensure_ascii=False)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=sub_env,
            )
            _ACTIVE_PICK_PROC = proc
            try:
                out, _err = proc.communicate(timeout=180)
                return (out or "").strip()
            except subprocess.TimeoutExpired:
                proc.kill()
                return ""
            finally:
                if _ACTIVE_PICK_PROC is proc:
                    _ACTIVE_PICK_PROC = None
        except Exception as e:
            print(f"[_run_tk_dialog subprocess error] {e}")
            return ""
    finally:
        _PICK_LOCK.release()


def pick_file_native(file_types=None, title="選擇要檢查與修復的 Centimani Excel 腳本"):
    init_dir = get_last_opened_dir()
    child_code = """
import sys, json, os, ctypes
try:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    import tkinter as tk
    from tkinter import filedialog
    try:
        ctypes.windll.user32.AllowSetForegroundWindow(-1)
    except Exception:
        pass
    cfg = json.loads(sys.argv[1])
    root = tk.Tk()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"1x1+{sw // 2}+{sh // 3}")
    root.overrideredirect(True)
    try:
        root.attributes('-alpha', 0.01)
    except Exception:
        pass
    root.attributes('-topmost', True)
    root.deiconify()
    root.lift()
    root.focus_force()
    root.update()
    try:
        ctypes.windll.user32.SetForegroundWindow(root.winfo_id())
    except Exception:
        pass
    ft = []
    if cfg.get('file_types'):
        for desc, pat in cfg['file_types']:
            ft.append((desc, pat))
    else:
        ft.append(('Excel 活頁簿 (*.xlsx;*.xlsm)', '*.xlsx;*.xlsm'))
        ft.append(('所有檔案 (*.*)', '*.*'))
    init_d = cfg.get('init_dir', '')
    if not init_d or not os.path.isdir(init_d):
        init_d = os.getcwd()
    path = filedialog.askopenfilename(
        parent=root,
        title=cfg.get('title', '選擇檔案'),
        initialdir=init_d,
        filetypes=ft
    )
    root.destroy()
    if path:
        sys.stdout.write(path)
except Exception as e:
    sys.stderr.write(str(e))
"""
    cfg_data = {
        "title": title,
        "init_dir": init_dir,
        "file_types": file_types or []
    }
    selected = _run_tk_dialog(child_code, cfg_data)
    if selected and os.path.exists(selected):
        set_last_opened_dir(os.path.dirname(os.path.abspath(selected)))
        return selected
    return ""


def pick_folder_native(title="選擇要批次掃描的 Centimani 專案資料夾"):
    init_dir = get_last_opened_dir()
    child_code = """
import sys, json, os, ctypes
try:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    import tkinter as tk
    from tkinter import filedialog
    try:
        ctypes.windll.user32.AllowSetForegroundWindow(-1)
    except Exception:
        pass
    cfg = json.loads(sys.argv[1])
    root = tk.Tk()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"1x1+{sw // 2}+{sh // 3}")
    root.overrideredirect(True)
    try:
        root.attributes('-alpha', 0.01)
    except Exception:
        pass
    root.attributes('-topmost', True)
    root.deiconify()
    root.lift()
    root.focus_force()
    root.update()
    try:
        ctypes.windll.user32.SetForegroundWindow(root.winfo_id())
    except Exception:
        pass
    path = filedialog.askdirectory(
        parent=root,
        title=cfg.get('title', '選擇資料夾'),
        initialdir=cfg.get('init_dir', '')
    )
    root.destroy()
    if path:
        sys.stdout.write(path)
except Exception as e:
    sys.stderr.write(str(e))
"""
    cfg_data = {
        "title": title,
        "init_dir": init_dir
    }
    selected = _run_tk_dialog(child_code, cfg_data)
    if selected and os.path.exists(selected):
        set_last_opened_dir(selected)
        return selected
    return ""


def _is_scannable_testflow(fname):
    low = fname.lower()
    if not low.endswith(".xlsx"):
        return False
    if low.startswith(("~$", "old_", "test item code")):
        return False
    stem = os.path.splitext(low)[0]
    if stem.endswith(("_fixed", "_dryrun")):
        return False
    return True


def _scan_project_folder(root_dir):
    candidates = []
    dir_counts = {}
    for r, _dirs, files in os.walk(root_dir):
        valid_in_dir = [f for f in files if _is_scannable_testflow(f)]
        if valid_in_dir:
            dir_counts[r] = len(valid_in_dir)
            for f in sorted(valid_in_dir):
                candidates.append((r, os.path.join(r, f)))

    items = []
    for r, p in candidates:
        rel_path = os.path.relpath(p, root_dir)
        base_name = os.path.splitext(os.path.basename(p))[0]
        for sfx in ["_Fixed", "_FIXED", "_DryRun", "temp_uploaded"]:
            base_name = base_name.replace(sfx, "")
        fixed_path = os.path.join(r, f"{base_name}_FIXED.xlsx")
        has_fixed = os.path.exists(fixed_path)
        try:
            ws = import_excel_to_workspace(p)
            rep = audit_workspace(ws)
            items.append({
                "file_path": p,
                "rel_path": rel_path,
                "sheet_count": len(ws.get("stations", {})),
                "error_count": rep.get("error_count", 0),
                "manual_warning_count": rep.get("manual_warning_count", 0),
                "auto_fix_warning_count": rep.get("auto_fix_warning_count", 0),
                "jump_issues": sum(1 for j in rep.get("jump_summaries", []) if j.get("status") != "ok"),
                "has_fixed": has_fixed,
                "multi_xlsx_in_dir": dir_counts.get(r, 1) > 1,
                "status": "error" if rep.get("error_count", 0) > 0 else ("warning" if rep.get("manual_warning_count", 0) > 0 else "ok")
            })
        except Exception as e:
            items.append({
                "file_path": p,
                "rel_path": rel_path,
                "sheet_count": 0,
                "error_count": 1,
                "manual_warning_count": 0,
                "auto_fix_warning_count": 0,
                "jump_issues": 0,
                "has_fixed": has_fixed,
                "multi_xlsx_in_dir": dir_counts.get(r, 1) > 1,
                "status": "read_error",
                "error_msg": str(e)
            })
    return items


def _bring_window_to_front(class_name, title_keyword="", max_wait_sec=3.5, maximize=False):
    """Polls for a visible window matching class_name/title_keyword and raises it above fullscreen Chrome."""
    import time, ctypes
    try:
        user32 = ctypes.windll.user32
        try:
            user32.AllowSetForegroundWindow(-1)
        except Exception:
            pass
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        kw_low = (title_keyword or "").lower()
        deadline = time.time() + max_wait_sec
        while time.time() < deadline:
            matched = []
            def _cb(hwnd, _lp):
                if user32.IsWindowVisible(hwnd):
                    buf_cls = ctypes.create_unicode_buffer(64)
                    user32.GetClassNameW(hwnd, buf_cls, 64)
                    if buf_cls.value == class_name:
                        buf_txt = ctypes.create_unicode_buffer(256)
                        user32.GetWindowTextW(hwnd, buf_txt, 256)
                        t_low = buf_txt.value.lower()
                        if not kw_low or kw_low in t_low:
                            matched.append(hwnd)
                return True
            user32.EnumWindows(WNDENUMPROC(_cb), 0)
            if matched:
                hwnd = matched[0]
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                if maximize:
                    user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
                # Toggle HWND_TOPMOST (-1) then HWND_NOTOPMOST (-2) to raise above Chrome Z-order
                user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
                user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
                user32.SetForegroundWindow(hwnd)
                return True
            time.sleep(0.25)
    except Exception:
        pass
    return False


def open_folder_in_explorer(folder_path):
    """Reliably opens folder in Windows Explorer and brings it in front of Chrome."""
    try:
        if not folder_path or not os.path.exists(folder_path):
            return
        norm_path = os.path.normpath(folder_path)

        def _task():
            try:
                subprocess.Popen(["explorer.exe", norm_path])
                _bring_window_to_front("CabinetWClass", os.path.basename(norm_path), max_wait_sec=2.5, maximize=False)
            except Exception as e:
                print(f"[open_folder_in_explorer] Popen explorer.exe failed: {e}")

        threading.Thread(target=_task, daemon=True).start()
    except Exception as e:
        print(f"[open_folder_in_explorer] error: {e}")


def _find_excel_executable():
    """Locates EXCEL.EXE from Windows Registry App Paths or standard Office directories."""
    candidates = [
        r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
        r"C:\Program Files\Microsoft Office\Office16\EXCEL.EXE",
        r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
        r"C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE",
        r"C:\Program Files\Microsoft Office\Office15\EXCEL.EXE",
    ]
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\excel.exe") as key:
            val, _ = winreg.QueryValueEx(key, "")
            if val and os.path.exists(val):
                candidates.insert(0, val)
    except Exception:
        pass
    for exe in candidates:
        if os.path.exists(exe):
            return exe
    return None


def launch_excel_file_async(file_path):
    """
    Reliably launches Microsoft Excel for the given file in a single debounced background thread,
    avoiding duplicate thread DDE collisions and raising the Excel window above fullscreen Chrome.
    """
    if not file_path or not os.path.exists(file_path):
        return

    import time
    norm_p = os.path.abspath(file_path)
    with _EXCEL_LAUNCH_LOCK:
        now = time.time()
        if _LAST_EXCEL_LAUNCH["path"] == norm_p and (now - _LAST_EXCEL_LAUNCH["time"]) < 1.5:
            return
        _LAST_EXCEL_LAUNCH["path"] = norm_p
        _LAST_EXCEL_LAUNCH["time"] = now

    def _open_task():
        launched = False
        excel_exe = _find_excel_executable()
        if excel_exe:
            try:
                subprocess.Popen([excel_exe, norm_p])
                launched = True
            except Exception as e_exe:
                print(f"[launch_excel_file_async] direct EXCEL.EXE spawn failed: {e_exe}")

        if not launched:
            try:
                os.startfile(norm_p)
                launched = True
            except Exception as e_sf:
                print(f"[launch_excel_file_async] os.startfile failed: {e_sf}")

        if not launched:
            try:
                subprocess.Popen(f'start "" "{norm_p}"', shell=True)
            except Exception as e_cmd:
                print(f"[launch_excel_file_async] cmd start failed: {e_cmd}")

        fname_stem = os.path.splitext(os.path.basename(norm_p))[0]
        if not _bring_window_to_front("XLMAIN", fname_stem, max_wait_sec=4.0, maximize=True):
            _bring_window_to_front("XLMAIN", "", max_wait_sec=1.0, maximize=True)

    threading.Thread(target=_open_task, daemon=True).start()


def launch_ini_file_async(ini_paths):
    """Launches Windows Notepad for the given INI file(s) and raises the window above fullscreen Chrome."""
    if isinstance(ini_paths, str):
        ini_paths = [ini_paths]
    valid_paths = [os.path.abspath(p) for p in (ini_paths or []) if p and os.path.exists(p)]
    if not valid_paths:
        return

    def _task():
        for p in valid_paths:
            try:
                subprocess.Popen(["notepad.exe", p])
            except Exception:
                try:
                    os.startfile(p)
                except Exception:
                    pass
        last_name = os.path.basename(valid_paths[-1])
        if not _bring_window_to_front("Notepad", last_name, max_wait_sec=2.5, maximize=False):
            _bring_window_to_front("Notepad", "", max_wait_sec=1.0, maximize=False)

    threading.Thread(target=_task, daemon=True).start()


def launch_centimani_tool_async(exe_path, working_dir=None):
    """Launches Centimani auxiliary tools (CentimaniSFISTest.exe / DLLtest.exe) cleanly without blocking."""
    if not exe_path or not os.path.isfile(exe_path):
        return False

    def _task():
        try:
            cwd = working_dir if (working_dir and os.path.isdir(working_dir)) else os.path.dirname(exe_path)
            subprocess.Popen([exe_path], cwd=cwd)
        except Exception:
            try:
                os.startfile(exe_path)
            except Exception:
                pass

    threading.Thread(target=_task, daemon=True).start()
    return True


def extract_isn_info(ws):
    """Extracts the configured ISN barcode digit length and rule from DUTs ScanBarcode."""
    import re
    for dut in ws.get("duts", []):
        for k, v in dut.items():
            if "ScanBarcode" in str(k) and v:
                raw = str(v).strip()
                m = re.search(r"\{\s*ISN\s*,\s*(\d+)\s*,\s*([^}]+)\}", raw, re.IGNORECASE)
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
            {"Phase": "1", "Title": "0,Measure Voltage Test,3", "Marco": "", "Instrument": "Voltage", "Switch": "NI6008", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "INST#-#Obtain NI6008 Lock", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f':Dev.VOLTAGE,"RSE,1000,{",".join(channels)}"', "Reply": "0", "EndPrompt": "", "Ref": ref_str, "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": f"INST#-#Read {ch_desc}", "TestID": "BRPW033"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "INST#-#Release NI6008 Lock", "TestID": "BRME027"},
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
                {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f"UART@{cmd}\\r\\n", "Reply": "@", "EndPrompt": "#", "Ref": '$DUT_FW:WithinString,"version=","\\r\\n",""', "Validation": "(DUT_FW,%s,*$(FW_VERSION),*$(FW_VERSION))", "Prompt": "", "Waiting": "5000", "ExecMode": "1", "Description": "DUT#-#Verify Firmware Version (UART)", "TestID": "VSCH026"},
            ]
        elif mode == "adb":
            return [
                {"Phase": "4", "Title": "0,Check ADB & FW Version,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"CmdConsole"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Open CMD Console for ADB", "TestID": "B7PL025"},
                {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f"CmdConsole@{cmd}\\r\\n", "Reply": "@", "EndPrompt": ">", "Ref": '$DUT_FW:WithinString,"version=","\\n",""', "Validation": "(DUT_FW,%s,*$(FW_VERSION),*$(FW_VERSION))", "Prompt": "", "Waiting": "8000", "ExecMode": "1", "Description": "DUT#-#Verify Firmware Version (ADB)", "TestID": "VSCH026"},
                {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Disconnect,"CmdConsole"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Close CMD Console", "TestID": "B7PL025"},
            ]
        elif mode == "ssh":
            return [
                {"Phase": "4", "Title": "0,Check SSH & FW Version,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"CmdConsole"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Open CMD Console for SSH", "TestID": "B7PL025"},
                {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f"CmdConsole@{cmd}\\r\\n", "Reply": "@", "EndPrompt": ">", "Ref": '$DUT_FW:WithinString,"version=","\\n",""', "Validation": "(DUT_FW,%s,*$(FW_VERSION),*$(FW_VERSION))", "Prompt": "", "Waiting": "8000", "ExecMode": "1", "Description": "DUT#-#Verify Firmware Version (SSH)", "TestID": "VSCH026"},
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
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f'CmdConsole@cd *$(PythonPath)&&cmd /c python.exe {script_name} "*(ISN)"\\r\\n', "Reply": "@Command pass", "EndPrompt": ">", "Ref": f'$PyVal:WithinString,"{prefix}","\\n",""', "Validation": f"(PyVal,%f,{pmin},{pmax})", "Prompt": "", "Waiting": "10000", "ExecMode": "1", "Description": f"PC#-#Execute {script_name} & Validate Output", "TestID": "OTFX054"},
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
        last_inst = ""
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
            row_inst = "MeasWIFI" if last_inst != "MeasWIFI" else ""
            last_inst = "MeasWIFI"
            steps.append({
                "Phase": "9" if len(steps) == 0 else "",
                "Title": f"0,{lbl}",
                "Marco": "WIFI Tx MCS",
                "Instrument": row_inst, "Switch": "InstIQApiA" if row_inst else "",
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
            row_inst = "GenWIFI" if last_inst != "GenWIFI" else ""
            last_inst = "GenWIFI"
            steps.append({
                "Phase": "9" if len(steps) == 0 else "",
                "Title": f"0,{lbl}",
                "Marco": "WIFI Rx MCS",
                "Instrument": row_inst, "Switch": "InstIQApiA" if row_inst else "",
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
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Dev.Switch,"1,0"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Power#-#Turn OFF Channel 1", "TestID": "BRPW011"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f':Delay,"{delay_ms}"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": f"PC#-#Wait Discharge ({delay_ms}ms)", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Dev.Switch,"1,1"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Power#-#Turn ON Channel 1", "TestID": "BRPW011"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "Power#-#Release iPower Lock", "TestID": "BRME027"},
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
            {"Phase": "2", "Title": f"0,Measure {nm},3", "Marco": "", "Instrument": "Voltage", "Switch": "NI6008", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "INST#-#Obtain NI6008 Lock", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f':Dev.VOLTAGE,"DIFF,2000,{ch}"', "Reply": "0", "EndPrompt": "", "Ref": f"${nm}", "Validation": f"({nm},%f,{vmin},{vmax})", "Prompt": "", "Waiting": "", "ExecMode": "2:0", "Description": f"DUT#-#Measure {nm} ({vmin}V~{vmax}V)", "TestID": "BRPW024"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "INST#-#Release NI6008 Lock", "TestID": "BRME027"},
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
            {"Phase": "8", "Title": "0,Check LED Color & Intensity,3", "Marco": "", "Instrument": "LED_Test", "Switch": "FeasaLED", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "LED#-#Obtain Feasa LED Lock", "TestID": "BRME027"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": f':Dev.CaptureAndRead,"{ch}"', "Reply": "0", "EndPrompt": "", "Ref": "$LED_Wave;\n$LED_Int", "Validation": f"(LED_Wave,%f,{wmin},{wmax});\n(LED_Int,%f,{imin},{imax})", "Prompt": "", "Waiting": "", "ExecMode": "2:0", "Description": f"LED#-#Verify Ch{ch} Wavelength({wmin}~{wmax}) & Intensity", "TestID": "IOLE015"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "LED#-#Release Feasa LED Lock", "TestID": "BRME027"},
        ]

    if bid == "BLK_SFIS_MAC_69PN":
        sf = wizard_config.get("sfis_config") or {}
        if sf.get("use_hmi_items") and sf.get("hmi_items"):
            from core.sfis_client import build_sfis_excel_steps
            raw_items = [it for it in (sf.get("hmi_items") or []) if str(it.get("kind", "")).lower() not in ("login", "logout")]
            has_pre = bool(sf.get("has_pretest_route", False))
            if has_pre:
                raw_items = [it for it in raw_items if str(it.get("kind", "")).lower() != "checkroute"]
            if raw_items:
                return build_sfis_excel_steps(raw_items, start_phase=0 if not has_pre else 5, include_show_isn=not has_pre)
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
        try:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ["/", "/index.html"]:
            html_path = os.path.join(BASE_DIR, "web", "index.html")
            with open(html_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif parsed.path.startswith("/images/"):
            fname = os.path.basename(unquote(parsed.path[len("/images/"):]))
            img_path = os.path.join(PROJECT_ROOT, "IMAGES", fname)
            if not fname or not os.path.exists(img_path):
                self.send_error(404)
                return
            ext = os.path.splitext(fname)[1].lower()
            ctype = "image/png" if ext == ".png" else ("image/jpeg" if ext in (".jpg", ".jpeg") else "application/octet-stream")
            with open(img_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif parsed.path.startswith("/css/") or parsed.path.startswith("/js/"):
            sub = "css" if parsed.path.startswith("/css/") else "js"
            fname = os.path.basename(unquote(parsed.path.split("/", 2)[2]))
            fpath = os.path.join(BASE_DIR, "web", sub, fname)
            if not fname or not os.path.exists(fpath):
                self.send_error(404)
                return
            ctype = "text/css; charset=utf-8" if sub == "css" else "application/javascript; charset=utf-8"
            with open(fpath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif parsed.path == "/api/init":
            from core.golden_data import scan_centimani_environment
            self._send_json({
                "server_build": "Build v0.8.055",
                "blocks": STANDARD_BLOCKS,
                "last_dir": get_last_opened_dir(),
                "recent_files": get_recent_excel_files(),
                "tic_info": get_active_tic_info(),
                "settings": get_app_settings(),
                "centimani_profile": scan_centimani_environment(persist=False)
            })
        elif parsed.path == "/api/template_bundle/catalog":
            from core.template_sku_engine import list_perter_templates
            self._send_json({"status": "ok", **list_perter_templates()})
        elif parsed.path == "/api/recent_files":
            self._send_json({
                "status": "ok",
                "recent_files": get_recent_excel_files()
            })
        elif parsed.path == "/api/browse_dir":
            qs = parse_qs(parsed.query)
            target_d = qs.get("dir", [""])[0]
            if not target_d or not os.path.exists(target_d):
                target_d = get_last_opened_dir()
            target_d = os.path.abspath(target_d)

            parent_d = os.path.dirname(target_d) if os.path.dirname(target_d) != target_d else ""
            folders = []
            files = []
            try:
                for item in os.listdir(target_d):
                    full_p = os.path.join(target_d, item)
                    if os.path.isdir(full_p):
                        if not item.startswith("."):
                            folders.append({"name": item, "path": full_p})
                    elif os.path.isfile(full_p):
                        if item.lower().endswith(".xlsx") and not item.startswith("~"):
                            try:
                                sz = round(os.path.getsize(full_p) / 1024, 1)
                                mtime = os.path.getmtime(full_p)
                                files.append({"name": item, "path": full_p, "size_kb": sz, "mtime": mtime})
                            except Exception:
                                pass
                folders.sort(key=lambda x: x["name"].lower())
                files.sort(key=lambda x: x["mtime"], reverse=True)
            except Exception as e:
                pass

            self._send_json({
                "status": "ok",
                "current_dir": target_d,
                "parent_dir": parent_d,
                "folders": folders,
                "files": files
            })
        elif parsed.path == "/api/get_settings":
            from core.golden_data import get_configured_centimani_dir
            s = get_app_settings()
            if not s.get("centimani_dir"):
                s["centimani_dir"] = get_configured_centimani_dir()
            self._send_json({"status": "ok", "settings": s})
        elif parsed.path == "/api/instrument_catalog":
            gm = get_golden_mother()
            prof_path = os.path.join(BASE_DIR, "core", "instrument_profiles.json")
            profiles = {}
            if os.path.exists(prof_path):
                try:
                    with open(prof_path, "r", encoding="utf-8") as pf:
                        profiles = json.load(pf)
                except Exception:
                    profiles = {}
            self._send_json({
                "status": "ok",
                "instruments": gm.get("instruments", []),
                "profiles": profiles
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
            qs = parse_qs(parsed.query)
            path_only = qs.get("path_only", ["0"])[0] in ("1", "true", "True")
            dlg_title = qs.get("title", [""])[0] or "選擇要檢查與修復的 Centimani Excel 腳本"
            selected_path = pick_file_native(title=dlg_title)
            if not selected_path:
                self._send_json({"status": "cancel"})
                return
            if path_only:
                self._send_json({"status": "ok", "file_path": selected_path})
                return
            ws = import_excel_to_workspace(selected_path)
            rep = audit_workspace(ws)
            self._send_json({
                "status": "ok",
                "file_path": selected_path,
                "workspace": ws,
                "report": rep,
                "recent_files": get_recent_excel_files(),
                "isn_info": extract_isn_info(ws)
            })
        elif parsed.path == "/api/load_specific_file":
            qs = parse_qs(parsed.query)
            selected_path = qs.get("path", [""])[0]
            if not selected_path or not os.path.exists(selected_path):
                self._send_json({"status": "error", "message": "找不到指定檔案"}, 404)
                return
            set_last_opened_dir(os.path.dirname(os.path.abspath(selected_path)))
            ws = import_excel_to_workspace(selected_path)
            rep = audit_workspace(ws)
            self._send_json({
                "status": "ok",
                "file_path": selected_path,
                "workspace": ws,
                "report": rep,
                "recent_files": get_recent_excel_files(),
                "isn_info": extract_isn_info(ws)
            })
        elif parsed.path == "/api/pick_folder_and_scan":
            root_dir = pick_folder_native()
            if not root_dir:
                self._send_json({"status": "cancel"})
                return
            items = _scan_project_folder(root_dir)
            self._send_json({
                "status": "ok",
                "root_dir": root_dir,
                "items": items
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
        elif parsed.path == "/api/sfis_hmi_profiles":
            from core.sfis_client import SFIS_PLANT_PRESETS, DEFAULT_VIRTUAL_MO_TEMPLATES
            prof_file = os.path.join(BASE_DIR, "sfis_hmi_profiles.json")
            saved = {}
            if os.path.exists(prof_file):
                try:
                    with open(prof_file, "r", encoding="utf-8") as f:
                        saved = json.load(f) or {}
                except Exception:
                    saved = {}
            self._send_json({
                "status": "ok",
                "plants": saved.get("plants") or SFIS_PLANT_PRESETS,
                "virtual_mos": saved.get("virtual_mos") or DEFAULT_VIRTUAL_MO_TEMPLATES,
                "used_isns": saved.get("used_isns") or [],
                "default_plants": SFIS_PLANT_PRESETS,
                "default_virtual_mos": DEFAULT_VIRTUAL_MO_TEMPLATES,
            })
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/upload_and_analyze_log":
            # Direct multipart file upload for Log / CSV with zero UI dialog freeze
            fields = _parse_multipart_form(self.headers, self.rfile)
            if fields is not None:
                file_items = fields.get("log_file", [])
                if not file_items:
                    self._send_json({"status": "error", "message": "未收到上傳的 Log 檔案"}, 400)
                    return
                raw_bytes = file_items[0]
                content = ""
                for enc in ["utf-8", "big5", "cp950", "gbk", "latin-1"]:
                    try:
                        content = raw_bytes.decode(enc)
                        break
                    except Exception:
                        pass
                if not content:
                    content = raw_bytes.decode("latin-1", errors="replace")

                # Cache uploaded log to a temporary file so '🔄 重新解析本檔' works seamlessly!
                scratch_dir = os.path.join(BASE_DIR, "uploaded_temp")
                os.makedirs(scratch_dir, exist_ok=True)
                cached_log_path = os.path.join(scratch_dir, "last_uploaded_log.log")
                try:
                    with open(cached_log_path, "wb") as f_cache:
                        f_cache.write(raw_bytes)
                except Exception:
                    pass

                res = analyze_centimani_log(content)
                self._send_json({
                    "status": "ok",
                    "file_path": cached_log_path,
                    "file_size_kb": round(len(raw_bytes) / 1024, 2),
                    "log_snippet": content[:1200] if len(content) > 1200 else content,
                    "result": res
                })
            else:
                self._send_json({"status": "error", "message": "Invalid content-type"}, 400)
            return

        if parsed.path == "/api/upload_and_audit":
            # Handles multipart file upload from web browser, preserving real filename & resolving original project folder!
            fields = _parse_multipart_form(self.headers, self.rfile)
            if fields is not None:
                file_items = fields.get("excel_file", [])
                if not file_items:
                    self._send_json({"status": "error", "message": "未收到上傳的 Excel 檔案"}, 400)
                    return
                file_bytes = file_items[0]
                orig_fname = fields.get("excel_file__filename", "") or "Uploaded_TestFlow.xlsx"
                orig_fname = os.path.basename(orig_fname).strip() or "Uploaded_TestFlow.xlsx"

                # Try resolving to the real local file in last_dir or SCRIPTS_ROOT so in-place export saves in the original folder!
                resolved_path = ""
                search_roots = []
                last_d = get_last_opened_dir()
                if last_d and os.path.exists(last_d):
                    search_roots.append(last_d)
                if os.path.exists(SCRIPTS_ROOT) and SCRIPTS_ROOT not in search_roots:
                    search_roots.append(SCRIPTS_ROOT)
                if os.path.exists(PROJECT_ROOT) and PROJECT_ROOT not in search_roots:
                    search_roots.append(PROJECT_ROOT)

                for s_root in search_roots:
                    direct_cand = os.path.join(s_root, orig_fname)
                    if os.path.isfile(direct_cand) and os.path.getsize(direct_cand) == len(file_bytes):
                        resolved_path = direct_cand
                        break
                    for r_dir, _d_names, f_names in os.walk(s_root):
                        if "uploaded_temp" in r_dir or "output_system" in r_dir:
                            continue
                        for fn in f_names:
                            if fn.lower() == orig_fname.lower():
                                full_c = os.path.join(r_dir, fn)
                                try:
                                    if os.path.getsize(full_c) == len(file_bytes):
                                        resolved_path = full_c
                                        break
                                except Exception:
                                    pass
                        if resolved_path:
                            break
                    if resolved_path:
                        break

                if resolved_path:
                    temp_path = resolved_path
                    set_last_opened_dir(os.path.dirname(os.path.abspath(resolved_path)))
                else:
                    stem = os.path.splitext(orig_fname)[0] or "Uploaded_Script"
                    for sfx in ["_Fixed", "_FIXED", "_DryRun", "temp_uploaded"]:
                        stem = stem.replace(sfx, "")
                    upload_out_dir = os.path.join(OUTPUT_ROOT, f"{stem}_Uploaded", "System")
                    os.makedirs(upload_out_dir, exist_ok=True)
                    temp_path = os.path.join(upload_out_dir, orig_fname)
                    try:
                        with open(temp_path, "wb") as f:
                            f.write(file_bytes)
                    except (PermissionError, IOError):
                        import time
                        ext = os.path.splitext(orig_fname)[1] or ".xlsx"
                        temp_path = os.path.join(upload_out_dir, f"{stem}_{time.strftime('%H%M%S')}{ext}")
                        with open(temp_path, "wb") as f:
                            f.write(file_bytes)

                ws = import_excel_to_workspace(temp_path)
                rep = audit_workspace(ws)
                self._send_json({
                    "status": "ok",
                    "file_path": temp_path,
                    "workspace": ws,
                    "report": rep,
                    "recent_files": get_recent_excel_files(),
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

            if parsed.path == "/api/save_settings":
                updated = save_app_settings(payload.get("settings", {}))
                self._send_json({"status": "ok", "settings": updated})
                return

            if parsed.path == "/api/re_audit":
                ws = payload.get("workspace", {})
                rep = audit_workspace(ws)
                self._send_json({
                    "status": "ok",
                    "report": rep,
                    "isn_info": extract_isn_info(ws)
                })
                return

            if parsed.path == "/api/apply_safety_fix":
                ws = payload.get("workspace", {})
                sheet_name = payload.get("sheet_name", "")
                fix_kind = payload.get("fix_kind", "")
                added = apply_safety_ending_fix(ws, sheet_name, fix_kind)
                rep = audit_workspace(ws)
                self._send_json({
                    "status": "ok",
                    "added_rows": added,
                    "workspace": ws,
                    "report": rep
                })
                return

            if parsed.path == "/api/insert_instrument_block":
                ws = payload.get("workspace")
                if not ws or not isinstance(ws, dict):
                    # 若前端未載入任何腳本直接插入儀器，後台自動提供 Golden Mother 避免 NoneType 例外
                    ws = get_golden_mother("INST_PROJECT", "MB")
                sheet_name = payload.get("sheet_name") or ""
                if not sheet_name or sheet_name not in ws.get("stations", {}):
                    avail = list(ws.get("stations", {}).keys())
                    sheet_name = avail[0] if avail else "MB"
                    if sheet_name not in ws.get("stations", {}):
                        ws.setdefault("stations", {})[sheet_name] = []
                inst_name = payload.get("inst_name", "")
                title_name = payload.get("title_name", "")
                after_block_idx = int(payload.get("after_block_idx", -1))
                dl_val = payload.get("dl_val", "")
                ul_val = payload.get("ul_val", "")
                added = insert_instrument_title_block(
                    ws, sheet_name, inst_name, title_name,
                    after_block_idx=after_block_idx, dl_val=dl_val, ul_val=ul_val,
                    custom_steps=payload.get("custom_steps"),
                    globals_patch=payload.get("globals_patch"),
                    use_ini_switch=bool(payload.get("use_ini_switch", False))
                )
                if bool(payload.get("no_hw_phase_pause", False)):
                    from core.block_sorter import pause_hardware_phases_minus_one
                    pause_hardware_phases_minus_one(ws, target_sheet=sheet_name)
                rep = audit_workspace(ws)
                self._send_json({
                    "status": "ok",
                    "added_rows": added,
                    "workspace": ws,
                    "report": rep
                })
                return

            if parsed.path == "/api/insert_ni6009_block":
                ws = payload.get("workspace")
                if not ws or not isinstance(ws, dict):
                    ws = get_golden_mother("NI6009_PROJECT", "MB")
                sheet_name = payload.get("sheet_name") or ""
                if not sheet_name or sheet_name not in ws.get("stations", {}):
                    avail = list(ws.get("stations", {}).keys())
                    sheet_name = avail[0] if avail else "MB"
                    if sheet_name not in ws.get("stations", {}):
                        ws.setdefault("stations", {})[sheet_name] = []
                added = insert_ni6009_block(
                    ws,
                    sheet_name=sheet_name,
                    mode=payload.get("mode", "RSE"),
                    sample_ms=str(payload.get("sample_ms", "1000")),
                    dev_id=str(payload.get("dev_id", "Dev1")),
                    title_name=str(payload.get("title_name", "Measure Voltage Test")),
                    channels=payload.get("channels", []),
                    after_block_idx=int(payload.get("after_block_idx", -1)),
                    use_ini_switch=bool(payload.get("use_ini_switch", False)),
                    inst_name=str(payload.get("inst_name", "NI6008") or "NI6008")
                )
                if bool(payload.get("no_hw_phase_pause", False)):
                    from core.block_sorter import pause_hardware_phases_minus_one
                    pause_hardware_phases_minus_one(ws, target_sheet=sheet_name)
                rep = audit_workspace(ws)
                self._send_json({
                    "status": "ok",
                    "added_rows": added,
                    "workspace": ws,
                    "report": rep
                })
                return

            if parsed.path == "/api/insert_rf_iqxel_block":
                ws = payload.get("workspace")
                if not ws or not isinstance(ws, dict):
                    ws = get_golden_mother("RF_PROJECT", "MB")
                sheet_name = payload.get("sheet_name") or ""
                if not sheet_name or sheet_name not in ws.get("stations", {}):
                    avail = list(ws.get("stations", {}).keys())
                    sheet_name = avail[0] if avail else "MB"
                    if sheet_name not in ws.get("stations", {}):
                        ws.setdefault("stations", {})[sheet_name] = []
                added = insert_rf_iqxel_block(
                    ws,
                    sheet_name=sheet_name,
                    inst_name=str(payload.get("inst_name", "InstIQApiA")),
                    title_name=str(payload.get("title_name", "WIFI RF Test")),
                    settings_str=str(payload.get("settings_str", "")),
                    tx_tests=payload.get("tx_tests", []),
                    rx_tests=payload.get("rx_tests", []),
                    after_block_idx=int(payload.get("after_block_idx", -1)),
                    use_ini_switch=bool(payload.get("use_ini_switch", False))
                )
                if bool(payload.get("no_hw_phase_pause", False)):
                    from core.block_sorter import pause_hardware_phases_minus_one
                    pause_hardware_phases_minus_one(ws, target_sheet=sheet_name)
                rep = audit_workspace(ws)
                self._send_json({
                    "status": "ok",
                    "added_rows": added,
                    "workspace": ws,
                    "report": rep
                })
                return

            if parsed.path == "/api/update_comm_settings":
                ws = payload.get("workspace", {})
                converted = update_comm_settings(
                    ws,
                    dut_ur1=str(payload.get("dut_ur1", "")),
                    dut_ip1=str(payload.get("dut_ip1", "")),
                    dut_login=str(payload.get("dut_login", "")),
                    convert_uart_to_ssh=bool(payload.get("convert_uart_to_ssh", False)),
                    target_sheet=str(payload.get("target_sheet", ""))
                )
                rep = audit_workspace(ws)
                self._send_json({
                    "status": "ok",
                    "converted_rows": converted,
                    "workspace": ws,
                    "report": rep
                })
                return

            if parsed.path == "/api/batch_fix_folder":
                import shutil
                file_paths = payload.get("file_paths", [])
                root_dir = payload.get("root_dir", "")
                results = []
                for src_file in file_paths:
                    if not src_file or not os.path.exists(src_file):
                        continue
                    try:
                        orig_dir = os.path.dirname(os.path.abspath(src_file))
                        base_name = os.path.splitext(os.path.basename(src_file))[0]
                        for sfx in ["_Fixed", "_FIXED", "_DryRun", "temp_uploaded"]:
                            base_name = base_name.replace(sfx, "")
                        if not base_name:
                            base_name = "Centimani_TestFlow"
                        fixed_xlsx_name = f"{base_name}_FIXED.xlsx"

                        for ini_n in ("System.ini", "Global.ini"):
                            ini_p = os.path.join(orig_dir, ini_n)
                            bak_p = os.path.join(orig_dir, f"{ini_n}.bak")
                            if os.path.exists(ini_p) and not os.path.exists(bak_p):
                                shutil.copy2(ini_p, bak_p)

                        ws = import_excel_to_workspace(src_file)
                        rep_before = audit_workspace(ws)
                        choices = {c["card_id"]: c["recommended_value"] for c in rep_before.get("choice_cards", [])}
                        fixed_logs = auto_fix_workspace(ws, user_choices=choices)
                        out_xlsx_path = os.path.join(orig_dir, fixed_xlsx_name)
                        export_workspace_to_excel(ws, out_xlsx_path)
                        sys_ini, _ = sync_and_generate_inis(ws, fixed_xlsx_name, orig_dir)
                        generate_official_checksum(out_xlsx_path, sys_ini)
                        results.append({
                            "file_path": src_file,
                            "fixed_path": out_xlsx_path,
                            "fixed_count": len(fixed_logs),
                            "status": "ok"
                        })
                    except Exception as e:
                        results.append({
                            "file_path": src_file,
                            "status": "error",
                            "message": str(e)
                        })
                if root_dir and os.path.exists(root_dir):
                    open_folder_in_explorer(root_dir)
                self._send_json({
                    "status": "ok",
                    "fixed_files": sum(1 for r in results if r["status"] == "ok"),
                    "results": results
                })
                return

            if parsed.path == "/api/get_station_blocks":
                from core.block_sorter import (
                    extract_station_blocks,
                    serialize_blocks_for_ui,
                    check_var_dependencies,
                )
                ws = payload.get("workspace", {})
                sheet_name = payload.get("sheet_name", "")
                rows = (ws.get("stations") or {}).get(sheet_name, [])
                blocks = extract_station_blocks(rows)
                self._send_json({
                    "status": "ok",
                    "blocks": serialize_blocks_for_ui(blocks),
                    "dep_warnings": check_var_dependencies(blocks),
                })
                return

            if parsed.path == "/api/reorder_station_blocks":
                from core.block_sorter import reorder_station_blocks
                ws = payload.get("workspace", {})
                sheet_name = payload.get("sheet_name", "")
                new_order = payload.get("new_order_indices", [])
                auto_renum = bool(payload.get("auto_renumber_phase", True))
                paused_indices = payload.get("paused_orig_indices", None)
                res = reorder_station_blocks(
                    ws,
                    sheet_name,
                    new_order,
                    auto_renumber_phase=auto_renum,
                    paused_orig_indices=paused_indices,
                )
                rep = audit_workspace(ws)
                self._send_json({
                    "status": "ok",
                    "workspace": ws,
                    "report": rep,
                    "blocks": res["blocks"],
                    "dep_warnings": res["dep_warnings"],
                })
                return

            if parsed.path == "/api/diff_station_sheets":
                from core.block_sorter import diff_station_sheets
                ws = payload.get("workspace", {})
                stations = ws.get("stations", {}) or {}
                st_keys = list(stations.keys())
                sheet_a = payload.get("sheet_a", "").strip()
                sheet_b = payload.get("sheet_b", "").strip()
                if not sheet_a and st_keys:
                    sheet_a = next((k for k in st_keys if not k.endswith("_TAIPEI")), st_keys[0])
                if not sheet_b and st_keys:
                    cand_tp = f"{sheet_a[:24]}_TAIPEI" if len(sheet_a) > 24 else f"{sheet_a}_TAIPEI"
                    if cand_tp in stations:
                        sheet_b = cand_tp
                    else:
                        sheet_b = next((k for k in st_keys if k != sheet_a), "")
                if not sheet_a or not sheet_b or sheet_a not in stations or sheet_b not in stations:
                    self._send_json({
                        "status": "error",
                        "message": "工作簿需要至少 2 個測試站分頁才能進行差異比對（例如 MB 與 MB_TAIPEI）。",
                    }, 400)
                    return
                diff_res = diff_station_sheets(ws, sheet_a, sheet_b)
                self._send_json({"status": "ok", **diff_res})
                return

            if parsed.path == "/api/fix_and_export_in_place":
                ws = payload.get("workspace", {})
                user_choices = payload.get("user_choices", {})
                dry_run = payload.get("dry_run", False)
                taipei_dual_mode = bool(payload.get("taipei_dual_mode", False))
                no_hw_phase_pause = bool(payload.get("no_hw_phase_pause", False))
                station_name_mode = str(payload.get("station_name_mode", "fixed")).strip().lower()
                active_sheet = payload.get("active_sheet", "")
                open_excel = payload.get("open_excel", False)

                src_file = ws.get("source_file", "")
                if not src_file or not os.path.exists(src_file) or "uploaded_temp" in os.path.abspath(src_file):
                    st_first = active_sheet or (list(ws.get("stations", {}).keys())[0] if ws.get("stations") else "MB")
                    proj_first = ws.get("project_name", "Centimani") or "Centimani"
                    fallback_dir = os.path.join(OUTPUT_ROOT, f"{proj_first}_{st_first}_Fixed", "System")
                    os.makedirs(fallback_dir, exist_ok=True)
                    if src_file and os.path.exists(src_file):
                        orig_dir = fallback_dir
                    else:
                        src_file = os.path.join(fallback_dir, f"{proj_first}_TestFlow_{st_first}.xlsx")
                        orig_dir = fallback_dir
                else:
                    orig_dir = os.path.dirname(os.path.abspath(src_file))

                base_name = os.path.splitext(os.path.basename(src_file))[0]
                # Strip previous suffixes if present
                for sfx in ["_Fixed", "_FIXED", "_DryRun", "temp_uploaded"]:
                    base_name = base_name.replace(sfx, "")
                if not base_name:
                    st_first = active_sheet or (list(ws.get("stations", {}).keys())[0] if ws.get("stations") else "MB")
                    base_name = f"Centimani_TestFlow_{st_first}"

                if dry_run:
                    ws_to_export = convert_workspace_to_dry_run(ws)
                    fixed_xlsx_name = f"{base_name}_DryRun.xlsx"
                else:
                    ws_to_export = ws
                    fixed_xlsx_name = f"{base_name}_FIXED.xlsx"

                fixed_logs = auto_fix_workspace(ws_to_export, user_choices=user_choices)
                if no_hw_phase_pause and not dry_run:
                    from core.block_sorter import pause_hardware_phases_minus_one
                    pause_hardware_phases_minus_one(ws_to_export)
                if station_name_mode == "ask":
                    ws_to_export.setdefault("system_ini", {})["StationName_Mode"] = "ask"
                    ws_to_export["system_ini"]["StationName"] = ""
                else:
                    ws_to_export.setdefault("system_ini", {}).pop("StationName_Mode", None)
                    if not ws_to_export["system_ini"].get("StationName"):
                        st_fallback = active_sheet or (next(iter(ws_to_export.get("stations", {}).keys()), "MB"))
                        ws_to_export["system_ini"]["StationName"] = st_fallback

                taipei_sheet = ""
                if taipei_dual_mode and not dry_run:
                    from core.block_sorter import build_taipei_dual_station
                    st_keys_exp = [k for k in (ws_to_export.get("stations") or {}).keys() if not k.endswith("_TAIPEI")]
                    prod_st = active_sheet if (active_sheet and not active_sheet.endswith("_TAIPEI") and active_sheet in (ws_to_export.get("stations") or {})) else (st_keys_exp[0] if st_keys_exp else "")
                    if prod_st:
                        taipei_sheet = build_taipei_dual_station(ws_to_export, prod_st)

                # Export to the original file directory with file lock conflict protection!
                out_xlsx_path = os.path.join(orig_dir, fixed_xlsx_name)
                
                # Check if file is currently open / locked by Excel
                target_xlsx_path = out_xlsx_path
                try:
                    if os.path.exists(target_xlsx_path):
                        # Test write access
                        with open(target_xlsx_path, "a+"):
                            pass
                except (PermissionError, IOError):
                    import time
                    timestamp = time.strftime("%H%M%S")
                    fixed_xlsx_name = f"{base_name}_FIXED_{timestamp}.xlsx"
                    target_xlsx_path = os.path.join(orig_dir, fixed_xlsx_name)
                    print(f"[File Lock Protection] {out_xlsx_path} is locked by Excel. Saving to {target_xlsx_path} instead.")

                actual_xlsx_path = export_workspace_to_excel(ws_to_export, target_xlsx_path, active_sheet=active_sheet)
                actual_xlsx_name = os.path.basename(actual_xlsx_path)

                # Sync and generate INIs in the original directory (preserving original SFIS keys & computing Checksum)
                sys_ini, glb_ini = sync_and_generate_inis(ws_to_export, actual_xlsx_name, orig_dir)
                from core.template_sku_engine import write_companion_files_to_dir
                written_companions = write_companion_files_to_dir(ws_to_export.get("_companion_files"), orig_dir)

                switch_bats = []
                if taipei_sheet:
                    from core.block_sorter import write_env_switch_bats
                    st_keys_exp = [k for k in (ws_to_export.get("stations") or {}).keys() if not k.endswith("_TAIPEI")]
                    prod_st = active_sheet if (active_sheet and not active_sheet.endswith("_TAIPEI")) else (st_keys_exp[0] if st_keys_exp else "MB")
                    switch_bats = write_env_switch_bats(orig_dir, prod_st, taipei_sheet, xlsx_filename=actual_xlsx_name)

                # Re-import and audit BEFORE launching Excel so openpyxl closes the file before Excel locks it!
                ws_re = import_excel_to_workspace(actual_xlsx_path)
                rep_re = audit_workspace(ws_re)

                open_folder_in_explorer(orig_dir)
                if open_excel and os.path.exists(actual_xlsx_path):
                    launch_excel_file_async(actual_xlsx_path)

                from core.golden_data import check_workspace_missing_dlls
                from core.script_notes import generate_companion_logic_txt
                dll_chk = check_workspace_missing_dlls(ws_re)
                guide_txt_path = generate_companion_logic_txt(ws_re, actual_xlsx_path, dll_chk=dll_chk, fixed_logs=fixed_logs, build_ver="Build v0.8.055")

                self._send_json({
                    "status": "ok",
                    "output_dir": orig_dir,
                    "excel_path": actual_xlsx_path,
                    "guide_txt_path": guide_txt_path,
                    "written_companions": written_companions,
                    "taipei_sheet": taipei_sheet,
                    "switch_bats": switch_bats,
                    "system_ini": sys_ini,
                    "global_ini": glb_ini,
                    "checksum": "已自動寫入 [Checksum]",
                    "fixed_logs": fixed_logs,
                    "isn_info": extract_isn_info(ws_re),
                    "workspace": ws_re,
                    "report": rep_re,
                    **dll_chk
                })

            elif parsed.path == "/api/save_and_open_ini":
                ws = payload.get("workspace", {})
                open_target = str(payload.get("open_target", "global")).lower()
                src_file = ws.get("source_file", "")
                if not src_file or not os.path.exists(src_file) or "uploaded_temp" in os.path.abspath(src_file):
                    st_first = list(ws.get("stations", {}).keys())[0] if ws.get("stations") else "MB"
                    proj_first = ws.get("project_name", "Centimani") or "Centimani"
                    orig_dir = os.path.join(OUTPUT_ROOT, f"{proj_first}_{st_first}_Fixed", "System")
                    os.makedirs(orig_dir, exist_ok=True)
                    xlsx_name = f"{proj_first}_TestFlow_{st_first}.xlsx"
                else:
                    orig_dir = os.path.dirname(os.path.abspath(src_file))
                    xlsx_name = os.path.basename(src_file)

                sys_ini, glb_ini = sync_and_generate_inis(ws, xlsx_name, orig_dir)
                to_open = []
                if open_target == "system":
                    to_open = [sys_ini]
                elif open_target == "both":
                    to_open = [glb_ini, sys_ini]
                else:
                    to_open = [glb_ini]

                launch_ini_file_async(to_open)
                rep_re = audit_workspace(ws)
                self._send_json({
                    "status": "ok",
                    "output_dir": orig_dir,
                    "global_ini": glb_ini,
                    "global_ini_path": glb_ini,
                    "system_ini": sys_ini,
                    "system_ini_path": sys_ini,
                    "opened_files": to_open,
                    "workspace": ws,
                    "report": rep_re,
                })

            elif parsed.path == "/api/open_excel_file":
                fpath = payload.get("file_path", "")
                if not fpath or not os.path.exists(fpath):
                    self._send_json({"status": "error", "message": "找不到該 Excel 檔案"}, 404)
                    return
                if not fpath.lower().endswith((".xlsx", ".xls")):
                    self._send_json({"status": "error", "message": "僅支援開啟 Excel 檔案"}, 400)
                    return
                launch_excel_file_async(fpath)
                self._send_json({"status": "ok"})

            elif parsed.path == "/api/open_guide_txt":
                fpath = str(payload.get("file_path", "")).strip()
                if not fpath or not os.path.exists(fpath):
                    self._send_json({"status": "error", "message": "找不到編寫與使用說明 .txt 檔案"}, 404)
                    return
                if not fpath.lower().endswith(".txt"):
                    self._send_json({"status": "error", "message": "僅支援開啟 .txt 說明檔案"}, 400)
                    return
                launch_ini_file_async([fpath])
                self._send_json({"status": "ok"})

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
                sf_cfg_wiz = wizard_config.get("sfis_config")
                if isinstance(sf_cfg_wiz, dict):
                    sf_cfg_wiz["has_pretest_route"] = ("BLK_PRETEST_ROUTE" in sorted_block_ids)
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

                # Keep only instruments actually referenced by selected blocks (cleaner mother workbook) and set Mount=st
                used_inst_funcs = {str(s.get("Instrument", "")).strip().upper() for s in steps if str(s.get("Instrument", "")).strip()}
                used_sw_names = {str(s.get("Switch", "")).strip().split(",")[0].strip().lower() for s in steps if str(s.get("Switch", "")).strip()}
                for s in steps:
                    m_sub = re.match(r'^:ObtainSubDevice\s*,\s*"([^"]+)"', str(s.get("Send", "")).strip(), re.IGNORECASE)
                    if m_sub:
                        used_sw_names.add(m_sub.group(1).strip().lower())
                filtered_insts = []
                func_to_inst_name = {}
                seen_funcs = set()
                for inst in ws.get("instruments", []):
                    inst_name_low = str(inst.get("Name", "")).strip().lower()
                    inst_funcs = [f.strip().upper() for f in str(inst.get("Functions", "")).split(",") if f.strip()]
                    matched = [fn for fn in inst_funcs if fn in used_inst_funcs and fn not in seen_funcs]
                    if matched or inst_name_low in used_sw_names:
                        inst["Mount"] = st
                        seen_funcs.update(matched)
                        for fn in matched:
                            func_to_inst_name.setdefault(fn, inst.get("Name", ""))
                        filtered_insts.append(inst)
                ws["instruments"] = filtered_insts
                # Fill missing Col F (Switch) on Instrument rows (e.g. POWERSWITCH) with mounted device Name
                for st_row in steps:
                    if str(st_row.get("Instrument", "")).strip() and not str(st_row.get("Switch", "")).strip():
                        fn_up = str(st_row.get("Instrument", "")).strip().upper()
                        if fn_up in func_to_inst_name and func_to_inst_name[fn_up]:
                            st_row["Switch"] = func_to_inst_name[fn_up]

                # Ensure non-teardown Phases are strictly contiguous (0, 1, 2, 3...) with no gaps
                if steps and str(steps[0].get("Phase", "")).strip() == "":
                    steps[0]["Phase"] = "0"
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

                sf_hmi_meta = (wizard_config.get("sfis_config") or {}).get("hmi_config") if isinstance(wizard_config.get("sfis_config"), dict) else None
                if isinstance(sf_hmi_meta, dict) and (wizard_config.get("sfis_config") or {}).get("use_hmi_items"):
                    sys_target = ws.setdefault("system_ini", {})
                    if sf_hmi_meta.get("url"):
                        sys_target["SFIS_WebLink"] = str(sf_hmi_meta["url"]).strip()
                    if sf_hmi_meta.get("tsp"):
                        sys_target["SFIS_TSP"] = str(sf_hmi_meta["tsp"]).strip()
                    if sf_hmi_meta.get("op"):
                        sys_target["SFIS_LoginID"] = str(sf_hmi_meta["op"]).strip()
                        sys_target["SFIS_AutoLogin"] = "1"
                    if sf_hmi_meta.get("isn"):
                        sys_target["SFIS_GetDateISN"] = str(sf_hmi_meta["isn"]).strip()
                    if "skip_save_on_fail" in sf_hmi_meta:
                        sys_target["SFIS_SkipSaveResultOnFail"] = "1" if sf_hmi_meta.get("skip_save_on_fail") else "0"
                    if sf_hmi_meta.get("device_id"):
                        ws.setdefault("global_ini", {}).setdefault("Settings", {})["DEVID_1"] = str(sf_hmi_meta["device_id"]).strip()

                sys_overrides = payload.get("system_ini_overrides") or {}
                if isinstance(sys_overrides, dict) and sys_overrides:
                    ws.setdefault("system_ini", {}).update({str(k): str(v) for k, v in sys_overrides.items()})

                custom_inst_blocks = payload.get("custom_inst_blocks", []) or []
                for ci in custom_inst_blocks:
                    inst_nm = str(ci.get("inst_name", "")).strip()
                    if inst_nm:
                        insert_instrument_title_block(
                            ws, st, inst_nm,
                            str(ci.get("title_name", "")).strip() or f"{inst_nm} Test",
                            after_block_idx=-1,
                            dl_val=str(ci.get("dl_val", "")).strip(),
                            ul_val=str(ci.get("ul_val", "")).strip(),
                            custom_steps=ci.get("custom_steps"),
                            globals_patch=ci.get("globals_patch")
                        )

                for nb in (payload.get("ni6009_blocks", []) or []):
                    insert_ni6009_block(
                        ws, st,
                        mode=nb.get("mode", "RSE"),
                        sample_ms=str(nb.get("sample_ms", "1000")),
                        dev_id=str(nb.get("dev_id", "Dev1")),
                        title_name=str(nb.get("title_name", "Measure Voltage Test")),
                        channels=nb.get("channels", []),
                        after_block_idx=-1
                    )

                for rb in (payload.get("rf_blocks", []) or []):
                    insert_rf_iqxel_block(
                        ws, st,
                        inst_name=str(rb.get("inst_name", "InstIQApiA")),
                        title_name=str(rb.get("title_name", "WIFI RF Test")),
                        settings_str=str(rb.get("settings_str", "")),
                        tx_tests=rb.get("tx_tests", []),
                        rx_tests=rb.get("rx_tests", []),
                        after_block_idx=-1
                    )

                tpl_bundle = payload.get("template_bundle") or wizard_config.get("template_bundle")
                sku_wizard_cfg = payload.get("sku_wizard") or wizard_config.get("sku_wizard")
                bundle_summary = None
                if (isinstance(tpl_bundle, dict) and (tpl_bundle.get("selected_block_keys") or tpl_bundle.get("ini_overrides") or tpl_bundle.get("companion_overrides"))) or (isinstance(sku_wizard_cfg, dict) and sku_wizard_cfg.get("enabled")):
                    from core.template_sku_engine import apply_bundle_and_sku_to_workspace
                    ws, bundle_summary = apply_bundle_and_sku_to_workspace(ws, st, bundle_spec=tpl_bundle, sku_spec=sku_wizard_cfg)

                auto_fix_workspace(ws)
                taipei_dual_mode = bool(payload.get("taipei_dual_mode", False))
                no_hw_phase_pause = bool(payload.get("no_hw_phase_pause", False))
                station_name_mode = str(payload.get("station_name_mode", "fixed")).strip().lower()
                if no_hw_phase_pause and not dry_run:
                    from core.block_sorter import pause_hardware_phases_minus_one
                    pause_hardware_phases_minus_one(ws)
                if station_name_mode == "ask":
                    ws.setdefault("system_ini", {})["StationName_Mode"] = "ask"
                    ws["system_ini"]["StationName"] = ""
                else:
                    ws.setdefault("system_ini", {})["StationName_Mode"] = "fixed"
                    ws["system_ini"]["StationName"] = st
                taipei_sheet = ""
                if taipei_dual_mode and not dry_run:
                    from core.block_sorter import build_taipei_dual_station
                    taipei_sheet = build_taipei_dual_station(ws, st)

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
                actual_xlsx = export_workspace_to_excel(ws, out_xlsx, active_sheet=st)
                actual_xlsx_name = os.path.basename(actual_xlsx)
                sys_ini, glb_ini = sync_and_generate_inis(ws, actual_xlsx_name, target_dir)
                from core.template_sku_engine import write_companion_files_to_dir
                written_companions = write_companion_files_to_dir(ws.get("_companion_files"), target_dir)
                switch_bats = []
                if taipei_sheet:
                    from core.block_sorter import write_env_switch_bats
                    switch_bats = write_env_switch_bats(target_dir, st, taipei_sheet, xlsx_filename=actual_xlsx_name)
                chk = "已自動寫入 [Checksum]"

                open_folder_in_explorer(target_dir)

                if bool(payload.get("open_excel", False)) and os.path.exists(actual_xlsx):
                    launch_excel_file_async(actual_xlsx)

                from core.golden_data import check_workspace_missing_dlls
                from core.script_notes import generate_companion_logic_txt
                dll_chk = check_workspace_missing_dlls(ws)
                guide_txt_path = generate_companion_logic_txt(ws, actual_xlsx, dll_chk=dll_chk, build_ver="Build v0.8.055")

                self._send_json({
                    "status": "ok",
                    "output_dir": target_dir,
                    "excel_path": actual_xlsx,
                    "guide_txt_path": guide_txt_path,
                    "written_companions": written_companions,
                    "bundle_summary": bundle_summary,
                    "taipei_sheet": taipei_sheet,
                    "switch_bats": switch_bats,
                    "system_ini": sys_ini,
                    "global_ini": glb_ini,
                    "checksum": chk or "已自動寫入 [Checksum]",
                    "isn_info": extract_isn_info(ws),
                    **dll_chk
                })

            elif parsed.path == "/api/generate_inst_template_standalone":
                items = payload.get("items")
                if not items or not isinstance(items, list):
                    inst_name = str(payload.get("inst_name", "NI6008")).strip() or "NI6008"
                    title_name = str(payload.get("title_name", "")).strip() or f"Test_{inst_name}"
                    dl_val = str(payload.get("dl_val", "")).strip()
                    ul_val = str(payload.get("ul_val", "")).strip()
                    items = [{"inst_name": inst_name, "title_name": title_name, "dl_val": dl_val, "ul_val": ul_val}]

                proj_name = str(payload.get("project_name", "INST_MOTHER")).strip() or "INST_MOTHER"
                st_name = str(payload.get("station_name", "MB")).strip() or "MB"

                # 1. 建立全新標準母體 (Golden Blank Mother Template)
                ws = get_golden_mother(proj_name, st_name)

                # 2. 自動載入前置路由與收尾保護骨架
                blk_map = {b["block_id"]: b for b in STANDARD_BLOCKS}
                init_steps = []
                for b_key in ["BLK_PRETEST_ROUTE", "BLK_PHASE97_TEARDOWN"]:
                    b_obj = blk_map.get(b_key)
                    if b_obj:
                        for k, v in b_obj.get("required_globals", {}).get("Settings", {}).items():
                            ws["global_ini"]["Settings"][k] = v
                        for k, v in b_obj.get("required_globals", {}).get("Scripts", {}).items():
                            ws["global_ini"]["Scripts"][k] = v
                        for m_name, m_rows in b_obj.get("required_marcos", {}).items():
                            ws.setdefault("marcos", {})[m_name] = [dict(mr) for mr in m_rows]
                        for s_row in b_obj.get("steps", []):
                            init_steps.append(dict(s_row))

                ws["stations"] = {st_name: init_steps}
                for inst_r in ws.get("instruments", []):
                    inst_r["Mount"] = ""

                # 3. 連續載入目標儀器測項（支援標準上下限、NI-6009 多通道 HMI、IQxel RF HMI 與自訂步驟 HMI）
                auto_sample_mode = bool(payload.get("auto_sample_mode", False))
                global_use_sw = bool(payload.get("use_ini_switch", False))
                taipei_dual_mode = bool(payload.get("taipei_dual_mode", False))
                no_hw_phase_pause = bool(payload.get("no_hw_phase_pause", False))
                station_name_mode = str(payload.get("station_name_mode", "fixed")).strip().lower()
                rf_inst_names = {"InstIQApiA", "XelM8-A", "IQFlex-A", "XelM8-B", "MT8870A", "E4418B", "U2004A", "OSP120", "SAn9000", "vnxRFSW"}
                inst_occ_counts = {}
                sub_or_spec_insts = {"ScpiController", "Keithley2700", "Keithley2380", "Transmitter1", "vnxRFSW", "DevUart"}
                for idx_item, it in enumerate(items):
                    i_name = str(it.get("inst_name", "NI6008")).strip() or "NI6008"
                    base_family = re.sub(r"-\d+$", "", i_name)
                    inst_occ_counts[base_family] = inst_occ_counts.get(base_family, 0) + 1
                    occ_num = inst_occ_counts[base_family]
                    var_sfx = f"_{occ_num}" if occ_num > 1 else ""
                    t_name = str(it.get("title_name", "")).strip() or f"Test_{i_name}_{idx_item + 1}"
                    d_val = str(it.get("dl_val", "")).strip()
                    u_val = str(it.get("ul_val", "")).strip()
                    item_use_sw = bool(it.get("use_ini_switch", global_use_sw))
                    item_same_phase = bool(it.get("same_phase", False))
                    m_ni = re.match(r"^NI6008(?:-(\d+))?$", i_name)
                    if it.get("ni6009_block"):
                        nb = it["ni6009_block"]
                        ni_dev_def = f"Dev{m_ni.group(1)}" if (m_ni and m_ni.group(1)) else "Dev1"
                        insert_ni6009_block(
                            ws, st_name,
                            mode=nb.get("mode", "RSE"),
                            sample_ms=str(nb.get("sample_ms", "1000")),
                            dev_id=str(nb.get("dev_id", ni_dev_def)),
                            title_name=str(nb.get("title_name", t_name)),
                            channels=nb.get("channels", []),
                            after_block_idx=-1,
                            same_phase=item_same_phase,
                            use_ini_switch=item_use_sw,
                            inst_name=str(nb.get("inst_name", i_name))
                        )
                    elif it.get("rf_block"):
                        rb = it["rf_block"]
                        insert_rf_iqxel_block(
                            ws, st_name,
                            inst_name=str(rb.get("inst_name", i_name)),
                            title_name=str(rb.get("title_name", t_name)),
                            settings_str=str(rb.get("settings_str", "")),
                            tx_tests=rb.get("tx_tests", []),
                            rx_tests=rb.get("rx_tests", []),
                            after_block_idx=-1,
                            same_phase=item_same_phase,
                            use_ini_switch=item_use_sw
                        )
                    elif auto_sample_mode and m_ni:
                        ni_dev_def = f"Dev{m_ni.group(1)}" if m_ni.group(1) else "Dev1"
                        insert_ni6009_block(
                            ws, st_name,
                            mode="RSE", sample_ms="1000", dev_id=ni_dev_def,
                            title_name=f"{t_name}_Sample",
                            channels=[
                                {"ch": 0, "name": f"VCC_3V3{var_sfx}", "dl": "3.13", "ul": "3.47"},
                                {"ch": 1, "name": f"VCC_5V0{var_sfx}", "dl": "4.75", "ul": "5.25"},
                                {"ch": 2, "name": f"VCC_1V8{var_sfx}", "dl": "1.71", "ul": "1.89"},
                            ],
                            after_block_idx=-1,
                            same_phase=item_same_phase,
                            use_ini_switch=item_use_sw,
                            inst_name=i_name
                        )
                    elif auto_sample_mode and (i_name in rf_inst_names or base_family in rf_inst_names):
                        insert_rf_iqxel_block(
                            ws, st_name,
                            inst_name=i_name,
                            title_name=f"{t_name}_RF_Sample",
                            settings_str="",
                            tx_tests=[
                                {"channel": "6", "bw": "20", "mcs": "7", "antenna": "1", "target_pwr": "15", "pwr_min": "13", "pwr_max": "17", "evm_min": "-50", "evm_max": "-28"},
                                {"channel": "36", "bw": "40", "mcs": "9", "antenna": "1", "target_pwr": "14", "pwr_min": "12", "pwr_max": "16", "evm_min": "-50", "evm_max": "-30"},
                            ],
                            rx_tests=[
                                {"channel": "11", "bw": "20", "mcs": "7", "antenna": "1", "per_min": "0", "per_max": "10"},
                            ],
                            after_block_idx=-1,
                            same_phase=item_same_phase,
                            use_ini_switch=item_use_sw
                        )
                    elif auto_sample_mode and not it.get("custom_steps") and i_name not in sub_or_spec_insts and base_family not in sub_or_spec_insts:
                        if base_family == "FeasaLED":
                            sample_steps = [
                                {"Send": ":ObtainDevice", "ExecMode": "0", "Description": f"PC#-#Obtain {i_name}", "TestID": "BRME027"},
                                {"Send": ':Dev.CaptureAndRead,"01"', "Ref": f"$LED_Wave_1{var_sfx};\n$LED_Int_1{var_sfx}", "Validation": f"(LED_Wave_1{var_sfx},%f,515,535);\n(LED_Int_1{var_sfx},%f,1000,99999)", "ExecMode": "2:0", "Description": f"LED#-#{t_name} CH01 Green", "TestID": "IOLE015"},
                                {"Send": ':Dev.CaptureAndRead,"02"', "Ref": f"$LED_Wave_2{var_sfx};\n$LED_Int_2{var_sfx}", "Validation": f"(LED_Wave_2{var_sfx},%f,615,640);\n(LED_Int_2{var_sfx},%f,1000,99999)", "ExecMode": "2:0", "Description": f"LED#-#{t_name} CH02 Red", "TestID": "IOLE015"},
                                {"Send": ':Dev.CaptureAndRead,"03"', "Ref": f"$LED_Wave_3{var_sfx};\n$LED_Int_3{var_sfx}", "Validation": f"(LED_Wave_3{var_sfx},%f,450,475);\n(LED_Int_3{var_sfx},%f,1000,99999)", "ExecMode": "2:0", "Description": f"LED#-#{t_name} CH03 Blue", "TestID": "IOLE015"},
                                {"Send": ":ReleaseDevice", "ExecMode": "3", "Description": f"PC#-#Release {i_name}", "TestID": "BRME027"},
                            ]
                        else:
                            sample_steps = [
                                {"Send": ":ObtainDevice", "ExecMode": "1", "Description": f"PC#-#Obtain {i_name}", "TestID": "B7PL025"},
                                {"Send": ':Dev.Measure,"1"', "Validation": f"({i_name}{var_sfx}_M1,%f,{d_val or '0.0'},{u_val or '5.0'})", "ExecMode": "2:0", "Description": f"DUT#-#{i_name} Sample Step 1: Primary Measure", "TestID": "B7PL025"},
                                {"Send": ':Dev.Measure,"2"', "Validation": f"({i_name}{var_sfx}_M2,%f,{d_val or '0.0'},{u_val or '5.0'})", "ExecMode": "2:0", "Description": f"DUT#-#{i_name} Sample Step 2: Secondary Verify", "TestID": "B7PL025"},
                                {"Send": ':Dev.Measure,"3"', "Validation": f"({i_name}{var_sfx}_M3,%f,{d_val or '0.0'},{u_val or '5.0'})", "ExecMode": "2:0", "Description": f"DUT#-#{i_name} Sample Step 3: Boundary Check", "TestID": "B7PL025"},
                                {"Send": ":ReleaseDevice", "ExecMode": "3", "Description": f"PC#-#Release {i_name}", "TestID": "B7PL025"},
                            ]
                        insert_instrument_title_block(
                            ws, st_name, i_name, t_name,
                            after_block_idx=-1,
                            dl_val=d_val,
                            ul_val=u_val,
                            custom_steps=sample_steps,
                            globals_patch=it.get("globals_patch"),
                            same_phase=item_same_phase,
                            use_ini_switch=item_use_sw
                        )
                    else:
                        insert_instrument_title_block(
                            ws, st_name, i_name, t_name,
                            after_block_idx=-1,
                            dl_val=d_val,
                            ul_val=u_val,
                            custom_steps=it.get("custom_steps"),
                            globals_patch=it.get("globals_patch"),
                            same_phase=item_same_phase,
                            use_ini_switch=item_use_sw
                        )

                # 自動補掛載 MB 工作表實際用到 (如 Phase 97 之 POWERSWITCH) 且未掛載的儀器，並過濾未使用的儀器避免 DLL 缺失報錯
                used_test_types = {
                    str(s.get("Instrument", "")).strip().lower()
                    for s in ws.get("stations", {}).get(st_name, [])
                    if str(s.get("Instrument", "")).strip()
                }
                func_to_mounted = {}
                for inst_r in ws.get("instruments", []):
                    funcs_tokens = [f.strip().lower() for f in str(inst_r.get("Functions", "")).split(",") if f.strip()]
                    if str(inst_r.get("Mount", "")).strip():
                        for ft in funcs_tokens:
                            func_to_mounted.setdefault(ft, inst_r.get("Name", ""))
                        continue
                    if any(ft in used_test_types for ft in funcs_tokens):
                        # Prefer instruments whose DLL exists locally
                        if inst_r.get("dll_exists", True):
                            inst_r["Mount"] = st_name
                            used_test_types.difference_update(funcs_tokens)
                            for ft in funcs_tokens:
                                func_to_mounted.setdefault(ft, inst_r.get("Name", ""))
                ws["instruments"] = [i for i in ws.get("instruments", []) if str(i.get("Mount", "")).strip()]
                for s_row in ws.get("stations", {}).get(st_name, []):
                    if str(s_row.get("Instrument", "")).strip() and not str(s_row.get("Switch", "")).strip():
                        fn_low = str(s_row.get("Instrument", "")).strip().lower()
                        if fn_low in func_to_mounted and func_to_mounted[fn_low]:
                            s_row["Switch"] = func_to_mounted[fn_low]

                # 4. 全自動檢查與錯誤修復 (Auto Audit & Repair)
                audit_rep = audit_workspace(ws)
                fix_logs = auto_fix_workspace(ws)
                post_audit = audit_workspace(ws)
                if no_hw_phase_pause:
                    from core.block_sorter import pause_hardware_phases_minus_one
                    pause_hardware_phases_minus_one(ws)
                if station_name_mode == "ask":
                    ws.setdefault("system_ini", {})["StationName_Mode"] = "ask"
                    ws["system_ini"]["StationName"] = ""
                else:
                    ws.setdefault("system_ini", {})["StationName_Mode"] = "fixed"
                    ws["system_ini"]["StationName"] = st_name

                taipei_sheet = ""
                if taipei_dual_mode:
                    from core.block_sorter import build_taipei_dual_station
                    taipei_sheet = build_taipei_dual_station(ws, st_name)

                # 5. 輸出 Excel (預設開啟於測試站 st_name 分頁) 與 INI，自動寫入 Checksum
                lead_inst = items[0].get("inst_name", "INST") if items else "INST"
                xlsx_name = f"{proj_name}_{lead_inst}_{st_name}.xlsx"
                folder_label = f"InstTemplate_{lead_inst}_{st_name}"
                target_dir = os.path.join(OUTPUT_ROOT, folder_label, "System")
                os.makedirs(target_dir, exist_ok=True)
                for old_f in os.listdir(target_dir):
                    try:
                        os.remove(os.path.join(target_dir, old_f))
                    except Exception:
                        pass

                out_xlsx = os.path.join(target_dir, xlsx_name)
                actual_xlsx = export_workspace_to_excel(ws, out_xlsx, active_sheet=st_name)
                actual_xlsx_name = os.path.basename(actual_xlsx)
                sys_ini, glb_ini = sync_and_generate_inis(ws, actual_xlsx_name, target_dir)

                switch_bats = []
                if taipei_sheet:
                    from core.block_sorter import write_env_switch_bats
                    switch_bats = write_env_switch_bats(target_dir, st_name, taipei_sheet, xlsx_filename=actual_xlsx_name)

                # 6. 匯出時一律自動開啟目標目錄，Excel 依前端確認視窗決定是否開啟
                open_folder_in_explorer(target_dir)

                if bool(payload.get("open_excel", False)) and os.path.exists(actual_xlsx):
                    launch_excel_file_async(actual_xlsx)

                # 匯出前實機 DLL 檢查（確認本機 Centimani 目錄與所選儀器 DLL 是否齊備）
                from core.golden_data import check_workspace_missing_dlls
                from core.script_notes import generate_companion_logic_txt
                dll_chk = check_workspace_missing_dlls(ws)
                guide_txt_path = generate_companion_logic_txt(ws, actual_xlsx, dll_chk=dll_chk, fixed_logs=fix_logs, build_ver="Build v0.8.055")

                self._send_json({
                    "status": "ok",
                    "output_dir": target_dir,
                    "excel_path": actual_xlsx,
                    "guide_txt_path": guide_txt_path,
                    "taipei_sheet": taipei_sheet,
                    "switch_bats": switch_bats,
                    "inst_name": lead_inst,
                    "total_items": len(items),
                    "total_steps": len(ws.get("stations", {}).get(st_name, [])),
                    "auto_fixed_count": len(fix_logs) if isinstance(fix_logs, list) else 0,
                    "audit_report": post_audit,
                    **dll_chk
                })
            elif parsed.path == "/api/list_excel_sheets":
                from core.excel_engine import list_excel_sheet_names
                excel_path = payload.get("excel_path", "").strip()
                if not excel_path or not os.path.exists(excel_path):
                    self._send_json({"status": "error", "message": "找不到指定的 Excel 檔案"}, 404)
                    return
                sheets = list_excel_sheet_names(excel_path)
                self._send_json({"status": "ok", "excel_path": excel_path, "sheets": sheets})
            elif parsed.path == "/api/copy_sheet_across_files":
                from core.excel_engine import copy_sheet_between_excels
                src_path = payload.get("source_excel_path", "").strip()
                src_sheet = payload.get("source_sheet_name", "").strip()
                dst_path = payload.get("target_excel_path", "").strip()
                dst_sheet = payload.get("target_sheet_name", "").strip() or src_sheet
                overwrite = bool(payload.get("overwrite", False))
                use_com = bool(payload.get("use_excel_com", True))
                open_excel = bool(payload.get("open_excel", True))

                if not src_path or not src_sheet or not dst_path:
                    self._send_json({"status": "error", "message": "請完整指定來源 Excel、來源 Sheet 與目標 Excel"}, 400)
                    return

                res = copy_sheet_between_excels(
                    src_path,
                    src_sheet,
                    dst_path,
                    target_sheet_name=dst_sheet,
                    overwrite=overwrite,
                    use_excel_com=use_com,
                )
                if os.path.exists(dst_path):
                    open_folder_in_explorer(os.path.dirname(dst_path))
                    if open_excel:
                        launch_excel_file_async(dst_path)
                self._send_json(res)
            elif parsed.path == "/api/template_bundle/inspect":
                from core.template_sku_engine import inspect_template_bundle
                excel_path = str(payload.get("excel_path") or "").strip()
                sheet_name = str(payload.get("sheet_name") or "").strip() or None
                if not excel_path or not os.path.exists(excel_path):
                    self._send_json({"status": "error", "message": f"找不到來源範本 Excel：{excel_path}"}, 404)
                    return
                res = inspect_template_bundle(excel_path, sheet_name=sheet_name)
                self._send_json({"status": "ok", **res})
            elif parsed.path == "/api/template_bundle/apply":
                from core.template_sku_engine import apply_bundle_and_sku_to_workspace
                target_mode = str(payload.get("target_mode") or "edit").strip().lower()
                bundle_spec = payload.get("bundle_spec") or {}
                sku_spec = payload.get("sku_spec") or {}
                preview_only = bool(payload.get("preview", False))

                if target_mode == "create" or not isinstance(payload.get("workspace"), dict) or not payload.get("workspace", {}).get("stations"):
                    proj = str(payload.get("project_name") or "PEGA_NEW").strip() or "PEGA_NEW"
                    st_name = str(payload.get("station_name") or "MB").strip() or "MB"
                    base_ws = get_golden_mother(proj, st_name)
                    base_ws["stations"] = {st_name: [
                        {"Index": "000", "Phase": "0", "Title": "0,CheckRoute", "Marco": "", "Instrument": "", "Switch": "", "Send": ':ShowISN,"*(ISN)"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Show ISN", "TestID": "B7PL025"},
                        {"Index": "001", "Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":SfCheckRoute", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "2000", "ExecMode": "8", "Description": "PC#-#CheckRoute", "TestID": "OTFX064"},
                        {"Index": "002", "Phase": "97", "Title": "1,End Test,1", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Disconnect,"UART"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Close UART", "TestID": "B7PL025"},
                    ]}
                else:
                    base_ws = payload["workspace"]
                    st_name = str(payload.get("station_name") or base_ws.get("station_name") or next(iter(base_ws.get("stations", {}).keys()), "MB")).strip()

                ws_out, summary = apply_bundle_and_sku_to_workspace(
                    base_ws, st_name, bundle_spec=bundle_spec, sku_spec=sku_spec
                )
                fix_logs = auto_fix_workspace(ws_out)
                rep = audit_workspace(ws_out)
                self._send_json({
                    "status": "ok",
                    "preview": preview_only,
                    "station_name": st_name,
                    "summary": summary,
                    "fixed_logs": fix_logs,
                    "report": rep,
                    "workspace": ws_out,
                    "companion_files": ws_out.get("_companion_files", {}),
                })
            elif parsed.path == "/api/pick_file":
                path_only = bool(payload.get("path_only", False))
                dlg_title = str(payload.get("title", "")).strip() or "選擇 Centimani Excel 檔案 (*.xlsx)"
                selected_path = pick_file_native(title=dlg_title)
                if not selected_path:
                    self._send_json({"status": "cancel"})
                    return
                if path_only:
                    self._send_json({"status": "ok", "file_path": selected_path})
                    return
                ws = import_excel_to_workspace(selected_path)
                rep = audit_workspace(ws)
                self._send_json({
                    "status": "ok",
                    "file_path": selected_path,
                    "workspace": ws,
                    "report": rep,
                    "recent_files": get_recent_excel_files(),
                    "isn_info": extract_isn_info(ws)
                })
            elif parsed.path == "/api/pick_centimani_dir":
                from core.golden_data import scan_centimani_environment
                folder = pick_folder_native("選擇本機 Centimani 主程式目錄 (含 Device\\ 資料夾與 LoadScript.dll)")
                if not folder:
                    self._send_json({"status": "cancel"})
                    return
                profile = scan_centimani_environment(target_dir=folder, persist=True, confirmed=True)
                gm = get_golden_mother()
                self._send_json({
                    "status": "ok",
                    "centimani_dir": folder,
                    "centimani_profile": profile,
                    "instruments": gm.get("instruments", [])
                })
            elif parsed.path == "/api/scan_centimani_dir":
                from core.golden_data import scan_centimani_environment
                target_dir = str(payload.get("centimani_dir", "")).strip() or None
                confirm_flag = payload.get("confirm", True)
                profile = scan_centimani_environment(target_dir=target_dir, persist=True, confirmed=bool(confirm_flag))
                if not profile.get("exists"):
                    self._send_json({"status": "error", "message": "找不到有效的 Centimani 主程式目錄，請先指定資料夾。"}, 404)
                    return
                gm = get_golden_mother()
                self._send_json({
                    "status": "ok",
                    "centimani_dir": profile["centimani_dir"],
                    "centimani_profile": profile,
                    "instruments": gm.get("instruments", []),
                    "settings": get_app_settings()
                })
            elif parsed.path == "/api/launch_centimani_tool":
                from core.golden_data import get_configured_centimani_dir
                tool_name = os.path.basename(str(payload.get("tool_name", "")).strip())
                allowed_tools = {
                    "CentimaniSFISTest.exe": "已啟動 SFIS 連線測試工具：選廠區或貼入 System.ini 的 SFIS_WebLink，點 Test 即可驗證內網 SFIS 是否正常連線與回寫。",
                    "DLLtest.exe": "已啟動 DLL 單步測試工具：依序操作「Find DLL file (選 Device\\*.dll)」→「LoadSetting」→「Load」→「Execute」即可在開主程式前單測儀器指令。"
                }
                if tool_name not in allowed_tools:
                    self._send_json({"status": "error", "message": f"不支援的工具名稱：{tool_name}"}, 400)
                    return
                cm_dir = get_configured_centimani_dir()
                exe_path = os.path.join(cm_dir, tool_name) if cm_dir else ""
                if not exe_path or not os.path.isfile(exe_path):
                    self._send_json({"status": "error", "message": f"目前目錄 ({cm_dir}) 下找不到 {tool_name}，請確認該版本主程式是否附帶此工具。"}, 404)
                    return
                launch_centimani_tool_async(exe_path, cm_dir)
                self._send_json({
                    "status": "ok",
                    "tool_name": tool_name,
                    "exe_path": exe_path,
                    "guide_tip": allowed_tools[tool_name]
                })
            elif parsed.path == "/api/check_sfis_weblink":
                import urllib.request
                import urllib.error
                raw_link = str(payload.get("url", "")).strip()
                if not raw_link:
                    self._send_json({"status": "error", "message": "未提供 SFIS_WebLink 網址"}, 400)
                    return
                base_url = raw_link.split(",", 1)[0].strip()
                if not base_url.lower().startswith(("http://", "https://")):
                    self._send_json({"status": "ok", "reachable": False, "checked_url": base_url, "message": f"網址格式非 HTTP/HTTPS：{base_url}"})
                    return
                chk_url = base_url + ("?WSDL" if (base_url.lower().endswith(".asmx") and "?" not in base_url) else "")
                try:
                    req = urllib.request.Request(chk_url, method="GET")
                    with urllib.request.urlopen(req, timeout=2.5) as resp:
                        code = getattr(resp, "status", 200)
                    self._send_json({
                        "status": "ok", "reachable": True, "http_code": code,
                        "checked_url": chk_url, "message": f"內網 SFIS WebService 回應正常 (HTTP {code})"
                    })
                except urllib.error.HTTPError as he:
                    self._send_json({
                        "status": "ok", "reachable": (he.code < 500), "http_code": he.code,
                        "checked_url": chk_url, "message": f"伺服器回應 HTTP {he.code}（服務可連通，正式測試請在 CentimaniSFISTest.exe 帶入工單/ISN）"
                    })
                except Exception as ue:
                    self._send_json({
                        "status": "ok", "reachable": False, "http_code": 0,
                        "checked_url": chk_url, "message": f"無法連通 SFIS WebService（可能不在公司/產線內網）：{ue}"
                    })
            elif parsed.path == "/api/sfis_soap_test":
                from core.sfis_client import call_sfis_soap, call_sfis_mock_soap
                url = str(payload.get("url", "")).strip()
                action = str(payload.get("action", "")).strip()
                params = payload.get("params") or {}
                use_mock = bool(payload.get("mock", False))
                if not use_mock and not url:
                    self._send_json({"status": "error", "message": "請先輸入 SFIS WebService 網址"}, 400)
                    return
                try:
                    res = call_sfis_mock_soap(action, params) if use_mock else call_sfis_soap(url, action, params)
                    self._send_json(res)
                except ValueError as ve:
                    self._send_json({"status": "error", "message": str(ve)}, 400)
            elif parsed.path == "/api/sfis_mock_reset":
                from core.sfis_client import reset_sfis_mock_db
                self._send_json(reset_sfis_mock_db())
            elif parsed.path == "/api/export_sfis_hmi_script":
                from core.sfis_client import build_sfis_excel_steps
                from core.script_notes import generate_companion_logic_txt
                items = payload.get("items") or []
                cfg = payload.get("config") or {}
                mode = str(payload.get("mode", "new_template")).strip()
                proj = str(cfg.get("project_name", "SFIS_TEST") or "SFIS_TEST").strip() or "SFIS_TEST"
                st = str(cfg.get("station", "MB") or "MB").strip() or "MB"
                url = str(cfg.get("url", "")).strip()
                tsp = str(cfg.get("tsp", f"{proj[:6]},2") or f"{proj[:6]},2").strip()
                dev_id = str(cfg.get("device_id", "710001") or "710001").strip()
                sfis_en = str(cfg.get("sfis_enable", "1") or "1").strip()

                sfis_steps = build_sfis_excel_steps(items, start_phase=0, include_show_isn=True)
                if not sfis_steps:
                    self._send_json({"status": "error", "message": "請至少保留 1 張非 Login 的 SFIS 測試積木（如 CheckRoute / GetVersion / SaveLinkData）"}, 400)
                    return

                if mode == "insert_current" and isinstance(payload.get("workspace"), dict):
                    ws = payload["workspace"]
                    stations = ws.setdefault("stations", {})
                    target_st = st if st in stations else (next(iter(stations.keys()), st))
                    existing = list(stations.get(target_st, []))
                    # Keep Phase < 97 non-SFIS-ShowISN steps after inserted SFIS sequence or cleanly prepend at Phase 0
                    non_teardown = []
                    teardown = []
                    cur_p = ""
                    for r in existing:
                        pr = str(r.get("Phase", "")).strip()
                        if pr:
                            cur_p = pr.split(":")[0].strip()
                        if cur_p in ("97", "98", "99"):
                            teardown.append(r)
                        else:
                            non_teardown.append(r)
                    # Replace existing leading CheckRoute block if sfis_steps already provides Phase 0 CheckRoute
                    if non_teardown and any(":ShowISN" in str(r.get("Send", "")) for r in sfis_steps):
                        first_blk_end = 0
                        for idx_nt, nt_row in enumerate(non_teardown):
                            if idx_nt > 0 and (str(nt_row.get("Phase", "")).strip() != "" or str(nt_row.get("Title", "")).strip() != ""):
                                break
                            first_blk_end = idx_nt + 1
                        head_sends = " ".join(str(x.get("Send", "")) for x in non_teardown[:first_blk_end])
                        if ":ShowISN" in head_sends or ":SfCheckRoute" in head_sends:
                            non_teardown = non_teardown[first_blk_end:]
                    combined = sfis_steps + non_teardown + teardown
                    next_p = 0
                    for r in combined:
                        ps = str(r.get("Phase", "")).strip()
                        if ps and ps not in ("-1", "97", "98", "99"):
                            r["Phase"] = str(next_p)
                            next_p += 1
                    stations[target_st] = combined
                    sys_ini = ws.setdefault("system_ini", {})
                    if url:
                        sys_ini["SFIS_WebLink"] = url
                    if tsp:
                        sys_ini["SFIS_TSP"] = tsp
                    if cfg.get("op"):
                        sys_ini["SFIS_LoginID"] = str(cfg.get("op")).strip()
                        sys_ini["SFIS_AutoLogin"] = "1"
                    if cfg.get("isn"):
                        sys_ini["SFIS_GetDateISN"] = str(cfg.get("isn")).strip()
                    sys_ini["SFIS_Enable"] = sfis_en
                    if "skip_save_on_fail" in cfg:
                        sys_ini["SFIS_SkipSaveResultOnFail"] = "1" if cfg.get("skip_save_on_fail") else "0"
                    glb_set = ws.setdefault("global_ini", {}).setdefault("Settings", {})
                    glb_set["DEVID_1"] = dev_id
                    if ws.get("duts"):
                        for d_r in ws["duts"]:
                            if str(d_r.get("Station", "")).split(",")[0].strip() == target_st:
                                d_r["SFIS_DeviceID"] = "*$(DEVID_1)" if "DEVID_1" in str(d_r.get("SFIS_DeviceID", "")) else dev_id
                    auto_fix_workspace(ws)
                    rep = audit_workspace(ws)
                    self._send_json({
                        "status": "ok",
                        "mode": "insert_current",
                        "station": target_st,
                        "inserted_count": len(sfis_steps),
                        "workspace": ws,
                        "report": rep,
                    })
                    return

                ws = get_golden_mother(proj, st)
                ws["duts"] = ws["duts"][:1]
                # Centimani LoadScript.MainScript.ExcelToDTs 要求 Switch 與 Instrument 分頁皆至少須有 1 列資料（否則報 Read Excel for Switch failed / File Name doestn't set.），
                # 保留 Mount="" (未掛載) 即可通過讀檔檢查且不觸發任何硬體 DLL 載入。
                ws["switches"] = [dict(x, Mount="") for x in (ws.get("switches") or [])[:1]]
                ws["instruments"] = [dict(x, Mount="") for x in (ws.get("instruments") or [])[:2]]
                cfg_op = str(cfg.get("op", "S09166390") or "S09166390").strip()
                cfg_isn = str(cfg.get("isn", "") or "").strip()
                isn_len = len(cfg_isn) if (1 <= len(cfg_isn) <= 32) else 13
                glb_set = ws.setdefault("global_ini", {}).setdefault("Settings", {})
                glb_set["LOAD_1"] = "true"
                glb_set["DEVID_1"] = dev_id
                glb_scr = ws.setdefault("global_ini", {}).setdefault("Scripts", {})
                glb_scr.setdefault("gUUID", "TEST_UUID_001")
                for slot in range(2, 5):
                    for sfx in (f"LOAD_{slot}", f"PCIP_{slot}", f"DUTIP_{slot}", f"DUT_UR{slot}", f"PCUART_fixture_{slot}", f"DEVID_{slot}"):
                        glb_set.pop(sfx, None)
                if ws.get("duts"):
                    d0 = ws["duts"][0]
                    d0["SFIS_DeviceID"] = "*$(DEVID_1)"
                    for dk in list(d0.keys()):
                        if dk.startswith("ScanBarcode"):
                            d0[dk] = f"{{ISN,{isn_len},[0-9A-Z]}}"
                        elif dk.startswith("Connection1"):
                            d0[dk] = '"APP","CmdConsole","C:\\Windows\\System32\\cmd.exe,0,5000,"'
                        elif dk.startswith("Connection2") or dk.startswith("Connection3") or dk.startswith("Connection4"):
                            d0[dk] = ""

                phase97_row = {
                    "Index": f"{len(sfis_steps):03d}",
                    "Phase": "97",
                    "Title": "1,End SFIS Verify,1",
                    "Description": "Close prompt and finish SFIS check",
                    "Instrument": "",
                    "Switch": "",
                    "Send": ":CloseMessage",
                    "Reply": "0",
                    "EndPrompt": "",
                    "Ref": "",
                    "Validation": "",
                    "Waiting": "0",
                    "ExecMode": "3",
                    "Parameter": "",
                    "Marco": "",
                    "TestID": "B7PL025",
                }
                ws["stations"] = {st: sfis_steps + [phase97_row]}
                sys_ini = ws.setdefault("system_ini", {})
                sys_ini["SFIS_Enable"] = sfis_en
                if url:
                    sys_ini["SFIS_WebLink"] = url
                sys_ini["SFIS_TSP"] = tsp
                sys_ini["SFIS_AutoLogin"] = "1"
                sys_ini["SFIS_LoginID"] = cfg_op
                if cfg_isn:
                    sys_ini["SFIS_GetDateISN"] = cfg_isn
                sys_ini["SFIS_SkipSaveResultOnFail"] = "1" if cfg.get("skip_save_on_fail", True) else "0"
                sys_ini["StationName"] = st
                sys_ini["StationName_Mode"] = "fixed"

                auto_fix_workspace(ws)
                rep = audit_workspace(ws)
                folder_label = f"SFIS_Verify_{proj}_{st}"
                target_dir = os.path.join(OUTPUT_ROOT, folder_label, "System")
                os.makedirs(target_dir, exist_ok=True)
                out_xlsx = os.path.join(target_dir, f"SFIS_{proj}_{st}.xlsx")
                actual_xlsx = export_workspace_to_excel(ws, out_xlsx, active_sheet=st)
                actual_name = os.path.basename(actual_xlsx)
                sync_and_generate_inis(ws, actual_name, target_dir)
                guide_txt_path = generate_companion_logic_txt(ws, actual_xlsx, build_ver="Build v0.8.055")
                open_folder_in_explorer(target_dir)
                if bool(payload.get("open_excel", True)) and os.path.exists(actual_xlsx):
                    launch_excel_file_async(actual_xlsx)
                self._send_json({
                    "status": "ok",
                    "mode": "new_template",
                    "excel_path": actual_xlsx,
                    "output_dir": target_dir,
                    "guide_txt_path": guide_txt_path,
                    "audit_report": rep,
                    "total_steps": len(ws["stations"][st]),
                    "missing_dlls": [],
                    "missing_drivers": [],
                    "centimani_dir_exists": True,
                })
            elif parsed.path == "/api/pick_sfis_ini":
                from core.golden_data import get_configured_centimani_dir
                ini_path = str(payload.get("ini_path", "") or "").strip()
                do_pick = bool(payload.get("pick", False))
                if do_pick:
                    init_d = SCRIPTS_ROOT if os.path.exists(SCRIPTS_ROOT) else PROJECT_ROOT
                    cm_dir = get_configured_centimani_dir()
                    if cm_dir and os.path.exists(os.path.join(cm_dir, "System")):
                        init_d = os.path.join(cm_dir, "System")
                    ini_path = _run_tk_dialog({
                        "title": "選擇產線 System.ini 或 Global.ini 帶入 SFIS 設定",
                        "init_dir": init_d,
                        "file_types": [("Centimani INI 設定檔 (*.ini)", "*.ini"), ("所有檔案 (*.*)", "*.*")],
                    })
                    if not ini_path:
                        self._send_json({"status": "cancelled"})
                        return
                elif not ini_path:
                    cm_dir = get_configured_centimani_dir()
                    for cand in [
                        os.path.join(cm_dir, "System", "System.ini") if cm_dir else "",
                        os.path.join(cm_dir, "System.ini") if cm_dir else "",
                        os.path.join(SCRIPTS_ROOT, "System.ini"),
                    ]:
                        if cand and os.path.exists(cand):
                            ini_path = cand
                            break
                if not ini_path or not os.path.exists(ini_path):
                    self._send_json({"status": "error", "message": "找不到可讀取的 System.ini 檔案"}, 404)
                    return

                folder = os.path.dirname(ini_path)
                sys_ini_p = os.path.join(folder, "System.ini") if os.path.basename(ini_path).lower() != "system.ini" else ini_path
                glb_ini_p = os.path.join(folder, "Global.ini") if os.path.basename(ini_path).lower() != "global.ini" else ini_path
                parsed_cfg = {"source_path": sys_ini_p if os.path.exists(sys_ini_p) else ini_path}
                if os.path.exists(sys_ini_p):
                    for line in open(sys_ini_p, "r", encoding="utf-8", errors="ignore"):
                        s = line.strip()
                        if not s or s.startswith(("//", ";", "[")) or "=" not in s:
                            continue
                        k, v = [x.strip() for x in s.split("=", 1)]
                        if k == "SFIS_WebLink" and v:
                            parsed_cfg["url"] = v.split(",")[0].strip()
                        elif k == "SFIS_TSP" and v:
                            parsed_cfg["tsp"] = v
                        elif k == "StationName" and v:
                            parsed_cfg["station"] = v
                        elif k == "SFIS_LoginID" and v:
                            parsed_cfg["op"] = v
                        elif k == "SFIS_GetDateISN" and v:
                            parsed_cfg["isn"] = v
                        elif k == "SFIS_SkipSaveResultOnFail":
                            parsed_cfg["skip_save_on_fail"] = (v == "1")
                if os.path.exists(glb_ini_p):
                    for line in open(glb_ini_p, "r", encoding="utf-8", errors="ignore"):
                        s = line.strip()
                        if not s or s.startswith(("//", ";", "[")) or "=" not in s:
                            continue
                        k, v = [x.strip() for x in s.split("=", 1)]
                        if k == "DEVID_1" and v:
                            parsed_cfg["device_id"] = v
                self._send_json({"status": "ok", "config": parsed_cfg})
            elif parsed.path == "/api/sfis_hmi_profiles":
                prof_file = os.path.join(BASE_DIR, "sfis_hmi_profiles.json")
                cur = {}
                if os.path.exists(prof_file):
                    try:
                        with open(prof_file, "r", encoding="utf-8") as f:
                            cur = json.load(f) or {}
                    except Exception:
                        cur = {}
                if "plants" in payload and isinstance(payload["plants"], list):
                    cur["plants"] = payload["plants"]
                if "virtual_mos" in payload and isinstance(payload["virtual_mos"], list):
                    cur["virtual_mos"] = payload["virtual_mos"]
                if "used_isns" in payload and isinstance(payload["used_isns"], list):
                    cur["used_isns"] = payload["used_isns"]
                with open(prof_file, "w", encoding="utf-8") as f:
                    json.dump(cur, f, ensure_ascii=False, indent=2)
                self._send_json({"status": "ok", "saved": cur})
            else:
                self._send_json({"status": "error", "message": "Unknown endpoint"}, 404)
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)


def _maximize_studio_window_async():
    """Finds the Centimani Studio browser window and maximizes it via Win32 API (works even if browser is already running)."""
    def _worker():
        import time
        import ctypes
        for _ in range(10):
            time.sleep(0.5)
            try:
                user32 = ctypes.windll.user32
                found = []

                @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                def _enum_cb(hwnd, _lparam):
                    if user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buf = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buf, length + 1)
                            if "Centimani Studio" in buf.value:
                                found.append(hwnd)
                    return True

                user32.EnumWindows(_enum_cb, 0)
                if found:
                    SW_MAXIMIZE = 3
                    user32.ShowWindow(found[0], SW_MAXIMIZE)
                    user32.SetForegroundWindow(found[0])
                    return
            except Exception:
                return
    threading.Thread(target=_worker, daemon=True).start()


def launch_fullscreen_browser(url):
    """Launches the default or installed browser in maximized/fullscreen mode if enabled."""
    use_fs = get_app_settings().get("auto_fullscreen", True)
    browser_candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe")
    ]
    launched = False
    for exe in browser_candidates:
        if os.path.exists(exe):
            flags = ["--start-maximized", "--new-window"] if use_fs else ["--new-window"]
            if "chrome" in exe.lower():
                subprocess.Popen([exe] + flags + ["--app=" + url])
            else:
                subprocess.Popen([exe] + flags + [url])
            launched = True
            break
    if not launched:
        webbrowser.open(url)
    if use_fs:
        _maximize_studio_window_async()


def run_server(port=8765):
    from core.golden_data import get_valid_test_ids, get_configured_centimani_dir
    threading.Thread(target=get_valid_test_ids, daemon=True).start()
    threading.Thread(target=get_configured_centimani_dir, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", port), StudioRequestHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"Centimani Studio V2.4 (Build v0.8.055) Server running at {url}")
    launch_fullscreen_browser(url)
    server.serve_forever()


if __name__ == "__main__":
    run_server(port=8765)
