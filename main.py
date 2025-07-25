#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UIGF/SRGF 抽卡记录分离工具
主程序入口点，提供图形用户界面

by: 马乞
GitHub: https://github.com/maqibg/yunzai-uigf-splitter
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from file_processor import FileProcessor
from game_config import GameConfig
from github_integration import GitHubIntegration


class Tooltip:
    """创建Tkinter控件的工具提示"""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("tahoma", "8", "normal"),
        )
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None


class ApplicationUI:
    """负责构建和管理所有UI组件 (v1.1 两栏式布局)"""

    def __init__(self, root, app_logic):
        self.root = root
        self.logic = app_logic
        self._create_widgets()

    def _create_widgets(self):
        # --- 主框架 ---
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1, minsize=350)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=1)

        # --- 左侧控制栏 ---
        left_pane = ttk.Frame(main_frame, padding="10")
        left_pane.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        left_pane.columnconfigure(0, weight=1)

        # --- 右侧状态栏 ---
        right_pane = ttk.Frame(main_frame, padding="10")
        right_pane.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_pane.columnconfigure(0, weight=1)
        right_pane.rowconfigure(1, weight=1)

        # --- 填充左侧控制栏 ---
        self._create_control_widgets(left_pane)

        # --- 填充右侧状态栏 ---
        self._create_status_widgets(right_pane)

        # --- 底部信息栏 ---
        self._create_bottom_bar(main_frame)

    def _create_control_widgets(self, parent):
        """创建左侧的所有控制组件"""
        current_row = 0

        # 功能选择
        func_frame = ttk.LabelFrame(parent, text="1. 功能选择", padding="10")
        func_frame.grid(row=current_row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        func_frame.columnconfigure(0, weight=1)
        options = {"分离": "split", "合并": "merge", "修复": "repair"}
        for i, (text, value) in enumerate(options.items()):
            ttk.Radiobutton(
                func_frame,
                text=text,
                variable=self.logic.current_function,
                value=value,
                command=self.logic.on_function_tab_change,
            ).pack(side=tk.LEFT, expand=True, padx=5)
        current_row += 1

        # 游戏选择
        game_frame = ttk.LabelFrame(parent, text="2. 游戏类型", padding="10")
        game_frame.grid(row=current_row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        game_frame.columnconfigure(0, weight=1)
        ttk.Radiobutton(
            game_frame,
            text="原神 (UIGF)",
            variable=self.logic.selected_game,
            value="genshin",
            command=self.logic.on_game_selection_change,
        ).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Radiobutton(
            game_frame,
            text="崩坏：星穹铁道 (SRGF)",
            variable=self.logic.selected_game,
            value="starrail",
            command=self.logic.on_game_selection_change,
        ).pack(side=tk.LEFT, expand=True, padx=5)
        current_row += 1

        # 文件IO
        io_frame = ttk.LabelFrame(parent, text="3. 文件与目录", padding="10")
        io_frame.grid(row=current_row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        io_frame.columnconfigure(0, weight=1)
        self._create_file_io_widgets(io_frame)
        current_row += 1

        # 执行操作
        action_frame = ttk.LabelFrame(parent, text="4. 执行操作", padding="10")
        action_frame.grid(row=current_row, column=0, sticky=(tk.W, tk.E))
        action_frame.columnconfigure(0, weight=1)
        self.convert_button = ttk.Button(
            action_frame,
            text="开始转换",
            command=self.logic.start_operation,
            style="Accent.TButton",
        )
        self.convert_button.pack(fill=tk.X, ipady=5)
        current_row += 1

    def _create_file_io_widgets(self, parent):
        """创建文件输入/输出相关组件"""
        # 文件1
        self.file1_label = ttk.Label(parent, text="输入文件:")
        self.file1_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 2))
        file1_frame = ttk.Frame(parent)
        file1_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file1_frame.columnconfigure(0, weight=1)
        self.file_entry = ttk.Entry(
            file1_frame, textvariable=self.logic.input_file_path, state="readonly"
        )
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.file1_button = ttk.Button(
            file1_frame,
            text="...",
            command=lambda: self.logic.select_input_file(0),
            width=4,
        )
        self.file1_button.grid(row=0, column=1)
        Tooltip(self.file1_button, "选择要处理的UIGF/SRGF文件")

        # 文件2 (合并专用)
        self.file2_label = ttk.Label(parent, text="第二个文件 (合并专用):")
        self.file2_label.grid(row=2, column=0, sticky=tk.W, pady=(5, 2))
        file2_frame = ttk.Frame(parent)
        file2_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file2_frame.columnconfigure(0, weight=1)
        self.file2_entry = ttk.Entry(
            file2_frame, textvariable=self.logic.input_file_path2, state="readonly"
        )
        self.file2_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.file2_button = ttk.Button(
            file2_frame,
            text="...",
            command=lambda: self.logic.select_input_file(1),
            width=4,
        )
        self.file2_button.grid(row=0, column=1)
        Tooltip(self.file2_button, "选择要合并的第二个文件")
        self.file2_widgets = [self.file2_label, file2_frame]

        # 合并后转换
        self.merge_convert_checkbox = ttk.Checkbutton(
            parent,
            text="合并后自动分离",
            variable=self.logic.convert_after_merge,
        )
        self.merge_convert_checkbox.grid(row=4, column=0, sticky=tk.W, pady=(0, 10))

        # 输出目录
        output_label = ttk.Label(parent, text="输出目录:")
        output_label.grid(row=5, column=0, sticky=tk.W, pady=(5, 2))
        output_frame = ttk.Frame(parent)
        output_frame.grid(row=6, column=0, sticky=(tk.W, tk.E))
        output_frame.columnconfigure(0, weight=1)
        self.dir_entry = ttk.Entry(
            output_frame, textvariable=self.logic.output_dir_path, state="readonly"
        )
        self.dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        output_button = ttk.Button(
            output_frame,
            text="...",
            command=self.logic.select_output_directory,
            width=4,
        )
        output_button.grid(row=0, column=1)
        Tooltip(output_button, "选择保存结果的文件夹")

    def _create_status_widgets(self, parent):
        """创建右侧的状态和信息显示组件"""
        # 功能说明
        self.info_frame = ttk.LabelFrame(parent, text="功能说明", padding="10")
        self.info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        self.info_frame.columnconfigure(0, weight=1)
        self.info_label = ttk.Label(
            self.info_frame,
            text="",
            justify=tk.LEFT,
            wraplength=self.logic.text_wraplength,
        )
        self.info_label.pack(fill=tk.X)

        # 状态日志
        status_frame = ttk.LabelFrame(parent, text="状态日志", padding="10")
        status_frame.grid(
            row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10)
        )
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        self.status_text = tk.Text(
            status_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            borderwidth=1,
            relief="solid",
            font=("Microsoft YaHei UI", 9),
        )
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar = ttk.Scrollbar(
            status_frame, orient=tk.VERTICAL, command=self.status_text.yview
        )
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.status_text.configure(yscrollcommand=scrollbar.set)

        # 进度条
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.S))
        progress_frame.columnconfigure(0, weight=1)
        self.progress_label = ttk.Label(progress_frame, text="进度:")
        self.progress_label.pack(fill=tk.X)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X, ipady=4, pady=(5, 0))

    def _create_bottom_bar(self, parent):
        """创建底部作者和GitHub链接栏"""
        bottom_frame = ttk.Frame(parent, padding=(10, 5))
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        bottom_frame.columnconfigure(1, weight=1)
        author_info = GitHubIntegration.get_author_info()
        author_label = ttk.Label(
            bottom_frame,
            text=f"by：{author_info['name']}",
            font=("Arial", 9),
            foreground="#666666",
        )
        author_label.pack(side=tk.LEFT)
        self.github_button = ttk.Button(
            bottom_frame,
            text="GitHub",
            command=self.logic.open_github_repo,
            width=10,
        )
        self.github_button.pack(side=tk.RIGHT)
        Tooltip(self.github_button, "打开项目的GitHub页面")


class MainWindow:
    def __init__(self):
        """初始化主窗口"""
        self.root = tk.Tk()
        self.root.title("UIGF/SRGF 抽卡记录分离工具 v1.1")

        self._setup_window_size()
        self.root.resizable(True, True)
        self.root.minsize(750, 550)

        self.setup_styles()

        # 初始化变量
        self.selected_game = tk.StringVar(value="genshin")
        self.input_file_path = tk.StringVar()
        self.input_file_path2 = tk.StringVar()
        self.output_dir_path = tk.StringVar()
        self.current_function = tk.StringVar(value="split")
        self.convert_after_merge = tk.BooleanVar(value=True)

        # 创建UI
        self.ui = ApplicationUI(self.root, self)
        self.on_function_tab_change()  # 初始化UI状态

    def on_cursor_wait(self):
        self.root.config(cursor="wait")

    def on_cursor_default(self):
        self.root.config(cursor="")

    def _setup_window_size(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        if screen_width >= 1920 and screen_height >= 1080:
            window_width, window_height, self.text_wraplength = 900, 650, 400
        elif screen_width >= 1366 and screen_height >= 768:
            window_width, window_height, self.text_wraplength = 800, 600, 350
        else:
            window_width, window_height, self.text_wraplength = 750, 550, 300
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def setup_styles(self):
        self.style = ttk.Style(self.root)
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")
        primary_color = "#0078D7"
        secondary_color = "#F3F3F3"
        text_color = "#202020"
        self.style.configure(
            ".",
            font=("Microsoft YaHei UI", 10),
            background=secondary_color,
            foreground=text_color,
        )
        self.style.configure("TFrame", background=secondary_color)
        self.style.configure(
            "TLabel", background=secondary_color, foreground=text_color
        )
        self.style.configure(
            "TRadiobutton", background=secondary_color, foreground=text_color
        )
        self.style.configure(
            "TCheckbutton", background=secondary_color, foreground=text_color
        )
        self.style.configure(
            "TLabelframe",
            background=secondary_color,
            borderwidth=1,
            relief="groove",
            padding=10,
        )
        self.style.configure(
            "TLabelframe.Label",
            background=secondary_color,
            foreground=primary_color,
            font=("Microsoft YaHei UI", 11, "bold"),
        )
        self.style.configure(
            "TButton", padding=5, relief="flat", font=("Microsoft YaHei UI", 10)
        )
        self.style.map(
            "TButton",
            foreground=[("pressed", "white"), ("active", "white")],
            background=[
                ("pressed", "!disabled", primary_color),
                ("active", primary_color),
            ],
        )
        self.style.configure(
            "Accent.TButton",
            font=("Microsoft YaHei UI", 11, "bold"),
            background=primary_color,
            foreground="white",
        )
        self.style.map(
            "Accent.TButton",
            background=[("pressed", "!disabled", "#005A9E"), ("active", "#005A9E")],
        )
        self.style.configure("TProgressbar", thickness=15, background=primary_color)

    def on_function_tab_change(self):
        current_func = self.current_function.get()
        function_names = {"split": "分离", "repair": "修复", "merge": "合并"}
        self.update_status(f"已切换到 {function_names[current_func]} 功能")
        self.input_file_path.set("")
        self.input_file_path2.set("")
        self.output_dir_path.set("")

        is_merge = current_func == "merge"
        for widget in self.ui.file2_widgets:
            if is_merge:
                widget.grid()
            else:
                widget.grid_remove()
        if is_merge:
            self.ui.merge_convert_checkbox.grid()
        else:
            self.ui.merge_convert_checkbox.grid_remove()

        self.ui.file1_label.config(text="输入文件:" if not is_merge else "第一个文件:")

        info_texts = {
            "split": "分离功能：将单个UIGF/SRGF文件按祈愿类型 (gacha_type) 分离为多个独立的JSON文件。",
            "repair": "修复功能：自动检测并修复UIGF/SRGF文件中的常见问题，例如：\n• 缺失必需字段\n• 无效数据类型\n• 重复的ID\n• 错误的时间格式",
            "merge": "合并功能：将两个相同UID的UIGF/SRGF文件合并为一个，并自动处理重复记录。可选择在合并后直接进行分离操作。",
        }
        self.ui.info_label.config(text=info_texts[current_func])
        self.ui.convert_button.config(text=f"开始{function_names[current_func]}")
        self.ui.progress_var.set(0)

    def on_game_selection_change(self):
        selected_game = self.selected_game.get()
        game_name = "原神" if selected_game == "genshin" else "崩坏：星穹铁道"
        self.update_status(f"已选择游戏类型: {game_name}")
        if self.input_file_path.get():
            self.input_file_path.set("")
            self.update_status("已清除之前选择的文件，请重新选择对应游戏的记录文件")
        if selected_game == "genshin":
            self.update_status("请选择UIGF格式的原神抽卡记录文件")
        else:
            self.update_status("请选择SRGF格式的崩坏：星穹铁道抽卡记录文件")

    def select_input_file(self, file_index=0):
        game_name = (
            "原神" if self.selected_game.get() == "genshin" else "崩坏：星穹铁道"
        )
        current_func = self.current_function.get()
        if current_func == "repair":
            title = f"选择需修复的{game_name}记录文件"
        elif current_func == "merge":
            title = (
                f"选择第一个{game_name}记录文件"
                if file_index == 0
                else f"选择第二个{game_name}记录文件"
            )
        else:
            title = f"选择{game_name}记录文件"
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialdir=os.path.expanduser("~"),
        )
        if file_path:
            target_var = (
                self.input_file_path if file_index == 0 else self.input_file_path2
            )
            target_var.set(file_path)
            self.update_status(
                f"已选择文件{file_index + 1}: {os.path.basename(file_path)}"
            )

            # 文件验证
            try:
                if current_func == "repair":
                    import json

                    with open(file_path, "r", encoding="utf-8") as f:
                        json.load(f)
                    self.update_status("文件JSON格式有效，可进行修复")
                else:
                    processor = FileProcessor(self.selected_game.get())
                    is_valid, error_message = processor.validate_file(file_path)
                    if is_valid:
                        self.update_status("文件格式验证通过")
                    else:
                        messagebox.showerror("文件验证失败", error_message)
                        target_var.set("")
            except Exception as e:
                messagebox.showerror("验证错误", f"文件验证时出错: {e}")
                target_var.set("")

    def select_output_directory(self):
        dir_path = filedialog.askdirectory(
            title="选择输出目录", initialdir=os.path.expanduser("~")
        )
        if dir_path:
            from utils import create_output_directory

            success, error_message = create_output_directory(dir_path)
            if success:
                self.output_dir_path.set(dir_path)
                self.update_status(f"已选择输出目录: {dir_path}")
            else:
                messagebox.showerror("目录错误", error_message)

    def start_operation(self):
        current_func = self.current_function.get()
        if not self._validate_inputs(current_func):
            return
        self.on_cursor_wait()
        self.ui.convert_button.config(state="disabled")
        self.ui.progress_var.set(0)
        operation_name = self.ui.convert_button["text"]
        self.update_status(f"{operation_name}...")

        try:
            target_func, processor, args = self._prepare_operation(current_func)
        except Exception as e:
            self.on_operation_error("准备", f"创建处理器失败: {e}")
            return

        thread = threading.Thread(
            target=target_func, args=(processor, *args), daemon=True
        )
        thread.start()

    def _prepare_operation(self, current_func):
        """根据功能准备处理器和参数"""
        if current_func == "split":
            processor = FileProcessor(self.selected_game.get())
            args = (
                self.input_file_path.get(),
                self.output_dir_path.get(),
                self.update_progress,
            )
            target_func = self._run_split
        elif current_func == "repair":
            from file_repair import FileRepairer

            processor = FileRepairer(self.selected_game.get())
            args = (
                self.input_file_path.get(),
                self.output_dir_path.get(),
                self.update_progress,
            )
            target_func = self._run_repair
        elif current_func == "merge":
            from file_merger import FileMerger

            processor = FileMerger(self.selected_game.get())
            args = (
                self.input_file_path.get(),
                self.input_file_path2.get(),
                self.output_dir_path.get(),
                self.convert_after_merge.get(),
                self.update_progress,
            )
            target_func = self._run_merge
        else:
            raise ValueError(f"未知功能: {current_func}")
        return target_func, processor, args

    def _validate_inputs(self, current_func):
        if not self.input_file_path.get():
            messagebox.showerror("错误", "请先选择输入文件")
            return False
        if current_func == "merge" and not self.input_file_path2.get():
            messagebox.showerror("错误", "进行合并操作需要选择第二个文件")
            return False
        if not self.output_dir_path.get():
            messagebox.showerror("错误", "请先选择输出目录")
            return False
        return True

    def _run_split(self, processor, input_path, output_path, progress_callback):
        try:
            data, error_msg = processor.load_data(input_path)
            if data is None:
                self.root.after(0, lambda: self.on_operation_error("split", error_msg))
                return
            success, error_msg, stats = processor.process_records(
                data, output_path, progress_callback
            )
            if success:
                self.root.after(0, lambda: self.show_operation_result("split", stats))
            else:
                self.root.after(0, lambda: self.on_operation_error("split", error_msg))
        except Exception as e:
            self.root.after(
                0, lambda e=e: self.on_operation_error("split", f"发生未预期错误: {e}")
            )

    def _run_repair(self, repairer, input_path, output_path, progress_callback):
        try:
            success, error_msg, repair_info = repairer.repair_file(
                input_path, output_path, progress_callback
            )
            if success:
                self.root.after(
                    0, lambda: self.show_operation_result("repair", repair_info)
                )
            else:
                self.root.after(0, lambda: self.on_operation_error("repair", error_msg))
        except Exception as e:
            self.root.after(
                0, lambda e=e: self.on_operation_error("repair", f"发生未预期错误: {e}")
            )

    def _run_merge(
        self,
        merger,
        file1_path,
        file2_path,
        output_path,
        convert_after,
        progress_callback,
    ):
        try:
            success, error_msg, merge_info = merger.merge_files(
                file1_path, file2_path, output_path, convert_after, progress_callback
            )
            if success:
                self.root.after(
                    0, lambda: self.show_operation_result("merge", merge_info)
                )
            else:
                self.root.after(0, lambda: self.on_operation_error("merge", error_msg))
        except Exception as e:
            self.root.after(
                0, lambda e=e: self.on_operation_error("merge", f"发生未预期错误: {e}")
            )

    def update_status(self, message):
        self.ui.status_text.config(state=tk.NORMAL)
        self.ui.status_text.insert(tk.END, f"{message}\n")
        self.ui.status_text.see(tk.END)
        self.ui.status_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def update_progress(self, current, total, message):
        def update_ui():
            progress_percent = (current / total) * 100 if total > 0 else 0
            self.ui.progress_var.set(progress_percent)
            operation_name = self.ui.convert_button["text"].replace("开始", "")
            self.ui.progress_label.config(
                text=f"{operation_name}进度: {current}/{total}"
            )
            self.update_status(f"进度: {progress_percent:.1f}% - {message}")

        self.root.after(0, update_ui)

    def show_operation_result(self, operation_type, result_info):
        operation_names = {"split": "分离", "repair": "修复", "merge": "合并"}
        op_name = operation_names.get(operation_type, "处理")
        self.ui.progress_var.set(100)
        self.update_status(f"{op_name}完成！")

        title = f"{op_name}完成"
        message = f"{op_name}成功！\n\n"
        if operation_type == "split":
            summary = "\n".join(
                [
                    f"  • {g_type}.json: {count} 条"
                    for g_type, count in result_info.get("gacha_types", {}).items()
                ]
            )
            message += f"总记录: {result_info.get('total_records', 0)}\n处理: {result_info.get('processed_records', 0)}\n跳过: {result_info.get('skipped_records', 0)}\n\n各类型记录:\n{summary}"
        elif operation_type == "repair":
            summary = "\n".join(
                [
                    f"  • {issue}: {count} 个"
                    for issue, count in result_info.get("issue_types", {}).items()
                ]
            )
            message += f"检测到问题: {result_info.get('total_issues', 0)}\n成功修复: {result_info.get('fixed_issues', 0)}\n\n修复详情:\n{summary}"
        elif operation_type == "merge":
            message += f"文件1: {result_info.get('file1_records', 0)} 条\n文件2: {result_info.get('file2_records', 0)} 条\n合并后: {result_info.get('merged_records', 0)} 条\n去重: {result_info.get('duplicate_records', 0)} 条"
            if result_info.get("converted_after_merge"):
                summary = "\n".join(
                    [
                        f"  • {g_type}.json: {count} 条"
                        for g_type, count in result_info.get("gacha_types", {}).items()
                    ]
                )
                message += f"\n\n自动分离结果:\n{summary}"

        message += f"\n\n输出目录: {self.output_dir_path.get()}"
        messagebox.showinfo(title, message)
        self.reset_conversion_state()

    def on_operation_error(self, operation_type, error_message):
        op_name = operation_type if operation_type != "准备" else "操作"
        self.update_status(f"{op_name}失败: {error_message}")
        messagebox.showerror(f"{op_name}错误", f"{op_name}失败：\n{error_message}")
        self.reset_conversion_state()

    def reset_conversion_state(self):
        self.ui.convert_button.config(state="normal")
        self.on_cursor_default()
        self.ui.progress_var.set(0)
        self.ui.progress_label.config(text="进度:")

    def open_github_repo(self):
        success, message = GitHubIntegration.open_github_repo()
        self.update_status(message)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MainWindow()
    app.run()
