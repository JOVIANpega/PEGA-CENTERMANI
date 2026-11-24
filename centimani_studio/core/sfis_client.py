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

    def _add(title_str, desc, send_cmd, ref="", val="", tid="B7PL025", em="8", phase_val=""):
        rows.append({
            "Index": f"{len(rows):03d}",
            "Phase": phase_val,
            "Title": title_str,
            "Description": desc,
            "Instrument": "",
            "Switch": "",
            "Send": send_cmd,
            "Reply": "",
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
                    "0,SFIS CheckRoute",
                    "Display ISN on Centimani UI",
                    ':ShowISN,"*(ISN)"',
                    tid="B7PL025",
                    em="1",
                    phase_val=str(phase_num),
                )
                has_show_isn = True
                _add("", "Check SFIS Station Route", ":SfCheckRoute", tid="OTCH013", em="8", phase_val="")
            else:
                _add(
                    "0,SFIS CheckRoute" if not rows else "",
                    "Check SFIS Station Route",
                    ":SfCheckRoute",
                    tid="OTCH013",
                    em="8",
                    phase_val=str(phase_num) if not rows else "",
                )
            phase_num += 1

        elif kind in ("getversion", "get"):
            ver_type, slot_code, chk1, chk2, ref_var = _resolve_get_params(item)
            send_cmd = f':SfGetVersion,"*(ISN)","{ver_type}","{slot_code}","{chk1}","{chk2}"'
            is_first = (len(rows) == 0)
            _add(
                f"0,SFIS GET {chk1 or ver_type}",
                f"SFIS GetVersion ({ver_type} {chk1})".strip(),
                send_cmd,
                ref=f"${ref_var}:lwString;",
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
            _add(
                "0,SFIS GET MAC",
                "SFIS Get iMAC",
                send_cmd,
                ref=f'${ref_var}:SubString,"0","12":lwString;',
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
            )
            phase_num += 1

    if include_show_isn and rows and not has_show_isn:
        rows.insert(0, {
            "Index": "000",
            "Phase": str(max(0, int(start_phase))),
            "Title": "0,SFIS ShowISN",
            "Description": "Display ISN on Centimani UI",
            "Instrument": "",
            "Switch": "",
            "Send": ':ShowISN,"*(ISN)"',
            "Reply": "",
            "EndPrompt": "",
            "Ref": "",
            "Validation": "",
            "Waiting": "0",
            "ExecMode": "1",
            "Parameter": "",
            "Marco": "",
            "TestID": "B7PL025",
        })
        for idx, r in enumerate(rows):
            r["Index"] = f"{idx:03d}"

    return rows
