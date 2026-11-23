# -*- coding: utf-8 -*-
"""
Centimani Studio - Golden Mother Template, 16-Column Block Library, and TestID Dictionary
Integrates official rules from Centimani Script User Guide (2022/2023), Ver1.65 Instrument Spec,
and real production blocks from VALO360, KANGAROO (MU310/Olympus), Raptor, and MiniBox.
"""
import os
import glob
import openpyxl

STATION_HEADERS_16 = [
    "Index", "Phase", "Title", "Marco", "Instrument", "Switch",
    "Send", "Reply", "EndPrompt", "Ref", "Validation", "Prompt",
    "Waiting", "ExecMode", "Description", "TestID"
]

MARCO_HEADERS_11 = [
    "Index", "Send", "Reply", "EndPrompt", "Ref", "Validation",
    "Prompt", "Waiting", "ExecMode", "Description", "TestID"
]

DUTS_HEADERS_10 = [
    "Load", "DUT Name", "Station", "Parameter", "SFIS_DeviceID",
    "ScanBarcode( {Name,Lengh,Pattern} )",
    "Connection1 (Type,Name,ConnectString)",
    "Connection2 (Type,Name,ConnectString)",
    "Connection3 (Type,Name,ConnectString)",
    "Connection4(Type,Name,ConnectString)"
]

SWITCH_HEADERS_7 = [
    "Mount", "Name", "ControlDLL", "Settings", "Version", "Loss", "Desc"
]

INSTRUMENT_HEADERS_9 = [
    "Mount", "Name", "Sub", "ControlDLL", "Settings", "Functions", "Version", "Switch", "Desc"
]


def get_golden_mother(project_name="NEW_PROJECT", station_name="MB"):
    """Returns a complete Golden Blank Mother Template (Properties, 4-Slot DUTs, Switch, Instrument, and initial Station)."""
    duts_rows = []
    for slot in range(1, 5):
        # Centimani requires unique Connection Names across DUTs if multi-slot (e.g. UART_1, UART_2)
        # and Utility is built-in so Connection4 is not needed
        conn1_name = "UART" if slot == 1 else f"UART_{slot}"
        conn2_name = "CmdConsole" if slot == 1 else f"CmdConsole_{slot}"
        conn3_name = "UARTF" if slot == 1 else f"UARTF_{slot}"
        duts_rows.append({
            "Load": f"*$(LOAD_{slot})",
            "DUT Name": f"{project_name}${station_name}",
            "Station": f"{station_name},{slot}",
            "Parameter": f"*$(PCIP_{slot}),*$(DUTIP_{slot}),{slot}",
            "SFIS_DeviceID": f"*$(DEVID_{slot})",
            "ScanBarcode( {Name,Lengh,Pattern} )": "{ISN,3,[0-9A-Z]}",
            "Connection1 (Type,Name,ConnectString)": f'"Uart","{conn1_name}","*$(DUT_UR{slot}),115200,8,One,None,None,10000,5000"',
            "Connection2 (Type,Name,ConnectString)": f'"APP","{conn2_name}","C:\\Windows\\System32\\cmd.exe,0,5000,"',
            "Connection3 (Type,Name,ConnectString)": f'"Uart","{conn3_name}","*$(PCUART_fixture_{slot}),9600,8,One,None,None,10000,5000"',
            "Connection4(Type,Name,ConnectString)": ""
        })

    return _sync_real_dll_versions({
        "project_name": project_name,
        "station_name": station_name,
        "properties": [
            {"Name": "Version", "Value": "AUTO_TIMESTAMP"},
            {"Name": "Creator", "Value": "PEGA_Engineer"},
            {"Name": "FailCount", "Value": "0"}
        ],
        "duts": duts_rows,
        "switches": [
            {
                "Mount": "",
                "Name": "RFSwitch3001",
                "ControlDLL": "RFSwitch3001.dll",
                "Settings": "GPIB,GPIB0::1::INSTR,1,1",
                "Version": "1.0.0.0",
                "Loss": "0",
                "Desc": "RF Switch 1 to 4"
            }
        ],
        "instruments": [
            {"Mount": "", "Name": "IPOWER2401", "Sub": "", "ControlDLL": "iPower2401.dll", "Settings": "192.168.201.11,192.168.201.3,9999,1", "Functions": "POWERSWITCH", "Version": "1.0.0.0", "Switch": "", "Desc": "Power Switch 2401"},
            {"Mount": "", "Name": "IPRO800", "Sub": "", "ControlDLL": "iPowerPro800.dll", "Settings": "*$(PCUART_P),1", "Functions": "POWERSWITCH", "Version": "1.0.0.0", "Switch": "", "Desc": "Power Switch Pro800"},
            {"Mount": "", "Name": "NI6008-1", "Sub": "", "ControlDLL": "DaqUSBNi.dll", "Settings": "*$(DAQ_1)", "Functions": "Voltage", "Version": "1.1.2.0", "Switch": "", "Desc": "DAQ device NI6008/6009"},
            {"Mount": "", "Name": "Agilent34401A", "Sub": "", "ControlDLL": "Agilent34401A.dll", "Settings": "GPIB,GPIB0::16::INSTR", "Functions": "DC,AC,FREQ", "Version": "1.0.0.2", "Switch": "", "Desc": "Agilent 34401A Multimeter (Device\\Agilent34401A.dll)"},
            {"Mount": "", "Name": "FeasaLED", "Sub": "", "ControlDLL": "LED_analyser.dll", "Settings": "*$(LED_AZ1),57600,*$(LED_Light1)", "Functions": "LED_Test", "Version": "2.1.0.1", "Switch": "", "Desc": "LED analyser FeasaLED"},
            {"Mount": "", "Name": "NI4461", "Sub": "", "ControlDLL": "DaqNI4461.dll", "Settings": "Dev2", "Functions": "VOIP,RMS", "Version": "1.0.0.0", "Switch": "", "Desc": "DAQ device NI4461 Audio"},
            {"Mount": "", "Name": "QRDecode", "Sub": "", "ControlDLL": "QRDecode.dll", "Settings": "", "Functions": "QRCode", "Version": "1.0.0.0", "Switch": "", "Desc": "Decode QR Code"},
            {"Mount": "", "Name": "InstIQApiA", "Sub": "", "ControlDLL": "InstIQApi_A.dll", "Settings": "192.168.100.254,1,2,1,60000,PathLoss.ini", "Functions": "MeasWIFI,MeasCW,GenWIFI,GenBT,MeasBT,WIFI 5G,WIFI 2.4G,BT,CW", "Version": "1.0.0.4", "Switch": "", "Desc": "LitePoint IQxel A Route"},
            {"Mount": "", "Name": "XelM8-B", "Sub": "", "ControlDLL": "InstIQApi_B.dll", "Settings": "", "Functions": "MeasWIFI,MeasBT,WIFI 5G,WIFI 2.4G,BT,CW", "Version": "1.0.0.0", "Switch": "", "Desc": "LitePoint IQxel B Route"},
            {"Mount": "", "Name": "MT8870A", "Sub": "", "ControlDLL": "InstAnritsu.dll", "Settings": "", "Functions": "MeasWIFI,MeasBT,WIFI,BT", "Version": "1.0.0.0", "Switch": "", "Desc": "Anritsu MT8870A RF Tester"},
            {"Mount": "", "Name": "Chroma6150x", "Sub": "", "ControlDLL": "Chroma6150x.dll", "Settings": "", "Functions": "ACSource,PowerSource", "Version": "1.0.0.0", "Switch": "", "Desc": "Chroma AC Power Source"},
            {"Mount": "", "Name": "Chroma6310A", "Sub": "", "ControlDLL": "Chroma6310A.dll", "Settings": "", "Functions": "DCLoad,ElectronicLoad", "Version": "1.0.0.0", "Switch": "", "Desc": "Chroma DC Electronic Load"},
            {"Mount": "", "Name": "KEITHLEY2302", "Sub": "", "ControlDLL": "KEITHLEY2302.dll", "Settings": "", "Functions": "DC,SetVoltageCurrent,GetVoltageCurrent", "Version": "1.0.0.0", "Switch": "", "Desc": "Keithley 2302 Battery Simulator"},
            {"Mount": "", "Name": "PPH1503", "Sub": "", "ControlDLL": "PPH1503.dll", "Settings": "GPIB,*$(GPIBPPH1503)", "Functions": "DC,MCurr,MVolt,SCurr,SVolt,SON,OnOff,CLR,MSCurr,MSVolt,SetCurr,SetVolt,SetON,OUTONOFF", "Version": "1.0.2.0", "Switch": "", "Desc": "Power Supply PPH1503"},
            {"Mount": "", "Name": "PSS1503-1", "Sub": "", "ControlDLL": "PPH1503.dll", "Settings": "GPIB,*$(GPIB1503-1)", "Functions": "DC,MCurr,MVolt,SCurr,SVolt,SON,OnOff,CLR", "Version": "1.0.3.0", "Switch": "", "Desc": "DC Power 1503"},
            {"Mount": "", "Name": "PS2005-1", "Sub": "", "ControlDLL": "PSS2005.dll", "Settings": "GPIB,*$(GPIB2005)", "Functions": "DC,MCurr,MVolt,SCurr,SVolt,SON,OnOff,CLR", "Version": "1.0.1.0", "Switch": "", "Desc": "Power Supply PSS2005"},
            {"Mount": "", "Name": "GDM906x", "Sub": "", "ControlDLL": "GDM906x.dll", "Settings": "", "Functions": "DMM,VDC,ADC,VAC,AAC,FREQ", "Version": "1.0.0.0", "Switch": "", "Desc": "GW Instek GDM906x Multimeter"},
            {"Mount": "", "Name": "MDA2700", "Sub": "", "ControlDLL": "MDA2700.dll", "Settings": "", "Functions": "DAQ,FREQ,AC,DC", "Version": "1.0.0.1", "Switch": "", "Desc": "MDA2700 Data Acquisition"},
            {"Mount": "", "Name": "E4418B", "Sub": "", "ControlDLL": "PMeterE4418B.dll", "Settings": "", "Functions": "PMeter,RFPWR", "Version": "1.0.0.0", "Switch": "", "Desc": "Agilent E4418B Power Meter"},
            {"Mount": "", "Name": "U2004A", "Sub": "", "ControlDLL": "U2004A.dll", "Settings": "", "Functions": "PMeter,txPWR", "Version": "2.0.1.0", "Switch": "", "Desc": "Keysight U2004A USB Power Sensor"},
            {"Mount": "", "Name": "OSP120", "Sub": "", "ControlDLL": "NFT.dll", "Settings": "", "Functions": "RFSW,NFT", "Version": "1.0.0.0", "Switch": "", "Desc": "R&S OSP120 RF Switch"},
            {"Mount": "", "Name": "SAn9000", "Sub": "", "ControlDLL": "SAn9000.dll", "Settings": "", "Functions": "SA,RFPWR,FREQ,SMASK", "Version": "1.0.0.0", "Switch": "", "Desc": "Spectrum Analyzer"},
            {"Mount": "", "Name": "vnxRFSW", "Sub": "1", "ControlDLL": "vnxRFSWlib.dll", "Settings": ".\\device\\VNX_switch.dll", "Functions": "RFSW,gInfo,gName,initDev,getSwitch,setSwitch,getActive", "Version": "1.0.0.0", "Switch": "", "Desc": "Vaunix RF Switch (SubDevice)"},
            {"Mount": "", "Name": "HXTaudio", "Sub": "", "ControlDLL": "HXTaudio.dll", "Settings": "", "Functions": "Audio,HXTaudio1", "Version": "1.0.0.6", "Switch": "", "Desc": "HXT Audio Analyzer"},
            {"Mount": "", "Name": "SAu3751", "Sub": "", "ControlDLL": "SAu3751.dll", "Settings": "", "Functions": "Audio,RFPWR,FREQ,SMASK", "Version": "1.0.0.0", "Switch": "", "Desc": "Audio Analyzer SAu3751"},
            {"Mount": "", "Name": "FC6000-1", "Sub": "", "ControlDLL": "FCPM6000.dll", "Settings": "FCPM-6000RC,1,500", "Functions": "AirTest,PwrRG,FcRG,rFreq,rPwr,rVol,rFrPw,List,gIP,Rst,CHECK", "Version": "1.0.1.10", "Switch": "", "Desc": "Fukuda Air Leak Tester FC6000"},
            {"Mount": "", "Name": "FM480-1", "Sub": "", "ControlDLL": "FM480.dll", "Settings": "", "Functions": "AirTest,FSCAN", "Version": "1.0.1.0", "Switch": "", "Desc": "Flow Meter FM480"},
            {"Mount": "", "Name": "DIO6509", "Sub": "", "ControlDLL": "DigitIO6509.dll", "Settings": "", "Functions": "DIO,IOswitch", "Version": "1.0.0.0", "Switch": "", "Desc": "NI PCI-6509 Digital I/O"},
            {"Mount": "", "Name": "Redrat", "Sub": "", "ControlDLL": "RedratOut.dll", "Settings": "", "Functions": "IR,RRout", "Version": "1.0.0.0", "Switch": "", "Desc": "RedRat IR Blaster"},
            {"Mount": "", "Name": "SFE100", "Sub": "", "ControlDLL": "SFE100.dll", "Settings": "", "Functions": "SFE,SETDVBC,PREDEV,RESDEV,DEFDEV", "Version": "1.0.0.0", "Switch": "", "Desc": "SFE100 Test Device"},
            {"Mount": "", "Name": "ScpTDS3014B", "Sub": "", "ControlDLL": "ScpTDS3014B.dll", "Settings": "", "Functions": "Scope,RMS,VOLAGE,FREQ,MEAN,AMPL,PK2PK", "Version": "1.0.3.2", "Switch": "", "Desc": "Tektronix TDS3014B Oscilloscope"},
            {"Mount": "", "Name": "DevUart", "Sub": "1", "ControlDLL": "DevUart.dll", "Settings": "", "Functions": "UART", "Version": "1.0.1.1", "Switch": "", "Desc": "SubDevice UART Controller (SubDevice)"},
            {"Mount": "", "Name": "AutoTFTP", "Sub": "", "ControlDLL": "AutoTFTP.dll", "Settings": "", "Functions": "TFTP", "Version": "1.0.0.0", "Switch": "", "Desc": "Auto TFTP Server"},
            {"Mount": "", "Name": "DevQueue", "Sub": "", "ControlDLL": "DevQueue.dll", "Settings": "", "Functions": "Queue", "Version": "1.0.1.0", "Switch": "", "Desc": "Device Queue Sync"},
            {"Mount": "", "Name": "LVdev", "Sub": "", "ControlDLL": "tf_LVDevice.dll", "Settings": "", "Functions": "LV", "Version": "1.0.0.0", "Switch": "", "Desc": "LabVIEW Test Device"}
        ],
        "stations": {
            station_name: []
        },
        "global_ini": {
            "Settings": {
                "PCIP_1": "192.168.11.3",
                "DUTIP_1": "192.168.11.143",
                "PCIP_2": "192.168.12.3",
                "DUTIP_2": "192.168.12.143",
                "PCIP_3": "192.168.13.3",
                "DUTIP_3": "192.168.13.143",
                "PCIP_4": "192.168.14.3",
                "DUTIP_4": "192.168.14.143",
                "DUT_UR1": "COM4",
                "DUT_UR2": "COM5",
                "DUT_UR3": "COM6",
                "DUT_UR4": "COM7",
                "PCUART_fixture_1": "COM8",
                "PCUART_fixture_2": "COM9",
                "PCUART_fixture_3": "COM10",
                "PCUART_fixture_4": "COM11",
                "PCUART_P": "COM12",
                "DUT_Login": "root",
                "LOAD_1": "true",
                "LOAD_2": "false",
                "LOAD_3": "false",
                "LOAD_4": "false",
                "DEVID_1": "825201",
                "DEVID_2": "825202",
                "DEVID_3": "825203",
                "DEVID_4": "825204",
                "DAQ_1": "Dev1",
                "LED_AZ1": "COM17",
                "LED_Light1": "02"
            },
            "Scripts": {
                "FW_VERSION": "1.0.0_release",
                "sfisSKU": "DEFAULT_SKU",
                "Boot_Delay": "3000",
                "PythonPath": "D:\\PythonScript"
            }
        },
        "system_ini": {
            "DebugMode": "1",
            "RetryCount": "3",
            "SFIS_Enable": "0",
            "iPLAS_Enable": "0",
            "IpFinder_Enable": "0",
            "CSVReport_Enable": "1",
            "TestItemCodeFile": "Test Item Code V2.04_20250310.xlsx"
        }
    })


def get_configured_centimani_dir():
    """
    Returns the Centimani main program directory (containing Device/ and LoadScript.dll).
    Reads `centimani_dir` from config.json; if unset/missing, auto-scans PROJECT_ROOT
    and saves the discovered path into config.json so the user isn't prompted repeatedly.
    """
    import json
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proj_root = os.path.dirname(base_dir)
    cfg_path = os.path.join(base_dir, "config.json")
    cfg = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f) or {}
        except Exception:
            cfg = {}
    saved_dir = str(cfg.get("centimani_dir", "")).strip()
    if saved_dir and os.path.isdir(saved_dir):
        return saved_dir

    # Auto-detect inside PROJECT_ROOT
    candidates = [
        os.path.join(proj_root, "CENTERMAINA_TRY"),
        os.path.join(proj_root, "Centimani_1.5.3_sample"),
    ]
    for d_name in os.listdir(proj_root):
        d_path = os.path.join(proj_root, d_name)
        if os.path.isdir(d_path) and d_path not in candidates:
            if os.path.exists(os.path.join(d_path, "LoadScript.dll")) or os.path.isdir(os.path.join(d_path, "Device")):
                candidates.append(d_path)

    for cand in candidates:
        if os.path.isdir(cand) and (os.path.exists(os.path.join(cand, "LoadScript.dll")) or os.path.isdir(os.path.join(cand, "Device"))):
            cfg["centimani_dir"] = cand
            try:
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return cand
    return ""


def _get_local_dll_versions(force_refresh=False):
    """Reads actual FileVersion of local Centimani Device/Switch DLLs (cached)."""
    if not force_refresh and hasattr(_get_local_dll_versions, "_cache"):
        return _get_local_dll_versions._cache
    versions = {}
    try:
        import glob
        import win32api
        proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        search_dirs = []
        cm_dir = get_configured_centimani_dir()
        if cm_dir:
            search_dirs.append(cm_dir)
        for sub in ("CENTERMAINA_TRY", "Centimani_1.5.3_sample"):
            p = os.path.join(proj_root, sub)
            if p not in search_dirs:
                search_dirs.append(p)
        for base_d in search_dirs:
            if not os.path.exists(base_d):
                continue
            for dll_p in glob.glob(os.path.join(base_d, "**", "*.dll"), recursive=True):
                d_name = os.path.basename(dll_p).lower()
                if d_name in versions:
                    continue
                try:
                    info = win32api.GetFileVersionInfo(dll_p, "\\")
                    ver = f"{win32api.HIWORD(info['FileVersionMS'])}.{win32api.LOWORD(info['FileVersionMS'])}.{win32api.HIWORD(info['FileVersionLS'])}.{win32api.LOWORD(info['FileVersionLS'])}"
                    versions[d_name] = ver
                except Exception:
                    pass
    except Exception:
        pass
    _get_local_dll_versions._cache = versions
    return versions


TEMPLATED_INSTS = {
    "NI6008-1", "FeasaLED", "IPOWER2401", "IPRO800",
    "Agilent34401A", "MDA2700", "PS2005-1",
    "InstIQApiA", "XelM8-B", "MT8870A", "DIO6509",
}


def _sync_real_dll_versions(mother_dict):
    dll_vers = _get_local_dll_versions()
    for sec in ("instruments", "switches"):
        for item in mother_dict.get(sec, []):
            dll_n = str(item.get("ControlDLL", "")).strip().lower()
            i_name = str(item.get("Name", "")).strip()
            has_tpl = i_name in TEMPLATED_INSTS
            if dll_vers:
                item["dll_exists"] = (dll_n in dll_vers) if dll_n else True
                if dll_n and dll_n in dll_vers:
                    item["Version"] = dll_vers[dll_n]
            else:
                item["dll_exists"] = True
            item["has_template"] = has_tpl
            item["is_usable"] = bool(item["dll_exists"] or has_tpl)
    return mother_dict


def check_workspace_missing_dlls(ws: dict) -> dict:
    """檢查 workspace 中實際有掛載 (Mount 非空) 或測站步驟有使用之 Instrument / Switch 對應的 ControlDLL 是否存在。"""
    cm_dir = get_configured_centimani_dir()
    cm_dir_exists = bool(cm_dir and os.path.isdir(cm_dir))
    dll_vers = _get_local_dll_versions(force_refresh=True) if cm_dir_exists else {}

    used_inst_tokens = set()
    used_sw_tokens = set()
    for rows in (ws.get("stations") or {}).values():
        if not isinstance(rows, list):
            continue
        for r in rows:
            it = str(r.get("Instrument", "")).strip().lower()
            if it:
                used_inst_tokens.add(it)
            sw = str(r.get("Switch", "")).strip().lower()
            if sw:
                used_sw_tokens.add(sw)

    missing_dlls = []
    seen = set()
    for sec in ("instruments", "switches"):
        for inst_r in ws.get(sec, []):
            d_fn = str(inst_r.get("ControlDLL", "")).strip()
            name = str(inst_r.get("Name", "")).strip()
            mount = str(inst_r.get("Mount", "")).strip()
            if not d_fn:
                continue
            if sec == "instruments":
                funcs = {f.strip().lower() for f in str(inst_r.get("Functions", "")).split(",") if f.strip()}
                is_active = bool(mount) or (name.lower() in used_inst_tokens) or bool(funcs & used_inst_tokens)
            else:
                is_active = bool(mount) or (name.lower() in used_sw_tokens)
            if not is_active:
                continue
            key = (name.lower(), d_fn.lower())
            if key in seen:
                continue
            seen.add(key)
            if not cm_dir_exists or d_fn.lower() not in dll_vers:
                missing_dlls.append({"inst": name, "dll": d_fn})
    return {
        "centimani_dir": cm_dir,
        "centimani_dir_exists": cm_dir_exists,
        "missing_dlls": missing_dlls,
    }


STANDARD_BLOCKS = [
    {
        "block_id": "BLK_PRETEST_ROUTE",
        "category": "01. 前置與治具控制 (Phase 0)",
        "name": "條碼顯示與 SFIS 路由驗證 (CheckRoute)",
        "description": "標準 Phase 0 開場積木：顯示 ISN 至 UI、斷開舊 UART、向 SFIS 驗證站點路由。",
        "default_phase": "0",
        "required_globals": {"Settings": {}, "Scripts": {}},
        "steps": [
            {"Phase": "0", "Title": "0,CheckRoute", "Marco": "", "Instrument": "", "Switch": "", "Send": ':ShowISN,"*(ISN)"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Show ISN to UI", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Disconnect,"UART"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Disconnect UART safely", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":SfCheckRoute", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "2000", "ExecMode": "8", "Description": "PC#-#CheckRoute from SFIS", "TestID": "OTFX064"}
        ]
    },
    {
        "block_id": "BLK_FIXTURE_ACTION",
        "category": "01. 前置與治具控制 (Phase 0)",
        "name": "氣動治具下壓與等待上電 (Fixture Down)",
        "description": "標準治具下壓動作，等待待測物供電穩定。",
        "default_phase": "",
        "required_globals": {"Settings": {"PCUART_fixture": "COM5"}, "Scripts": {}},
        "steps": [
            {"Phase": "", "Title": "0,Fixture Down", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"UARTF"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Fixture#-#Connect Fixture UART", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": "UARTF@G\\r\\n", "Reply": "", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Fixture#-#Pneumatic Fixture Down", "TestID": "OTFX157"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Delay,"3000"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "PC#-#Wait Power Rail Stable", "TestID": "B7PL025"}
        ]
    },
    {
        "block_id": "BLK_POWER_ON_IPOWER",
        "category": "01. 前置與治具控制 (Phase 0)",
        "name": "iPower 電源供應器冷復位上電 (Power Cold Reset)",
        "description": "取得電源互斥鎖 -> 關閉輸出 -> 延遲 -> 開啟輸出 -> 釋放鎖 (ExecMode=3)。",
        "default_phase": "",
        "required_globals": {"Settings": {}, "Scripts": {}},
        "steps": [
            {"Phase": "", "Title": "0,Power ON Sequence", "Marco": "", "Instrument": "POWERSWITCH", "Switch": "", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Power#-#Obtain Power Lock", "TestID": "BRME027"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Dev.SwitchOFF,"1"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Power#-#Switch OFF Channel 1", "TestID": "BRME027"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Delay,"500"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "PC#-#Wait Discharge", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Dev.SwitchON,"1"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Power#-#Switch ON Channel 1", "TestID": "BRME027"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "Power#-#Release Power Lock", "TestID": "BRME027"}
        ]
    },
    {
        "block_id": "BLK_VOLT_NI6008_BATCH",
        "category": "02. 電壓與電流測試 (Voltage & Power)",
        "name": "NI-6008 / NI-6009 電壓量測（支援單端 RSE 與差動 DIFF）",
        "description": "標準 DAQ 電壓量測：支援單端 RSE 多通道一次讀取與兩線差動 DIFF，可於 Step 3 開啟圖文接線介面點選腳位與上下限。",
        "default_phase": "1",
        "required_globals": {"Settings": {"DAQ_1": "Dev1"}, "Scripts": {}},
        "steps": [
            {"Phase": "1", "Title": "0,Measure Voltage Test,3", "Marco": "", "Instrument": "Voltage", "Switch": "NI6008-1", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "INST#-#Obtain NI6008 Lock", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Delay,"1500"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "PC#-#Wait Voltage Stabilize", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Dev.VOLTAGE,"RSE,1000,0,1,2"', "Reply": "0", "EndPrompt": "", "Ref": "$VCC_5V;\n$VCC_3V3;\n$VCC_1V8", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "INST#-#Read AI0(5V), AI1(3.3V), AI2(1.8V)", "TestID": "BRPW033"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "INST#-#Release NI6008 Lock", "TestID": "BRME027"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':CheckLimit,"*(VCC_5V)","4.75","5.25","%f"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "2:0", "Description": "DUT#-#Check VCC_5V (4.75V~5.25V)", "TestID": "BRPW024"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':CheckLimit,"*(VCC_3V3)","3.15","3.45","%f"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "2:0", "Description": "DUT#-#Check VCC_3V3 (3.15V~3.45V)", "TestID": "BRPW024"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':CheckLimit,"*(VCC_1V8)","1.71","1.89","%f"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "2:0", "Description": "DUT#-#Check VCC_1V8 (1.71V~1.89V)", "TestID": "BRPW024"}
        ]
    },
    {
        "block_id": "BLK_VOLT_MDA2700_DAQ970A",
        "category": "02. 電壓與電流測試 (Voltage & Power)",
        "name": "Agilent 34401A 萬用電表多通道 DC 電壓量測",
        "description": "使用本機 Device\\Agilent34401A.dll 透過 GPIB 讀取 DC 電壓（不缺 DLL）。",
        "default_phase": "3",
        "required_globals": {"Settings": {}, "Scripts": {}},
        "steps": [
            {"Phase": "3", "Title": "0,DMM Measure DC Voltage,3", "Marco": "", "Instrument": "DC", "Switch": "Agilent34401A", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "DMM#-#Obtain Multimeter Lock", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Dev.DC,"101-102-103,1500"', "Reply": "0", "EndPrompt": "", "Ref": "$CH101_12V;\n$CH102_5V;\n$CH103_3V3", "Validation": "(CH101_12V,%f,11.4,12.6);\n(CH102_5V,%f,4.75,5.25);\n(CH103_3V3,%f,3.15,3.45)", "Prompt": "", "Waiting": "", "ExecMode": "2:0", "Description": "DMM#-#Measure Ch101~103 DC Voltage", "TestID": "BRPW033"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "DMM#-#Release Multimeter Lock", "TestID": "BRME027"}
        ]
    },
    {
        "block_id": "BLK_UART_BOOT_FW",
        "category": "03. UART 通訊與韌體版本檢查 (Console & FW)",
        "name": "UART 開機登入與韌體版本比對 (*$(FW_VERSION))",
        "description": "連線 UART、發送換行確認進入 Console (#)，並讀取韌體版本與 Global.ini 的 [Scripts] FW_VERSION 比對。",
        "default_phase": "4",
        "required_globals": {"Settings": {"DUT_UR1": "COM4"}, "Scripts": {"FW_VERSION": "1.0.0_release"}},
        "steps": [
            {"Phase": "4", "Title": "0,Check UART & FW Version,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"UART"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Connect UART Port", "TestID": "OTFX082"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": "UART@\\r\\n", "Reply": "@#", "EndPrompt": "#", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "5000", "ExecMode": "1", "Description": "DUT#-#Check Console Prompt", "TestID": "OTFX079"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": "UART@cat /etc/version\\r\\n", "Reply": "@", "EndPrompt": "#", "Ref": '$DUT_FW:WithinString,"version=","\\r\\n","":Trim', "Validation": "(DUT_FW,%s,*$(FW_VERSION),*$(FW_VERSION))", "Prompt": "", "Waiting": "5000", "ExecMode": "1", "Description": "DUT#-#Verify Firmware Version", "TestID": "VSCH026"}
        ]
    },
    {
        "block_id": "BLK_SFIS_MAC_69PN",
        "category": "04. SFIS 資料讀取與寫入 (SFIS & MAC/SN)",
        "name": "SFIS 取得 MAC 與 69PN 並寫入比對",
        "description": "標準 SFIS 讀取積木：取得 LAN/WiFi MAC 與 69PN，並驗證 12 碼長度。",
        "default_phase": "5",
        "required_globals": {"Settings": {}, "Scripts": {}},
        "steps": [
            {"Phase": "5", "Title": "0,GET_SFIS_MAC_AND_PN,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ':SfGetVersion,"*(ISN)","ISN_BASEINFO","2","MAC1",""', "Reply": "", "EndPrompt": "", "Ref": "$sfisLANMAC", "Validation": "(sfisLANMAC,%len,12,12)", "Prompt": "", "Waiting": "", "ExecMode": "9", "Description": "PC#-#Get MAC1 from SFIS", "TestID": "OTFX133"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':SfGetVersion,"*(ISN)","ITEMINFO","2","69PN",""', "Reply": "", "EndPrompt": "", "Ref": "$sf69PN", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "9", "Description": "PC#-#Get 69PN from SFIS", "TestID": "OTFX085"}
        ]
    },
    {
        "block_id": "BLK_PYTHON_SCRIPT_CALL",
        "category": "05. 外部 Python 腳本與 Utility 呼叫 (Python & API)",
        "name": "呼叫外部 Python 腳本並抓回數值比對 (CmdConsole@python.exe)",
        "description": "Olympus (SSH_C.py / 1KHz.py) 實戰寫法：免做 DLL，直接透過 CmdConsole 執行 .py 並用 WithinString 擷取 print() 數值。",
        "default_phase": "6",
        "required_globals": {"Settings": {}, "Scripts": {"PythonPath": "D:\\PythonScript"}},
        "steps": [
            {"Phase": "6", "Title": "0,Run External Python Script,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"CmdConsole"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Open Windows CMD Console", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": 'CmdConsole@cd *$(PythonPath)&&cmd /c python.exe my_test.py "*(ISN)"\\r\\n', "Reply": "@Command pass", "EndPrompt": ">", "Ref": '$PyVal:WithinString,"RESULT=","\\n","":Trim', "Validation": "(PyVal,%f,0.0,100.0)", "Prompt": "", "Waiting": "10000", "ExecMode": "1", "Description": "PC#-#Execute Python Script & Validate Output", "TestID": "OTFX054"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Disconnect,"CmdConsole"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Close Windows CMD Console", "TestID": "B7PL025"}
        ]
    },
    {
        "block_id": "BLK_UTILITY_PING_LAN",
        "category": "05. 外部 Python 腳本與 Utility 呼叫 (Python & API)",
        "name": "網路 Ping 連通性測試 (:Utility.Ping)",
        "description": "Raptor / Olympus 實戰寫法：使用 UtilityLibrary 執行 Ping 測試確認網卡連通。",
        "default_phase": "7",
        "required_globals": {"Settings": {"PCIP_1": "192.168.11.3", "DUTIP_1": "192.168.11.143"}, "Scripts": {"DUTIP_1": "192.168.11.143", "PCIP_1": "192.168.11.3"}},
        "steps": [
            {"Phase": "7", "Title": "0,LAN Ping Test,5", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Utility.Ping,"*$(DUTIP_1)","5000","*$(PCIP_1)"', "Reply": "0", "EndPrompt": "", "Ref": "$PingRes", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Ping DUT Ethernet IP", "TestID": "IOPI113"}
        ]
    },
    {
        "block_id": "BLK_LED_FEASA",
        "category": "06. LED / 音訊 / 感測器測試 (Peripherals)",
        "name": "Feasa LED 色彩波長與亮度檢測",
        "description": "透過 Feasa LED Analyser 擷取色座標/波長與亮度並驗證範圍。",
        "default_phase": "8",
        "required_globals": {"Settings": {"LED_AZ1": "COM17", "LED_Light1": "02"}, "Scripts": {}},
        "steps": [
            {"Phase": "8", "Title": "0,Check LED Color & Intensity,3", "Marco": "", "Instrument": "LED_Test", "Switch": "FeasaLED", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "LED#-#Obtain Feasa LED Lock", "TestID": "BRME027"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Dev.CaptureAndRead,"01"', "Reply": "0", "EndPrompt": "", "Ref": "$LED_Wave;\n$LED_Int", "Validation": "(LED_Wave,%f,515,535);\n(LED_Int,%f,1000,99999)", "Prompt": "", "Waiting": "", "ExecMode": "2:0", "Description": "LED#-#Verify Green LED Wavelength & Intensity", "TestID": "IOLE015"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "LED#-#Release Feasa LED Lock", "TestID": "BRME027"}
        ]
    },
    {
        "block_id": "BLK_WIFI_RF_IQXEL",
        "category": "06. LED / 音訊 / 感測器 / RF 測試 (Peripherals & RF)",
        "name": "WiFi Tx / Rx 射頻量測完整 Marco 範本 (LitePoint IQxel)",
        "description": "整合實戰 WIFI Tx MCS 與 WIFI Rx MCS 子工作表（21 步完整 wl 控板 + InstIQApi_A 量測 Power/FreqErr/EVM/RxPER）。",
        "default_phase": "9",
        "required_globals": {"Settings": {}, "Scripts": {}},
        "required_marcos": {
            "WIFI Tx MCS": [
                {"Index": "00", "Send": ':SetOprVal,"pwrval","{4}*4"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Set Power Value", "TestID": "OTFX054"},
                {"Index": "01", "Send": ':SetCdtiVal,"chain","{3}==3","3","{3}"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Set chain", "TestID": "OTFX054"},
                {"Index": "02", "Send": ':SetCdtiVal,"bw","{1}==40","l",""', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Set bandwidth", "TestID": "OTFX054"},
                {"Index": "03", "Send": ':SetCdtiVal,"txbw","{1}==20","2","4"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "check bandwidth value", "TestID": "OTFX054"},
                {"Index": "04", "Send": ':SetCdtiVal,"chaddval","{1}==20","0","2"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "check channel add value", "TestID": "OTFX054"},
                {"Index": "05", "Send": ':SetOprVal,"chval","{0} + *(chaddval)"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "measure after bw channel", "TestID": "OTFX054"},
                {"Index": "06", "Send": ':SetCdtiVal,"Channel","{1}==40","*(chval)","{0}"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "check after bw channel", "TestID": "OTFX054"},
                {"Index": "07", "Send": "LAN@wl pkteng_stop tx", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "pkteng_stop tx", "TestID": "WFOT036"},
                {"Index": "08", "Send": "LAN@wl chanspec {0}*(bw)", "Reply": "@Chanspec set to 0x", "EndPrompt": "#", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set Channel,Bandwidth", "TestID": "WFOT036"},
                {"Index": "09", "Send": "LAN@wl mimo_txbw *(txbw)", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set mimo Bandwidth", "TestID": "WFOT036"},
                {"Index": "10", "Send": "LAN@wl 2g_rate auto", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set 2g Rate auto", "TestID": "WFOT036"},
                {"Index": "11", "Send": "LAN@wl nrate -m {2}", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set Modulation", "TestID": "WFOT036"},
                {"Index": "12", "Send": "LAN@wl txchain *(chain)", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set Antenna", "TestID": "WFOT036"},
                {"Index": "13", "Send": "LAN@wl txpwr1 -o -q *(pwrval)", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set Tx Power", "TestID": "WFOT036"},
                {"Index": "14", "Send": "LAN@wl phy_forcecal 1", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "phy_forcecal 1", "TestID": "WFOT036"},
                {"Index": "15", "Send": "LAN@wl isup", "Reply": "@1", "EndPrompt": "#", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "ask WIFI status", "TestID": "WFOT036"},
                {"Index": "16", "Send": "LAN@wl pkteng_start 00:11:22:33:44:55 tx 30 1500 0", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Send Tx Packet", "TestID": "WFOT036"},
                {"Index": "17", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Obtain Device", "TestID": "OTFX091"},
                {"Index": "18", "Send": ':Delay,"10"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Delay", "TestID": "OTFX054"},
                {"Index": "19", "Send": ':Dev.MeasWIFI,"{3}","11n_MCS{2}_{1}","*(Channel)","{4}","0",""', "Reply": "0", "EndPrompt": "", "Ref": "Power;\nFreqErrPPM;\nEVM", "Validation": "(Power,%f,{5},{6});\n(FreqErrPPM,%f,-20,20);\n(EVM,%f,{7},{8})", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Device analytic WIFI packets", "TestID": "OTFX091"},
                {"Index": "20", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "Release Device", "TestID": "OTFX091"}
            ],
            "WIFI Rx MCS": [
                {"Index": "00", "Send": ':SetCdtiVal,"chain","{3}==3","3","{3}"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Set chain", "TestID": "OTFX054"},
                {"Index": "01", "Send": ':SetCdtiVal,"bw","{1}==40","l",""', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Set bandwidth", "TestID": "OTFX054"},
                {"Index": "02", "Send": ':SetOprVal,"chval","{0}+2"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "measure after bw channel", "TestID": "OTFX054"},
                {"Index": "03", "Send": ':SetCdtiVal,"Channel","{1}==40","*(chval)","{0}"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "check after bw channel", "TestID": "OTFX054"},
                {"Index": "04", "Send": "LAN@wl down", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "WIFI down", "TestID": "WFOT036"},
                {"Index": "05", "Send": "LAN@wl band b", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "6", "Description": "Set 2.4G band b", "TestID": "WFOT036"},
                {"Index": "06", "Send": "LAN@wl up", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "WIFI up", "TestID": "WFOT036"},
                {"Index": "07", "Send": "LAN@wl chanspec {0}*(bw)", "Reply": "@Chanspec set to 0x", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "2000", "ExecMode": "1", "Description": "Set Channel,Bandwidth", "TestID": "WFOT036"},
                {"Index": "08", "Send": "LAN@wl mimo_txbw 4", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set mimo Bandwidth", "TestID": "WFOT036"},
                {"Index": "09", "Send": "LAN@wl 2g_rate auto", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set 2g Rate auto", "TestID": "WFOT036"},
                {"Index": "10", "Send": "LAN@wl nrate -m {2}", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set Modulation", "TestID": "WFOT036"},
                {"Index": "11", "Send": "LAN@wl rxchain *(chain)", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set Antenna", "TestID": "WFOT036"},
                {"Index": "12", "Send": "LAN@wl isup", "Reply": "@1", "EndPrompt": "#", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "ask WIFI status", "TestID": "WFOT036"},
                {"Index": "13", "Send": "LAN@wl phy_forcecal 1", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set phy_forcecal 1", "TestID": "WFOT036"},
                {"Index": "14", "Send": "LAN@wl pkteng_start 00:00:00:C0:FF:EE rxwithack", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Set rxwithack", "TestID": "WFOT036"},
                {"Index": "15", "Send": "LAN@wl phy_rssi_ant;echo OK", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "ask phy_rssi_ant", "TestID": "WFOT036"},
                {"Index": "16", "Send": "LAN@wl reset_cnts", "Reply": "@#", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Reset Rx Counter", "TestID": "WFOT036"},
                {"Index": "17", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Obtain Device", "TestID": "WFOT036"},
                {"Index": "18", "Send": ':Dev.GenWIFI,"{3}","11n_MCS{2}_{1}","*(Channel)","{4}","1000","0"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Device Start WIFI VSG", "TestID": "OTFX091"},
                {"Index": "19", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "Release Device", "TestID": "OTFX091"},
                {"Index": "20", "Send": ':Delay,"200"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "6", "Description": "Delay", "TestID": "OTFX054"},
                {"Index": "21", "Send": "LAN@wl counters;echo OK", "Reply": "@#", "EndPrompt": "", "Ref": 'RxOK:WithinString,"rxdfrmocast","rxmfrmocast","0"', "Validation": "(RxOK,%d,900,1000)", "Prompt": "", "Waiting": "", "ExecMode": "2:16", "Description": "Count OK's Packets for Rx", "TestID": "WFOT036"}
            ]
        },
        "steps": [
            {"Phase": "9", "Title": "0,WIFI TX1_CH3 MCS7_BW20", "Marco": "WIFI Tx MCS", "Instrument": "MeasWIFI", "Switch": "InstIQApiA", "Send": "3,20,7,1,15,13,17,-50,-28,WIFI TX1_CH3 MCS7_BW20", "Reply": "", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "RF#-#WIFI TX CH3 MCS7 BW20", "TestID": "WFOT036"},
            {"Phase": "", "Title": "0,WIFI RX1_CH5 MCS7_BW40", "Marco": "WIFI Rx MCS", "Instrument": "GenWIFI", "Switch": "InstIQApiA", "Send": "5,40,7,1,-59,WIFI RX1_CH5 MCS7_BW40", "Reply": "", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "RF#-#WIFI RX CH5 MCS7 BW40", "TestID": "WFOT036"}
        ]
    },
    {
        "block_id": "BLK_PHASE97_TEARDOWN",
        "category": "97. 強制安全收尾 (Phase 97 End Test)",
        "name": "Phase 97 強制斷電、治具抬起與資源釋放",
        "description": "必備安全收尾積木：無論前方 PASS 或 FAIL 皆強制執行斷電、治具復位與斷開所有 COM Port (ExecMode=3)。",
        "default_phase": "97",
        "required_globals": {"Settings": {}, "Scripts": {}},
        "steps": [
            {"Phase": "97", "Title": "1,End Test Safe Teardown,1", "Marco": "", "Instrument": "POWERSWITCH", "Switch": "", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "Power#-#Obtain Power Lock", "TestID": "BRME027"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Dev.SwitchOFF,"1"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "Power#-#Switch OFF Power", "TestID": "BRME027"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":ReleaseDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "Power#-#Release Power Lock", "TestID": "BRME027"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": "UARTF@F\\r\\n", "Reply": "", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "Fixture#-#Pneumatic Fixture UP", "TestID": "OTFX157"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Disconnect,"UARTF"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "Fixture#-#Disconnect Fixture UART", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Disconnect,"UART"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Disconnect DUT UART", "TestID": "B7PL025"}
        ]
    }
]


_CACHED_VALID_TEST_IDS = None
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(_BASE_DIR)
_TIC_CACHE_FILE = os.path.join(_BASE_DIR, ".tic_cache.json")


def get_valid_test_ids(scripts_root=None):
    """Loads all valid 6/7-character TestIDs from the cached Test Item Code V2.04+ catalog (fast <0.02s)."""
    global _CACHED_VALID_TEST_IDS
    if _CACHED_VALID_TEST_IDS is not None:
        return _CACHED_VALID_TEST_IDS

    valid_ids = {
        "B7PL025", "OTFX064", "OTFX082", "OTFX157", "OTFX15A", "OTFX133", "OTFX085",
        "OTFX054", "OTFX079", "OTFX075", "OTFX055", "OTCH013", "BRME027", "BRPW024",
        "BRPW033", "WUPO010", "WUPO011", "WUPO013", "KAOT041", "KAOT042", "KAOT043",
        "KAOT044", "KAOT045", "KAOT046", "VSCH026", "VSCH001", "VSCH002", "IOPI113",
        "IPIO01D", "IPIP048", "NUNU003", "CACK088", "CACK211", "CACK226", "WFOT013",
        "WFOT024", "WFOT030", "WFOT034", "WFOT036", "IOLE015"
    }
    try:
        for item in get_tic_catalog():
            tid = str(item.get("test_id", "")).strip().upper()
            if len(tid) in (6, 7) and tid.isalnum():
                valid_ids.add(tid)
    except Exception:
        pass

    _CACHED_VALID_TEST_IDS = valid_ids
    return valid_ids


_CACHED_TIC_CATALOG = None
_ACTIVE_TIC_PATH = None


def set_tic_catalog_path(file_path):
    """Switches the active Test Item Code Excel file and reloads the catalog."""
    global _CACHED_TIC_CATALOG, _ACTIVE_TIC_PATH
    _ACTIVE_TIC_PATH = file_path
    _CACHED_TIC_CATALOG = None
    cat = get_tic_catalog()
    return get_active_tic_info()


def get_active_tic_info():
    """Returns metadata about the currently loaded Test Item Code Excel file."""
    cat = get_tic_catalog()
    return {
        "file_path": _ACTIVE_TIC_PATH or "",
        "file_name": os.path.basename(_ACTIVE_TIC_PATH) if _ACTIVE_TIC_PATH else "未載入",
        "count": len(cat)
    }


def get_tic_catalog():
    """
    Loads the official Test Item Code catalog (TestID, ErrorCode, English/Chinese descriptions)
    from the selected or default Test Item Code Excel file.
    """
    global _CACHED_TIC_CATALOG, _ACTIVE_TIC_PATH
    if _CACHED_TIC_CATALOG is not None:
        return _CACHED_TIC_CATALOG

    catalog = []
    if _ACTIVE_TIC_PATH and os.path.exists(_ACTIVE_TIC_PATH):
        tic_path = _ACTIVE_TIC_PATH
    else:
        candidates = [
            os.path.join(_PROJECT_ROOT, "Centimani_1.5.3_sample", "System", "Test Item Code V2.04_20250310.xlsx"),
            os.path.join(_PROJECT_ROOT, "SCRIPTS", "Test Item Code V2.04_20250310.xlsx"),
            os.path.join(_PROJECT_ROOT, "SCRIPTS", "KANGAROO", "Test Item Code V2.04_20250310.xlsx"),
            r"D:\PYTHON\自動化編寫EXCEL\Centimani_1.5.3_sample\System\Test Item Code V2.04_20250310.xlsx",
            r"D:\PYTHON\自動化編寫EXCEL\SCRIPTS\AI_SOURCE\KANGAROO\FW\Test Item Code V2.04_20250310.xlsx",
        ]
        tic_path = next((p for p in candidates if os.path.exists(p)), None)
        if not tic_path:
            for sr in (os.path.join(_PROJECT_ROOT, "SCRIPTS"), r"D:\PYTHON\自動化編寫EXCEL\SCRIPTS"):
                if os.path.exists(sr):
                    found = glob.glob(os.path.join(sr, "**", "*Test Item Code V2*.xlsx"), recursive=True)
                    if found:
                        tic_path = found[0]
                        break
        _ACTIVE_TIC_PATH = tic_path

    if tic_path:
        import json
        try:
            cur_mtime = os.path.getmtime(tic_path)
            if os.path.exists(_TIC_CACHE_FILE):
                with open(_TIC_CACHE_FILE, "r", encoding="utf-8") as cf:
                    cached = json.load(cf)
                if cached.get("path") == tic_path and cached.get("mtime") == cur_mtime and cached.get("catalog"):
                    _CACHED_TIC_CATALOG = cached["catalog"]
                    return _CACHED_TIC_CATALOG
        except Exception:
            cur_mtime = 0

        try:
            wb = openpyxl.load_workbook(tic_path, read_only=True, data_only=True)
            ws = wb["Test Item All"] if "Test Item All" in wb.sheetnames else wb.active
            curr_mf = ""
            curr_if = ""
            for r in ws.iter_rows(min_row=6, values_only=True):
                if not r or len(r) < 7:
                    continue
                if r[0]:
                    curr_mf = str(r[0]).strip()
                if r[1]:
                    curr_if = str(r[1]).strip()
                tid = str(r[2] or "").strip().upper()
                if not tid or len(tid) < 6:
                    continue
                desc_en = str(r[3] or "").strip()
                desc_cn = str(r[4] or "").strip()
                err_code = str(r[6] or "").strip().upper()
                # Heuristic: generic codes usually have standard 6-char ErrorCode (e.g. BSFxxx, AFFxxx)
                # and avoid project-specific TP/board identifiers in the description.
                is_proj_specific = (
                    len(err_code) > 6
                    or "_TP" in desc_en.upper()
                    or "TP1" in desc_en.upper()
                    or "TP2" in desc_en.upper()
                    or "T86_" in desc_en.upper()
                    or "1080I" in desc_en.upper()
                    or "480P" in desc_en.upper()
                    or "720P" in desc_en.upper()
                    or "BARD_" in desc_en.upper()
                )
                catalog.append({
                    "test_id": tid,
                    "error_code": err_code,
                    "desc_en": desc_en,
                    "desc_cn": desc_cn,
                    "main_func": curr_mf,
                    "interface": curr_if,
                    "is_generic": not is_proj_specific,
                })
            wb.close()
            if catalog:
                try:
                    with open(_TIC_CACHE_FILE, "w", encoding="utf-8") as cf:
                        json.dump({"path": tic_path, "mtime": cur_mtime, "catalog": catalog}, cf, ensure_ascii=False)
                except Exception:
                    pass
        except Exception:
            pass

    _CACHED_TIC_CATALOG = catalog
    return catalog


def search_test_ids(query, limit=30, generic_only=False):
    """
    Searches the official Test Item Code catalog by free-text keywords (EN/CN/TestID/ErrorCode),
    prioritizing generic production codes over project-specific test point codes.
    """
    q = (query or "").strip()
    if not q:
        return []

    import re
    tokens = [t.lower() for t in re.split(r"[\s,;/#\-_]+", q) if t.strip()]
    if not tokens:
        return []

    catalog = get_tic_catalog()
    scored = []
    for item in catalog:
        if generic_only and not item["is_generic"]:
            continue
        tid_l = item["test_id"].lower()
        ec_l = item["error_code"].lower()
        en_l = item["desc_en"].lower()
        cn_l = item["desc_cn"].lower()
        mf_l = item["main_func"].lower()
        if_l = item["interface"].lower()

        score = 0
        matched_tokens = 0
        for tok in tokens:
            hit = False
            if tok == tid_l or tok == ec_l:
                score += 100
                hit = True
            elif tid_l.startswith(tok) or ec_l.startswith(tok):
                score += 50
                hit = True
            if tok in en_l:
                score += 20
                hit = True
            if tok in cn_l:
                score += 25
                hit = True
            if tok in mf_l or tok in if_l:
                score += 8
                hit = True
            if hit:
                matched_tokens += 1

        if matched_tokens == 0:
            continue

        # Bonus for matching all tokens and being a generic production code
        if matched_tokens == len(tokens):
            score += 30
        if item["is_generic"]:
            score += 25
        # Prefer concise generic descriptions
        score -= min(len(item["desc_en"]), 60) * 0.1
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored[:limit]]
