# -*- coding: utf-8 -*-
"""
Centimani Studio V2.3 - 原生 Windows 桌面應用程式 (Tkinter GUI)
1. 簡化檔案載入：拿掉多餘的目錄搜尋下拉選單與二次按鈕，改為單一「📂 1. 選擇 Excel 檔案（選完自動體檢）」按鈕。
2. 完整透明呈現：清楚列出每一筆抓到的邏輯錯誤與警告，並標明「系統將如何自動修正（如補齊 TestID、修正 ExecMode）」。
3. 新增「🧪 匯出無硬體辦公桌試跑版 (Dry-Run)」：自動將需要實體儀器/序列埠的步驟設為 ExecMode=6 (Skip) 並卸載 Instrument Mount，
   讓工程師在沒有接治具與板子的辦公電腦上也能直接開 CentimaniSystem.exe 跑完流程。
"""
import os
import sys
import copy
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SCRIPTS_ROOT = os.path.join(PROJECT_ROOT, "SCRIPTS")
OUTPUT_ROOT = os.path.join(BASE_DIR, "output_system")

sys.path.insert(0, BASE_DIR)
from core.golden_data import STANDARD_BLOCKS, get_golden_mother
from core.excel_engine import export_workspace_to_excel, import_excel_to_workspace
from core.ini_engine import sync_and_generate_inis
from core.script_doctor import audit_workspace, auto_fix_workspace

FONT_H1 = ("Microsoft JhengHei UI", 13, "bold")
FONT_H2 = ("Microsoft JhengHei UI", 11, "bold")
FONT_BODY = ("Microsoft JhengHei UI Light", 10)
FONT_BOLD = ("Microsoft JhengHei UI", 10, "bold")
FONT_MONO = ("Consolas", 10)


def bind_hover(widget, normal_bg, hover_bg, active_pred=None, active_bg=None):
    """依據全案規範實裝 Handover 游標懸停底色變色回饋與 hand2 游標。"""
    widget.configure(cursor="hand2", bg=normal_bg)

    def on_enter(_e):
        widget.configure(bg=hover_bg)

    def on_leave(_e):
        if active_pred and active_pred():
            widget.configure(bg=active_bg or normal_bg)
        else:
            widget.configure(bg=normal_bg)

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


def open_folder_and_highlight(folder_path):
    """產出完成後自動彈出該資料夾視窗。"""
    try:
        if os.path.exists(folder_path):
            os.startfile(folder_path)
    except Exception:
        pass


def convert_workspace_to_dry_run(ws):
    """
    將 Workspace 轉換為「無硬體辦公桌試跑版 (Dry-Run Simulation)」：
    1. 清空 Instrument 與 Switch 的 Mount 欄位，避免 CentimaniSystem.exe 開機時因找不到 NI6008 / GPIB / COM Port 而報錯。
    2. 將 Station 分頁中所有需要實體連線或儀器的步驟（UART@, :Connect, :Disconnect, :ObtainDevice, :Dev., :Sf）
       設為 ExecMode = 6 (Skip)，保留 UI 與邏輯步驟，讓辦公桌電腦不接硬體也能直接刷條碼跑完 PASS。
    """
    dry_ws = copy.deepcopy(ws)
    # 避免用原檔 in-place 保留舊 Instrument Mount，強制輸出乾淨 Dry-Run 工作簿
    dry_ws["source_file"] = ""

    # 無硬體試跑版預設單機測試（僅啟用 LOAD_1=true，避免多工等待其他槽位刷條碼卡住）
    settings = dry_ws.setdefault("global_ini", {}).setdefault("Settings", {})
    settings["LOAD_1"] = "true"
    for slot in range(2, 5):
        if f"LOAD_{slot}" in settings or len(dry_ws.get("duts", [])) >= slot:
            settings[f"LOAD_{slot}"] = "false"

    for inst in dry_ws.get("instruments", []):
        inst["Mount"] = ""
    for sw in dry_ws.get("switches", []):
        sw["Mount"] = ""

    hw_prefixes = (
        ":Connect", ":Disconnect", ":ObtainDevice", ":ReleaseDevice",
        ":ObtainSubDevice", ":ReleaseSubDevice", ":Dev.", ":sDev.",
        ":Utility.Ping", ":FindIP", ":CheckLimit"
    )
    all_step_sheets = list(dry_ws.get("stations", {}).items()) + list(dry_ws.get("marcos", {}).items())
    for st_name, steps in all_step_sheets:
        for idx, st in enumerate(steps):
            s_send = str(st.get("Send", "")).strip()
            s_inst = str(st.get("Instrument", "")).strip()
            s_sw = str(st.get("Switch", "")).strip()

            # Centimani rule: ALL :Sf* commands (:SfCheckRoute, :SfGetVersion, etc.) MUST have ExecMode 8 or 9
            # Setting ExecMode=6 triggers "ExecMode of SfGetVersion must be 8 or 9."
            if s_send.startswith(":Sf"):
                if str(st.get("ExecMode", "")).strip() not in ("8", "9"):
                    st["ExecMode"] = "9"
                if st.get("Validation", "").strip():
                    st["Validation"] = ""
                continue

            # In Dry-Run mode, all hardware commands, instruments, and downstream measurement
            # limit checks (:CheckLimit, or steps with Validation) must be skipped (ExecMode=6)
            # because no physical instruments were run to produce measurement variables!
            is_hw_or_meas_cmd = (
                s_inst != "" or
                s_sw != "" or
                s_send.startswith(hw_prefixes) or
                bool(st.get("Validation", "").strip()) or
                ("@" in s_send and not s_send.startswith(":"))
            )
            if is_hw_or_meas_cmd:
                st["ExecMode"] = "6"
                st["Instrument"] = ""
                st["Switch"] = ""
                dry_ws.setdefault("_modified_cells", []).append({
                    "sheet": st_name, "row": idx + 2, "col_name": "ExecMode",
                    "old": st.get("ExecMode", ""), "new": "6",
                    "note": "【無硬體試跑版】此步驟需實體硬體/連線或依賴量測數值，已自動設為 ExecMode=6 (Skip)"
                })
    return dry_ws


class CentimaniDesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Centimani Studio V2.3 — 新腳本積木產生器 & 現有 Excel 無負擔健檢修復工具")
        self.geometry("1220x800")
        self.minsize(1040, 700)
        self.configure(bg="#F8FAFC")

        self.current_mode = "B"
        self.loaded_file_path = ""
        self.loaded_workspace = None
        self.loaded_report = None
        self.user_choices = {}
        self.block_vars = {}

        self._build_header()
        self._build_door_switcher()
        self._build_main_panels()
        self._switch_mode("B")

    def _build_header(self):
        hdr = tk.Frame(self, bg="#0F172A", height=54, padx=20, pady=10)
        hdr.pack(fill="x")
        tk.Label(
            hdr,
            text="Centimani Studio V2.3  |  原生桌面工具（免開網頁，產出後自動彈出乾淨的 System 資料夾）",
            font=FONT_H1, fg="#FFFFFF", bg="#0F172A"
        ).pack(side="left")

        btn_open_out = tk.Button(
            hdr, text="📂 開啟總輸出目錄", font=FONT_BOLD,
            fg="#0F172A", bg="#E2E8F0", relief="flat", padx=12, pady=4,
            command=lambda: open_folder_and_highlight(OUTPUT_ROOT)
        )
        btn_open_out.pack(side="right")
        bind_hover(btn_open_out, "#E2E8F0", "#BAE6FD")

    def _build_door_switcher(self):
        bar = tk.Frame(self, bg="#F8FAFC", padx=20, pady=12)
        bar.pack(fill="x")
        bar.columnconfigure(0, weight=1)
        bar.columnconfigure(1, weight=1)

        self.btn_door_b = tk.Button(
            bar,
            text="🔵 入口一：檢查並修復現有 Excel 腳本（選檔自動體檢 ➡️ 點一下修好匯出）",
            font=FONT_H2, fg="#0F172A", bg="#EFF6FF", relief="solid", bd=1,
            padx=16, pady=10, command=lambda: self._switch_mode("B")
        )
        self.btn_door_b.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        bind_hover(self.btn_door_b, "#EFF6FF", "#BAE6FD", lambda: self.current_mode == "B", "#DBEAFE")

        self.btn_door_a = tk.Button(
            bar,
            text="🟢 入口二：從空白母體勾選積木、產生新 Script Excel",
            font=FONT_H2, fg="#0F172A", bg="#F8FAFC", relief="solid", bd=1,
            padx=16, pady=10, command=lambda: self._switch_mode("A")
        )
        self.btn_door_a.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        bind_hover(self.btn_door_a, "#F8FAFC", "#BBF7D0", lambda: self.current_mode == "A", "#DCFCE7")

    def _build_main_panels(self):
        self.container = tk.Frame(self, bg="#F8FAFC", padx=20, pady=4)
        self.container.pack(fill="both", expand=True)

        self.panel_b = tk.Frame(self.container, bg="#FFFFFF", relief="solid", bd=1, padx=18, pady=16)
        self._setup_panel_b()

        self.panel_a = tk.Frame(self.container, bg="#FFFFFF", relief="solid", bd=1, padx=18, pady=16)
        self._setup_panel_a()

    def _switch_mode(self, mode):
        self.current_mode = mode
        if mode == "B":
            self.panel_a.pack_forget()
            self.panel_b.pack(fill="both", expand=True)
            self.btn_door_b.configure(bg="#DBEAFE")
            self.btn_door_a.configure(bg="#F8FAFC")
        else:
            self.panel_b.pack_forget()
            self.panel_a.pack(fill="both", expand=True)
            self.btn_door_a.configure(bg="#DCFCE7")
            self.btn_door_b.configure(bg="#F8FAFC")

    # =========================================================================
    # Panel B: 現有 Excel 健康檢查與無負擔修復（精簡為 2 步：1.選檔自動體檢 -> 2.一鍵匯出）
    # =========================================================================
    def _setup_panel_b(self):
        top_row = tk.Frame(self.panel_b, bg="#F1F5F9", padx=14, pady=10, relief="solid", bd=1)
        top_row.pack(fill="x", pady=(0, 12))

        btn_pick = tk.Button(
            top_row, text="📂 第一步：點此選擇要檢查的 Excel 檔案（選完自動體檢）",
            font=FONT_BOLD, bg="#DBEAFE", fg="#1E3A8A",
            relief="solid", bd=1, padx=14, pady=6, command=self._browse_and_audit_excel
        )
        btn_pick.pack(side="left", padx=(0, 10))
        bind_hover(btn_pick, "#DBEAFE", "#BAE6FD")

        self.lbl_picked_file = tk.Label(
            top_row, text="尚未選擇檔案", font=FONT_MONO, bg="#F1F5F9", fg="#334155"
        )
        self.lbl_picked_file.pack(side="left", padx=4)

        btn_dry_fix = tk.Button(
            top_row, text="🧪 匯出『無硬體試跑版』(Skip 硬體列)", font=FONT_BOLD,
            bg="#E0E7FF", fg="#1E1B4B", relief="solid", bd=1, padx=12, pady=6,
            command=lambda: self._export_repaired_package(dry_run=True)
        )
        btn_dry_fix.pack(side="right", padx=(6, 0))
        bind_hover(btn_dry_fix, "#E0E7FF", "#C7D2FE")

        btn_export_fix = tk.Button(
            top_row, text="💾 第二步：一鍵修好並彈出輸出視窗 (.xlsx + 雙 INI)", font=FONT_BOLD,
            bg="#DCFCE7", fg="#14532D", relief="solid", bd=1, padx=14, pady=6,
            command=lambda: self._export_repaired_package(dry_run=False)
        )
        btn_export_fix.pack(side="right", padx=4)
        bind_hover(btn_export_fix, "#DCFCE7", "#BBF7D0")

        # 狀態摘要列
        self.lbl_audit_summary = tk.Label(
            self.panel_b,
            text="👉 操作說明：請先點擊左上角「📂 第一步：點此選擇要檢查的 Excel 檔案」，系統會立刻列出所有錯誤並幫您準備好修復方案。",
            font=FONT_BOLD, bg="#FEF08A", fg="#7F1D1D", anchor="w", justify="left", padx=12, pady=8, relief="solid", bd=1
        )
        self.lbl_audit_summary.pack(fill="x", pady=(0, 10))

        # 可捲動的點選題與完整錯誤明細區域
        canvas_frame = tk.Frame(self.panel_b, bg="#FFFFFF")
        canvas_frame.pack(fill="both", expand=True)

        self.canvas_b = tk.Canvas(canvas_frame, bg="#FFFFFF", highlightthickness=0)
        sb_b = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas_b.yview)
        self.scroll_inner_b = tk.Frame(self.canvas_b, bg="#FFFFFF")

        self.scroll_inner_b.bind(
            "<Configure>",
            lambda _e: self.canvas_b.configure(scrollregion=self.canvas_b.bbox("all"))
        )
        self.canvas_b.create_window((0, 0), window=self.scroll_inner_b, anchor="nw", width=1140)
        self.canvas_b.configure(yscrollcommand=sb_b.set)

        self.canvas_b.pack(side="left", fill="both", expand=True)
        sb_b.pack(side="right", fill="y")

    def _browse_and_audit_excel(self):
        config_path = os.path.join(BASE_DIR, "config.json")
        init_dir = PROJECT_ROOT
        try:
            if os.path.exists(config_path):
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    saved_dir = json.load(f).get("last_dir", "")
                    if saved_dir and os.path.exists(saved_dir):
                        init_dir = saved_dir
        except Exception:
            pass

        p = filedialog.askopenfilename(
            title="選擇要檢查與修復的 Centimani Excel 腳本",
            initialdir=init_dir,
            filetypes=[("Excel Files", "*.xlsx *.XLSX")]
        )
        if not p:
            return

        try:
            import json
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"last_dir": os.path.dirname(os.path.abspath(p))}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        self.loaded_file_path = p
        self.lbl_picked_file.configure(text=os.path.basename(p))
        self.loaded_workspace = import_excel_to_workspace(p)
        self.loaded_report = audit_workspace(self.loaded_workspace)
        self.user_choices = {}
        for c in self.loaded_report.get("choice_cards", []):
            self.user_choices[c["card_id"]] = tk.StringVar(value=c["recommended_value"])

        self._render_audit_cards(p)

    def _render_audit_cards(self, path):
        for w in self.scroll_inner_b.winfo_children():
            w.destroy()

        rep = self.loaded_report
        cards = rep.get("choice_cards", [])
        errors = rep.get("errors", [])
        warnings = rep.get("warnings", [])
        fname = os.path.basename(path)
        st_names = ", ".join(self.loaded_workspace.get("stations", {}).keys())

        self.lbl_audit_summary.configure(
            text=(
                f"📄 已載入：{fname} （測試站分頁：{st_names}）\n"
                f"🔍 檢查結果：共抓出 {len(errors)} 個錯誤、{len(warnings)} 個警告。"
                f"👉 接下來怎麼做？直接點擊右上角綠色「💾 第二步：一鍵修好並彈出輸出視窗」，系統就會把下方列出的問題全部修好並產出新檔！"
            )
        )

        # 區塊 1：若有需要點選確認的步號越界題
        if cards:
            tk.Label(
                self.scroll_inner_b,
                text=f"🎯 一、步號越界 / 重複借鎖確認題（共 {len(cards)} 題，系統已預設幫您勾好【智慧推薦答案】，可不改直接點右上角綠色按鈕存檔）：",
                font=FONT_H2, bg="#FFFFFF", fg="#0F172A"
            ).pack(anchor="w", pady=(4, 6))

            for idx, c in enumerate(cards, start=1):
                card_fr = tk.Frame(self.scroll_inner_b, bg="#FFFBEB", relief="solid", bd=1, padx=14, pady=10)
                card_fr.pack(fill="x", pady=5)

                tk.Label(
                    card_fr,
                    text=f"題目 {idx}：{c['issue_title']}",
                    font=FONT_BOLD, bg="#FFFBEB", fg="#78350F"
                ).pack(anchor="w")

                tk.Label(
                    card_fr,
                    text=f"指令：{c['send_cmd']}   |   說明：{c['description']}   |   原填寫 ExecMode：{c['current_value']}",
                    font=FONT_MONO, bg="#F4F5F7", fg="#0F172A", padx=8, pady=4
                ).pack(fill="x", pady=4)

                var = self.user_choices[c["card_id"]]
                for opt in c["options"]:
                    rb = tk.Radiobutton(
                        card_fr,
                        text=opt["label"],
                        variable=var,
                        value=opt["value"],
                        font=FONT_BODY,
                        bg="#FFFFFF",
                        fg="#0F172A",
                        selectcolor="#DCFCE7",
                        anchor="w",
                        padx=8, pady=3,
                        relief="solid", bd=1
                    )
                    rb.pack(fill="x", pady=2)
                    bind_hover(rb, "#FFFFFF", "#E0F2FE", lambda v=var, val=opt["value"]: v.get() == val, "#DCFCE7")

        # 區塊 2：把抓到的每一筆 Error 與 Warning 清楚列出來，告訴使用者為什麼錯、系統會怎麼自動修！
        list_box = tk.Frame(self.scroll_inner_b, bg="#F8FAFC", relief="solid", bd=1, padx=14, pady=12)
        list_box.pack(fill="x", pady=8)

        tk.Label(
            list_box,
            text=f"🛠️ 二、系統抓到的問題清單與自動修復預覽（共 {len(errors)} 個錯誤、{len(warnings)} 個警告 — 按右上角綠色按鈕即全數自動修補）：",
            font=FONT_H2, bg="#F8FAFC", fg="#0F172A"
        ).pack(anchor="w", pady=(0, 8))

        if not errors and not warnings:
            tk.Label(
                list_box,
                text="🎉 恭喜！此檔案未發現任何邏輯錯誤或警告。",
                font=FONT_BOLD, bg="#F8FAFC", fg="#166534"
            ).pack(anchor="w")
        else:
            for e_idx, err_msg in enumerate(errors[:40], start=1):
                tk.Label(
                    list_box,
                    text=f"  ❌ [錯誤 {e_idx}] {err_msg}",
                    font=FONT_BODY, bg="#F8FAFC", fg="#991B1B", anchor="w", justify="left"
                ).pack(fill="x", pady=1)
            if len(errors) > 40:
                tk.Label(
                    list_box,
                    text=f"  ... 其餘 {len(errors) - 40} 筆錯誤亦將一併自動修復",
                    font=FONT_BOLD, bg="#F8FAFC", fg="#991B1B", anchor="w"
                ).pack(fill="x", pady=2)

            for w_idx, warn_msg in enumerate(warnings[:30], start=1):
                tk.Label(
                    list_box,
                    text=f"  ⚠️ [警告 {w_idx}] {warn_msg}",
                    font=FONT_BODY, bg="#F8FAFC", fg="#92400E", anchor="w", justify="left"
                ).pack(fill="x", pady=1)
            if len(warnings) > 30:
                tk.Label(
                    list_box,
                    text=f"  ... 其餘 {len(warnings) - 30} 筆警告亦將一併自動處理",
                    font=FONT_BOLD, bg="#F8FAFC", fg="#92400E", anchor="w"
                ).pack(fill="x", pady=2)

    def _export_repaired_package(self, dry_run=False):
        if not self.loaded_workspace:
            messagebox.showinfo("提示", "請先點擊左上角「📂 第一步：點此選擇要檢查的 Excel 檔案」！")
            return

        ws_to_export = copy.deepcopy(self.loaded_workspace)
        choices_dict = {k: v.get() for k, v in self.user_choices.items()}
        fixed_logs = auto_fix_workspace(ws_to_export, user_choices=choices_dict)

        src = self.loaded_file_path or self.loaded_workspace.get("source_file", "")
        if src and os.path.exists(src):
            orig_dir = os.path.dirname(os.path.abspath(src))
            base_name = os.path.splitext(os.path.basename(src))[0]
            for sfx in ["_Fixed", "_FIXED", "_DryRun"]:
                base_name = base_name.replace(sfx, "")
            xlsx_filename = f"{base_name}_DryRun.xlsx" if dry_run else f"{base_name}_FIXED.xlsx"
            target_dir = orig_dir
        else:
            base_name = "Repaired_Script"
            xlsx_filename = f"{base_name}_DryRun.xlsx" if dry_run else f"{base_name}_FIXED.xlsx"
            target_dir = os.path.join(OUTPUT_ROOT, f"{base_name}_修訂版", "System")
            os.makedirs(target_dir, exist_ok=True)

        out_xlsx = os.path.join(target_dir, xlsx_filename)
        export_workspace_to_excel(ws_to_export, out_xlsx)
        sys_ini, glb_ini = sync_and_generate_inis(ws_to_export, xlsx_filename, target_dir)
        chk = generate_official_checksum(out_xlsx, sys_ini)
        rep_after = audit_workspace(ws_to_export)

        open_folder_and_highlight(target_dir)

        mode_title = "無硬體辦公桌試跑版 (Dry-Run)" if dry_run else "正式修復版"
        messagebox.showinfo(
            f"{mode_title} 打包完成",
            f"已完成【{mode_title}】並自動彈出輸出資料夾！\n\n"
            f"📂 輸出資料夾：\n{target_dir}\n\n"
            f"📄 內含標準 4 檔案：\n"
            f"1. {xlsx_filename} （修改處已標亮黃底色與註解）\n"
            f"2. System.ini (已自動計算並寫入 64 碼 Checksum)\n"
            f"3. Global.ini\n"
            f"4. Test Item Code V2.04_20250310.xlsx\n\n"
            f"📊 共自動修補 {len(fixed_logs)} 項問題，修復後剩餘 Error 數：{rep_after['error_count']}"
        )

    # =========================================================================
    # Panel A: 從空白母體勾選積木、產生新 Script Excel（含無硬體試跑版按鈕）
    # =========================================================================
    def _setup_panel_a(self):
        top_row = tk.Frame(self.panel_a, bg="#F1F5F9", padx=12, pady=10, relief="solid", bd=1)
        top_row.pack(fill="x", pady=(0, 12))

        tk.Label(top_row, text="專案名稱：", font=FONT_BOLD, bg="#F1F5F9").pack(side="left")
        self.ent_proj = tk.Entry(top_row, font=FONT_MONO, width=14)
        self.ent_proj.insert(0, "PEGA_NEW")
        self.ent_proj.pack(side="left", padx=(4, 12))

        tk.Label(top_row, text="站別 (Station)：", font=FONT_BOLD, bg="#F1F5F9").pack(side="left")
        self.ent_station = tk.Entry(top_row, font=FONT_MONO, width=8)
        self.ent_station.insert(0, "MB")
        self.ent_station.pack(side="left", padx=(4, 12))

        tk.Label(top_row, text="多工連板模式：", font=FONT_BOLD, bg="#F1F5F9").pack(side="left")
        self.cmb_dut_count = ttk.Combobox(
            top_row,
            values=[
                "1 (單板測試 LOAD_1=true)",
                "2 (一對二雙板同步多工 LOAD_1~2=true)",
                "4 (一對四連板同步多工 LOAD_1~4=true)"
            ],
            width=30, font=FONT_BODY, state="readonly"
        )
        self.cmb_dut_count.current(2)
        self.cmb_dut_count.pack(side="left", padx=6)

        btn_dry_gen = tk.Button(
            top_row, text="🧪 產生『無硬體試跑版』", font=FONT_BOLD,
            bg="#E0E7FF", fg="#1E1B4B", relief="solid", bd=1, padx=12, pady=4,
            command=lambda: self._generate_new_mother_package(dry_run=True)
        )
        btn_dry_gen.pack(side="right", padx=(6, 0))
        bind_hover(btn_dry_gen, "#E0E7FF", "#C7D2FE")

        btn_gen = tk.Button(
            top_row, text="🚀 一鍵產生新 Excel 母體並彈出視窗", font=FONT_BOLD,
            bg="#DCFCE7", fg="#14532D", relief="solid", bd=1, padx=14, pady=4,
            command=lambda: self._generate_new_mother_package(dry_run=False)
        )
        btn_gen.pack(side="right", padx=4)
        bind_hover(btn_gen, "#DCFCE7", "#BBF7D0")

        tk.Label(
            self.panel_a,
            text="請勾選要組裝進空白母體的測試積木（產出後將自動建立專屬 System 資料夾並彈出視窗）：",
            font=FONT_H2, bg="#FFFFFF", fg="#0F172A"
        ).pack(anchor="w", pady=(0, 8))

        list_frame = tk.Frame(self.panel_a, bg="#FFFFFF")
        list_frame.pack(fill="both", expand=True)

        default_checked = {
            "BLK_PRETEST_ROUTE", "BLK_FIXTURE_ACTION", "BLK_VOLT_NI6008_BATCH",
            "BLK_UART_BOOT_FW", "BLK_MAC_WRITE_VERIFY", "BLK_PYTHON_BRIDGE", "BLK_PHASE97_TEARDOWN"
        }

        for idx, blk in enumerate(STANDARD_BLOCKS):
            bid = blk["block_id"]
            var = tk.BooleanVar(value=(bid in default_checked))
            self.block_vars[bid] = var

            r = idx // 2
            c = idx % 2
            cb = tk.Checkbutton(
                list_frame,
                text=f"{blk['name']}  ({len(blk['steps'])} 步) — {blk['description'][:38]}",
                variable=var,
                font=FONT_BODY,
                bg="#F8FAFC",
                fg="#0F172A",
                selectcolor="#DCFCE7",
                anchor="w",
                padx=10, pady=6,
                relief="solid", bd=1
            )
            cb.grid(row=r, column=c, sticky="ew", padx=6, pady=4)
            bind_hover(cb, "#F8FAFC", "#E0F2FE", lambda v=var: v.get(), "#F0FDF4")

        list_frame.columnconfigure(0, weight=1)
        list_frame.columnconfigure(1, weight=1)

    def _generate_new_mother_package(self, dry_run=False):
        proj = self.ent_proj.get().strip() or "PEGA_NEW"
        st = self.ent_station.get().strip() or "MB"
        dut_str = self.cmb_dut_count.get()
        dut_count = int(dut_str[0]) if dut_str and dut_str[0].isdigit() else 1

        ws = get_golden_mother(proj, st)
        for slot in range(1, 5):
            ws["global_ini"]["Settings"][f"LOAD_{slot}"] = "true" if slot <= dut_count else "false"

        steps = []
        for blk in STANDARD_BLOCKS:
            bid = blk["block_id"]
            if self.block_vars.get(bid) and self.block_vars[bid].get():
                for k, v in blk.get("required_globals", {}).get("Settings", {}).items():
                    ws["global_ini"]["Settings"][k] = v
                for k, v in blk.get("required_globals", {}).get("Scripts", {}).items():
                    ws["global_ini"]["Scripts"][k] = v
                for st_row in blk.get("steps", []):
                    steps.append(dict(st_row))

        ws["stations"] = {st: steps}
        auto_fix_workspace(ws)

        if dry_run:
            ws = convert_workspace_to_dry_run(ws)
            xlsx_filename = f"{proj}_TestFlow_{st}_DryRun.xlsx"
            folder_label = f"{proj}_{st}_無硬體試跑版"
        else:
            xlsx_filename = f"{proj}_TestFlow_{st}.xlsx"
            folder_label = f"{proj}_{st}"

        clean_proj_dir = os.path.join(OUTPUT_ROOT, folder_label, "System")
        os.makedirs(clean_proj_dir, exist_ok=True)
        for old_f in os.listdir(clean_proj_dir):
            try:
                os.remove(os.path.join(clean_proj_dir, old_f))
            except Exception:
                pass

        out_xlsx = os.path.join(clean_proj_dir, xlsx_filename)
        export_workspace_to_excel(ws, out_xlsx)
        sync_and_generate_inis(ws, xlsx_filename, clean_proj_dir)

        open_folder_and_highlight(clean_proj_dir)

        mode_title = "無硬體辦公桌試跑版 (Dry-Run)" if dry_run else "正式新腳本母體"
        messagebox.showinfo(
            f"{mode_title} 產出完成",
            f"已成功產出【{mode_title}】並自動彈出資料夾視窗！\n\n"
            f"📂 專屬乾淨目錄：\n{clean_proj_dir}\n\n"
            f"📄 內含標準 4 檔案（可直接放入 Centimani_1.5.3_FINAL\\System\\）：\n"
            f"1. {xlsx_filename}\n"
            f"2. System.ini\n"
            f"3. Global.ini\n"
            f"4. Test Item Code V2.04_20250310.xlsx"
        )


if __name__ == "__main__":
    app = CentimaniDesktopApp()
    app.mainloop()
