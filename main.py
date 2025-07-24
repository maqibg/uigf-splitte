#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UIGF/SRGF 抽卡记录分离工具
主程序入口点，提供图形用户界面

by: 马乞
GitHub: https://github.com/maqibg/yunzai-uigf-splitte
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from file_processor import FileProcessor
from game_config import GameConfig
from github_integration import GitHubIntegration


class MainWindow:
    def __init__(self):
        """初始化主窗口"""
        self.root = tk.Tk()
        self.root.title("UIGF/SRGF 抽卡记录分离工具 v1.0")
        self.root.geometry("600x550")
        self.root.resizable(False, False)
        
        # 设置窗口居中
        self.center_window()
        
        # 初始化变量
        self.selected_game = tk.StringVar(value="genshin")
        self.input_file_path = tk.StringVar()
        self.output_dir_path = tk.StringVar()
        
        # 设置UI组件
        self.setup_ui()
    
    def center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """设置用户界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 游戏类型选择
        game_frame = ttk.LabelFrame(main_frame, text="游戏类型", padding="10")
        game_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Radiobutton(game_frame, text="原神 (UIGF)", variable=self.selected_game, 
                       value="genshin", command=self.on_game_selection_change).grid(row=0, column=0, padx=(0, 20))
        ttk.Radiobutton(game_frame, text="崩坏：星穹铁道 (SRGF)", variable=self.selected_game, 
                       value="starrail", command=self.on_game_selection_change).grid(row=0, column=1)
        
        # 输入文件选择
        ttk.Label(main_frame, text="输入文件:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        file_frame.columnconfigure(0, weight=1)
        
        self.file_entry = ttk.Entry(file_frame, textvariable=self.input_file_path, state="readonly")
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(file_frame, text="选择文件", command=self.select_input_file).grid(row=0, column=1)
        
        # 输出目录选择
        ttk.Label(main_frame, text="输出目录:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        dir_frame.columnconfigure(0, weight=1)
        
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.output_dir_path, state="readonly")
        self.dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(dir_frame, text="选择目录", command=self.select_output_directory).grid(row=0, column=1)
        
        # 转换按钮
        self.convert_button = ttk.Button(main_frame, text="开始转换", command=self.start_conversion)
        self.convert_button.grid(row=5, column=0, columnspan=2, pady=(0, 20))
        
        # 进度条
        ttk.Label(main_frame, text="转换进度:").grid(row=6, column=0, sticky=tk.W, pady=(0, 5))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # 状态信息显示区域
        ttk.Label(main_frame, text="状态信息:").grid(row=8, column=0, sticky=tk.W, pady=(0, 5))
        
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        self.status_text = tk.Text(status_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        # 底部信息区域
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=10, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(15, 0))
        bottom_frame.columnconfigure(1, weight=1)  # 中间区域可扩展
        
        # 左下角：作者信息
        author_info = GitHubIntegration.get_author_info()
        author_label = ttk.Label(bottom_frame, text=f"by：{author_info['name']}", 
                                font=("Arial", 9), foreground="#666666")
        author_label.grid(row=0, column=0, sticky=tk.W)
        
        # 右下角：Github按钮
        self.github_button = ttk.Button(bottom_frame, text="Github", 
                                       command=self.open_github_repo, width=10)
        self.github_button.grid(row=0, column=2, sticky=tk.E)
        
        # 配置主框架的行权重
        main_frame.rowconfigure(9, weight=1)
    
    def update_status(self, message):
        """更新状态信息显示"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def update_progress(self, current, total, message):
        """
        更新进度显示
        
        Args:
            current (int): 当前进度
            total (int): 总数
            message (str): 进度消息
        """
        # 确保线程安全的UI更新
        def update_ui():
            # 计算进度百分比
            if total > 0:
                progress_percent = (current / total) * 100
                self.progress_var.set(progress_percent)
            else:
                self.progress_var.set(0)
            
            # 更新状态信息文本
            progress_text = f"进度: {current}/{total} ({progress_percent:.1f}%) - {message}"
            self.update_status(progress_text)
        
        # 使用after方法确保在主线程中更新UI
        self.root.after(0, update_ui)
    
    def on_game_selection_change(self):
        """处理游戏类型选择变化"""
        # 获取当前选择的游戏类型
        selected_game = self.selected_game.get()
        game_name = "原神" if selected_game == "genshin" else "崩坏：星穹铁道"
        
        # 更新状态信息
        self.update_status(f"已选择游戏类型: {game_name}")
        
        # 清除之前的文件选择
        if self.input_file_path.get():
            self.input_file_path.set("")
            self.update_status("已清除之前选择的文件，请重新选择对应游戏的抽卡记录文件")
        
        # 根据游戏类型更新界面提示信息
        if selected_game == "genshin":
            self.update_status("请选择UIGF格式的原神抽卡记录文件")
        else:
            self.update_status("请选择SRGF格式的崩坏：星穹铁道抽卡记录文件")
    
    def select_input_file(self):
        """选择输入文件"""
        # 根据选择的游戏类型设置文件对话框标题
        game_name = "原神" if self.selected_game.get() == "genshin" else "崩坏：星穹铁道"
        title = f"选择{game_name}抽卡记录文件"
        
        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=[
                ("JSON文件", "*.json"),
                ("所有文件", "*.*")
            ],
            initialdir=os.path.expanduser("~")
        )
        
        # 如果用户选择了文件
        if file_path:
            # 更新输入文件路径变量
            self.input_file_path.set(file_path)
            
            # 在状态区域显示选中的文件路径
            self.update_status(f"已选择输入文件: {file_path}")
            
            # 验证文件格式
            try:
                # 创建临时的FileProcessor来验证文件
                processor = FileProcessor(self.selected_game.get())
                is_valid, error_message = processor.validate_file(file_path)
                
                if is_valid:
                    self.update_status("文件格式验证通过")
                else:
                    self.update_status(f"文件验证失败: {error_message}")
                    self.input_file_path.set("")  # 清除无效文件路径
                    messagebox.showerror("文件验证失败", error_message)
                    
            except Exception as e:
                error_msg = f"文件验证过程中发生错误: {str(e)}"
                self.update_status(error_msg)
                self.input_file_path.set("")  # 清除无效文件路径
                messagebox.showerror("验证错误", error_msg)
    
    def select_output_directory(self):
        """选择输出目录"""
        # 打开目录选择对话框
        dir_path = filedialog.askdirectory(
            title="选择输出目录",
            initialdir=os.path.expanduser("~")
        )
        
        # 如果用户选择了目录
        if dir_path:
            # 使用增强的目录验证功能
            from utils import create_output_directory
            
            success, error_message = create_output_directory(dir_path)
            
            if success:
                # 权限验证通过，更新输出目录路径变量
                self.output_dir_path.set(dir_path)
                
                # 在状态区域显示选中的目录路径
                self.update_status(f"已选择输出目录: {dir_path}")
                self.update_status("目录验证通过")
                
                # 检查磁盘空间并显示信息
                try:
                    import shutil
                    free_space = shutil.disk_usage(dir_path).free
                    free_space_mb = free_space // (1024 * 1024)
                    self.update_status(f"可用磁盘空间: {free_space_mb}MB")
                except Exception:
                    pass
                
            else:
                self.update_status(f"目录验证失败: {error_message}")
                
                # 根据错误类型显示不同的对话框
                if "权限不足" in error_message:
                    messagebox.showerror("权限错误", 
                        f"{error_message}\n\n建议解决方案：\n"
                        "1. 选择其他有写入权限的目录\n"
                        "2. 以管理员身份运行程序\n"
                        "3. 检查目录的安全设置")
                elif "磁盘空间不足" in error_message:
                    messagebox.showerror("磁盘空间不足", 
                        f"{error_message}\n\n建议解决方案：\n"
                        "1. 清理磁盘空间\n"
                        "2. 选择其他磁盘的目录\n"
                        "3. 删除不需要的文件")
                elif "路径过长" in error_message:
                    messagebox.showerror("路径错误", 
                        f"{error_message}\n\n建议解决方案：\n"
                        "1. 选择路径较短的目录\n"
                        "2. 重命名父目录以缩短路径")
                else:
                    messagebox.showerror("目录错误", error_message)
    
    def start_conversion(self):
        """开始转换"""
        # 验证输入文件和输出目录已选择
        if not self.input_file_path.get():
            messagebox.showerror("错误", "请先选择输入文件")
            self.update_status("错误: 请先选择输入文件")
            return
        
        if not self.output_dir_path.get():
            messagebox.showerror("错误", "请先选择输出目录")
            self.update_status("错误: 请先选择输出目录")
            return
        
        # 禁用转换按钮，防止重复点击
        self.convert_button.config(state="disabled")
        
        # 重置进度条
        self.progress_var.set(0)
        
        # 更新状态
        self.update_status("开始转换...")
        
        # 创建FileProcessor实例
        try:
            processor = FileProcessor(self.selected_game.get())
        except Exception as e:
            self.update_status(f"错误: 创建文件处理器失败 - {str(e)}")
            messagebox.showerror("错误", f"创建文件处理器失败: {str(e)}")
            self.convert_button.config(state="normal")
            return
        
        # 在单独线程中执行转换避免UI冻结
        def conversion_thread():
            try:
                # 加载数据
                self.update_status("正在加载文件...")
                data, error_msg = processor.load_data(self.input_file_path.get())
                
                if data is None:
                    self.root.after(0, lambda: self.on_conversion_error(error_msg))
                    return
                
                self.root.after(0, lambda: self.update_status("文件加载成功，开始处理记录..."))
                
                # 处理记录
                success, error_msg, stats = processor.process_records(
                    data, 
                    self.output_dir_path.get(), 
                    progress_callback=self.update_progress
                )
                
                if success:
                    self.root.after(0, lambda: self.on_conversion_success(stats))
                else:
                    self.root.after(0, lambda: self.on_conversion_error(error_msg))
                    
            except Exception as e:
                error_msg = f"转换过程中发生未预期错误: {str(e)}"
                self.root.after(0, lambda: self.on_conversion_error(error_msg))
        
        # 启动转换线程
        thread = threading.Thread(target=conversion_thread, daemon=True)
        thread.start()
    
    def on_conversion_success(self, stats):
        """
        处理转换成功
        
        Args:
            stats (dict): 转换统计信息
        """
        # 设置进度条为100%
        self.progress_var.set(100)
        
        # 显示转换成功消息和统计信息
        success_message = "转换完成！"
        self.update_status(success_message)
        
        # 显示详细统计信息
        total_records = stats.get("total_records", 0)
        processed_records = stats.get("processed_records", 0)
        skipped_records = stats.get("skipped_records", 0)
        gacha_types = stats.get("gacha_types", {})
        
        self.update_status(f"总记录数: {total_records}")
        self.update_status(f"成功处理: {processed_records}")
        if skipped_records > 0:
            self.update_status(f"跳过记录: {skipped_records}")
        
        self.update_status("各类型记录分布:")
        for gacha_type, count in gacha_types.items():
            self.update_status(f"  {gacha_type}.json: {count} 条记录")
        
        self.update_status(f"输出目录: {self.output_dir_path.get()}")
        
        # 显示成功对话框
        gacha_type_summary = "\n".join([f"{gacha_type}.json: {count} 条记录" 
                                       for gacha_type, count in gacha_types.items()])
        
        messagebox.showinfo(
            "转换完成", 
            f"转换成功完成！\n\n"
            f"总记录数: {total_records}\n"
            f"成功处理: {processed_records}\n"
            f"跳过记录: {skipped_records}\n\n"
            f"各类型记录分布:\n{gacha_type_summary}\n\n"
            f"输出目录: {self.output_dir_path.get()}"
        )
        
        # 重置界面状态允许新的转换
        self.reset_conversion_state()
    
    def on_conversion_error(self, error_message):
        """
        处理转换过程中的错误
        
        Args:
            error_message (str): 错误信息
        """
        # 更新状态显示错误信息
        self.update_status(f"转换失败: {error_message}")
        
        # 根据错误类型显示不同的对话框和建议
        if "权限不足" in error_message:
            messagebox.showerror("权限错误", 
                f"转换失败：{error_message}\n\n"
                "建议解决方案：\n"
                "1. 以管理员身份运行程序\n"
                "2. 检查输出目录的写入权限\n"
                "3. 选择其他有权限的目录")
        elif "磁盘空间不足" in error_message:
            messagebox.showerror("磁盘空间不足", 
                f"转换失败：{error_message}\n\n"
                "建议解决方案：\n"
                "1. 清理磁盘空间\n"
                "2. 删除不需要的文件\n"
                "3. 选择其他磁盘的目录")
        elif "内存不足" in error_message:
            messagebox.showerror("内存不足", 
                f"转换失败：{error_message}\n\n"
                "建议解决方案：\n"
                "1. 关闭其他程序释放内存\n"
                "2. 重启程序后重试\n"
                "3. 处理较小的数据文件")
        elif "文件格式错误" in error_message or "JSON格式错误" in error_message:
            messagebox.showerror("文件格式错误", 
                f"转换失败：{error_message}\n\n"
                "建议解决方案：\n"
                "1. 确认选择了正确的UIGF/SRGF格式文件\n"
                "2. 检查文件是否完整，没有损坏\n"
                "3. 重新导出抽卡记录文件")
        elif "编码错误" in error_message:
            messagebox.showerror("文件编码错误", 
                f"转换失败：{error_message}\n\n"
                "建议解决方案：\n"
                "1. 确保文件使用UTF-8编码\n"
                "2. 重新导出抽卡记录文件\n"
                "3. 使用文本编辑器转换文件编码")
        else:
            # 通用错误处理
            messagebox.showerror("转换失败", 
                f"转换过程中发生错误：\n\n{error_message}\n\n"
                "建议解决方案：\n"
                "1. 检查文件和目录是否正常\n"
                "2. 重启程序后重试\n"
                "3. 如果问题持续，请联系技术支持")
        
        # 重置界面状态允许新的转换
        self.reset_conversion_state()
    
    def reset_conversion_state(self):
        """重置界面状态允许新的转换"""
        # 重新启用转换按钮
        self.convert_button.config(state="normal")
        
        # 重置进度条
        self.progress_var.set(0)
    
    def open_github_repo(self):
        """打开GitHub仓库链接"""
        success, message = GitHubIntegration.open_github_repo()
        
        # 在状态区域显示操作结果
        if success:
            self.update_status("已打开GitHub仓库页面")
        else:
            self.update_status(f"GitHub链接操作: {message}")
    
    def run(self):
        """运行主程序"""
        self.root.mainloop()


if __name__ == "__main__":
    app = MainWindow()
    app.run()