# -*- coding: utf-8 -*-
"""
Automated regression tests for Centimani Studio core engines:
- golden_data (mother template + STANDARD_BLOCKS)
- script_doctor (NI-6009, FeasaLED, IQxel RF, UART->SSH, auto_fix)
- excel_engine (in-place patch preserving Mount + Marco + clean audit)
- ini_engine (System.ini SFIS/iPLAS & Global.ini COM/IP)
"""
import os
import sys
import tempfile
import shutil
import unittest
import openpyxl

STUDIO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if STUDIO_DIR not in sys.path:
    sys.path.insert(0, STUDIO_DIR)

from core.golden_data import get_golden_mother, STANDARD_BLOCKS
from core.script_doctor import (
    audit_workspace,
    auto_fix_workspace,
    insert_ni6009_block,
    insert_instrument_title_block,
    insert_rf_iqxel_block,
    update_comm_settings,
)
from core.excel_engine import export_workspace_to_excel, import_excel_to_workspace
from core.ini_engine import sync_and_generate_inis


class TestCentimaniStudioCore(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="centimani_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_golden_mother_and_blocks_clean(self):
        gm = get_golden_mother()
        self.assertIn("stations", gm)
        self.assertIn("instruments", gm)
        block_ids = [b["block_id"] for b in STANDARD_BLOCKS]
        self.assertIn("BLK_VOLT_NI6008_BATCH", block_ids)
        self.assertNotIn("BLK_VOLT_DIFF_SINGLE", block_ids)
        for b in STANDARD_BLOCKS:
            text = (b.get("name", "") + b.get("description", "")).upper()
            for proj in ("VALO360", "MU310", "KANGAROO"):
                self.assertNotIn(proj, text)

    def test_ni6009_insert_export_and_mount_sync(self):
        ws = get_golden_mother()
        st = list(ws["stations"].keys())[0]
        added = insert_ni6009_block(
            ws, st, mode="RSE", sample_ms="1000", dev_id="Dev1",
            title_name="Measure Voltage Test",
            channels=[{"ch": 0, "name": "VCC_5V", "dl": "4.75", "ul": "5.25"}]
        )
        self.assertGreaterEqual(added, 5)
        auto_fix_workspace(ws)
        out_xlsx = os.path.join(self.tmp_dir, "TestFlow.xlsx")
        export_workspace_to_excel(ws, out_xlsx)

        # Now test in-place patch mode preserves Instrument Mount
        ws_in = import_excel_to_workspace(out_xlsx)
        insert_ni6009_block(
            ws_in, st, mode="DIFF", sample_ms="1000", dev_id="Dev1",
            title_name="Measure 12V DIFF",
            channels=[{"ch": 1, "name": "VCC_12V", "dl": "11.40", "ul": "12.60"}]
        )
        auto_fix_workspace(ws_in)
        out_fixed = os.path.join(self.tmp_dir, "TestFlow_FIXED.xlsx")
        export_workspace_to_excel(ws_in, out_fixed)

        wb = openpyxl.load_workbook(out_fixed)
        ni_rows = [[c.value for c in r[:2]] for r in wb["Instrument"].iter_rows() if r[1].value == "NI6008-1"]
        wb.close()
        self.assertEqual(len(ni_rows), 1)
        self.assertIn(st, str(ni_rows[0][0] or ""))

        ws_re = import_excel_to_workspace(out_fixed)
        rep = audit_workspace(ws_re)
        self.assertEqual(rep["error_count"], 0)

    def test_feasa_led_custom_steps(self):
        ws = get_golden_mother()
        st = list(ws["stations"].keys())[0]
        added = insert_instrument_title_block(
            ws, st, "FeasaLED", "Check Green LED",
            custom_steps=[
                {"Instrument": "LED_Test", "Send": ":ObtainDevice", "ExecMode": "0", "Description": "LED#-#Obtain"},
                {"Instrument": "LED_Test", "Send": ':Dev.CaptureAndRead,"01"', "Ref": "$LED_Wave;\n$LED_Int", "Validation": "(LED_Wave,%f,515,535);\n(LED_Int,%f,1000,99999)", "ExecMode": "2:0", "Description": "LED#-#Check"},
                {"Instrument": "LED_Test", "Send": ":ReleaseDevice", "ExecMode": "3", "Description": "LED#-#Release"},
            ],
            globals_patch={"Settings": {"LED_AZ1": "COM17", "LED_Light1": "01"}}
        )
        self.assertEqual(added, 3)
        auto_fix_workspace(ws)
        rep = audit_workspace(ws)
        self.assertEqual(rep["error_count"], 0)
        self.assertEqual(ws["global_ini"]["Settings"].get("LED_AZ1"), "COM17")

    def test_rf_iqxel_block_and_marcos(self):
        ws = get_golden_mother()
        st = list(ws["stations"].keys())[0]
        added = insert_rf_iqxel_block(
            ws, st, "InstIQApiA", "WIFI RF Test",
            settings_str="192.168.100.254,1,2,1,60000,PathLoss.ini",
            tx_tests=[{"channel": "6", "bw": "20", "mcs": "7", "antenna": "1", "target_pwr": "15", "pwr_min": "13", "pwr_max": "17", "evm_min": "-50", "evm_max": "-28"}],
            rx_tests=[{"channel": "6", "bw": "20", "mcs": "7", "antenna": "1", "rx_level": "-59"}]
        )
        self.assertEqual(added, 2)
        self.assertIn("WIFI Tx MCS", ws["marcos"])
        self.assertIn("WIFI Rx MCS", ws["marcos"])
        self.assertEqual(len(ws["marcos"]["WIFI Tx MCS"]), 21)
        self.assertEqual(len(ws["marcos"]["WIFI Rx MCS"]), 22)
        auto_fix_workspace(ws)
        rep = audit_workspace(ws)
        self.assertEqual(rep["error_count"], 0)

    def test_sfis_iplas_and_comm_settings(self):
        ws = get_golden_mother()
        st = list(ws["stations"].keys())[0]
        ws["stations"][st].append({
            "Index": "001", "Phase": "1", "Title": "0,UART Test,3", "Marco": "",
            "Instrument": "", "Switch": "", "Send": ':Connect,"UART"', "Reply": "0",
            "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "",
            "Waiting": "", "ExecMode": "1", "Description": "Open UART", "TestID": "B7PL025"
        })
        ws["stations"][st].append({
            "Index": "002", "Phase": "", "Title": "", "Marco": "",
            "Instrument": "", "Switch": "", "Send": "UART@cat /etc/version", "Reply": "@#",
            "EndPrompt": "", "Ref": "", "Validation": "", "Prompt": "",
            "Waiting": "", "ExecMode": "1", "Description": "Read FW", "TestID": "VSCH026"
        })
        ws["system_ini"] = {
            "SFIS_Enable": "1",
            "SFIS_WebLink": "http://172.18.125.49/SFISWebService/SFISTSPWebService.asmx,2",
            "iPLAS_Enable": "1",
            "iPLAS_Site": "PCQ",
        }
        conv = update_comm_settings(ws, dut_ur1="COM9", dut_ip1="192.168.50.10", convert_uart_to_ssh=True, target_sheet=st)
        self.assertEqual(conv, 2)
        sys_ini, glb_ini = sync_and_generate_inis(ws, "TestFlow.xlsx", self.tmp_dir)
        sys_txt = open(sys_ini, encoding="utf-8").read()
        glb_txt = open(glb_ini, encoding="utf-8").read()
        self.assertIn("SFIS_Enable=1", sys_txt)
        self.assertIn("172.18.125.49", sys_txt)
        self.assertIn("iPLAS_Site=PCQ", sys_txt)
        self.assertIn("DUT_UR1=COM9", glb_txt)
        self.assertIn("DUTIP_1=192.168.50.10", glb_txt)

    def test_phase_order_detection_and_block_sorter(self):
        from core.block_sorter import (
            extract_station_blocks,
            reorder_station_blocks,
        )
        ws = get_golden_mother()
        st = "MB"
        ws["stations"][st] = [
            {"Index": "001", "Phase": "2", "Title": "Load", "Send": ':SetVal,"$sEth_MAC","AABBCC"', "Ref": "", "Validation": "", "ExecMode": "0", "Description": "Set MAC", "TestID": "B7PL025"},
            {"Index": "002", "Phase": "3", "Title": "WaitBoot", "Send": ':Delay,"3000"', "Ref": "", "Validation": "", "ExecMode": "0", "Description": "Wait", "TestID": "B7PL025"},
            {"Index": "003", "Phase": "12", "Title": "Software reboot", "Send": 'LAN@@reboot', "Ref": "", "Validation": "", "ExecMode": "0", "Description": "Reboot", "TestID": "B7PL025"},
            {"Index": "004", "Phase": "", "Title": "", "Send": ':Delay,"1000"', "Ref": "", "Validation": "", "ExecMode": "0", "Description": "Substep", "TestID": "B7PL025"},
            {"Index": "005", "Phase": "4", "Title": "CheckVersion", "Send": ':Compare,"$sEth_MAC"', "Ref": "", "Validation": "", "ExecMode": "0", "Description": "Use MAC", "TestID": "B7PL025"},
            {"Index": "006", "Phase": "97", "Title": "Teardown", "Send": ':Disconnect,"LAN"', "Ref": "", "Validation": "", "ExecMode": "3", "Description": "End", "TestID": "B7PL025"},
        ]
        rep = audit_workspace(ws)
        issues = rep.get("phase_order_issues", [])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["title"], "CheckVersion")
        self.assertIn("倒退", issues[0]["reason"])

        # Reorder so Software reboot (idx 2) goes after CheckVersion (idx 3), and auto-renumber Phase
        res = reorder_station_blocks(ws, st, [0, 1, 3, 2, 4], auto_renumber_phase=True)
        self.assertEqual(res["dep_warnings"], [])
        rep_after = audit_workspace(ws)
        self.assertEqual(rep_after.get("phase_order_issues", []), [])
        phases_after = [r["Phase"] for r in ws["stations"][st] if r["Phase"]]
        self.assertEqual(phases_after, ["1", "2", "3", "4", "97"])

        # Now test variable dependency warning if producer (Load, now idx 0) is moved after consumer (CheckVersion, now idx 2)
        res_bad = reorder_station_blocks(ws, st, [1, 2, 0, 3, 4], auto_renumber_phase=True)
        self.assertEqual(len(res_bad["dep_warnings"]), 1)
        self.assertIn("$sEth_MAC", res_bad["dep_warnings"][0])


        # Test active_sheet setting in export_workspace_to_excel
        import openpyxl, tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_test_xlsx = os.path.join(tmp_dir, "test_active_sheet.xlsx")
            export_workspace_to_excel(ws, out_test_xlsx, active_sheet="MB")
            wb_check = openpyxl.load_workbook(out_test_xlsx)
            self.assertEqual(wb_check.active.title, "MB")


if __name__ == "__main__":
    unittest.main()
