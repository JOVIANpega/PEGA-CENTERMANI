# -*- coding: utf-8 -*-
"""
Centimani Studio - Checksum Auto-Signer Engine
Uses LoadScript.dll (from Centimani_1.5.3_sample) to compute official 64-char SHA256 Checksum
and write it into System.ini [Checksum] section automatically!
"""
import os
import glob
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)


def _find_loadscript_dll():
    candidates = []
    try:
        from .golden_data import get_configured_centimani_dir
        cm_dir = get_configured_centimani_dir()
        if cm_dir:
            candidates.append(os.path.join(cm_dir, "LoadScript.dll"))
    except Exception:
        pass
    candidates.extend([
        os.path.join(PROJECT_ROOT, "Centimani_1.5.3_sample", "LoadScript.dll"),
        os.path.join(PROJECT_ROOT, "CENTERMAINA_TRY", "LoadScript.dll"),
        os.path.join(BASE_DIR, "LoadScript.dll"),
    ])
    for p in candidates:
        if os.path.exists(p):
            return p
    found = glob.glob(os.path.join(PROJECT_ROOT, "**", "LoadScript.dll"), recursive=True)
    return found[0] if found else candidates[0]


LOADSCRIPT_DLL = _find_loadscript_dll()


def generate_official_checksum(excel_file_path, sys_ini_path):
    """
    Computes official 64-char Centimani Checksum using LoadScript.MainScript.GetChecksum().
    Returns the 64-character hex string, or None if computation fails.
    """
    dll_path = LOADSCRIPT_DLL if os.path.exists(LOADSCRIPT_DLL) else _find_loadscript_dll()
    if not os.path.exists(dll_path) or not os.path.exists(excel_file_path):
        return None

    # PowerShell 32-bit script to invoke LoadScript.dll
    ps_cmd = (
        f"$p = '{dll_path}'; "
        f"$asm = [System.Reflection.Assembly]::LoadFrom($p); "
        f"$inst = [System.Activator]::CreateInstance($asm.GetType('LoadScript.MainScript')); "
        f"$res = $inst.GetChecksum('{excel_file_path}', '{sys_ini_path}', ''); "
        f"Write-Host $res"
    )

    powershell_x86 = os.path.join(os.environ.get("windir", r"C:\Windows"), "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
    if not os.path.exists(powershell_x86):
        powershell_x86 = "powershell.exe"

    try:
        proc = subprocess.run(
            [powershell_x86, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15
        )
        out = proc.stdout.strip()
        # Output format is often "HEX64[]" or "HEX64[signer]"
        if len(out) >= 64:
            clean_hash = out[:64].upper()
            if all(c in "0123456789ABCDEF" for c in clean_hash):
                return clean_hash
    except Exception:
        pass
    return None
