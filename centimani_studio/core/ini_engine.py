# -*- coding: utf-8 -*-
r"""
Centimani Studio V2.2 - System.ini & Global.ini Engine
1. When repairing an existing Excel that already has a sibling System.ini, preserves all original
   SFIS / iPLAS / MiniCloud / LoopRunning keys and only updates NewFormatScriptFile & TestItemCodeFile.
2. Automatically copies Test Item Code V2.04_20250310.xlsx into the output System\ folder so
   CentimaniSystem.exe and EditorScriptTool.exe can run immediately without missing-file errors.
"""
import os
import sys
import re
import glob
import shutil
from .checksum_signer import generate_official_checksum

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)


def copy_test_item_code_to_output(output_dir, tic_filename="Test Item Code V2.04_20260521.xlsx"):
    """Copies the official Test Item Code Excel file into output_dir so CentimaniSystem.exe can load it."""
    target_path = os.path.join(output_dir, tic_filename)
    if os.path.exists(target_path):
        return tic_filename

    _meipass = getattr(sys, "_MEIPASS", None)
    _exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else None
    search_roots = [p for p in [
        os.path.join(BASE_DIR, "data"),
        os.path.join(_meipass, "data") if _meipass else "",
        os.path.join(_exe_dir, "data") if _exe_dir else "",
        os.path.join(PROJECT_ROOT, "SCRIPTS", "ATLAS_SAMPLE"),
        os.path.join(PROJECT_ROOT, "Centmimani_Altas_TRY", "System"),
        os.path.join(PROJECT_ROOT, "Centimani_1.5.3_sample", "System"),
        os.path.join(PROJECT_ROOT, "TEST_SECRIPT"),
        os.path.join(PROJECT_ROOT, "SCRIPTS"),
        r"D:\PYTHON\自動化編寫EXCEL\SCRIPTS",
    ] if p]
    for s_root in search_roots:
        if not os.path.exists(s_root):
            continue
        exact_p = os.path.join(s_root, tic_filename)
        if os.path.exists(exact_p):
            shutil.copy2(exact_p, os.path.join(output_dir, tic_filename))
            return tic_filename
        candidates = glob.glob(os.path.join(s_root, "**", tic_filename), recursive=True)
        if not candidates:
            candidates = glob.glob(os.path.join(s_root, "**", "*Test Item Code V2*.xlsx"), recursive=True)
        if candidates:
            src_tic = candidates[0]
            actual_name = os.path.basename(src_tic)
            shutil.copy2(src_tic, os.path.join(output_dir, actual_name))
            return actual_name
    return tic_filename


def sync_and_generate_inis(workspace, excel_filename, output_dir):
    """
    Scans the workspace for all *$(VAR) references:
    - Variables in DUTs / Instrument -> placed in Global.ini [Settings]
    - Variables in Station / Marco sheets -> placed in Global.ini [Scripts]
    Generates 100% compliant System.ini and Global.ini in output_dir, and copies Test Item Code file.
    """
    os.makedirs(output_dir, exist_ok=True)
    g_ini = workspace.setdefault("global_ini", {"Settings": {}, "Scripts": {}})
    settings_map = g_ini.setdefault("Settings", {})
    scripts_map = g_ini.setdefault("Scripts", {})

    # 1. Scan DUTs and Instrument for [Settings] variables
    for sec in ["duts", "instruments", "switches"]:
        for row in workspace.get(sec, []):
            text = " ".join([str(v) for v in row.values() if v])
            for m in re.finditer(r"\*\$\(([^)]+)\)", text):
                vname = m.group(1).strip()
                if vname not in settings_map:
                    settings_map[vname] = scripts_map.get(vname, "1")

    # 2. Scan Station & Marco sheets for [Scripts] variables
    for sheet_group in (workspace.get("stations", {}), workspace.get("marcos", {})):
        for _s_name, steps in sheet_group.items():
            if not isinstance(steps, list):
                continue
            for step in steps:
                text = " ".join([str(v) for v in step.values() if v])
                for m in re.finditer(r"\*\$\(([^)]+)\)", text):
                    vname = m.group(1).strip()
                    if vname not in scripts_map:
                        scripts_map[vname] = settings_map.get(vname, "DEFAULT_VAL")

    # 3. Build Global.ini content
    global_lines = [
        "[Settings]",
        "// ============================================================================",
        "// [Settings] 區段：僅供 DUTs 與 Instrument 工作表透過 *$(變數名) 讀取",
        "// ============================================================================"
    ]
    for k, v in settings_map.items():
        global_lines.append(f"{k}={v}")

    global_lines.extend([
        "",
        "[Scripts]",
        "// ============================================================================",
        "// [Scripts] 區段：僅供各測試站位 (Station / Marco) 工作表透過 *$(變數名) 讀取",
        "// ============================================================================"
    ])
    for k, v in scripts_map.items():
        global_lines.append(f"{k}={v}")

    global_ini_path = os.path.join(output_dir, "Global.ini")
    with open(global_ini_path, "w", encoding="utf-8") as f:
        f.write("\n".join(global_lines) + "\n")

    # 4. Copy Test Item Code file into output_dir so the package is 100% self-contained
    sys_cfg = workspace.get("system_ini", {})
    desired_tic = sys_cfg.get("TestItemCodeFile", "Test Item Code V2.04_20260521.xlsx")
    actual_tic_name = copy_test_item_code_to_output(output_dir, desired_tic)

    # 5. Check if source_file has an existing sibling System.ini we should preserve!
    source_file = workspace.get("source_file", "")
    system_ini_path = os.path.join(output_dir, "System.ini")
    station_names = list(workspace.get("stations", {}).keys())
    station_list_str = ",".join(station_names) if station_names else workspace.get("station_name", "MB")
    if str(sys_cfg.get("StationName_Mode", "")).lower() == "ask":
        active_station = ""
    elif "StationName" in sys_cfg:
        active_station = str(sys_cfg.get("StationName", "")).strip()
    else:
        active_station = workspace.get("station_name", station_names[0] if station_names else "MB")

    has_preserved_sys = False
    if source_file and os.path.exists(source_file):
        src_folder = os.path.dirname(source_file)
        for cand_sys in [os.path.join(src_folder, "System.ini"), os.path.join(src_folder, "System", "System.ini")]:
            if os.path.exists(cand_sys):
                raw_sys = open(cand_sys, "r", encoding="utf-8", errors="ignore").read()
                raw_sys = re.sub(r"(?m)^NewFormatScriptFile=.*$", f"NewFormatScriptFile={excel_filename}", raw_sys)
                raw_sys = re.sub(r"(?m)^TestItemCodeFile=.*$", f"TestItemCodeFile={actual_tic_name}", raw_sys)
                if str(sys_cfg.get("StationName_Mode", "")).lower() == "ask" or (
                    "StationName" in sys_cfg and str(sys_cfg.get("StationName", "")).strip() == ""
                ):
                    if re.search(r"(?m)^StationName=.*$", raw_sys):
                        raw_sys = re.sub(r"(?m)^StationName=.*$", "StationName=", raw_sys)
                for k_ov in ("DebugMode", "RetryCount", "StationList", "StationName", "SFIS_Enable", "SFIS_LinkIPLAS", "SFIS_WebLink", "SFIS_TSP", "iPLAS_Enable", "iPLAS_Site", "iPLAS_ProjectName"):
                    if k_ov in sys_cfg and str(sys_cfg[k_ov]).strip() != "":
                        v_ov = str(sys_cfg[k_ov]).strip()
                        if re.search(rf"(?m)^{re.escape(k_ov)}=.*$", raw_sys):
                            raw_sys = re.sub(rf"(?m)^{re.escape(k_ov)}=.*$", lambda _m, val=f"{k_ov}={v_ov}": val, raw_sys)
                with open(system_ini_path, "w", encoding="utf-8") as f:
                    f.write(raw_sys)
                has_preserved_sys = True
                break

    if not has_preserved_sys:
        # Generate complete standard 9-section System.ini
        proj_name = workspace.get("project_name", "PEGA_PROJECT")
        system_lines = [
            "[System]",
            f"LargeWindow={sys_cfg.get('LargeWindow', '0')}",
            f"DUTFlowDirection={sys_cfg.get('DUTFlowDirection', '0')}",
            f"RetryCount={sys_cfg.get('RetryCount', '3')}",
            f"DeviceSemaphore={sys_cfg.get('DeviceSemaphore', '1')}",
            f"DebugMode={sys_cfg.get('DebugMode', '1')}",
            f"IndividualScanBarCode={sys_cfg.get('IndividualScanBarCode', '1')}",
            f"NewFormatScriptFile={excel_filename}",
            f"TestItemCodeFile={actual_tic_name}",
            f"StationList={station_list_str}",
            f"StationName={active_station}",
            "SendWithout\\n=1",
            f"LoopRunning={sys_cfg.get('LoopRunning', '0')}",
            f"RobotMode={sys_cfg.get('RobotMode', '0')}",
            "DontLogRef=1",
            "DontConvertErrorCode=0",
            "SetScanFocus=1",
            "CreateReport=1",
            "",
            "[IpFinder]",
            f"IpFinder_Enable={sys_cfg.get('IpFinder_Enable', '0')}",
            "IpFinder_LocalIP=192.168.1.100",
            "IpFinder_Segment=192.168.1",
            "IpFinder_LastNoStart=2",
            "IpFinder_LastNoEnd=20",
            "IpFinder_SaveDebugLog=1",
            "",
            "[SFIS]",
            f"SFIS_Enable={sys_cfg.get('SFIS_Enable', '0')}",
            "SFIS_AutoLogin=1",
            f"SFIS_LinkIPLAS={sys_cfg.get('SFIS_LinkIPLAS', '0')}",
            f"SFIS_WebLink={sys_cfg.get('SFIS_WebLink', 'http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx')}",
            f"SFIS_TSP={sys_cfg.get('SFIS_TSP', proj_name[:6] + ',2')}",
            "SFIS_OPID_LENGTH=9",
            "SFIS_OPID_PATTERN=[L-S][0-9A-Z][0-9A-Z][0-9A-Z][0-9][0-9][0-9][0-9][0-9]",
            "SFIS_CheckRouteType=1",
            "SFIS_RepairEnable=1",
            "SFIS_RepairType=1",
            "SFIS_RepairReason=ZR",
            "SFIS_RepairDuty=7C0",
            "SFIS_RepairNGRP=AUTO2A",
            "SFIS_SkipSaveResultOnFail=0",
            "SFIS_GetDateISN=111111111111111",
            "SFIS_ResultFile=",
            "SFIS_SaveGPRS=0",
            "SFIS_SaveError=0",
            "SFIS_SyncTime=0",
            "SFIS_LoginID=",
            "",
            "[FTP]",
            "FTP_Enable=0",
            "FTP_Host=172.24.255.135",
            f"FTP_Folder={proj_name}/MP",
            "FTP_ID=",
            "FTP_PW=",
            "",
            "[MiniCloud]",
            "MiniCloud_Enable=0",
            "MiniCloud_Host=172.22.248.50",
            f"MiniCloud_ProjectName={proj_name}",
            f"MiniCloud_ModelName={proj_name}",
            "MiniCloud_LogPath=",
            "MiniCloud_iPLAS=0",
            "MiniCloud_iPLASLogPath=",
            "MiniCloud_DebugMode=0",
            "",
            "[iPLAS]",
            f"iPLAS_Enable={sys_cfg.get('iPLAS_Enable', '0')}",
            "iPLAS_DebugMsg=1",
            f"iPLAS_ProjectName={sys_cfg.get('iPLAS_ProjectName', proj_name)}",
            "iPLAS_ScanDirectories=Log;Report;Record;Debug",
            "iPLAS_UploadPassLog=1",
            "iPLAS_UploadFailLog=1",
            "iPLAS_UploadValidInSeconds=600",
            "iPLAS_UploadFileTypes=log;ini;ct;bmp;csv;wav;txt",
            "iPLAS_UploadDebugFile=1",
            "iPLAS_UploadMatchISN=1",
            "iPLAS_EncryptedZip=0",
            "iPLAS_SkipErrorCode=BSFO14;BSFO75;OTCH013",
            f"iPLAS_Site={sys_cfg.get('iPLAS_Site', 'DC')}",
            "",
            "[YRsetting]",
            "Auto_Clear=1",
            "Diff_HRs=48",
            "YR_Limit=0.9",
            "YR_FileN=YR.st",
            "",
            "[CSVReport]",
            f"CSVReport_Enable={sys_cfg.get('CSVReport_Enable', '1')}",
            f"CSVReport_LogFile={proj_name}_{active_station}_Report.csv",
            "CSVReport_WhiteList=",
            "CSVReport_ContactInfo=",
            "CSVReport_ToHex=",
            "",
            "[Checksum]",
            f"// 調試階段 DebugMode=1 免驗證 Checksum；正式上線請以 EditorScriptTool.exe 對 System\\{excel_filename} 產生簽章"
        ]
        with open(system_ini_path, "w", encoding="utf-8") as f:
            f.write("\n".join(system_lines) + "\n")

    # 6. Automatically compute and write official 64-char Checksum into System.ini!
    excel_full_path = os.path.join(output_dir, excel_filename)
    computed_sign = generate_official_checksum(excel_full_path, system_ini_path)
    if computed_sign:
        with open(system_ini_path, "r", encoding="utf-8", errors="ignore") as f:
            cur_sys = f.read()

        sign_line = f"{excel_filename}={computed_sign}"
        # Preserve all other files in [Checksum] section, and update/add the current file!
        file_pattern = rf"(?m)^{re.escape(excel_filename)}=.*$"
        if re.search(file_pattern, cur_sys):
            cur_sys = re.sub(file_pattern, sign_line, cur_sys)
        elif "[Checksum]" in cur_sys:
            cur_sys = re.sub(r"(?m)^\[Checksum\]\r?$", f"[Checksum]\n{sign_line}", cur_sys)
        else:
            cur_sys += f"\n[Checksum]\n{sign_line}\n"

        with open(system_ini_path, "w", encoding="utf-8") as f:
            f.write(cur_sys)

    return system_ini_path, global_ini_path
