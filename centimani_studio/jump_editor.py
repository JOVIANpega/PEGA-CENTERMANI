# -*- coding: utf-8 -*-
"""
Title 區塊跳轉編輯器 (Pop-up Toplevel)
提供「選取起點 -> 打勾指定 PASS 跳這 / FAIL 跳這 / 失敗重回這」的視覺化設定，
自動換算 0-based 相對步號 (2:XX 與 4:P,F) 並寫入 _modified_cells 供匯出時反白標記。
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.script_doctor import _build_title_blocks

FONT_H2 = ("Microsoft JhengHei UI", 11, "bold")
FONT_BODY = ("Microsoft JhengHei UI Light", 10)
FONT_BOLD = ("Microsoft JhengHei UI", 10, "bold")
FONT_MONO = ("Consolas", 10)


def _bind_hover(widget, normal_bg, hover_bg):
    widget.configure(cursor="hand2", bg=normal_bg)
    widget.bind("<Enter>", lambda _e: widget.configure(bg=hover_bg))
    widget.bind("<Leave>", lambda _e: widget.configure(bg=normal_bg))


class JumpEditorDialog(tk.Toplevel):
    """彈出式 Title 區塊跳轉設定視窗。"""

    def __init__(self, parent, workspace, on_done_callback=None):
        super().__init__(parent)
        self.title("Title 區塊跳轉編輯器（打勾設定 PASS / FAIL / 重試點）")
        self.geometry("1120x700")
        self.configure(bg="#F8FAFC")
        self.transient(parent)
        self.grab_set()

        self.workspace = workspace
        self.on_done_callback = on_done_callback

        self.all_sheets = {}
        self.all_sheets.update(self.workspace.get("stations", {}))
        self.all_sheets.update(self.workspace.get("marcos", {}))
        self.sheet_names = list(self.all_sheets.keys())
        if not self.sheet_names:
            messagebox.showinfo("提示", "目前工作區沒有任何測試站工作表。", parent=self)
            self.destroy()
            return

        self.var_sheet = tk.StringVar(value=self.sheet_names[0])
        self.var_block = tk.StringVar()
        self.var_retry_cnt = tk.StringVar(value="0")
        self.var_src_offset = tk.IntVar(value=0)

        self.blocks = []
        self.current_block = None
        self.pass_target_off = None
        self.fail_target_off = None
        self.row_widgets = []

        self._build_ui()
        self._on_sheet_changed()

    def _build_ui(self):
        # Top filter bar
        top = tk.Frame(self, bg="#EFF6FF", padx=14, pady=10, relief="solid", bd=1)
        top.pack(fill="x", padx=12, pady=(12, 8))

        tk.Label(top, text="工作表：", font=FONT_BOLD, bg="#EFF6FF", fg="#1E3A8A").pack(side="left")
        self.cmb_sheet = ttk.Combobox(
            top, textvariable=self.var_sheet, values=self.sheet_names, state="readonly", width=18, font=FONT_MONO
        )
        self.cmb_sheet.pack(side="left", padx=(4, 14))
        self.cmb_sheet.bind("<<ComboboxSelected>>", lambda _e: self._on_sheet_changed())

        tk.Label(top, text="Title 區塊：", font=FONT_BOLD, bg="#EFF6FF", fg="#1E3A8A").pack(side="left")
        self.cmb_block = ttk.Combobox(
            top, textvariable=self.var_block, state="readonly", width=42, font=FONT_BODY
        )
        self.cmb_block.pack(side="left", padx=(4, 14))
        self.cmb_block.bind("<<ComboboxSelected>>", lambda _e: self._on_block_changed())

        tk.Label(top, text="Title RetryCount：", font=FONT_BOLD, bg="#EFF6FF", fg="#1E3A8A").pack(side="left")
        ent_retry = tk.Entry(top, textvariable=self.var_retry_cnt, width=5, font=FONT_MONO, justify="center")
        ent_retry.pack(side="left", padx=(4, 6))

        btn_save_retry = tk.Button(
            top, text="更新次數", font=FONT_BOLD, fg="#1E3A8A", relief="solid", bd=1, padx=8, pady=2,
            command=self._save_retry_count
        )
        btn_save_retry.pack(side="left")
        _bind_hover(btn_save_retry, "#DBEAFE", "#BAE6FD")

        # Hint bar
        hint = tk.Label(
            self,
            text="操作方式：① 點選左側『起點』→ ② 在目標列勾選『PASS 跳這』或『FAIL 跳這』"
                 "（勾在起點下方產生 4:P,F；FAIL 勾在起點上方或自己產生 2:XX / 1）→ ③ 點擊『套用此步跳轉』。",
            font=FONT_BODY, bg="#FEF08A", fg="#7F1D1D", anchor="w", padx=12, pady=6, relief="solid", bd=1
        )
        hint.pack(fill="x", padx=12, pady=(0, 8))

        # Table Header
        hdr = tk.Frame(self, bg="#1E293B", padx=10, pady=6)
        hdr.pack(fill="x", padx=12)
        cols = [
            ("起點", 6), ("步號 / 列", 11), ("Send 指令", 34), ("Description 說明", 26),
            ("目前 ExecMode", 14), ("PASS 跳這", 11), ("FAIL 跳這", 11)
        ]
        for txt, w in cols:
            tk.Label(hdr, text=txt, width=w, font=FONT_BOLD, bg="#1E293B", fg="#FFFFFF", anchor="w").pack(side="left", padx=2)

        # Scrollable step rows
        list_wrap = tk.Frame(self, bg="#FFFFFF", relief="solid", bd=1)
        list_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.canvas = tk.Canvas(list_wrap, bg="#FFFFFF", highlightthickness=0)
        sb = ttk.Scrollbar(list_wrap, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg="#FFFFFF")
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw", width=1060)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Bottom preview & action bar
        bot = tk.Frame(self, bg="#F1F5F9", padx=14, pady=10, relief="solid", bd=1)
        bot.pack(fill="x", padx=12, pady=(0, 12))

        self.lbl_preview = tk.Label(
            bot, text="預覽：請選擇起點與跳轉目標", font=FONT_BOLD, bg="#F1F5F9", fg="#0F172A", anchor="w"
        )
        self.lbl_preview.pack(side="left", fill="x", expand=True)

        btn_done = tk.Button(
            bot, text="✔ 完成並重新體檢", font=FONT_BOLD, fg="#14532D",
            relief="solid", bd=1, padx=14, pady=6, command=self._finish_and_close
        )
        btn_done.pack(side="right", padx=(6, 0))
        _bind_hover(btn_done, "#DCFCE7", "#BBF7D0")

        btn_clear = tk.Button(
            bot, text="🧹 清除本步跳轉 (設為 0)", font=FONT_BOLD, fg="#334155",
            relief="solid", bd=1, padx=12, pady=6, command=self._clear_current_jump
        )
        btn_clear.pack(side="right", padx=6)
        _bind_hover(btn_clear, "#E2E8F0", "#CBD5E1")

        btn_apply = tk.Button(
            bot, text="✨ 套用此步跳轉", font=FONT_BOLD, fg="#1E3A8A",
            relief="solid", bd=1, padx=14, pady=6, command=self._apply_current_jump
        )
        btn_apply.pack(side="right", padx=6)
        _bind_hover(btn_apply, "#DBEAFE", "#BAE6FD")

    def _on_sheet_changed(self):
        st_name = self.var_sheet.get()
        steps = self.all_sheets.get(st_name, [])
        self.blocks = _build_title_blocks(steps)
        labels = [f"[{i + 1}] {b['title']} ({len(b['steps'])} 步)" for i, b in enumerate(self.blocks)]
        self.cmb_block["values"] = labels
        if labels:
            self.var_block.set(labels[0])
            self._on_block_changed()
        else:
            self.current_block = None
            self._render_rows()

    def _on_block_changed(self):
        idx = self.cmb_block.current()
        if idx < 0 or idx >= len(self.blocks):
            return
        self.current_block = self.blocks[idx]
        t_parts = [p.strip() for p in str(self.current_block.get("title", "")).split(",")]
        self.var_retry_cnt.set(t_parts[2] if len(t_parts) >= 3 and t_parts[2] else "0")
        self.var_src_offset.set(0)
        self._load_targets_from_source()
        self._render_rows()

    def _load_targets_from_source(self):
        self.pass_target_off = None
        self.fail_target_off = None
        if not self.current_block:
            return
        src_off = self.var_src_offset.get()
        b_steps = self.current_block["steps"]
        if src_off < 0 or src_off >= len(b_steps):
            return
        mode = str(b_steps[src_off]["step"].get("ExecMode", "")).strip()
        if mode.startswith("4:") and "," in mode:
            try:
                p_st, f_st = [int(x.strip()) for x in mode[2:].split(",", 1)]
                if 0 <= p_st < len(b_steps):
                    self.pass_target_off = p_st
                if 0 <= f_st < len(b_steps):
                    self.fail_target_off = f_st
            except ValueError:
                pass
        elif mode.startswith("2:") and ":" in mode:
            try:
                r_pt = int(mode.split(":", 1)[1].strip())
                if 0 <= r_pt <= src_off:
                    self.fail_target_off = r_pt
            except ValueError:
                pass
        elif mode == "1":
            self.fail_target_off = src_off

    def _on_select_source(self):
        self._load_targets_from_source()
        self._render_rows()

    def _toggle_pass(self, target_off, var):
        if var.get():
            src_off = self.var_src_offset.get()
            if target_off <= src_off:
                var.set(False)
                return
            self.pass_target_off = target_off
            if self.fail_target_off is not None and self.fail_target_off <= src_off:
                self.fail_target_off = None
        else:
            if self.pass_target_off == target_off:
                self.pass_target_off = None
        self._render_rows()

    def _toggle_fail(self, target_off, var):
        if var.get():
            src_off = self.var_src_offset.get()
            self.fail_target_off = target_off
            if target_off <= src_off:
                self.pass_target_off = None
        else:
            if self.fail_target_off == target_off:
                self.fail_target_off = None
        self._render_rows()

    def _compute_exec_mode(self):
        if not self.current_block:
            return None, "尚未選擇區塊"
        b_len = len(self.current_block["steps"])
        src_off = self.var_src_offset.get()
        p_off = self.pass_target_off
        f_off = self.fail_target_off

        if p_off is None and f_off is None:
            return None, "請勾選至少一個 PASS 或 FAIL 跳轉目標"

        # Retry mode (FAIL jumps back to <= src_off)
        if f_off is not None and f_off <= src_off and p_off is None:
            if f_off == src_off:
                return "1", f"單步原地重試 (ExecMode = 1)"
            return f"2:{f_off}", f"失敗重試跳回步號 {f_off} (ExecMode = 2:{f_off})"

        # Forward branch mode (4:P,F)
        default_next = min(src_off + 1, b_len - 1)
        final_p = p_off if (p_off is not None and p_off > src_off) else default_next
        final_f = f_off if (f_off is not None and f_off > src_off) else default_next
        if src_off >= b_len - 1:
            return None, "最後一步沒有後續步驟可供 4:P,F 往前跳轉"
        if final_p == final_f:
            return f"4:{final_p},{final_f}", f"無論 PASS/FAIL 皆跳至步號 {final_p} (4:{final_p},{final_f})"
        return f"4:{final_p},{final_f}", f"PASS 跳步號 {final_p}，FAIL 跳步號 {final_f} (4:{final_p},{final_f})"

    def _render_rows(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.row_widgets = []

        if not self.current_block:
            return

        src_off = self.var_src_offset.get()
        b_steps = self.current_block["steps"]

        for item in b_steps:
            off = item["offset"]
            r_num = item["row_num"]
            st = item["step"]
            s_send = str(st.get("Send", "")).strip()
            s_desc = str(st.get("Description", "")).strip()
            s_mode = str(st.get("ExecMode", "")).strip()

            is_src = (off == src_off)
            row_bg = "#DBEAFE" if is_src else ("#FFFFFF" if off % 2 == 0 else "#F8FAFC")

            rf = tk.Frame(self.inner, bg=row_bg, padx=8, pady=4, relief="flat")
            rf.pack(fill="x")

            rb = tk.Radiobutton(
                rf, variable=self.var_src_offset, value=off, bg=row_bg, activebackground=row_bg,
                cursor="hand2", command=self._on_select_source
            )
            rb.config(width=4)
            rb.pack(side="left", padx=2)

            tk.Label(
                rf, text=f"{off:02d} (列{r_num})", width=11, font=FONT_MONO, bg=row_bg, fg="#0F172A", anchor="w"
            ).pack(side="left", padx=2)
            tk.Label(
                rf, text=s_send[:32], width=34, font=FONT_MONO, bg=row_bg, fg="#1E293B", anchor="w"
            ).pack(side="left", padx=2)
            tk.Label(
                rf, text=s_desc[:24], width=26, font=FONT_BODY, bg=row_bg, fg="#475569", anchor="w"
            ).pack(side="left", padx=2)

            mode_fg = "#2563EB" if s_mode.startswith(("2:", "4:")) else "#334155"
            tk.Label(
                rf, text=s_mode or "(空)", width=14, font=FONT_MONO, bg=row_bg, fg=mode_fg, anchor="w"
            ).pack(side="left", padx=2)

            p_var = tk.BooleanVar(value=(self.pass_target_off == off))
            p_chk = tk.Checkbutton(
                rf, text="PASS", variable=p_var, bg=row_bg, activebackground=row_bg,
                font=FONT_BOLD, fg="#15803D", cursor="hand2" if off > src_off else "arrow",
                state="normal" if off > src_off else "disabled",
                command=lambda o=off, v=p_var: self._toggle_pass(o, v)
            )
            p_chk.config(width=9, anchor="w")
            p_chk.pack(side="left", padx=2)

            f_var = tk.BooleanVar(value=(self.fail_target_off == off))
            f_label = "FAIL" if off > src_off else ("重試本步" if off == src_off else "重回此步")
            f_chk = tk.Checkbutton(
                rf, text=f_label, variable=f_var, bg=row_bg, activebackground=row_bg,
                font=FONT_BOLD, fg="#B91C1C", cursor="hand2",
                command=lambda o=off, v=f_var: self._toggle_fail(o, v)
            )
            f_chk.config(width=10, anchor="w")
            f_chk.pack(side="left", padx=2)

        new_mode, msg = self._compute_exec_mode()
        src_send = str(b_steps[src_off]["step"].get("Send", "")).strip() if src_off < len(b_steps) else ""
        warn_txt = ""
        if ":ReleaseDevice" in src_send or ":Disconnect" in src_send:
            warn_txt = "  [注意：釋放資源指令建議維持 ExecMode=3]"
        elif src_send.startswith(":Sf"):
            warn_txt = "  [注意：SFIS 指令強制要求 ExecMode=8 或 9]"
        self.lbl_preview.configure(
            text=f"起點步號 {src_off:02d} ({src_send[:24]}) ➜ {msg}{warn_txt}",
            fg="#B91C1C" if warn_txt else "#0F172A"
        )

    def _record_modified_cell(self, st_name, row_num, col_name, old_val, new_val, note):
        mods = self.workspace.setdefault("_modified_cells", [])
        mods.append({
            "sheet": st_name, "row": row_num, "col_name": col_name,
            "old": old_val, "new": new_val, "note": note
        })

    def _save_retry_count(self):
        if not self.current_block:
            return
        val = self.var_retry_cnt.get().strip()
        if not val.isdigit():
            messagebox.showwarning("格式錯誤", "RetryCount 請輸入整數（例如 0 或 3）。", parent=self)
            return
        first_item = self.current_block["steps"][0]
        step = first_item["step"]
        old_title = str(step.get("Title", "")).strip()
        parts = [p.strip() for p in old_title.split(",")]
        while len(parts) < 2:
            parts.append("")
        if len(parts) == 2:
            parts.append(val)
        else:
            parts[2] = val
        new_title = ",".join(parts)
        step["Title"] = new_title
        self.current_block["title"] = new_title
        self._record_modified_cell(
            self.var_sheet.get(), first_item["row_num"], "Title", old_title, new_title,
            f"透過跳轉編輯器更新 RetryCount 為 {val}"
        )
        messagebox.showinfo("已更新", f"已將此 Title 的 RetryCount 更新為 {val}。", parent=self)

    def _apply_current_jump(self):
        new_mode, msg = self._compute_exec_mode()
        if not new_mode:
            messagebox.showwarning("無法套用", msg, parent=self)
            return
        src_off = self.var_src_offset.get()
        item = self.current_block["steps"][src_off]
        step = item["step"]
        old_mode = str(step.get("ExecMode", "")).strip()
        step["ExecMode"] = new_mode

        st_name = self.var_sheet.get()
        self._record_modified_cell(
            st_name, item["row_num"], "ExecMode", old_mode, new_mode,
            f"跳轉編輯器設定：{msg}"
        )

        # If using 2:XX / 1 and RetryCount is 0, suggest bumping RetryCount to 3
        if new_mode.startswith("2:") or new_mode == "1":
            if self.var_retry_cnt.get().strip() in ("", "0"):
                if messagebox.askyesno(
                    "補上 RetryCount",
                    "此步驟設為失敗重試，但目前 Title 的 RetryCount 為 0。\n是否一併將 RetryCount 設為 3？",
                    parent=self
                ):
                    self.var_retry_cnt.set("3")
                    self._save_retry_count()

        self._render_rows()

    def _clear_current_jump(self):
        if not self.current_block:
            return
        src_off = self.var_src_offset.get()
        item = self.current_block["steps"][src_off]
        step = item["step"]
        old_mode = str(step.get("ExecMode", "")).strip()
        step["ExecMode"] = "0"
        self.pass_target_off = None
        self.fail_target_off = None
        self._record_modified_cell(
            self.var_sheet.get(), item["row_num"], "ExecMode", old_mode, "0",
            "跳轉編輯器清除跳轉設定，恢復 ExecMode = 0"
        )
        self._render_rows()

    def _finish_and_close(self):
        if self.on_done_callback:
            self.on_done_callback()
        self.destroy()
