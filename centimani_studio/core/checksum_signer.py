# -*- coding: utf-8 -*-
"""
Centimani Studio - Checksum Auto-Signer Engine
Uses LoadScript.dll (from Centimani_1.5.3_sample) to compute official 64-char SHA256 Checksum
and write it into System.ini [Checksum] section automatically!
"""
import os
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
LOADSCRIPT_DLL = os.path.join(PROJECT_ROOT, "Centimani_1.5.3_sample", "LoadScript.dll")


def generate_official_checksum(excel_file_path, sys_ini_path):
    """
    Computes official 64-char Centimani Checksum using LoadScript.MainScript.GetChecksum().
    Returns the 64-character hex string, or None if computation fails.
    """
    if not os.path.exists(LOADSCRIPT_DLL) or not os.path.exists(excel_file_path):
        return None

    # PowerShell 32-bit script to invoke LoadScript.dll
    ps_cmd = (
        f"$p = '{LOADSCRIPT_DLL}'; "
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
