# -*- coding: utf-8 -*-
"""
SFIS WebService (SFISTSPWebService.asmx) SOAP 1.1 Client & Centimani Excel Step Builder.
Based on WebServiceProxy.SFISTSPWebService (http://www.pegatroncorp.com/SFISWebService/).
"""
import html
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as _xml_escape


SFIS_SOAP_NS = "http://www.pegatroncorp.com/SFISWebService/"

SFIS_PLANT_PRESETS = [
    {
        "id": "PTB_PROD",
        "label": "巴淡 PTB 正式機 (10.176.33.13)",
        "url": "http://10.176.33.13/SFISWebService/SFISTSPWebService.asmx",
        "default_device": "710001",
        "default_tsp": "ATLAS,2",
        "editable_hint": "預設廠區：巴淡 PTB 正式機",
    },
    {
        "id": "PTB_QA",
        "label": "巴淡 PTB 測試機 (BTARDB0QA)",
        "url": "http://172.24.255.10/SFISWebService_BTARDB0QA/SFISTSPWebService.asmx",
        "default_device": "710001",
        "default_tsp": "ATLAS,2",
        "editable_hint": "巴淡 PTB 測試機 BTARDB0QA",
    },
    {
        "id": "PTB_F1",
        "label": "巴淡 PTB F1 (可編輯自填 IP)",
        "url": "http://172.24.255.113/SFISWebService/SFISTSPWebService.asmx",
        "default_device": "710001",
        "default_tsp": "ATLAS,2",
        "editable_hint": "巴淡 PTB F1 預留範本（可點編輯自行修改名稱與 IP）",
    },
    {
        "id": "TY3_PROD",
        "label": "桃園三廠 TY3 正式機 (pxd-sftsp-n3)",
        "url": "http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService/SFISTSPWebService.asmx",
        "default_device": "710001",
        "default_tsp": "ATLAS,2",
        "editable_hint": "VALO360 / TY3 桃園三廠正式機 (SCRIPTS/0411_ER2_DONE/System.ini)",
    },
    {
        "id": "TY3_QA",
        "label": "桃園三廠 TY3 測試機 (XDNPDB0QA)",
        "url": "http://pxd-sftsp-n3.sfis.pegatroncorp.com/SFISWebService_XDNPDB0QA/sfistspwebservice.asmx",
        "default_device": "710001",
        "default_tsp": "ATLAS,2",
        "editable_hint": "TY3 桃園三廠測試資料庫 XDNPDB0QA (SCRIPTS/0411_ER2_DONE/System.ini)",
    },
    {
        "id": "SUZHOU_PROD",
        "label": "蘇州正式機 (.248.15)",
        "url": "http://172.24.248.15/SFISWebService/SFISTSPWebService.asmx",
        "default_device": "710001",
        "default_tsp": "ATLAS,2",
        "editable_hint": "蘇州 SFIS 正式伺服器",
    },
    {
        "id": "SUZHOU_QA",
        "label": "蘇州測試機 (SZASCD0QA)",
        "url": "http://172.24.255.10/SFISWebService_SZASCD0QA/SFISTSPWebService.asmx",
        "default_device": "430079",
        "default_tsp": "ATLAS,2",
        "editable_hint": "蘇州 QA 測試機",
    },
]

DEFAULT_VIRTUAL_MO_TEMPLATES = [
    {"date": "9月21日", "model": "PL AURORA1A/V200/TAA", "pn": "90AA221000S0", "qty": 5, "reason": "Aurora SFIS 驗線", "mo": "26951603", "seq_digits": 5, "seq_start": 1, "note": "TECO"},
    {"date": "9月21日", "model": "PL AURORA1B/V250/TAA", "pn": "90AA221000K0", "qty": 5, "reason": "Aurora SFIS 驗線", "mo": "26951604", "seq_digits": 5, "seq_start": 1, "note": "TECO"},
    {"date": "9月21日", "model": "PL AURORA3A/V400/TAA", "pn": "90AA221000B0", "qty": 5, "reason": "Aurora SFIS 驗線", "mo": "26951605", "seq_digits": 5, "seq_start": 1, "note": "TECO"},
    {"date": "9月21日", "model": "PL AURORA3B/V450/TAA", "pn": "90AA221001B0", "qty": 5, "reason": "Aurora SFIS 驗線", "mo": "26951606", "seq_digits": 5, "seq_start": 1, "note": "TECO"},
    {"date": "9月21日", "model": "PL AURORA5A/V800/TAA", "pn": "90AA221000Z0", "qty": 5, "reason": "Aurora SFIS 驗線", "mo": "26951607", "seq_digits": 5, "seq_start": 1, "note": "TECO"},
    {"date": "9月21日", "model": "PL AURORA5B/V850/TAA", "pn": "90AA22100120", "qty": 5, "reason": "Aurora SFIS 驗線", "mo": "26951608", "seq_digits": 5, "seq_start": 1, "note": "TECO"},
]

GETVERSION_TYPES = [
    {"value": "ISN_BASEINFO", "label": "ISN_BASEINFO (MAC1 / SSN / SN1 / SYSDATE)"},
    {"value": "ITEMINFO", "label": "ITEMINFO (SN_UNI / 料件關聯資訊)"},
    {"value": "GETSN_BYRULE", "label": "GETSN_BYRULE (依規則取唯一 ID)"},
    {"value": "ITEM_FEATURE_BASEINFO", "label": "ITEM_FEATURE_BASEINFO (ModelNumber / EPG / 預設檔)"},
    {"value": "ISN_BASE_CUSTITEM", "label": "ISN_BASE_CUSTITEM (客戶料號特性)"},
    {"value": "MOKP_SN", "label": "MOKP_SN (工單關鍵組件序號如 HD)"},
    {"value": "MOKP_D_BASEINFO", "label": "MOKP_D_BASEINFO (工單組件明細)"},
    {"value": "ASSIGN_SSN", "label": "ASSIGN_SSN (配發出貨 SSN)"},
]

GETVERSION_SLOTS = [
    {"code": "2", "name": "P_CAVER"},
    {"code": "3", "name": "P_CBVER"},
    {"code": "4", "name": "P_CCVER"},
    {"code": "5", "name": "P_CDVER"},
    {"code": "6", "name": "P_IAVER"},
    {"code": "7", "name": "P_IBVER"},
]


def _tag(name, val):
    return f"<{name}>{_xml_escape(str(val if val is not None else ''))}</{name}>"


def build_soap_envelope(action: str, params: dict) -> str:
    """Build a SOAP 1.1 XML envelope matching WebServiceProxy.SFISTSPWebService."""
    p = params or {}
    prog_id = p.get("programId", "Centimani")
    prog_pw = p.get("programPassword", "")
    device = p.get("device", "710001")
    isn = p.get("isn", "")
    tsp = p.get("tsp", "PEGA,2")

    act = str(action or "").strip()
    if act == "WTSP_LOGINOUT":
        login_st = int(p["status"]) if p.get("status") not in (None, "") else 1
        inner = (
            _tag("programId", prog_id)
            + _tag("programPassword", prog_pw)
            + _tag("op", p.get("op", "S09166390"))
            + _tag("password", p.get("password", ""))
            + _tag("device", device)
            + _tag("TSP", tsp)
            + _tag("status", login_st)
        )
    elif act == "WTSP_CHKROUTE":
        inner = (
            _tag("programId", prog_id)
            + _tag("programPassword", prog_pw)
            + _tag("ISN", isn)
            + _tag("device", device)
            + _tag("checkFlag", p.get("checkFlag", "1"))
            + _tag("checkData", p.get("checkData", ""))
            + _tag("type", int(p.get("route_type", 1) or 1))
        )
    elif act == "WTSP_GETVERSION":
        inner = (
            _tag("programId", prog_id)
            + _tag("programPassword", prog_pw)
            + _tag("ISN", isn)
            + _tag("device", device)
            + _tag("type", p.get("ver_type", "ISN_BASEINFO"))
            + _tag("ChkData", p.get("chk_data", ""))
            + _tag("ChkData2", p.get("chk_data2", ""))
        )
    elif act == "WTSP_GETIMAC":
        inner = (
            _tag("programId", prog_id)
            + _tag("programPassword", prog_pw)
            + _tag("device", device)
            + _tag("ISN", isn)
            + _tag("status", int(p.get("status", 1) or 1))
            + _tag("imacnum", int(p.get("imacnum", 1) or 1))
        )
    elif act == "WTSP_RESULT":
        data_str = str(p.get("data", "") or "").strip()
        save_key = str(p.get("save_key", "") or "").strip()
        save_val = str(p.get("save_val", "") or "")
        if not data_str and save_key:
            data_str = f"#SAVE:{save_key}={save_val};"
        res_st = int(p["status"]) if p.get("status") not in (None, "") else 1
        inner = (
            _tag("programId", prog_id)
            + _tag("programPassword", prog_pw)
            + _tag("ISN", isn)
            + _tag("error", p.get("error", ""))
            + _tag("device", device)
            + _tag("TSP", p.get("result_tsp", "PASS"))
            + _tag("data", data_str)
            + _tag("status", res_st)
            + _tag("CPKFlag", p.get("cpk_flag", ""))
        )
    elif act == "WTSP_GETLABEL":
        inner = (
            _tag("programId", prog_id)
            + _tag("programPassword", prog_pw)
            + _tag("type", p.get("label_type", "ISN"))
            + _tag("ISN", isn)
            + _tag("DEV", device)
            + _tag("status", int(p["status"]) if p.get("status") not in (None, "") else 1)
        )
    elif act == "WTSP_LOADKEY":
        inner = (
            _tag("programId", prog_id)
            + _tag("programPassword", prog_pw)
            + _tag("SNTYPE", p.get("sn_type", "MAC1"))
            + _tag("DATA", isn or p.get("data", ""))
            + _tag("OP", p.get("op", "S09166390"))
        )
    elif act == "WTSP_REPAIR":
        inner = (
            _tag("programId", prog_id)
            + _tag("programPassword", prog_pw)
            + _tag("TYPE", p.get("repair_type", "1"))
            + _tag("ISN", isn)
            + _tag("DEV", device)
            + _tag("REASON", p.get("reason", "ZR"))
            + _tag("DUTY", p.get("duty", "7C0"))
            + _tag("NGRP", p.get("ngrp", "AUTO2A"))
            + _tag("TSP", tsp)
        )
    elif act == "GetDatabaseInformation":
        inner = ""
    else:
        raise ValueError(f"Unsupported SFIS SOAP action: {act}")

    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">\n'
        '  <soap:Body>\n'
        f'    <{act} xmlns="{SFIS_SOAP_NS}">{inner}</{act}>\n'
        '  </soap:Body>\n'
        '</soap:Envelope>'
    )


def parse_soap_response(action: str, raw_xml: str) -> dict:
    """Extract Result text, P_RET / passed flag, and P_CAVER..P_IBVER slots from SOAP XML."""
    raw_text = ""
    try:
        root = ET.fromstring(raw_xml)
        target_tag = f"{action}Result"
        for elem in root.iter():
            local = elem.tag.split("}")[-1]
            if local == target_tag:
                raw_text = elem.text or ""
                break
        if not raw_text:
            for elem in root.iter():
                local = elem.tag.split("}")[-1]
                if local == "faultstring" and elem.text:
                    return {
                        "passed": False,
                        "ret_code": "FAULT",
                        "msg": elem.text.strip(),
                        "slots": {},
                        "raw_result": elem.text.strip(),
                    }
    except Exception:
        # Legacy .asmx responses sometimes contain ASCII 0x1F delimiters invalid in XML 1.0
        m_res = re.search(
            rf"<(?:[A-Za-z0-9_]+:)?{re.escape(action)}Result[^>]*>([\s\S]*?)</(?:[A-Za-z0-9_]+:)?{re.escape(action)}Result>",
            raw_xml or "",
        )
        if m_res:
            raw_text = html.unescape(m_res.group(1))
        else:
            m_fault = re.search(
                r"<(?:[A-Za-z0-9_]+:)?faultstring[^>]*>([\s\S]*?)</(?:[A-Za-z0-9_]+:)?faultstring>",
                raw_xml or "",
            )
            if m_fault:
                fmsg = html.unescape(m_fault.group(1)).strip()
                return {
                    "passed": False,
                    "ret_code": "FAULT",
                    "msg": fmsg,
                    "slots": {},
                    "raw_result": fmsg,
                }
            raw_text = raw_xml or ""

    res_s = str(raw_text).strip()
    slots = {}
    ret_code = ""
    msg = res_s

    # Handle structured delimiters returned by SFISTSPWebService:
    # Example patterns: "1\x1fMsg\x1fCAVER\x1fCBVER..." or "1|Msg|..." or leading '1'/'0'
    if res_s.startswith("1"):
        ret_code = "1"
    elif res_s.startswith("0"):
        ret_code = "0"

    slot_names = ["P_CAVER", "P_CBVER", "P_CCVER", "P_CDVER", "P_IAVER", "P_IBVER"]
    parts = None
    for sep in ("\x1f", "\t", "|"):
        if sep in res_s:
            parts = res_s.split(sep)
            break
    if parts and len(parts) >= 2:
        ret_code = parts[0].strip()
        msg = parts[1].strip()
        for idx, sname in enumerate(slot_names):
            if idx + 2 < len(parts):
                slots[sname] = parts[idx + 2].strip()
    elif ";" in res_s and action in ("WTSP_GETVERSION", "WTSP_GETIMAC"):
        toks = res_s.split(";")
        if toks[0].strip() in ("0", "1"):
            ret_code = toks[0].strip()
            msg = toks[1].strip() if len(toks) > 1 else res_s
            for idx, sname in enumerate(slot_names):
                if idx + 2 < len(toks):
                    slots[sname] = toks[idx + 2].strip()

    passed = (ret_code == "1")
    return {
        "passed": passed,
        "ret_code": ret_code or ("OK" if passed else "ERR"),
        "msg": msg,
        "slots": slots,
        "raw_result": res_s,
    }


def call_sfis_soap(url: str, action: str, params: dict, timeout: float = 6.0) -> dict:
    """Send SOAP 1.1 request to SFISTSPWebService.asmx with clean offline/error reporting."""
    clean_url = str(url or "").strip()
    envelope = build_soap_envelope(action, params)
    if not clean_url or not clean_url.lower().startswith(("http://", "https://")):
        return {
            "status": "error",
            "reachable": False,
            "passed": False,
            "ret_code": "INVALID_URL",
            "msg": "請輸入有效的 http:// 或 https:// SFIS WebService 網址",
            "slots": {},
            "soap_request": envelope,
            "raw_result": "",
        }

    req = urllib.request.Request(
        clean_url,
        data=envelope.encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{SFIS_SOAP_NS}{action}"',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_xml = resp.read().decode("utf-8", errors="replace")
            parsed = parse_soap_response(action, raw_xml)
            return {
                "status": "ok",
                "reachable": True,
                "http_code": getattr(resp, "status", 200),
                "soap_request": envelope,
                **parsed,
            }
    except urllib.error.HTTPError as he:
        body = ""
        try:
            body = he.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        parsed = parse_soap_response(action, body) if body else {}
        return {
            "status": "ok" if he.code < 500 else "error",
            "reachable": True,
            "http_code": he.code,
            "passed": False,
            "ret_code": parsed.get("ret_code", f"HTTP_{he.code}"),
            "msg": parsed.get("msg") or f"HTTP {he.code}: {he.reason}",
            "slots": parsed.get("slots", {}),
            "soap_request": envelope,
            "raw_result": body[:1000],
        }
    except Exception as exc:
        return {
            "status": "offline",
            "reachable": False,
            "http_code": 0,
            "passed": False,
            "ret_code": "OFFLINE",
            "msg": f"無法連線至 SFIS 伺服器（可能不在廠區/公司內網）：{exc}",
            "slots": {},
            "soap_request": envelope,
            "raw_result": "",
        }


_MOCK_SFIS_DB = {
    "fields": {},   # {isn: {key: val}}
    "routed": set(), # ISNs already passed WTSP_RESULT PASS
}


def reset_sfis_mock_db() -> dict:
    """Reset in-memory offline SFIS simulator state (simulates PE resetting/clearing ISN routes)."""
    _MOCK_SFIS_DB["fields"].clear()
    _MOCK_SFIS_DB["routed"].clear()
    return {"status": "ok", "message": "已重置本機模擬 SFIS 資料庫與過站狀態"}


def call_sfis_mock_soap(action: str, params: dict) -> dict:
    """
    Offline SFIS simulator emitting authentic WEB_SFIS V2.0 / Centimani Log formats
    including stacked [0..7] slots (P_RET, P_Msg, P_CAVER..P_IBVER) and semicolon payloads.
    """
    p = params or {}
    act = str(action or "").strip()
    isn = str(p.get("isn", "") or "2695160300001").strip()
    device = str(p.get("device", "710001") or "710001").strip()
    op = str(p.get("op", "S09166390") or "S09166390").strip()
    envelope = build_soap_envelope(act, p)
    isn_store = _MOCK_SFIS_DB["fields"].setdefault(isn, {
        "SNA": "NULL",
        "SNB": "TEST_SNB_DEFAULT",
        "SNC": "PID_AURORA_1A",
        "SND": "SSN_90AA2210",
        "SNE": "NULL",
        "SNF": "NULL",
        "SNG": "NULL",
        "MAC1": "48210B47E42C",
        "SSN": f"SSN_{isn[-6:]}",
    })

    if act == "WTSP_LOGINOUT":
        st_code = int(p["status"]) if p.get("status") not in (None, "") else 1
        if st_code == 0:
            raw = f"1Logout OK ({op} @ {device})"
            return {"status": "ok", "reachable": True, "is_mock": True, "http_code": 200,
                    "passed": True, "ret_code": "1", "msg": raw, "slots": {},
                    "soap_request": envelope, "raw_result": raw}
        raw = f"1Welcome using Pegatron SFIS:{op}(模擬OP){op}OP"
        return {"status": "ok", "reachable": True, "is_mock": True, "http_code": 200,
                "passed": True, "ret_code": "1", "msg": raw, "slots": {},
                "soap_request": envelope, "raw_result": raw}

    if act == "WTSP_CHKROUTE":
        if isn in _MOCK_SFIS_DB["routed"]:
            msg = f"Route Error: ISN [{isn}] 已於本機模擬資料庫過站完成（可按重置模擬DB模擬PE清站）"
            raw = f"0\x1f{msg}"
            return {"status": "ok", "reachable": True, "is_mock": True, "http_code": 200,
                    "passed": False, "ret_code": "0", "msg": msg, "slots": {},
                    "soap_request": envelope, "raw_result": raw}
        msg = f"ISN [{isn}] Route OK @ Device [{device}] (模擬內網)"
        raw = f"1\x1f{msg}"
        return {"status": "ok", "reachable": True, "is_mock": True, "http_code": 200,
                "passed": True, "ret_code": "1", "msg": msg, "slots": {},
                "soap_request": envelope, "raw_result": raw}

    if act == "WTSP_GETVERSION":
        vt = str(p.get("ver_type", "ISN_BASEINFO") or "ISN_BASEINFO").strip().upper()
        c1 = str(p.get("chk_data", "") or "").strip()
        c2 = str(p.get("chk_data2", "") or "").strip()
        slots = {"P_CAVER": "", "P_CBVER": "", "P_CCVER": "", "P_CDVER": "", "P_IAVER": "", "P_IBVER": ""}
        if vt == "ITEMINFO":
            slots["P_CAVER"] = "1"
            slots["P_CBVER"] = "PL_AURORA/PEGA;"
            slots["P_CCVER"] = f"60_{isn}"
            slots["P_CDVER"] = f"90AA221000S0_{isn[-5:]}"
            msg = f"TYPE:[ITEMINFO] GET INFO ISN:[{isn}/60_{isn}] TYPE:[ITEMINFO] OK!!"
        elif vt == "MOKP_SN":
            slots["P_CAVER"] = f"SN:90AA221000S0_{isn[-5:]};IMEI:35888109{isn[-5:]};SW:V1.0.6;"
            slots["P_CBVER"] = "90AA221000S0"
            msg = f"TYPE:[MOKP_SN] OK!! ({c1 or 'MB'})"
        elif vt == "GET_IVMAC_NEW":
            slots["P_CAVER"] = f"GUID1:AA11{isn[-4:]};GUID2:BB22{isn[-4:]};MAC1:48210B47E42C;"
            msg = "TYPE:[GET_IVMAC_NEW] OK!!"
        elif vt == "ITEM_FEATURE_BASEINFO":
            slots["P_CAVER"] = f"{isn};90AA-221000S0"
            slots["P_CBVER"] = f"{isn};69B35-AURORA"
            slots["P_CCVER"] = f";{c1 or 'AURORA'};{c2 or 'ModelNumber'};PL_AURORA1A;1;"
            slots["P_CDVER"] = "N/A"
            msg = "TYPE:[ITEM_FEATURE_BASEINFO] OK!!"
        elif vt == "GETSN_BYRULE":
            slots["P_CAVER"] = f"M{isn[-8:]}01,"
            msg = f"TYPE:[GETSN_BYRULE] M{isn[-8:]}01, DATA GOT!!"
        elif vt == "ASSIGN_SSN":
            slots["P_CAVER"] = f"[ITEM2,CUSTITEMNM,1]SSN{isn[-7:]}"
            msg = "TYPE:[ASSIGN_SSN] OK!!"
        else:
            val = isn_store.get(c1, isn_store.get(c1.upper(), f"MOCK_{c1 or 'DATA'}"))
            slots["P_CAVER"] = val
            slots["P_CBVER"] = f"90AA221000S0;{val};"
            slots["P_CCVER"] = f"KEY:{c1 or 'MAC1'};VAL:{val};DATE:2026/11/24;"
            msg = f"TYPE:[{vt}] DATA GOT!! ({c1 or 'ISN_BASEINFO'})"
        raw = "\x1f".join(["1", msg, slots["P_CAVER"], slots["P_CBVER"], slots["P_CCVER"], slots["P_CDVER"], slots["P_IAVER"], slots["P_IBVER"]])
        return {"status": "ok", "reachable": True, "is_mock": True, "http_code": 200,
                "passed": True, "ret_code": "1", "msg": msg, "slots": slots,
                "soap_request": envelope, "raw_result": raw}

    if act == "WTSP_GETIMAC":
        macs = f"{isn_store.get('MAC1', '48210B47E42C')},48210B47E42D"
        msg = f"GETIMAC OK ({macs})"
        slots = {"P_CAVER": macs}
        return {"status": "ok", "reachable": True, "is_mock": True, "http_code": 200,
                "passed": True, "ret_code": "1", "msg": msg, "slots": slots,
                "soap_request": envelope, "raw_result": f"1\x1f{msg}\x1f{macs}"}

    if act == "WTSP_GETLABEL":
        lbl = f"ISN:{isn};PN:90AA221000S0;QTY:1;"
        msg = f"GETLABEL OK ({lbl})"
        return {"status": "ok", "reachable": True, "is_mock": True, "http_code": 200,
                "passed": True, "ret_code": "1", "msg": msg, "slots": {"P_CAVER": lbl},
                "soap_request": envelope, "raw_result": f"1\x1f{msg}\x1f{lbl}"}

    if act == "WTSP_RESULT":
        data_str = str(p.get("data", "") or "").strip()
        save_key = str(p.get("save_key", "") or "").strip()
        save_val = str(p.get("save_val", "") or "")
        if not data_str and save_key:
            data_str = f"#SAVE:{save_key}={save_val};"
        for m in re.finditer(r"#SAVE:([^=;]+)=([^;]*)", data_str, re.I):
            k_n = m.group(1).strip().split(":")[0]
            isn_store[k_n] = m.group(2).strip() or "NULL"
        res_st = int(p["status"]) if p.get("status") not in (None, "") else 1
        if res_st == 1:
            _MOCK_SFIS_DB["routed"].add(isn)
        msg = f"P_RET=1 RESULT SAVED (Mock): {data_str or 'PASS'}"
        return {"status": "ok", "reachable": True, "is_mock": True, "http_code": 200,
                "passed": True, "ret_code": "1", "msg": msg, "slots": {},
                "soap_request": envelope, "raw_result": f"1\x1f{msg}"}

    if act in ("WTSP_LOADKEY", "WTSP_REPAIR"):
        msg = f"{act} OK (Mock Simulator)"
        return {"status": "ok", "reachable": True, "is_mock": True, "http_code": 200,
                "passed": True, "ret_code": "1", "msg": msg, "slots": {},
                "soap_request": envelope, "raw_result": f"1\x1f{msg}"}

    return {"status": "ok", "reachable": True, "is_mock": True, "http_code": 200,
            "passed": True, "ret_code": "1", "msg": f"{act} Mock OK", "slots": {},
            "soap_request": envelope, "raw_result": f"1\x1f{act} Mock OK"}


def escape_centimani_ref_arg(raw: str) -> str:
    """
    Escape Centimani Ref helper function parameters per 'Ref輔助Function說明' (User Guide R20-R22):
    " -> \", , -> \,, * -> \*, \ -> \\, / -> \/, : -> \:, ; -> \;, } -> }}
    """
    s = str(raw or "")
    s = s.replace("\\", "\\\\")
    for ch in ('"', ",", "*", "/", ":", ";"):
        s = s.replace(ch, "\\" + ch)
    s = s.replace("}", "}}")
    return s


def build_centimani_ref_expr(var_name: str, mode: str = "raw", **kw) -> str:
    """Build a compliant Centimani Ref string-extraction formula."""
    vn = str(var_name or "sfData").strip().lstrip("$") or "sfData"
    m = str(mode or "raw").strip().lower()
    if m == "split":
        delim = escape_centimani_ref_arg(kw.get("delim", ";") or ";")
        idx = str(int(kw.get("index", 0) or 0))
        return f'${vn}:SplitString,"{delim}","{idx}":Trim;'
    if m == "within":
        left_s = escape_centimani_ref_arg(kw.get("left", "") or "")
        right_s = escape_centimani_ref_arg(kw.get("right", "") or "")
        idx = str(kw.get("index", "") or "")
        return f'${vn}:WithinString,"{left_s}","{right_s}","{idx}":Trim;'
    if m == "substr":
        start = str(int(kw.get("start", 0) or 0))
        length = str(int(kw.get("length", 12) or 12))
        return f'${vn}:SubString,"{start}","{length}";'
    if m == "ma":
        tok = escape_centimani_ref_arg(kw.get("marker", "") or "")
        return f'${vn}:maString,"{tok}":Trim;'
    if m == "mb":
        tok = escape_centimani_ref_arg(kw.get("marker", "") or "")
        return f'${vn}:mbString,"{tok}":Trim;'
    if m == "getmac2":
        return f'${vn}:getMAC2;'
    return f'${vn};'


def escape_build_get_ref(item: dict, default_var: str) -> str:
    explicit = str(item.get("ref_expr") or "").strip()
    if explicit:
        return explicit
    return f"${default_var}:lwString;"


def build_sfis_excel_steps(items: list, start_phase: int = 1, include_show_isn: bool = True) -> list:
    """
    Convert SFIS HMI card sequence into Centimani-compliant TestFlow rows:
    - Automatically prepends :ShowISN,\"*(ISN)\" before :SfCheckRoute (Loader rule).
    - Enforces ExecMode = '8' on every :Sf* call (Centimani 1.2.1.2 8~11 rule).
    - Maps P_CAVER..P_IBVER slots ('2'..'7') and Ref $GlobalVar cleanly.
    """
    rows = []
    phase_num = max(0, int(start_phase))
    has_show_isn = False

    def _add(title_str, desc, send_cmd, ref="", val="", tid="B7PL025", em="8", phase_val="", reply_val=""):
        rows.append({
            "Index": f"{len(rows):03d}",
            "Phase": phase_val,
            "Title": title_str,
            "Description": desc,
            "Instrument": "",
            "Switch": "",
            "Send": send_cmd,
            "Reply": reply_val,
            "EndPrompt": "",
            "Ref": ref,
            "Validation": val,
            "Waiting": "0",
            "ExecMode": em,
            "Parameter": "",
            "Marco": "",
            "TestID": tid,
        })

    def _resolve_get_params(it: dict):
        fk = str(it.get("field_key", "") or "").strip()
        fk_u = fk.upper()
        if fk_u == "ITEMINFO_60":
            return "ITEMINFO", "4", "", "", str(it.get("ref_var") or "sf60ISN").strip().lstrip("$")
        if fk_u == "ITEMINFO_80":
            return "ITEMINFO", "5", "", "", str(it.get("ref_var") or "sf80ISN").strip().lstrip("$")
        if fk_u == "SSN":
            return "ISN_BASEINFO", "3", "SSN", "", str(it.get("ref_var") or "sfSSN").strip().lstrip("$")
        vt = str(it.get("ver_type", "ISN_BASEINFO") or "ISN_BASEINFO").strip()
        sc = str(it.get("slot_code", "2") or "2").strip()
        c1 = str(it.get("chk_data", fk or "MAC1") or "").strip()
        c2 = str(it.get("chk_data2", "") or "").strip()
        rv = str(it.get("ref_var") or (f"sf_{fk}" if fk else "sfData")).strip().lstrip("$")
        return vt, sc, c1, c2, rv

    for item in (items or []):
        kind = str(item.get("kind", "")).strip().lower()
        if kind in ("login", "logout"):
            # Centimani logs into SFIS automatically via System.ini SFIS_AutoLogin=1
            continue

        if kind == "checkroute":
            if include_show_isn and not has_show_isn:
                _add(
                    "0,CheckRoute",
                    "Display ISN on Centimani UI",
                    ':ShowISN,"*(ISN)"',
                    tid="B7PL025",
                    em="0",
                    phase_val=str(phase_num),
                    reply_val="0",
                )
                has_show_isn = True
                _add("", "Check SFIS Station Route", ":SfCheckRoute", tid="OTCH013", em="8", phase_val="", reply_val="0")
            else:
                _add(
                    "0,CheckRoute" if not rows else "",
                    "Check SFIS Station Route",
                    ":SfCheckRoute",
                    tid="OTCH013",
                    em="8",
                    phase_val=str(phase_num) if not rows else "",
                    reply_val="0",
                )
            phase_num += 1

        elif kind in ("getversion", "get"):
            ver_type, slot_code, chk1, chk2, ref_var = _resolve_get_params(item)
            send_cmd = f':SfGetVersion,"*(ISN)","{ver_type}","{slot_code}","{chk1}","{chk2}"'
            _add(
                f"0,SFIS GET {chk1 or ver_type}",
                f"SFIS GetVersion ({ver_type} {chk1})".strip(),
                send_cmd,
                ref=escape_build_get_ref(item, ref_var),
                tid="OTFX085",
                em="8",
                phase_val=str(phase_num),
            )
            phase_num += 1

        elif kind == "getimac":
            slot_code = str(item.get("slot_code", "2") or "2").strip()
            imac_num = str(item.get("imacnum", "1") or "1").strip()
            ref_var = str(item.get("ref_var", "sfMAC") or "sfMAC").strip().lstrip("$")
            send_cmd = f':SfGetiMAC,"*(ISN)","1","{imac_num}","{slot_code}"'
            ref_val = str(item.get("ref_expr") or "").strip() or f'${ref_var}:SubString,"0","12":lwString;'
            _add(
                "0,SFIS GET MAC",
                "SFIS Get iMAC",
                send_cmd,
                ref=ref_val,
                tid="OTFX085",
                em="8",
                phase_val=str(phase_num),
            )
            phase_num += 1

        elif kind == "savelink":
            raw_key = str(item.get("save_key", "SNA") or "SNA").strip()
            save_key = re.sub(r"^#SAVE:", "", raw_key, flags=re.IGNORECASE).strip() or "SNA"
            save_val = str(item.get("save_val", "*(gUUID)") or "*(gUUID)").strip()
            send_cmd = f':SfSaveLinkData,"{save_key}","{save_val}"'
            _add(
                f"0,SFIS WRITE {save_key}",
                f"SFIS SaveLinkData ({save_key})",
                send_cmd,
                tid="OTFX064",
                em="8",
                phase_val=str(phase_num),
                reply_val="0",
            )
            phase_num += 1

        elif kind == "rw":
            raw_key = str(item.get("save_key") or item.get("field_key") or "SNA").strip()
            save_key = re.sub(r"^#SAVE:", "", raw_key, flags=re.IGNORECASE).strip() or "SNA"
            save_val = str(item.get("save_val", "TEST_VAL") or "TEST_VAL").strip()
            ref_var = str(item.get("ref_var") or f"sf_{save_key}").strip().lstrip("$")
            _add(
                f"0,SFIS R/W {save_key}",
                f"SFIS SaveLinkData ({save_key})",
                f':SfSaveLinkData,"{save_key}","{save_val}"',
                tid="OTFX064",
                em="8",
                phase_val=str(phase_num),
                reply_val="0",
            )
            _add(
                "",
                f"SFIS ReadBack Verify ({save_key})",
                f':SfGetVersion,"*(ISN)","ISN_BASEINFO","2","{save_key}",""',
                ref=f"${ref_var}:lwString;",
                tid="OTFX085",
                em="8",
                phase_val="",
            )
            phase_num += 1

        elif kind == "clear":
            raw_key = str(item.get("save_key") or item.get("field_key") or "SNA").strip()
            save_key = re.sub(r"^#SAVE:", "", raw_key, flags=re.IGNORECASE).strip() or "SNA"
            _add(
                f"0,SFIS CLEAR {save_key}",
                f"SFIS Clear Proxy Field ({save_key})",
                f':SfSaveLinkData,"{save_key}",""',
                tid="OTFX064",
                em="8",
                phase_val=str(phase_num),
                reply_val="0",
            )
            phase_num += 1

    if include_show_isn and rows and not has_show_isn:
        rows.insert(0, {
            "Index": "000",
            "Phase": str(max(0, int(start_phase))),
            "Title": "0,CheckRoute",
            "Description": "Display ISN on Centimani UI",
            "Instrument": "",
            "Switch": "",
            "Send": ':ShowISN,"*(ISN)"',
            "Reply": "0",
            "EndPrompt": "",
            "Ref": "",
            "Validation": "",
            "Waiting": "0",
            "ExecMode": "0",
            "Parameter": "",
            "Marco": "",
            "TestID": "B7PL025",
        })
        for idx, r in enumerate(rows):
            r["Index"] = f"{idx:03d}"

    return rows
