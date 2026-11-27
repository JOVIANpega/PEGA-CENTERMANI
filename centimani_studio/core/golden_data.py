# -*- coding: utf-8 -*-
"""
Centimani Studio - Golden Mother Template, 16-Column Block Library, and TestID Dictionary
Integrates official rules from Centimani Script User Guide (2022/2023), Ver1.65 Instrument Spec,
and real production blocks from VALO360, KANGAROO (MU310/Olympus), Raptor, and MiniBox.
"""
import os
import sys
import re
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
        # Centimani checks ConnectionList uniqueness per DUT row (NOT across multi-DUT slots):
        # Parallel slots 1..4 share connection aliases ("UART", "CmdConsole", "UARTF") while each row binds its own COM Port,
        # and Utility is built-in so Connection4 is not needed
        conn1_name = "UART"
        conn2_name = "CmdConsole"
        conn3_name = "UARTF"
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
            {"Mount": "", "Name": "NI6008", "Sub": "", "ControlDLL": "DaqUSBNi.dll", "Settings": "*$(DAQ_1)", "Functions": "Voltage", "Version": "1.1.2.0", "Switch": "", "Desc": "DAQ device NI6008/6009"},
            {"Mount": "", "Name": "Agilent34401A", "Sub": "", "ControlDLL": "Agilent34401A.dll", "Settings": "GPIB,GPIB0::16::INSTR", "Functions": "DC,AC,FREQ", "Version": "1.0.0.2", "Switch": "", "Desc": "Agilent 34401A Multimeter (Device\\Agilent34401A.dll)"},
            {"Mount": "", "Name": "FeasaLED", "Sub": "", "ControlDLL": "LED_analyser.dll", "Settings": "*$(LED_AZ1),57600,*$(LED_Light1)", "Functions": "LED_Test", "Version": "2.1.0.1", "Switch": "", "Desc": "LED analyser FeasaLED"},
            {"Mount": "", "Name": "NI4461", "Sub": "", "ControlDLL": "DaqNI4461.dll", "Settings": "Dev2", "Functions": "VOIP,RMS", "Version": "1.0.0.0", "Switch": "", "Desc": "DAQ device NI4461 Audio"},
            {"Mount": "", "Name": "QRDecode", "Sub": "", "ControlDLL": "QRDecode.dll", "Settings": "", "Functions": "QRCode", "Version": "1.0.0.0", "Switch": "", "Desc": "Decode QR Code"},
            {"Mount": "", "Name": "InstIQApiA", "Sub": "", "ControlDLL": "InstIQApi_A.dll", "Settings": "192.168.100.254,1,2,1,60000,PathLoss.ini", "Functions": "MeasWIFI,MeasCW,GenWIFI,GenBT,MeasBT,WIFI 5G,WIFI 2.4G,BT,CW", "Version": "1.0.1.2", "Switch": "", "Desc": "LitePoint IQxel A Route"},
            {"Mount": "", "Name": "XelM8-A", "Sub": "", "ControlDLL": "InstIQApi_A.dll", "Settings": "*$(IQ_IP),4,2,*$(IQapt),20000,XelM8_PathLoss.ini", "Functions": "MeasWIFI,GenWIFI,MeasBT,GenBT,WIFI 5G,WIFI 2.4G,BT,11ah,CW", "Version": "1.0.1.2", "Switch": "", "Desc": "LitePoint XelM8-A RF Tester (含 11ah)"},
            {"Mount": "", "Name": "IQFlex-A", "Sub": "", "ControlDLL": "InstIQApi_A.dll", "Settings": "*$(IQ_IP),0,0,3,60000,PathLoss.ini", "Functions": "MeasWIFI,GenWIFI,MeasBT,WIFI 2.4G,BT", "Version": "1.0.0.6", "Switch": "", "Desc": "LitePoint IQFlex-A RF Tester"},
            {"Mount": "", "Name": "XelM8-B", "Sub": "", "ControlDLL": "InstIQApi_B.dll", "Settings": "", "Functions": "MeasWIFI,MeasBT,WIFI 5G,WIFI 2.4G,BT,CW", "Version": "1.0.0.0", "Switch": "", "Desc": "LitePoint IQxel B Route"},
            {"Mount": "", "Name": "MT8870A", "Sub": "", "ControlDLL": "InstAnritsu.dll", "Settings": "", "Functions": "MeasWIFI,MeasBT,WIFI,BT", "Version": "1.0.0.0", "Switch": "", "Desc": "Anritsu MT8870A RF Tester"},
            {"Mount": "", "Name": "Chroma6150x", "Sub": "", "ControlDLL": "Chroma6150x.dll", "Settings": "", "Functions": "ACSource,PowerSource", "Version": "1.0.0.0", "Switch": "", "Desc": "Chroma AC Power Source"},
            {"Mount": "", "Name": "Chroma6310A", "Sub": "", "ControlDLL": "Chroma6310A.dll", "Settings": "", "Functions": "DCLoad,ElectronicLoad", "Version": "1.0.0.0", "Switch": "", "Desc": "Chroma DC Electronic Load"},
            {"Mount": "", "Name": "KEITHLEY2302", "Sub": "", "ControlDLL": "KEITHLEY2302.dll", "Settings": "", "Functions": "DC,SetVoltageCurrent,GetVoltageCurrent", "Version": "1.0.0.0", "Switch": "", "Desc": "Keithley 2302 Battery Simulator"},
            {"Mount": "", "Name": "PPH1503", "Sub": "", "ControlDLL": "PPH1503.dll", "Settings": "GPIB,*$(GPIBPPH1503)", "Functions": "DC,MCurr,MVolt,SCurr,SVolt,SON,OnOff,CLR,MSCurr,MSVolt,SetCurr,SetVolt,SetON,OUTONOFF", "Version": "1.0.2.0", "Switch": "", "Desc": "Power Supply PPH1503"},
            {"Mount": "", "Name": "PSS1503", "Sub": "", "ControlDLL": "PPH1503.dll", "Settings": "GPIB,*$(GPIB1503-1)", "Functions": "DC,MCurr,MVolt,SCurr,SVolt,SON,OnOff,CLR", "Version": "1.0.3.0", "Switch": "", "Desc": "DC Power 1503"},
            {"Mount": "", "Name": "PS2005", "Sub": "", "ControlDLL": "PSS2005.dll", "Settings": "GPIB,*$(GPIB2005)", "Functions": "DC,MCurr,MVolt,SCurr,SVolt,SON,OnOff,CLR", "Version": "1.0.1.0", "Switch": "", "Desc": "Power Supply PSS2005"},
            {"Mount": "", "Name": "GDM906x", "Sub": "", "ControlDLL": "GDM906x.dll", "Settings": "", "Functions": "DMM,VDC,ADC,VAC,AAC,FREQ", "Version": "1.0.0.0", "Switch": "", "Desc": "GW Instek GDM906x Multimeter"},
            {"Mount": "", "Name": "MDA2700", "Sub": "", "ControlDLL": "MDA2700.dll", "Settings": "", "Functions": "DAQ,FREQ,AC,DC", "Version": "1.0.0.1", "Switch": "", "Desc": "MDA2700 Data Acquisition"},
            {"Mount": "", "Name": "E4418B", "Sub": "", "ControlDLL": "PMeterE4418B.dll", "Settings": "", "Functions": "PMeter,RFPWR", "Version": "1.0.0.0", "Switch": "", "Desc": "Agilent E4418B Power Meter"},
            {"Mount": "", "Name": "U2004A", "Sub": "", "ControlDLL": "U2004A.dll", "Settings": "", "Functions": "PMeter,txPWR", "Version": "2.0.1.0", "Switch": "", "Desc": "Keysight U2004A USB Power Sensor"},
            {"Mount": "", "Name": "OSP120", "Sub": "", "ControlDLL": "NFT.dll", "Settings": "", "Functions": "RFSW,NFT", "Version": "1.0.0.0", "Switch": "", "Desc": "R&S OSP120 RF Switch"},
            {"Mount": "", "Name": "SAn9000", "Sub": "", "ControlDLL": "SAn9000.dll", "Settings": "", "Functions": "SA,RFPWR,FREQ,SMASK", "Version": "1.0.0.0", "Switch": "", "Desc": "Spectrum Analyzer"},
            {"Mount": "", "Name": "vnxRFSW", "Sub": "1", "ControlDLL": "vnxRFSWlib.dll", "Settings": ".\\device\\VNX_switch.dll", "Functions": "RFSW,gInfo,gName,initDev,getSwitch,setSwitch,getActive", "Version": "1.0.0.0", "Switch": "", "Desc": "Vaunix RF Switch (SubDevice)"},
            {"Mount": "", "Name": "HXTaudio", "Sub": "", "ControlDLL": "HXTaudio.dll", "Settings": "", "Functions": "Audio,HXTaudio1", "Version": "1.0.0.6", "Switch": "", "Desc": "HXT Audio Analyzer"},
            {"Mount": "", "Name": "SAu3751", "Sub": "", "ControlDLL": "SAu3751.dll", "Settings": "", "Functions": "Audio,RFPWR,FREQ,SMASK", "Version": "1.0.0.0", "Switch": "", "Desc": "Audio Analyzer SAu3751"},
            {"Mount": "", "Name": "RST", "Sub": "", "ControlDLL": "RST.dll", "Settings": "C:\\TrustSystem13.0\\TrustSystem13.0.exe,TS 144011,Engineer,Engineer", "Functions": "RST", "Version": "1.0.0.2", "Switch": "", "Desc": "Acoustic TrustSystem RST"},
            {"Mount": "", "Name": "FC6000", "Sub": "", "ControlDLL": "FCPM6000.dll", "Settings": "FCPM-6000RC,1,500", "Functions": "AirTest,PwrRG,FcRG,rFreq,rPwr,rVol,rFrPw,List,gIP,Rst,CHECK", "Version": "1.0.1.10", "Switch": "", "Desc": "Fukuda Air Leak Tester FC6000"},
            {"Mount": "", "Name": "FM480", "Sub": "", "ControlDLL": "FM480.dll", "Settings": "", "Functions": "AirTest,FSCAN", "Version": "1.0.1.0", "Switch": "", "Desc": "Flow Meter FM480"},
            {"Mount": "", "Name": "DIO6509", "Sub": "", "ControlDLL": "DigitIO6509.dll", "Settings": "", "Functions": "DIO,IOswitch", "Version": "1.0.0.0", "Switch": "", "Desc": "NI PCI-6509 Digital I/O"},
            {"Mount": "", "Name": "Redrat", "Sub": "", "ControlDLL": "RedratOut.dll", "Settings": "", "Functions": "IR,RRout", "Version": "1.0.0.0", "Switch": "", "Desc": "RedRat IR Blaster"},
            {"Mount": "", "Name": "SFE100", "Sub": "", "ControlDLL": "SFE100.dll", "Settings": "", "Functions": "SFE,SETDVBC,PREDEV,RESDEV,DEFDEV", "Version": "1.0.0.0", "Switch": "", "Desc": "SFE100 Test Device"},
            {"Mount": "", "Name": "ScpTDS3014B", "Sub": "", "ControlDLL": "ScpTDS3014B.dll", "Settings": "", "Functions": "Scope,RMS,VOLAGE,FREQ,MEAN,AMPL,PK2PK", "Version": "1.0.3.2", "Switch": "", "Desc": "Tektronix TDS3014B Oscilloscope"},
            {"Mount": "", "Name": "DevUart", "Sub": "1", "ControlDLL": "DevUart.dll", "Settings": "*$(FIXUART_1),19200,8,One,None,None,10000,5000", "Functions": "AddAttributes,Send,Receive", "Version": "1.0.1.1", "Switch": "", "Desc": "SubDevice UART Controller (SubDevice)"},
            {"Mount": "", "Name": "AutoTFTP", "Sub": "", "ControlDLL": "AutoTFTP.dll", "Settings": "", "Functions": "TFTP", "Version": "1.0.0.0", "Switch": "", "Desc": "Auto TFTP Server"},
            {"Mount": "", "Name": "DevQueue", "Sub": "", "ControlDLL": "DevQueue.dll", "Settings": "", "Functions": "Queue", "Version": "1.0.1.0", "Switch": "", "Desc": "Device Queue Sync"},
            {"Mount": "", "Name": "LVdev", "Sub": "", "ControlDLL": "tf_LVDevice.dll", "Settings": "", "Functions": "LV", "Version": "1.0.0.0", "Switch": "", "Desc": "LabVIEW Test Device"},
            {"Mount": "", "Name": "ScpiController", "Sub": "1", "ControlDLL": "SCPI_Controller.dll", "Settings": "GPIB,*$(GPIB_SCPI),6811B", "Functions": "OnOff", "Version": "1.0.0.0", "Switch": "", "Desc": "GPIB SCPI Controller"},
            {"Mount": "", "Name": "Keithley2380", "Sub": "", "ControlDLL": "Keithley2380.dll", "Settings": "GPIB,*$(GPIB_2380),2380", "Functions": "E-Load", "Version": "1.0.0.0", "Switch": "", "Desc": "Keithley 2380 Electronic Load"},
            {"Mount": "", "Name": "Keithley2700", "Sub": "1", "ControlDLL": "MDA2700.dll", "Settings": "GPIB,*$(GPIB_2700),1", "Functions": "Voltage,Current,Relay", "Version": "1.0.0.1", "Switch": "", "Desc": "Keithley 2700 Data Acquisition"},
            {"Mount": "", "Name": "Transmitter1", "Sub": "1", "ControlDLL": "VirtualTransmitter.dll", "Settings": "Transmitter1,192.168.1.11,2323", "Functions": "TCP_Transfer", "Version": "1.0.0.2", "Switch": "", "Desc": "Virtual Transmitter TCP"}
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
                "FIXUART_1": "COM43",
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
                "DAQ_2": "Dev2",
                "DAQ_3": "Dev3",
                "DAQ_4": "Dev4",
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
            "TestItemCodeFile": "Test Item Code V2.04_20260521.xlsx"
        }
    })


def get_configured_centimani_dir():
    """
    Returns the Centimani main program directory (containing Device/ and LoadScript.dll).
    Reads `centimani_dir` from config.json; if unset/missing, auto-scans PROJECT_ROOT
    and saves the discovered path into config.json so the user isn't prompted repeatedly.
    """
    import json
    if getattr(sys, "frozen", False):
        _exe_d = os.path.dirname(os.path.abspath(sys.executable))
        base_dir = _exe_d
        proj_root = _exe_d
        for _cand_root in (_exe_d, os.path.dirname(_exe_d), os.path.dirname(os.path.dirname(_exe_d))):
            if any(os.path.isdir(os.path.join(_cand_root, sub)) for sub in ("Centmimani_Altas_TRY", "CENTERMAINA_TRY", "SCRIPTS")):
                proj_root = _cand_root
                break
    else:
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

    # Auto-detect inside PROJECT_ROOT (prefer newer Centmimani_Altas_TRY first)
    candidates = [
        os.path.join(proj_root, "Centmimani_Altas_TRY"),
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
        if cm_dir and os.path.isdir(cm_dir):
            for sub in ("Device", "Switch"):
                sub_p = os.path.join(cm_dir, sub)
                if os.path.isdir(sub_p):
                    search_dirs.append(sub_p)
        else:
            for root_sub in ("Centmimani_Altas_TRY", "CENTERMAINA_TRY", "Centimani_1.5.3_sample"):
                for sub in ("Device", "Switch"):
                    sub_p = os.path.join(proj_root, root_sub, sub)
                    if os.path.isdir(sub_p) and sub_p not in search_dirs:
                        search_dirs.append(sub_p)
        for base_d in search_dirs:
            for dll_p in glob.glob(os.path.join(base_d, "*.dll")):
                d_name = os.path.basename(dll_p).lower()
                if d_name in versions:
                    continue
                try:
                    info = win32api.GetFileVersionInfo(dll_p, "\\")
                    ver = f"{win32api.HIWORD(info['FileVersionMS'])}.{win32api.LOWORD(info['FileVersionMS'])}.{win32api.HIWORD(info['FileVersionLS'])}.{win32api.LOWORD(info['FileVersionLS'])}"
                    versions[d_name] = ver
                except Exception:
                    versions[d_name] = "1.0.0.0"
    except Exception:
        pass
    _get_local_dll_versions._cache = versions
    return versions


def _read_pe_version(file_path):
    """Reads FileVersion string of a Windows EXE/DLL, or '' if missing/unreadable."""
    if not file_path or not os.path.isfile(file_path):
        return ""
    try:
        import win32api
        info = win32api.GetFileVersionInfo(file_path, "\\")
        return f"{win32api.HIWORD(info['FileVersionMS'])}.{win32api.LOWORD(info['FileVersionMS'])}.{win32api.HIWORD(info['FileVersionLS'])}.{win32api.LOWORD(info['FileVersionLS'])}"
    except Exception:
        return "未知版本"


def scan_centimani_environment(target_dir=None, persist=True, confirmed=None):
    """
    掃描指定（或目前已設定）的 Centimani 主程式目錄，記錄主程式版本、UtilityLibrary/LoadScript 版本、
    本機實際存在的 Device/Switch DLL 數量與清單，以及輔助工具 (CentimaniSFISTest.exe / DLLtest.exe) 是否存在。
    """
    import json
    import datetime
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(base_dir, "config.json")
    cfg = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f) or {}
        except Exception:
            cfg = {}

    cm_dir = str(target_dir or "").strip() or get_configured_centimani_dir()
    cm_exists = bool(cm_dir and os.path.isdir(cm_dir))
    if target_dir and cm_exists:
        cfg["centimani_dir"] = cm_dir
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    dll_vers = _get_local_dll_versions(force_refresh=True) if cm_exists else {}
    exe_ver = _read_pe_version(os.path.join(cm_dir, "CentimaniSystem.exe")) if cm_exists else ""
    editor_ver = _read_pe_version(os.path.join(cm_dir, "EditorScriptTool.exe")) if cm_exists else ""
    util_ver = _read_pe_version(os.path.join(cm_dir, "API", "UtilityLibrary.dll")) if cm_exists else ""
    load_ver = _read_pe_version(os.path.join(cm_dir, "LoadScript.dll")) if cm_exists else ""

    tools = {
        "CentimaniSFISTest.exe": bool(cm_exists and os.path.isfile(os.path.join(cm_dir, "CentimaniSFISTest.exe"))),
        "DLLtest.exe": bool(cm_exists and os.path.isfile(os.path.join(cm_dir, "DLLtest.exe"))),
        "EditorScriptTool.exe": bool(cm_exists and os.path.isfile(os.path.join(cm_dir, "EditorScriptTool.exe"))),
    }

    was_confirmed = bool(cfg.get("centimani_profile_confirmed", False))
    is_confirmed = bool(confirmed) if confirmed is not None else was_confirmed
    ni_daqmx_ok = os.path.isfile(r"C:\Windows\System32\nicaiu.dll") or os.path.isfile(r"C:\Windows\SysWOW64\nicaiu.dll")

    profile = {
        "centimani_dir": cm_dir,
        "dir_name": os.path.basename(os.path.normpath(cm_dir)) if cm_dir else "",
        "exists": cm_exists,
        "exe_version": exe_ver,
        "editor_version": editor_ver,
        "utility_version": util_ver,
        "loadscript_version": load_ver,
        "dll_count": len(dll_vers),
        "dll_names": sorted(dll_vers.keys()),
        "ni_daqmx_installed": ni_daqmx_ok,
        "tools": tools,
        "confirmed": is_confirmed,
        "scanned_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    if persist and cm_exists:
        cfg["centimani_dir"] = cm_dir
        cfg["centimani_profile"] = profile
        if confirmed is not None:
            cfg["centimani_profile_confirmed"] = bool(confirmed)
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return profile


TEMPLATED_INSTS = {
    "NI6008", "NI6008-1", "FeasaLED", "IPOWER2401", "IPRO800",
    "Agilent34401A", "MDA2700", "PS2005", "PS2005-1",
    "InstIQApiA", "XelM8-A", "IQFlex-A", "XelM8-B", "MT8870A", "DIO6509",
    "ScpiController", "Keithley2700", "Transmitter1",
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
            # Only instruments whose DLL physically exists in local Centimani Device/Switch count as real usable!
            item["is_usable"] = bool(item["dll_exists"])
    return mother_dict


def _resolve_shared_control_dll(name: str, cur_dll: str, catalog_rows: list, dll_vers: dict) -> str:
    """Resolve numbered multi-unit sibling (e.g. NI6008-2 / FeasaLED-2) to shared base catalog DLL."""
    d_fn = str(cur_dll or "").strip()
    clean_name = str(name or "").strip()
    if not clean_name:
        return d_fn
    is_synthetic = d_fn and d_fn.lower() == f"{clean_name.lower()}.dll" and (not dll_vers or d_fn.lower() not in dll_vers)
    if d_fn and not is_synthetic:
        return d_fn
    stem = re.sub(r"-\d+$", "", clean_name).strip().lower()
    candidates = {clean_name.lower(), stem, f"{stem}-1"}
    for cat in (catalog_rows or ()):
        cat_name = str(cat.get("Name", "")).strip().lower()
        cat_dll = str(cat.get("ControlDLL", "")).strip()
        if cat_name in candidates and cat_dll:
            return cat_dll
    return d_fn


def check_workspace_missing_dlls(ws: dict) -> dict:
    """檢查 workspace 中實際啟用（非 Phase=-1 / 非 ExecMode=6 略過）且有掛載或步驟使用之 Instrument / Switch 對應 ControlDLL 是否存在，同款多機自動合併為單一共享 DLL。"""
    cm_dir = get_configured_centimani_dir()
    cm_dir_exists = bool(cm_dir and os.path.isdir(cm_dir))
    dll_vers = _get_local_dll_versions(force_refresh=True) if cm_dir_exists else {}

    mother = get_golden_mother()
    cat_by_sec = {
        "instruments": mother.get("instruments") or [],
        "switches": mother.get("switches") or [],
    }

    used_inst_tokens = set()
    used_sw_tokens = set()
    for rows in (ws.get("stations") or {}).values():
        if not isinstance(rows, list):
            continue
        cur_phase = ""
        for r in rows:
            p_raw = str(r.get("Phase", "")).strip()
            if p_raw:
                cur_phase = p_raw
            if cur_phase == "-1":
                continue
            em = str(r.get("ExecMode", "")).strip()
            if em == "6":
                continue
            it = str(r.get("Instrument", "")).strip().lower()
            if it:
                used_inst_tokens.add(it)
                used_inst_tokens.add(it.split(",")[0].strip())
            sw = str(r.get("Switch", "")).strip().lower()
            if sw:
                used_sw_tokens.add(sw)
                used_sw_tokens.add(sw.split(",")[0].strip())

    missing_by_dll = {}
    dll_order = []
    for sec in ("instruments", "switches"):
        for inst_r in ws.get(sec, []):
            name = str(inst_r.get("Name", "")).strip()
            mount = str(inst_r.get("Mount", "")).strip()
            d_fn = _resolve_shared_control_dll(name, inst_r.get("ControlDLL", ""), cat_by_sec.get(sec), dll_vers)
            if not d_fn:
                continue
            if sec == "instruments":
                funcs = {f.strip().lower() for f in str(inst_r.get("Functions", "")).split(",") if f.strip()}
                is_active = bool(mount) or (name.lower() in used_inst_tokens) or bool(funcs & used_inst_tokens)
            else:
                is_active = bool(mount) or (name.lower() in used_sw_tokens)
            if not is_active:
                continue
            if not cm_dir_exists or d_fn.lower() not in dll_vers:
                dll_key = d_fn.lower()
                if dll_key not in missing_by_dll:
                    missing_by_dll[dll_key] = {"dll": d_fn, "insts": []}
                    dll_order.append(dll_key)
                if name and name not in missing_by_dll[dll_key]["insts"]:
                    missing_by_dll[dll_key]["insts"].append(name)

    missing_dlls = []
    uses_ni_daqmx = False
    for dll_key in dll_order:
        grp = missing_by_dll[dll_key]
        inst_list = grp["insts"]
        if len(inst_list) > 1:
            inst_label = f"{'、'.join(inst_list)} 共用"
        elif len(inst_list) == 1:
            inst_label = inst_list[0]
        else:
            inst_label = "未命名儀器"
        missing_dlls.append({
            "inst": inst_label,
            "dll": grp["dll"],
            "shared": len(inst_list) > 1,
            "insts": inst_list,
        })

    for sec in ("instruments", "switches"):
        for inst_r in ws.get(sec, []):
            mount = str(inst_r.get("Mount", "")).strip()
            d_fn = _resolve_shared_control_dll(inst_r.get("Name", ""), inst_r.get("ControlDLL", ""), cat_by_sec.get(sec), dll_vers)
            if d_fn.lower() == "daqusbni.dll" and (mount or str(inst_r.get("Name", "")).strip().lower() in used_inst_tokens):
                uses_ni_daqmx = True

    ni_daqmx_ok = os.path.isfile(r"C:\Windows\System32\nicaiu.dll") or os.path.isfile(r"C:\Windows\SysWOW64\nicaiu.dll")
    missing_drivers = []
    if uses_ni_daqmx and not ni_daqmx_ok:
        missing_drivers.append(
            "本機未安裝系統 NI-DAQmx 驅動 (缺 nicaiu.dll)：雖有 DaqUSBNi.dll 與 NationalInstruments.DAQmx.dll，"
            "直接啟動 CentimaniSystem.exe 仍會拋出 FileNotFoundException；無此驅動電腦請勾選「無儀器環境 Phase=-1」跳過 NI6008。"
        )

    return {
        "centimani_dir": cm_dir,
        "centimani_dir_exists": cm_dir_exists,
        "missing_dlls": missing_dlls,
        "ni_daqmx_installed": ni_daqmx_ok,
        "missing_drivers": missing_drivers,
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
        "block_id": "BLK_SUBDEV_DEVUART_FINALGO",
        "category": "01. 前置與治具控制 (Phase 0)",
        "name": "Sub=1 共用子裝置 (DevUart) 與一拖四 FinalGo 同步柵欄",
        "description": "01. FWDL 實戰寫法：多槽共用單一治具 COM Port (Sub=1 DevUart)，Col E/F 留空，以 :InitFinalGo / :CheckFinalGo 同步四槽並夾住 :ObtainSubDevice -> :sDev.* -> :ReleaseSubDevice。",
        "default_phase": "1",
        "required_globals": {"Settings": {"FIXUART_1": "COM43"}, "Scripts": {}},
        "steps": [
            {"Phase": "1", "Title": "0,Fixture Sync & SubDevice,1", "Marco": "", "Instrument": "", "Switch": "", "Send": ':ObtainSubDevice,"DevUart"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Fixture#-#Obtain Shared SubDevice DevUart", "TestID": "BRME027"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":InitFinalGo", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "PC#-#Init Multi-DUT FinalGo Barrier", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':sDev.Send,"55 AA 01 00 00 00 00 00 00 00 0D 0A,,@55 AA,,5000,true"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "Fixture#-#Trigger Shared Fixture Relay", "TestID": "OTFX157"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':sDev.Announce,"SAT{1},start"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Fixture#-#Announce Slot Ready to Barrier", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":CheckFinalGo", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "PC#-#Wait All Slots Reach FinalGo Barrier", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":ReleaseSubDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "Fixture#-#Release SubDevice DevUart", "TestID": "BRME027"}
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
            {"Phase": "1", "Title": "0,Measure Voltage Test,3", "Marco": "", "Instrument": "Voltage", "Switch": "NI6008", "Send": ":ObtainDevice", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "INST#-#Obtain NI6008 Lock", "TestID": "B7PL025"},
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
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": "UART@cat /etc/version\\r\\n", "Reply": "@", "EndPrompt": "#", "Ref": '$DUT_FW:WithinString,"version=","\\r\\n",""', "Validation": "(DUT_FW,%s,*$(FW_VERSION),*$(FW_VERSION))", "Prompt": "", "Waiting": "5000", "ExecMode": "1", "Description": "DUT#-#Verify Firmware Version", "TestID": "VSCH026"}
        ]
    },
    {
        "block_id": "BLK_SFIS_ENABLED_BRANCH",
        "category": "04. SFIS 資料讀取與寫入 (SFIS & MAC/SN)",
        "name": "SFIS 線上／離線雙模自動旁路分支 (:SfEnabled + 4:P,F)",
        "description": "01. FWDL Phase 3/4 實戰骨架：以 :SfEnabled 判斷 System.ini SFIS_Enable；產線 (=1) 執行線上取號，離線除錯 (=0) 依 ExecMode=4:2,4 自動保留離線預設值並匯流向下執行。",
        "default_phase": "5",
        "required_globals": {"Settings": {}, "Scripts": {"DebugMAC_Def": "001122334455"}},
        "steps": [
            {"Phase": "5", "Title": "0,SFIS Dual-Mode Branch,1", "Marco": "", "Instrument": "", "Switch": "", "Send": ':SetVal,"gMAC","*$(DebugMAC_Def)"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "PC#-#Preset Offline Fallback MAC", "TestID": "OTFX054"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":SfEnabled", "Reply": "1", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "4:2,4", "Description": "SFIS#-#Check SFIS_Enable (Online=2, Offline=4)", "TestID": "OTCH013"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':SfGetVersion,"*(ISN)","ISN_BASEINFO","2","MAC1",""', "Reply": "", "EndPrompt": "", "Ref": "$gMAC", "Validation": "(gMAC,%len,12,12)", "Prompt": "", "Waiting": "", "ExecMode": "9", "Description": "SFIS#-#Get Online MAC1", "TestID": "OTFX133"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':SfGetiMAC,"*(ISN)","1","1","2"', "Reply": "", "EndPrompt": "", "Ref": '$sfMAC:SubString,"0","12";', "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "8", "Description": "SFIS#-#Get Online iMAC", "TestID": "OTFX085"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Delay,"200"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "PC#-#SFIS Online/Offline Branch Convergence", "TestID": "B7PL025"}
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
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": 'CmdConsole@cd *$(PythonPath)&&cmd /c python.exe my_test.py "*(ISN)"\\r\\n', "Reply": "@Command pass", "EndPrompt": ">", "Ref": '$PyVal:WithinString,"RESULT=","\\n",""', "Validation": "(PyVal,%f,0.0,100.0)", "Prompt": "", "Waiting": "10000", "ExecMode": "1", "Description": "PC#-#Execute Python Script & Validate Output", "TestID": "OTFX054"},
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
        "block_id": "BLK_USB_FW_UPGRADE_COM",
        "category": "03. UART 通訊與韌體升級 (Console & FW)",
        "name": "USB 韌體升級＋自動偵測 COM Port (Utility.CMD + GetChainCOM)",
        "description": "ATLAS_SAMPLE 實戰寫法：執行 USB_upgrade.exe 燒錄韌體後，使用 :Utility.GetChainCOM 自動偵測 COM Port 並以 :AddAttribute 動態綁定 UART。",
        "default_phase": "10",
        "required_globals": {"Settings": {"PortCh1": "[1-1]"}, "Scripts": {}},
        "steps": [
            {"Phase": "10", "Title": "0,USB_FW_Upgrade_Boot,5", "Marco": "", "Instrument": "", "Switch": "", "Send": ':ShowConfirmBox,"請按住裝置按鍵並插入 USB 進入下載模式","OK"', "Reply": "OK", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "Wait#-#Prompt Operator USB Upgrade", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Utility.CMD,"USB_upgrade.exe","","on"', "Reply": "@PASS", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "90000", "ExecMode": "2:0", "Description": "DUT#-#Run USB_upgrade Firmware Flash", "TestID": "IPIO01D"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Delay,"5000"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Wait Reboot", "TestID": "OTFX074"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Utility.GetChainCOM,"*$(PortCh1)","0"', "Reply": "0", "EndPrompt": "", "Ref": "$comPort", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "2:0", "Description": "PC#-#Auto Detect DUT COM Port", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':AddAttribute,"UART","COM","*(comPort)"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "PC#-#Bind Detected COM to UART", "TestID": "OTFX15D"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"UART"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "0", "Description": "PC#-#Open Dynamic UART Port", "TestID": "OTFX074"}
        ]
    },
    {
        "block_id": "BLK_FW_STREAM_PROMPT_FLASH",
        "category": "03. UART 通訊與韌體升級 (Console & FW)",
        "name": "長輸出串流分段燒錄範本 (Prompt=\"!\" ＋ 階段重試)",
        "description": "01. FWDL STM32/MT7682/Vi37 燒錄實戰寫法：Prompt 欄填 '!' 持續監聽同一支 Console 串流（Erase -> Download -> Verify），分段設定 Waiting 與 ExecMode=2:0 退回重試。",
        "default_phase": "11",
        "required_globals": {"Settings": {"FlashTool": "STM32_Programmer_CLI.exe"}, "Scripts": {}},
        "steps": [
            {"Phase": "11", "Title": "0,Streaming FW Flash,3", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Connect,"UART"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "1", "Description": "PC#-#Connect Flash Console", "TestID": "OTFX082"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": "UART@erase_and_flash\\r\\n", "Reply": "@ERASE_START", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "!", "Waiting": "10000", "ExecMode": "2:0", "Description": "DUT#-#Stage 1 Erase Start", "TestID": "OTFX079"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": "UART@\\r", "Reply": "@Mass erase successfully achieved", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "!", "Waiting": "20000", "ExecMode": "2:0", "Description": "DUT#-#Stage 2 Mass Erase Complete", "TestID": "OTFX079"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": "UART@\\r", "Reply": "@File download complete", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "!", "Waiting": "30000", "ExecMode": "2:0", "Description": "DUT#-#Stage 3 Firmware Download Complete", "TestID": "IPIO01D"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": "UART@\\r", "Reply": "@Start operation achieved successfully", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "!", "Waiting": "30000", "ExecMode": "1", "Description": "DUT#-#Stage 4 Verify & Start OK", "TestID": "VSCH026"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ':Disconnect,"UART"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Close Flash Console", "TestID": "B7PL025"}
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
    },
    {
        "block_id": "BLK_PHASE98_99_BRANCH_TEARDOWN",
        "category": "97. 強制安全收尾 (Phase 97 End Test)",
        "name": "Phase 98 (PASS 後) 與 Phase 99 (FAIL 後) 分流收尾",
        "description": "01. FWDL / 09. ACOUSTIC 實戰架構：Phase 98 僅在整站 PASS 後執行（成功提示／狀態寫回）；Phase 99 僅在 FAIL 後執行（故障提示與安全復位）。",
        "default_phase": "98",
        "required_globals": {"Settings": {}, "Scripts": {}},
        "steps": [
            {"Phase": "98", "Title": "0,End Test PASS Branch,1", "Marco": "", "Instrument": "", "Switch": "", "Send": ':ShowMessage,"TEST PASS - Ready for Unload"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#PASS Only Post-Action", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":CloseMessage", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Close PASS Prompt", "TestID": "B7PL025"},
            {"Phase": "99", "Title": "0,End Test FAIL Branch,1", "Marco": "", "Instrument": "", "Switch": "", "Send": ':ShowMessage,"TEST FAIL - Check Fixture & Log"', "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#FAIL Only Alarm & Log", "TestID": "B7PL025"},
            {"Phase": "", "Title": "", "Marco": "", "Instrument": "", "Switch": "", "Send": ":CloseMessage", "Reply": "0", "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "", "Waiting": "", "ExecMode": "3", "Description": "PC#-#Close FAIL Prompt", "TestID": "B7PL025"}
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
        _meipass = getattr(sys, "_MEIPASS", None)
        _exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else None
        candidates = [
            os.path.join(_BASE_DIR, "data", "Test Item Code V2.04_20260521.xlsx"),
            os.path.join(_meipass, "data", "Test Item Code V2.04_20260521.xlsx") if _meipass else "",
            os.path.join(_exe_dir, "data", "Test Item Code V2.04_20260521.xlsx") if _exe_dir else "",
            os.path.join(_PROJECT_ROOT, "SCRIPTS", "ATLAS_SAMPLE", "Test Item Code V2.04_20260521.xlsx"),
            os.path.join(_PROJECT_ROOT, "Centimani_1.5.3_sample", "System", "Test Item Code V2.04_20250310.xlsx"),
            os.path.join(_PROJECT_ROOT, "SCRIPTS", "Test Item Code V2.04_20250310.xlsx"),
            os.path.join(_PROJECT_ROOT, "SCRIPTS", "KANGAROO", "Test Item Code V2.04_20250310.xlsx"),
            r"D:\PYTHON\自動化編寫EXCEL\SCRIPTS\ATLAS_SAMPLE\Test Item Code V2.04_20260521.xlsx",
            r"D:\PYTHON\自動化編寫EXCEL\Centimani_1.5.3_sample\System\Test Item Code V2.04_20250310.xlsx",
            r"D:\PYTHON\自動化編寫EXCEL\SCRIPTS\AI_SOURCE\KANGAROO\FW\Test Item Code V2.04_20250310.xlsx",
        ]
        tic_path = next((p for p in candidates if p and os.path.exists(p)), None)
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


def _and_term_hits(tl, tid_l, ec_l, en_l, cn_l, mf_l, if_l):
    """Smart strict matcher for a single AND keyword against a Test Item Code row."""
    import re
    if not tl:
        return (True, 0)
    if tl == tid_l or tl == ec_l:
        return (True, 120)
    if tid_l.startswith(tl) or ec_l.startswith(tl):
        return (True, 60)

    has_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in tl)
    if has_cjk:
        if tl in cn_l:
            return (True, 30)
        if tl in en_l or tl in mf_l or tl in if_l:
            return (True, 18)
        return (False, 0)

    # Pure numeric (e.g. 2402, 2412, 5180): forbid partial prefix overlap inside another channel number
    if tl.isdigit():
        pat = rf"(?<![0-9]){re.escape(tl)}(?![0-9])"
        if re.search(pat, en_l) or re.search(pat, cn_l):
            return (True, 32)
        return (False, 0)

    # Short ASCII tokens (<= 3 chars like tx, rx, le, bt, ac, dc, 5v): avoid false substring hits (e.g. 'le' in 'cable')
    if len(tl) <= 3:
        # Split identifiers like 'TX1_2402_BLE_PER' into alphanumeric word parts AND alpha/num sub-parts
        en_parts = set(re.findall(r"[a-z0-9]+|[a-z]+|[0-9]+", en_l))
        cn_parts = set(re.findall(r"[a-z0-9]+|[a-z]+|[0-9]+", cn_l))
        hit_en = (
            tl in en_parts
            or bool(re.search(rf"(?<![a-z0-9]){re.escape(tl)}(?![a-z0-9])", en_l))
            or (tl == "le" and ("ble" in en_parts or "1le" in en_parts))
            or (tl == "tx" and any(p.startswith("tx") and p[2:].isdigit() for p in en_parts))
            or (tl == "rx" and any(p.startswith("rx") and p[2:].isdigit() for p in en_parts))
        )
        hit_cn = (
            tl in cn_parts
            or bool(re.search(rf"(?<![a-z0-9]){re.escape(tl)}(?![a-z0-9])", cn_l))
            or (tl == "le" and ("ble" in cn_parts or "1le" in cn_parts))
        )
        if hit_en:
            return (True, 26)
        if hit_cn:
            return (True, 24)
        if tl in re.findall(r"[a-z0-9]+", mf_l) or tl in re.findall(r"[a-z0-9]+", if_l):
            return (True, 10)
        return (False, 0)

    pts = 0
    if tl in en_l:
        pts += 24
    if tl in cn_l:
        pts += 24
    if pts == 0 and (tl in mf_l or tl in if_l):
        pts += 8
    return (pts > 0, pts)


def search_test_ids(query="", limit=30, generic_only=False, and_terms=None):
    """
    Searches the official Test Item Code catalog by free-text keywords (EN/CN/TestID/ErrorCode),
    or strict multi-field AND filtering when `and_terms` has non-empty values.
    """
    import re
    catalog = get_tic_catalog()

    clean_and = [str(t or "").strip().lower() for t in (and_terms or []) if str(t or "").strip()]
    if clean_and:
        # Flatten any spaces inside individual boxes into required AND sub-tokens
        req_tokens = []
        for cell in clean_and:
            for part in re.split(r"[\s,;/#]+", cell):
                p = part.strip()
                if p and p not in req_tokens:
                    req_tokens.append(p)
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

            total_pts = 0
            all_ok = True
            for tok in req_tokens:
                ok, pts = _and_term_hits(tok, tid_l, ec_l, en_l, cn_l, mf_l, if_l)
                if not ok:
                    all_ok = False
                    break
                total_pts += pts
            if not all_ok:
                continue
            if item["is_generic"]:
                total_pts += 28
            total_pts -= min(len(item["desc_en"]), 60) * 0.1
            scored.append((total_pts, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in scored[:limit]]

    q = (query or "").strip()
    if not q:
        return []

    tokens = [t.lower() for t in re.split(r"[\s,;/#\-_]+", q) if t.strip()]
    if not tokens:
        return []

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
            ok, pts = _and_term_hits(tok, tid_l, ec_l, en_l, cn_l, mf_l, if_l)
            if ok:
                score += pts
                matched_tokens += 1

        if matched_tokens == 0:
            continue

        # Bonus for matching all tokens and being a generic production code
        if matched_tokens == len(tokens):
            score += 45
        if item["is_generic"]:
            score += 25
        # Prefer concise generic descriptions
        score -= min(len(item["desc_en"]), 60) * 0.1
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored[:limit]]


_CONTROL_SEND_PREFIXES = (
    ":delay",
    ":obtaindevice",
    ":releasedevice",
    ":obtainsubdevice",
    ":releasesubdevice",
    ":connect",
    ":disconnect",
    ":closemessage",
    ":showmessage",
    ":showimagemessage",
    ":load",
    ":showisn",
    ":end",
    ":return",
    ":if",
    ":else",
    ":endif",
)

_PLACEHOLDER_TEST_IDS = {
    "B7PL025",
    "B7PL011",
    "OTFX054",
    "OTFX074",
    "OTFX082",
    "OTFX001",
    "OTFX002",
    "OTFX000",
}

_ATE_SYNONYM_GROUPS = [
    (("電壓", "volt", "voltage", "vdd", "vcc", "vbus", "vbat", "dcv", "acv", "mvolt"), ["voltage", "volt", "電壓"]),
    (("電流", "curr", "current", "mscurr", "mcurr", "amp", "leakage", "consumption"), ["current", "curr", "電流"]),
    (("電阻", "ohm", "res", "resistance"), ["resistance", "ohm", "電阻"]),
    (("功率", "power", "watt", "pph", "ps2005", "pwr", "outonoff", "ipower"), ["power", "電源"]),
    (("版本", "version", "fw", "firmware", "sw_ver", "hw_ver", "cat /etc/version"), ["version", "fw", "版本"]),
    (("mac", "imac", "bdaddr", "efuse"), ["mac"]),
    (("ping", "ethernet", "lan", "iperf", "throughput", "dhcp", "rj45"), ["ping", "ethernet", "network", "lan"]),
    (("wifi", "wlan", "rssi", "evm", "2g", "5g", "6g", "iqxel", "xelm8", "mt8870", "bpsk", "ofdm", "cck", "11ag", "11ac", "11ax", "2412", "2437", "2462", "5180", "5500", "5745"), ["wifi", "wlan", "rf"]),
    (("tx1", "tx2", "tx3", "tx4"), ["wifi", "tx"]),
    (("rx1", "rx2", "rx3", "rx4"), ["wifi", "rx"]),
    (("bt", "bluetooth", "ble"), ["bluetooth", "bt", "藍牙"]),
    (("led", "feasa", "rgb"), ["led"]),
    (("lux", "亮度", "色溫", "light", "hue", "intensity"), ["led", "light"]),
    (("條碼", "isn", "barcode", "scan", "sn", "showisn"), ["isn", "barcode", "條碼"]),
    (("路由", "route", "sfcheck", "checkroute", "chkroute"), ["route", "sfis"]),
    (("上傳", "sfsave", "linkdata", "wsfis"), ["sfis", "save", "upload"]),
    (("uart", "com", "serial", "baud"), ["uart", "serial"]),
    (("adc", "ni6008", "ni6009", "daq", "analog"), ["voltage", "adc", "analog"]),
    (("sensor", "temp", "溫度", "imu", "accel", "gyro", "als"), ["sensor", "temp"]),
    (("camera", "cam", "sfr", "lens", "focus", "影像", "鏡頭"), ["camera", "cam"]),
    (("audio", "mic", "spk", "speaker", "聲音", "音頻", "ni4461"), ["audio", "mic", "speaker"]),
    (("button", "key", "按鍵", "switch", "reset", "gpio"), ["button", "key", "按鍵"]),
    (("fixture", "治具", "uartf"), ["fixture", "治具"]),
    (("flash", "燒錄", "fwdl", "download", "emmc", "spi", "nvme"), ["download", "flash", "燒錄"]),
    (("usb", "getcom"), ["usb"]),
    (("boot", "reboot", "startup", "開機", "delay", "wait"), ["boot", "delay", "wait"]),
    (("fan", "風扇"), ["fan", "風扇"]),
    (("pwm", "rpm", "轉速"), ["fan", "speed", "風扇"]),
    (("sound", "noise", "聲音", "異音", "噪音"), ["sound", "noise"]),
    (("rtc", "clock", "time", "ntp"), ["rtc", "time"]),
    (("lte", "5g", "wwan", "imei", "sim", "modem"), ["lte", "wwan", "sim"]),
    (("gps", "gnss"), ["gps", "gnss"]),
    (("nfc", "rfid"), ["nfc"]),
    (("34401", "2700", "dmm", "u2004", "multimeter"), ["voltage", "current", "power"]),
]

_STOP_KEYWORDS = {
    "test", "check", "chk", "get", "set", "read", "write", "run", "cmd", "send",
    "step", "item", "wait", "mode", "init", "start", "end", "pass", "fail",
    "dev", "utility", "dut", "phase", "auto", "manual", "all", "one", "the",
}


def _is_control_send(send_str):
    s = (send_str or "").strip().lower()
    if not s:
        return False
    return any(s.startswith(p) for p in _CONTROL_SEND_PREFIXES)


_TRANSPORT_ONLY_TOKENS = {"uart", "serial", "com", "adb", "ssh", "telnet", "cmd", "console"}


def _trigger_matches_text(trigger, low, spaced_low):
    import re
    if any("\u4e00" <= ch <= "\u9fff" for ch in trigger):
        return trigger in low
    if len(trigger) >= 5:
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(trigger)}|{re.escape(trigger)}(?![a-z0-9])", spaced_low))
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(trigger)}(?![a-z0-9])", spaced_low))


def _extract_row_keywords(title, desc, send, return_concrete=False):
    import re
    clean_desc = re.sub(r"^(?:DUT|PC|OP)#-#", "", (desc or "").strip(), flags=re.I)
    clean_desc = re.sub(r"^log[_\s]+", "", clean_desc, flags=re.I).strip()
    clean_title = re.sub(r"^(?:[0-9]+|\*\$\([^)]+\)),", "", (title or "").strip()).strip()
    # Prioritize Script Description (Col O) -> Title -> Send payload, preserving numeric/channel tokens like 2412, TX1, 5V
    primary_raw = f"{clean_desc} {clean_title}".strip()
    primary_low = primary_raw.lower()
    primary_spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", primary_raw).replace("_", " ").lower()

    send_raw = (send or "").strip()
    send_low_full = send_raw.lower()
    is_sfis_func = send_low_full.startswith((":sfget", ":sfsave", ":sfcheckroute", ":wsfis"))
    is_box_or_cmd = send_low_full.startswith((":showconfirmbox", ":showimageconfirmbox", ":lib.cmd", ":lib.substr"))
    send_clean = re.sub(r"^(?:UARTF?|SSH[0-9]*|TELNET[0-9]*|ADB[0-9]*|LAN|COM[0-9]*)@+", "", send_raw, flags=re.I)
    send_low = send_clean.lower()
    send_spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", send_clean).replace("_", " ").lower()

    syn_tokens = []
    concrete_tokens = []
    seen = set()

    # 1) Direct alphanumeric/Chinese tokens from Script Description (Col O) then Title (preserve 2412, TX1, 5V, etc.)
    for w in re.findall(r"[a-zA-Z0-9]{2,}|[\u4e00-\u9fff]{2,}", primary_raw.replace("_", " ").replace("-", " ")):
        wl = w.lower()
        # Normalize plural MACs -> MAC, LEDs -> LED, Buttons -> Button
        if wl in ("macs", "leds", "buttons", "ports", "pins"):
            w = w[:-1]
            wl = w.lower()
        if wl in _STOP_KEYWORDS or wl in _TRANSPORT_ONLY_TOKENS or wl in seen:
            continue
        # Ignore bare tiny integers like 1, 2, 10 unless >= 4 digits (e.g. 2412, 5180, 6008)
        if wl.isdigit() and len(wl) < 4:
            continue
        seen.add(wl)
        syn_tokens.append(w)
        concrete_tokens.append(w)

    # 2) Synonyms from Description + Title
    for triggers, expanded in _ATE_SYNONYM_GROUPS:
        if any(_trigger_matches_text(t, primary_low, primary_spaced) for t in triggers):
            for tok in expanded:
                tl = tok.lower()
                if tl not in seen:
                    seen.add(tl)
                    syn_tokens.append(tok)

    # 3) Synonyms from Send payload (only after Description + Title; skip false triggers from :SfGetVersion / file paths)
    if is_sfis_func:
        for tok in (("route", "sfis") if send_low_full.startswith(":sfcheckroute") else ("sfis",)):
            if tok not in seen:
                seen.add(tok)
                syn_tokens.append(tok)
    elif send_clean and not is_box_or_cmd:
        for triggers, expanded in _ATE_SYNONYM_GROUPS:
            if any(_trigger_matches_text(t, send_low, send_spaced) for t in triggers):
                for tok in expanded:
                    tl = tok.lower()
                    if tl not in seen and tl not in _TRANSPORT_ONLY_TOKENS:
                        seen.add(tl)
                        syn_tokens.append(tok)

    if return_concrete:
        return syn_tokens, concrete_tokens
    return syn_tokens


def _classify_step_category(title, desc, send, inst="", sw=""):
    blob = f"{title} {desc} {send} {inst} {sw}".lower()
    if any(k in blob for k in ("sfcheckroute", "sfget", "sfsave", "showisn", "sfis", "barcode", "isn", "route")):
        return "sfis"
    if any(k in blob for k in ("ni6008", "ni6009", "mvolt", "mscurr", "pph1503", "ps2005", "34401", "2700", "voltage", "current", "power", "volt", "curr", "電壓", "電流")):
        return "power_volt"
    if any(k in blob for k in ("wifi", "wlan", "tx1", "tx2", "rx1", "rx2", "2412", "5180", "bpsk", "ofdm", "11ag", "11ac", "11ax", "evm", "iqxel", "xelm8", "mt8870", "bluetooth", "ble", "bt_")) or re_has_rf(blob):
        return "rf_wireless"
    if (inst or "").strip() or (sw or "").strip() or ":dev." in blob or ":sdev." in blob or "feasa" in blob or "fan" in blob:
        return "instrument"
    return "general_cmd"


def re_has_rf(blob):
    import re
    return bool(re.search(r"(?<![a-z0-9])(rf|bt|2g|5g|6g)(?![a-z0-9])", blob))


_EXCLUSIVE_DOMAIN_WORDS = (
    "moca", "hdmi", "edid", "cable modem", "audio", "camera",
    "sata", "pcie", "nfc", "fingerprint", "touch", "battery", "gps", "zigbee",
    "scart", "1394", "modem line", "hdd", "keyboard", "touchpanel",
)


def _token_in_text(tok_l, text_l):
    import re
    if not tok_l or not text_l:
        return False
    if any("\u4e00" <= ch <= "\u9fff" for ch in tok_l):
        return tok_l in text_l
    if len(tok_l) <= 3:
        parts = set(re.findall(r"[a-z0-9]+|[a-z]+|[0-9]+", text_l))
        if tok_l in parts or bool(re.search(rf"(?<![a-z0-9]){re.escape(tok_l)}(?![a-z0-9])", text_l)):
            return True
        if tok_l in ("le", "1le") and ("ble" in parts or "1le" in parts or "le" in parts):
            return True
        return False
    return tok_l in text_l


def _score_candidate_confidence(kw_tokens, title, desc, send, cand, is_ctrl=False):
    """Compute a 0..100 similarity score between a script step and a Test Item Code entry."""
    import re
    from difflib import SequenceMatcher
    en_l = str(cand.get("desc_en") or "").lower()
    cn_l = str(cand.get("desc_cn") or "").lower()
    mf_l = str(cand.get("main_func") or "").lower()
    if_l = str(cand.get("interface") or "").lower()

    clean_desc = re.sub(r"^(?:DUT|PC|OP)#-#", "", (desc or "").strip(), flags=re.I)
    clean_desc = re.sub(r"^log[_\s]+", "", clean_desc, flags=re.I).strip()
    clean_title = re.sub(r"^(?:[0-9]+|\*\$\([^)]+\)),", "", (title or "").strip()).strip()
    row_text = f"{clean_title} {clean_desc}".strip().lower()
    send_payload = re.sub(r"^(?:UARTF?|SSH[0-9]*|TELNET[0-9]*|ADB[0-9]*|LAN[0-9]*|COM[0-9]*)@+", "", (send or "").strip(), flags=re.I)
    if not row_text:
        row_text = send_payload.strip().lower()
    full_row_blob = f"{row_text} {send_payload}".lower()
    full_cand_blob = f"{en_l} {mf_l} {if_l}"

    # Penalize if candidate targets an exclusive subsystem or specific port/product/position NOT mentioned in the script step
    domain_penalty = 0.0
    for dom in _EXCLUSIVE_DOMAIN_WORDS:
        if dom in full_cand_blob and dom not in full_row_blob:
            domain_penalty += 38.0

    # Specific port / position / product-line qualifiers (e.g. Eth_Left_LED_OFF, Power LED, 5G LED, Tuner, Notebook NB)
    _QUALIFIER_WORDS = (
        "eth", "ethernet", "left", "right", "charge led", "power led",
        "ring led", "record led", "7-segment", "bist", "480i", "480p", "720p", "1080i",
        "5g", "4g", "tuner", "tuner1", "qam", "sunken", "mm", "ir", "pid",
    )
    cand_q_words = set(re.findall(r"[a-z0-9]+", en_l))
    row_q_words = set(re.findall(r"[a-z0-9]+", full_row_blob))
    for qw in _QUALIFIER_WORDS:
        hit_cand = (qw in cand_q_words) if (" " not in qw and "-" not in qw) else (qw in en_l)
        hit_row = (qw in row_q_words) if (" " not in qw and "-" not in qw) else (qw in full_row_blob)
        if hit_cand and not hit_row:
            domain_penalty += 38.0
    if mf_l.strip() == "nb" and "nb" not in row_q_words and "notebook" not in full_row_blob:
        domain_penalty += 32.0

    # Bluetooth domain protection (allow BLE / 1LE / 2402 / 2440 / 2480 / BDR / EDR rows to match Bluetooth codes)
    if "bluetooth" in full_cand_blob and not any(k in full_row_blob for k in ("bluetooth", "ble", "1le", "bdr", "edr", "2402", "2440", "2480", "bt_")):
        if not re.search(r"(?<![a-z0-9])(bt|le)(?![a-z0-9])", full_row_blob):
            domain_penalty += 38.0

    # WiFi domain protection (LAN@admin Password must not match WIFI_Password fail)
    if "wifi" in (en_l + " " + mf_l) and not any(k in full_row_blob for k in ("wifi", "wlan", "ssid", "11ag", "11ac", "11ax", "bpsk", "ofdm", "2412", "2437", "2462", "5180", "5500", "5745", "2g", "5g", "6g")):
        domain_penalty += 40.0

    # TX vs RX directional exclusivity (TX step must NOT recommend RX code and vice versa)
    row_parts = set(re.findall(r"[a-z]+|[a-z0-9]+", full_row_blob))
    cand_parts = set(re.findall(r"[a-z]+|[a-z0-9]+", en_l))
    row_tx = ("tx" in row_parts or any(p.startswith("tx") and p[2:].isdigit() for p in row_parts))
    row_rx = ("rx" in row_parts or any(p.startswith("rx") and p[2:].isdigit() for p in row_parts))
    cand_tx = ("tx" in cand_parts or any(p.startswith("tx") and p[2:].isdigit() for p in cand_parts))
    cand_rx = ("rx" in cand_parts or any(p.startswith("rx") and p[2:].isdigit() for p in cand_parts))
    if (row_tx and not row_rx and cand_rx and not cand_tx) or (row_rx and not row_tx and cand_tx and not cand_rx):
        domain_penalty += 60.0

    # 4-digit RF channel frequency exclusivity (2402 step must NOT match 2440 or 2480)
    row_freqs = set(re.findall(r"(?<![0-9])(?:24[0-9]{2}|5[0-9]{3}|6[0-9]{3})(?![0-9])", full_row_blob))
    cand_freqs = set(re.findall(r"(?<![0-9])(?:24[0-9]{2}|5[0-9]{3}|6[0-9]{3})(?![0-9])", en_l + " " + cn_l))
    if row_freqs and cand_freqs and not (row_freqs & cand_freqs):
        domain_penalty += 60.0
    freq_en_bonus = 10.0 if (row_freqs and (row_freqs & set(re.findall(r"(?<![0-9])(?:24[0-9]{2}|5[0-9]{3}|6[0-9]{3})(?![0-9])", en_l)))) else 0.0

    matched = 0
    substantive_hits = 0
    substantive_total = sum(1 for t in (kw_tokens or []) if t.lower() not in _TRANSPORT_ONLY_TOKENS)
    weighted_hits = 0.0
    for idx_t, tok in enumerate(kw_tokens or []):
        tl = tok.lower()
        if not tl:
            continue
        is_sub = tl not in _TRANSPORT_ONLY_TOKENS
        if _token_in_text(tl, en_l) or _token_in_text(tl, cn_l):
            matched += 1
            if is_sub:
                substantive_hits += 1
                weighted_hits += 1.25 if idx_t < 3 else 1.0
            else:
                weighted_hits += 0.35
        elif _token_in_text(tl, mf_l) or _token_in_text(tl, if_l):
            matched += 1
            if is_sub:
                substantive_hits += 1
                weighted_hits += 0.55
            else:
                weighted_hits += 0.2

    tok_denom = max(1.0, min(substantive_total or len(kw_tokens or []), 4))
    tok_ratio = min(1.0, weighted_hits / tok_denom)
    seq_ratio = SequenceMatcher(None, row_text[:80], f"{en_l} {cn_l}".strip()[:80]).ratio() if (row_text and (en_l or cn_l)) else 0.0

    # Natural engineering intent bonus: e.g. 'Get ... MAC' matches OTFX133 ('Get MAC Fail') or 'Get SFIS' matches OTFX085 ('Get SFIS DATA Fail')
    intent_bonus = 0.0
    if domain_penalty <= 0:
        if re.search(r"\bget\b", row_text) and re.search(r"\bmac\b", row_text) and not any(w in row_text for w in ("wifi", "wlan", "eth", "bt")):
            if en_l.startswith("get mac"):
                intent_bonus += 26.0
        if "sfis" in row_text and re.search(r"\bget\b", row_text) and "get sfis data" in en_l:
            intent_bonus += 14.0

    # Penalize generic candidates that introduce many extra unmatched words (e.g. 'Eth_Left_LED_OFF' vs 'Set LEDs All Off')
    raw = tok_ratio * 64.0 + seq_ratio * 24.0 + (8.0 if cand.get("is_generic") else 0.0) + freq_en_bonus + intent_bonus - domain_penalty
    if domain_penalty <= 0:
        if substantive_total > 0 and substantive_hits == 0 and not is_ctrl:
            raw = min(raw, 36.0)
        elif substantive_hits == 1 and seq_ratio < 0.65 and intent_bonus <= 0:
            raw = min(raw, 65.0)
        elif matched == 0 and is_ctrl and str(cand.get("test_id") or "").upper() in _PLACEHOLDER_TEST_IDS:
            raw = max(raw, 65.0)
        elif matched == 0:
            raw = min(raw, 35.0)
    else:
        raw = min(raw, 34.0)

    return max(0, min(99, int(round(raw))))


def _clean_proposed_item_name(title, desc, send):
    import re
    clean_d = re.sub(r"^(?:DUT|PC|OP)#-#", "", (desc or "").strip(), flags=re.I).strip()
    clean_t = re.sub(r"^(?:[0-9]+|\*\$\([^)]+\)),", "", (title or "").strip()).strip()
    if clean_d and clean_t and clean_d.lower() != clean_t.lower():
        return f"{clean_t} - {clean_d}"
    return clean_t or clean_d or (send or "").strip()[:50]


def analyze_workspace_test_ids(workspace, target_station=""):
    """
    Scans a workspace's station sheets to detect missing, generic-placeholder,
    or semantically mismatched TestIDs, and proposes Top 5 catalog candidates with confidence tiers.
    """
    catalog = get_tic_catalog()
    cat_map = {item["test_id"].upper(): item for item in catalog if item.get("test_id")}
    stations = (workspace or {}).get("stations") or {}

    issues = []
    all_rows = []
    station_summary = {}
    total_checked = 0
    ok_count = 0

    for st_name, rows in stations.items():
        if target_station and st_name != target_station:
            continue
        # Detect station-wide dummy/copy-pasted TestIDs (e.g. 'AFFY001' pasted across 10+ unrelated rows)
        from collections import Counter
        st_tid_counts = Counter(
            str(rr.get("TestID") or "").strip().upper()
            for rr in (rows or [])
            if str(rr.get("TestID") or "").strip() and not _is_control_send(rr.get("Send") or "")
        )
        st_stat = {"total": 0, "ok": 0, "control": 0, "suggested": 0, "needs_pick": 0}
        cur_eff_phase = ""
        cur_eff_title = ""
        for row_idx, r in enumerate(rows or []):
            title = str(r.get("Title") or "").strip()
            desc = str(r.get("Description") or "").strip()
            send = str(r.get("Send") or "").strip()
            inst = str(r.get("Instrument") or "").strip()
            sw = str(r.get("Switch") or "").strip()
            tid = str(r.get("TestID") or "").strip().upper()
            phase = str(r.get("Phase") or "").strip()
            index_val = str(r.get("Index") or "").strip()
            if phase:
                cur_eff_phase = phase
            if title:
                cur_eff_title = title
            eff_phase = phase or cur_eff_phase or "-"
            eff_title = title or cur_eff_title or ""

            if not (title or desc or send or tid):
                continue
            if not send and not tid:
                continue

            total_checked += 1
            st_stat["total"] += 1
            is_ctrl = _is_control_send(send)
            import re
            tid_valid_fmt = bool(re.match(r"^[A-Z0-9]{7}$", tid))
            cur_item = cat_map.get(tid) if tid_valid_fmt else None
            cur_err_code = cur_item.get("error_code", "") if cur_item else ""

            if is_ctrl and cur_item is not None:
                ok_count += 1
                st_stat["ok"] += 1
                st_stat["control"] += 1
                all_rows.append({
                    "station": st_name,
                    "row_idx": row_idx,
                    "excel_row": row_idx + 2,
                    "index": index_val,
                    "phase": phase,
                    "effective_phase": eff_phase,
                    "effective_title": eff_title,
                    "item_category": _classify_step_category(eff_title, desc, send, inst, sw),
                    "title": title,
                    "description": desc,
                    "send": send,
                    "current_test_id": tid,
                    "current_error_code": cur_err_code,
                    "current_desc_en": cur_item.get("desc_en", ""),
                    "current_desc_cn": cur_item.get("desc_cn", ""),
                    "cur_match_score": 100,
                    "reason_code": "",
                    "reason_label": "控制 / 提示步驟保留原碼",
                    "row_status": "control_skip",
                    "query_keywords": [],
                    "candidates": [],
                    "best_score": 100,
                    "match_tier": "high",
                    "auto_confirmed": False,
                    "needs_review": False,
                    "suggest_new_item": False,
                    "proposed_new_desc": "",
                })
                continue

            kw_tokens, concrete_tokens = _extract_row_keywords(title, desc, send, return_concrete=True)
            reason_code = ""
            reason_label = ""

            if not tid:
                reason_code = "missing"
                reason_label = "TestID 空白未填"
            elif not tid_valid_fmt:
                reason_code = "missing"
                reason_label = f"TestID '{tid}' 非標準 7 碼格式"
            elif cur_item is None:
                reason_code = "missing"
                reason_label = f"TestID '{tid}' 不在官方代碼表內"
            else:
                cur_blob = f"{cur_item.get('desc_en', '')} {cur_item.get('desc_cn', '')} {cur_item.get('main_func', '')}".lower()
                is_ph = tid in _PLACEHOLDER_TEST_IDS or any(w in cur_item.get("desc_en", "").lower() for w in ("others", "other ", "delay time"))
                if is_ph and not is_ctrl:
                    reason_code = "generic_placeholder"
                    reason_label = f"測試步驟使用了通用佔位碼 {tid}（{cur_item.get('desc_en', '') or cur_item.get('desc_cn', '')}）"
                elif kw_tokens and not is_ctrl:
                    overlap = any(k.lower() in cur_blob for k in kw_tokens)
                    if not overlap:
                        if st_tid_counts.get(tid, 0) >= 5:
                            reason_code = "generic_placeholder"
                            reason_label = f"此站共有 {st_tid_counts[tid]} 列重複套用 {tid}（{cur_item.get('desc_en', '') or cur_item.get('desc_cn', '')}），疑似當成佔位碼使用"
                        else:
                            reason_code = "semantic_mismatch"
                            reason_label = f"現有 {tid}（{cur_item.get('desc_en', '')} / {cur_item.get('desc_cn', '')}）與步驟關鍵字不符"

            if not reason_code:
                ok_count += 1
                st_stat["ok"] += 1
                cur_sc = _score_candidate_confidence(kw_tokens, title, desc, send, cur_item, is_ctrl=is_ctrl) if cur_item else 0
                all_rows.append({
                    "station": st_name,
                    "row_idx": row_idx,
                    "excel_row": row_idx + 2,
                    "index": index_val,
                    "phase": phase,
                    "effective_phase": eff_phase,
                    "effective_title": eff_title,
                    "item_category": _classify_step_category(eff_title, desc, send, inst, sw),
                    "title": title,
                    "description": desc,
                    "send": send,
                    "current_test_id": tid,
                    "current_error_code": cur_err_code,
                    "current_desc_en": cur_item.get("desc_en", "") if cur_item else "",
                    "current_desc_cn": cur_item.get("desc_cn", "") if cur_item else "",
                    "cur_match_score": cur_sc,
                    "reason_code": "",
                    "reason_label": "原碼與描述相符",
                    "row_status": "matched_ok",
                    "query_keywords": kw_tokens[:6],
                    "search_terms": concrete_tokens[:5],
                    "candidates": [],
                    "best_score": cur_sc,
                    "match_tier": "high",
                    "auto_confirmed": False,
                    "needs_review": False,
                    "suggest_new_item": False,
                    "proposed_new_desc": "",
                })
                continue

            # Gather candidate TestIDs across all 5,253 entries: strict AND intersection first, then broader OR fallback
            raw_cands = []
            seen_tids = set()
            and_batches = []
            if len(concrete_tokens) >= 3:
                and_batches.append(concrete_tokens[:3])
            if len(concrete_tokens) >= 2:
                and_batches.append(concrete_tokens[:2])
            for a_terms in and_batches:
                for cand in search_test_ids("", limit=30, and_terms=a_terms):
                    c_tid = cand.get("test_id", "").upper()
                    if not c_tid or c_tid in seen_tids:
                        continue
                    seen_tids.add(c_tid)
                    scored_cand = dict(cand)
                    scored_cand["confidence_score"] = _score_candidate_confidence(
                        kw_tokens, title, desc, send, cand, is_ctrl=is_ctrl
                    )
                    raw_cands.append(scored_cand)

            queries_to_try = []
            if kw_tokens:
                queries_to_try.append(" ".join(kw_tokens[:3]))
                for single_kw in kw_tokens[:4]:
                    queries_to_try.append(single_kw)
            if not queries_to_try and title:
                queries_to_try.append(title)
            if is_ctrl and not tid:
                queries_to_try.append("delay others")

            for q_str in queries_to_try:
                for cand in search_test_ids(q_str, limit=25):
                    c_tid = cand.get("test_id", "").upper()
                    if not c_tid or c_tid in seen_tids:
                        continue
                    seen_tids.add(c_tid)
                    scored_cand = dict(cand)
                    scored_cand["confidence_score"] = _score_candidate_confidence(
                        kw_tokens, title, desc, send, cand, is_ctrl=is_ctrl
                    )
                    raw_cands.append(scored_cand)

            raw_cands.sort(key=lambda x: (x.get("confidence_score", 0), 1 if x.get("is_generic") else 0), reverse=True)
            # Filter out irrelevant <35% candidates (e.g. 0% false hits)
            filtered_cands = [c for c in raw_cands if int(c.get("confidence_score", 0)) >= 35]
            candidates = filtered_cands[:5]

            # Do not flag semantic_mismatch on an already-filled non-placeholder TestID unless a much stronger (>=72%) match exists
            if reason_code == "semantic_mismatch" and (not candidates or int(candidates[0].get("confidence_score", 0)) < 72):
                ok_count += 1
                st_stat["ok"] += 1
                cur_sc = _score_candidate_confidence(kw_tokens, title, desc, send, cur_item, is_ctrl=is_ctrl) if cur_item else 0
                all_rows.append({
                    "station": st_name,
                    "row_idx": row_idx,
                    "excel_row": row_idx + 2,
                    "index": index_val,
                    "phase": phase,
                    "effective_phase": eff_phase,
                    "effective_title": eff_title,
                    "item_category": _classify_step_category(eff_title, desc, send, inst, sw),
                    "title": title,
                    "description": desc,
                    "send": send,
                    "current_test_id": tid,
                    "current_error_code": cur_err_code,
                    "current_desc_en": cur_item.get("desc_en", "") if cur_item else "",
                    "current_desc_cn": cur_item.get("desc_cn", "") if cur_item else "",
                    "cur_match_score": cur_sc,
                    "reason_code": "",
                    "reason_label": "原碼尚可接受（無顯著更優替代碼）",
                    "row_status": "matched_ok",
                    "query_keywords": kw_tokens[:6],
                    "search_terms": concrete_tokens[:5],
                    "candidates": candidates,
                    "best_score": cur_sc,
                    "match_tier": "high",
                    "auto_confirmed": False,
                    "needs_review": False,
                    "suggest_new_item": False,
                    "proposed_new_desc": "",
                })
                continue

            best_score = int(candidates[0].get("confidence_score", 0)) if candidates else 0
            if best_score >= 72:
                match_tier = "high"
            elif best_score >= 42:
                match_tier = "medium"
            else:
                match_tier = "low_gap"

            # Auto-confirmed when high similarity (>=72%), or placeholder with a close-enough alternative (>=55%)
            auto_confirmed = (match_tier == "high") or (reason_code == "generic_placeholder" and best_score >= 55)
            row_status = "auto_suggested" if auto_confirmed else "needs_pick"
            if auto_confirmed:
                st_stat["suggested"] += 1
            else:
                st_stat["needs_pick"] += 1

            issue_item = {
                "station": st_name,
                "row_idx": row_idx,
                "excel_row": row_idx + 2,
                "index": index_val,
                "phase": phase,
                "effective_phase": eff_phase,
                "effective_title": eff_title,
                "item_category": _classify_step_category(eff_title, desc, send, inst, sw),
                "title": title,
                "description": desc,
                "send": send,
                "current_test_id": tid,
                "current_error_code": cur_err_code,
                "current_desc_en": cur_item.get("desc_en", "") if cur_item else "",
                "current_desc_cn": cur_item.get("desc_cn", "") if cur_item else "",
                "cur_match_score": _score_candidate_confidence(kw_tokens, title, desc, send, cur_item, is_ctrl=is_ctrl) if cur_item else 0,
                "reason_code": reason_code,
                "reason_label": reason_label,
                "row_status": row_status,
                "query_keywords": kw_tokens[:6],
                "search_terms": concrete_tokens[:5],
                "candidates": candidates,
                "best_score": best_score,
                "match_tier": match_tier,
                "auto_confirmed": auto_confirmed,
                "needs_review": not auto_confirmed,
                "suggest_new_item": (match_tier == "low_gap"),
                "proposed_new_desc": _clean_proposed_item_name(title, desc, send),
            }
            issues.append(issue_item)
            all_rows.append(issue_item)

        station_summary[st_name] = st_stat

    summary = {
        "total_checked": total_checked,
        "ok_count": ok_count,
        "flagged_count": len(issues),
        "missing_count": sum(1 for x in issues if x["reason_code"] == "missing"),
        "placeholder_count": sum(1 for x in issues if x["reason_code"] == "generic_placeholder"),
        "mismatch_count": sum(1 for x in issues if x["reason_code"] == "semantic_mismatch"),
        "high_match_count": sum(1 for x in issues if x.get("match_tier") == "high"),
        "medium_match_count": sum(1 for x in issues if x.get("match_tier") == "medium"),
        "gap_new_item_count": sum(1 for x in issues if x.get("match_tier") == "low_gap"),
        "auto_confirmed_count": sum(1 for x in issues if x.get("auto_confirmed")),
        "needs_review_count": sum(1 for x in issues if x.get("needs_review")),
    }
    return {
        "issues": issues,
        "all_rows": all_rows,
        "station_summary": station_summary,
        "summary": summary,
        "stations": list(stations.keys()),
    }

