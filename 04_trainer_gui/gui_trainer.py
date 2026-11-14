#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import messagebox, filedialog
import os
import subprocess
import threading
import time
import datetime
import queue
from pathlib import Path
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# =================================================================
# [ KLine-Trainer: KRONOS MODEL TRAINING TERMINAL ]
# GUI for running tokenizer and predictor finetuning in isolated env
# =================================================================

class TrainerMatrixGUI(ttk.Window):
    def __init__(self):
        super().__init__(themename="cyborg")
        self.title("Kronos Trainer · 脑机训练器终端")
        self.geometry("1100x860")
        self.minsize(1050, 800)
        
        try:
            self.createcommand('::tk::mac::ReopenApplication', self.deiconify)
        except Exception:
            pass
            
        # --- UI Colors & Styles (Flat Dark Gold) ---
        self.c_bg = "#080808"        
        self.c_panel = "#101010"     
        self.c_gold = "#F0B90B"      
        self.c_gold_dim = "#715A2B"  
        self.c_fg = "#E1C699"        
        self.c_green = "#00D47C"     
        self.c_red = "#FF3B30"       
        
        self.font_title = ("Menlo", 32, "bold")
        self.font_base = ("Menlo", 14)
        self.font_base_lg = ("Menlo", 16)
        self.font_log = ("Menlo", 13)

        # --- Paths & State ---
        self.root_dir = Path(__file__).resolve().parent  # 4-Kronos-Trainer-GUI
        self.suite_dir = self.root_dir.parent
        self.trainer_base_dir = self.suite_dir / "4-Kronos-Trainer-Base"
        self.venv_python = self.trainer_base_dir / "venv" / "bin" / "python"
        
        self.data_var = tk.StringVar(value=str(self.suite_dir / "3-KLine-Slicer" / "gui_out_slices"))
        self.target_pkl_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value="tokenizer") # 'tokenizer' or 'predictor'
        
        self.process = None
        self.log_queue = queue.Queue()
        self.stop_requested = False
        
        self._setup_styles()
        self._build_ui()
        self.after(100, self._process_log_queue)

    def _setup_styles(self):
        style = ttk.Style()
        style.configure(".", font=self.font_base, background=self.c_bg, foreground=self.c_fg)
        
        style.configure("FlatGold.TButton", font=self.font_base_lg, background=self.c_bg, foreground=self.c_gold, bordercolor=self.c_gold, borderwidth=1)
        style.map("FlatGold.TButton", background=[("active", "#1A140B")], foreground=[("active", "#FFD700")])
        style.configure("FlatRed.TButton", font=self.font_base_lg, background=self.c_bg, foreground=self.c_red, bordercolor=self.c_red, borderwidth=1)
        style.map("FlatRed.TButton", background=[("active", "#1A0505")])
        style.configure("Hidden.Vertical.TScrollbar", background=self.c_gold_dim, troughcolor=self.c_bg, bordercolor=self.c_bg, relief="flat")
        style.map("Hidden.Vertical.TScrollbar", background=[("active", self.c_gold)])
        
        style.configure("TRadiobutton", background=self.c_bg, foreground=self.c_fg, font=self.font_base)
        style.map("TRadiobutton", foreground=[("selected", self.c_gold)])

    def _build_ui(self):
        self.configure(bg=self.c_bg)
        self.lift()
        self.attributes('-topmost', True)
        self.after(500, lambda: self.attributes('-topmost', False))
        os.system('''osascript -e 'tell application "System Events" to set frontmost of the first process whose unix id is %d to true' ''' % os.getpid())

        # --- HEADER ---
        header_frame = tk.Frame(self, bg=self.c_bg, pady=15)
        header_frame.pack(fill=X, padx=20)
        tk.Label(header_frame, text="KRONOS TRAINER · 脑机训练器", font=self.font_title, fg=self.c_gold, bg=self.c_bg).pack(side=LEFT)
        self.status_sign = tk.Label(header_frame, text="系统就绪", font=("Menlo", 16, "bold"), fg=self.c_gold_dim, bg=self.c_bg)
        self.status_sign.pack(side=RIGHT, anchor=S)

        body_frame = tk.Frame(self, bg=self.c_bg)
        body_frame.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        
        # --- LEFT PANEL: CONTROLS ---
        left_panel = tk.Frame(body_frame, width=450, bg=self.c_bg)
        left_panel.pack(side=LEFT, fill=Y, padx=(0, 20))
        left_panel.pack_propagate(False)
        
        # 1. Mounts
        mount_lf = DashFrame(left_panel, title=" 训练数据挂载 MOUNTS ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        mount_lf.pack(fill=X, pady=(0, 15))
        
        tk.Label(mount_lf.content, text="选择巨型字典 (.pkl):", font=self.font_base, fg=self.c_fg, bg=self.c_bg).pack(anchor=W)
        src_fr = tk.Frame(mount_lf.content, bg=self.c_bg)
        src_fr.pack(fill=X, pady=(2, 10))
        tk.Entry(src_fr, textvariable=self.target_pkl_var, font=self.font_log, bg=self.c_panel, fg=self.c_gold, relief="flat", highlightthickness=1, highlightbackground=self.c_gold_dim).pack(side=LEFT, fill=X, expand=True)
        ttk.Button(src_fr, text="打开", style="FlatGold.TButton", command=self.on_browse_pkl).pack(side=RIGHT, padx=(5,0))
        
        # 2. Training Mode
        mode_lf = DashFrame(left_panel, title=" 训练模式 MODE ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        mode_lf.pack(fill=X, pady=(0, 15))
        
        ttk.Radiobutton(mode_lf.content, text="1. Tokenizer 基础词表训练 (压缩表述)", variable=self.mode_var, value="tokenizer", style="TRadiobutton").pack(anchor=W, pady=5)
        ttk.Radiobutton(mode_lf.content, text="2. Predictor 核心脑区训练 (时间序列推断)", variable=self.mode_var, value="predictor", style="TRadiobutton").pack(anchor=W, pady=5)
        
        tk.Label(mode_lf.content, text="* 注意：必须先完成 Tokenizer 训练，\n才能使用训练好的 Tokenizer 进行 Predictor 训练。", font=("Menlo", 12), fg=self.c_gold_dim, bg=self.c_bg, justify=LEFT).pack(anchor=W, pady=(10, 0))

        # 3. Action Controls
        ctrl_lf = DashFrame(left_panel, title=" 操作面板 ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        ctrl_lf.pack(fill=X, pady=(0, 15))

        self.start_btn = ttk.Button(ctrl_lf.content, text="🚀 启动环境隔离训练 (Start)", style="FlatGold.TButton", command=self.on_start_click)
        self.start_btn.pack(fill=X, pady=(5, 10), ipady=5)
        
        self.stop_btn = ttk.Button(ctrl_lf.content, text="🛑 强制阻断进程 (Kill)", style="FlatRed.TButton", command=self.on_stop, state=DISABLED)
        self.stop_btn.pack(fill=X, pady=(0, 5), ipady=5)
        
        # 4. Model outputs info
        out_lf = DashFrame(left_panel, title=" 模型产出 CHECKPOINTS ", bg_color=self.c_bg, fg_color=self.c_green, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        out_lf.pack(fill=BOTH, expand=True)
        
        tk.Label(out_lf.content, text="模型保存路径:", font=self.font_base, fg=self.c_fg, bg=self.c_bg).pack(anchor=W)
        tk.Label(out_lf.content, text=str(self.trainer_base_dir / "models"), font=("Menlo", 12), fg=self.c_gold, bg=self.c_bg, wraplength=400, justify=LEFT).pack(anchor=W, pady=(2, 10))
        
        ttk.Button(out_lf.content, text="一键直达模型目录", style="FlatGold.TButton", command=lambda: os.system(f'open "{self.trainer_base_dir / "models"}"')).pack(fill=X, pady=5)

        # --- RIGHT PANEL ---
        right_panel = tk.Frame(body_frame, bg=self.c_bg)
        right_panel.pack(side=LEFT, fill=BOTH, expand=True)
        
        term_lf = DashFrame(right_panel, title=" 隔离环境流式看板 (Isolated Terminal VENV) ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        term_lf.pack(fill=BOTH, expand=True)
        
        txt_frame = tk.Frame(term_lf.content, bg=self.c_panel)
        txt_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.log_widget = tk.Text(txt_frame, font=self.font_log, bg=self.c_panel, fg="#A0A0A0", insertbackground=self.c_fg, wrap=WORD, borderwidth=0, highlightthickness=0, spacing1=4, spacing3=4)
        txt_scroll = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL, command=self.log_widget.yview, style="Hidden.Vertical.TScrollbar")
        self.log_widget.configure(yscrollcommand=txt_scroll.set)
        
        txt_scroll.pack(side=RIGHT, fill=Y)
        self.log_widget.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Colors for terminal
        self.log_widget.tag_config("sys", foreground=self.c_gold, font=("Menlo", 13, "bold"))
        self.log_widget.tag_config("err", foreground=self.c_red, font=("Menlo", 13, "bold"))
        self.log_widget.tag_config("succ", foreground=self.c_green, font=("Menlo", 13, "bold"))
        self.log_widget.tag_config("epoch", foreground="#00BFFF", font=("Menlo", 13, "bold"))
        self.log_widget.tag_config("loss", foreground="#F08080")
        self.log_widget.configure(state=DISABLED)

        # Footer
        self.status_bar = tk.Label(self, text=f"环境挂载点: {self.venv_python}", bg=self.c_bg, fg=self.c_gold_dim, font=("Menlo", 11))
        self.status_bar.pack(side=BOTTOM, anchor=W, padx=20, pady=(0, 5))

    def gui_log(self, msg, level="info"):
        self.log_queue.put((msg, level))

    def _process_log_queue(self):
        try:
            while True:
                msg, level = self.log_queue.get_nowait()
                self.log_widget.configure(state=NORMAL)
                
                # Basic parsing for coloring
                if "--- Epoch" in msg: level = "epoch"
                elif "Loss:" in msg: level = "loss"
                elif "保存" in msg or "完成" in msg: level = "succ"
                elif "错误" in msg or "Error" in msg or "Traceback" in msg: level = "err"
                
                self.log_widget.insert(END, msg + "\n", level)
                self.log_widget.see(END)
                self.log_widget.configure(state=DISABLED)
        except queue.Empty:
            pass
        self.after(100, self._process_log_queue)

    def on_browse_pkl(self):
        # Ensure we pass a clear, absolute string path for macOS finder
        init_dir = str(self.suite_dir / "3-KLine-Slicer" / "gui_out_slices")
        f = filedialog.askopenfilename(initialdir=init_dir, filetypes=[("Pickle Dict", "*.pkl")])
        if f:
            self.target_pkl_var.set(f)

    def on_start_click(self):
        pkl_path = self.target_pkl_var.get().strip()
        if not pkl_path or not os.path.exists(pkl_path):
            messagebox.showerror("错误", "请先选择合法的 .pkl 巨型字典文件！")
            return
            
        if not self.venv_python.exists():
            messagebox.showerror("环境异常", f"找不到隔离环境的 Python 解释器:\n{self.venv_python}")
            return
            
        mode = self.mode_var.get()
        script_name = "train_tokenizer_local.py" if mode == "tokenizer" else "train_predictor_local.py"
        script_path = self.trainer_base_dir / script_name
        
        if not script_path.exists():
            messagebox.showerror("错误", f"找不到底座训练脚本:\n{script_path}")
            return
            
        self.stop_requested = False
        self.start_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.status_sign.config(text="🔥 训练中...", fg=self.c_red)
        
        # Clear log
        self.log_widget.configure(state=NORMAL)
        self.log_widget.delete('1.0', END)
        self.log_widget.configure(state=DISABLED)
        
        self.gui_log(f"[*] 启动完全隔离训练环境 (Mode: {mode.upper()})...", "sys")
        self.gui_log(f"[*] Interpreter: {self.venv_python}", "info")
        self.gui_log(f"[*] Target PKL: {pkl_path}", "info")
        self.gui_log("--------------------------------------------------\n", "sys")
        
        threading.Thread(target=self._run_training_process, args=(script_path, pkl_path), daemon=True).start()

    def _run_training_process(self, script_path, pkl_path):
        env = os.environ.copy()
        env["HF_ENDPOINT"] = "https://hf-mirror.com"
        
        try:
            # Added -u flag to force python to use unbuffered standard output and standard error
            self.process = subprocess.Popen(
                [str(self.venv_python), "-u", str(script_path), pkl_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(self.trainer_base_dir),
                env=env
            )
            
            for line in iter(self.process.stdout.readline, ''):
                if self.stop_requested:
                    break
                self.gui_log(line.rstrip())
                
            self.process.stdout.close()
            return_code = self.process.wait()
            
            if self.stop_requested:
                self.gui_log("\n[!] 进程已被用户强制阻断。", "warn")
                self.after(0, lambda: self.status_sign.config(text="阻断", fg=self.c_gold_dim))
            elif return_code == 0:
                self.gui_log("\n[+] 训练流水线安全退出，任务成功！", "succ")
                self.after(0, lambda: self.status_sign.config(text="训练完成", fg=self.c_green))
            else:
                self.gui_log(f"\n[-] 训练进程异常退出 (Code: {return_code})", "err")
                self.after(0, lambda: self.status_sign.config(text="异常终止", fg=self.c_red))
                
        except Exception as e:
            self.gui_log(f"[-] 环境启动失败: {e}", "err")
            self.after(0, lambda: self.status_sign.config(text="环境错误", fg=self.c_red))
            
        # Reset buttons in main thread
        self.after(0, self._reset_buttons)

    def _reset_buttons(self):
        self.start_btn.config(state=NORMAL)
        self.stop_btn.config(state=DISABLED)
        self.process = None

    def on_stop(self):
        if self.process:
            self.stop_requested = True
            self.gui_log("\n[!] 正在发送中断信号 (SIGINT)...", "err")
            try:
                # Send interrupt to the process group if possible, or just terminate
                self.process.terminate()
            except Exception as e:
                self.gui_log(f"[-] 无法安全中断进程: {e}", "err")

class DashFrame(tk.Frame):
    def __init__(self, master, title, bg_color, fg_color, dash_color, font, **kwargs):
        super().__init__(master, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self.dash_color = dash_color
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.content = tk.Frame(self, bg=bg_color)
        self.content.pack(fill=BOTH, expand=True, padx=12, pady=(25, 12)) 
        self.bind("<Configure>", self._draw)
        self.title_text = title
        self.fg_color = fg_color
        self.font = font
    def _draw(self, event=None):
        self.canvas.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10: return
        self.canvas.create_rectangle(2, 10, w-2, h-2, outline=self.dash_color, dash=(5, 5))
        self.canvas.create_rectangle(15, 0, 15 + len(self.title_text)*10, 20, fill=self.bg_color, outline="")
        self.canvas.create_text(20, 10, text=self.title_text, anchor="nw", font=self.font, fill=self.fg_color)

if __name__ == "__main__":
    try:
        app = TrainerMatrixGUI()
        app.mainloop()
    except Exception as e:
        print(f"\n[致命错误] GUI启动失败:")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出 (Wait for input)...")
