import tkinter as tk
from tkinter import ttk
from utils.process.process_java import new_file_chooser
from utils.process.process_dir_seeker import path_finding_thread
from utils.camera.ast_loop import camera_mode_manager
from gui_para_window import create_modal_window
from utils.process.process_java import Preferences

def create_task_frame(self, parent):
    """
    创建节点选择器（使用 Canvas 绘制）
    """

    # 创建Canvas
    self.task_canvas = tk.Canvas(parent, bg='#cccccc', width=80 ,highlightthickness=0)
    self.task_canvas.pack(fill='x', padx=5, pady=5)
    self.scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.task_canvas.yview)
    self.scrollable_frame = ttk.Frame(self.task_canvas)

    # 配置画布滚动区域
    self.scrollable_frame.bind(
        "<Configure>",
        lambda e: self.task_canvas.configure(scrollregion=self.task_canvas.bbox("all")))

    # 创建窗口并绑定滚动条
    self.canvas_window = self.task_canvas.create_window(
        (0, 0), window=self.scrollable_frame, anchor="nw")
    self.task_canvas.configure(yscrollcommand=self.scrollbar.set)

    # 布局组件
    self.task_canvas.pack(side="left", fill="both", expand=True)
    self.scrollbar.pack(side="right", fill="y")

    # 绑定鼠标滚轮事件
    self.task_canvas.bind("<Configure>", lambda event, s=self: _on_canvas_configure(s, event))
    self.task_canvas.bind_all("<MouseWheel>", lambda event, s=self: _on_mousewheel(s, event))

def create_east_frame(self):
    """
    创建东部的控制面板
    """

    east_frame = tk.Frame(self.root, bg='#eaeaea', padx=10, pady=10,
                          highlightbackground='#cccccc', highlightthickness=1)
    east_frame.grid(row=1, column=2, sticky='ns')

    # 文本框
    self.path_var = tk.StringVar()

    self.path_entry = tk.Entry(east_frame, textvariable=self.path_var, width=20,
                          font=('宋体', 10), state="disabled")
    self.path_entry.pack(pady=(0, 0), padx=10, fill='x')
    self.path_scrollbar = ttk.Scrollbar(east_frame, orient="horizontal", command=self.path_entry.xview)
    self.path_entry.configure(xscrollcommand=self.path_scrollbar.set)
    self.path_scrollbar.pack(pady=(0, 0), padx=10, fill="x")
    self.path_entry.xview_moveto(1)

    # 浏览按钮
    browse_btn = tk.Button(east_frame, text="浏览输入目录...", command=lambda s=self:browse_file(s),
                           bg='#eaeaea', relief='raised', font=('宋体', 10))
    browse_btn.pack(pady=(0, 5), padx=10, fill='x')

    # 文本框
    self.output_path_var = tk.StringVar()

    self.output_path_entry = tk.Entry(east_frame, textvariable=self.output_path_var, width=20,
                               font=('宋体', 10), state="disabled")
    self.output_path_entry.pack(pady=(0, 0), padx=10, fill='x')
    self.output_path_scrollbar = ttk.Scrollbar(east_frame, orient="horizontal", command=self.output_path_entry.xview)
    self.output_path_entry.configure(xscrollcommand=self.output_path_scrollbar.set)
    self.output_path_scrollbar.pack(pady=(0, 0), padx=10, fill="x")
    self.output_path_entry.xview_moveto(1)

    output_choose_frame = tk.Frame(east_frame, bg='#eaeaea', padx=0, pady=0,
                          highlightbackground='#cccccc', highlightthickness=1)
    output_choose_frame.pack(pady=(0, 5), padx=10, fill="x")
    # 浏览按钮

    output_browse_btn = tk.Button(output_choose_frame, text="设置输出目录", command=lambda s=self: output_browse_file(s),
                           bg='#eaeaea', relief='raised', font=('宋体', 10))
    output_browse_btn.pack(side="left", pady=(0, 0), padx=0, fill='both')
    auto_browse_btn = tk.Button(output_choose_frame, text="设为自动", command=lambda s=self: output_auto(s),
                           bg='#eaeaea', relief='raised', font=('宋体', 10))
    auto_browse_btn.pack( pady=(0, 0), padx=0, fill='both')

    # 开始/中断按钮
    self.start_btn_var = tk.StringVar(value="搜索【" + self.nodes[self.program_start] + "】任务文件")
    self.start_btn = tk.Button(east_frame, textvariable=self.start_btn_var,
                               command=lambda s=self:toggle_start(s), bg='#4CAF50', fg='white',
                               relief='raised', font=('宋体', 10, 'bold'))
    self.start_btn.pack(pady=10, padx=10, fill='x')

    # 摄像参数按钮
    camera_btn = tk.Button(east_frame, text="摄像参数 ⚙",
                           command=lambda s=self:open_camera_settings(s),
                           bg='#eaeaea', relief='raised', font=('宋体', 10))
    camera_btn.pack(pady=5, padx=10, fill='x')

    # 噪声过滤参数按钮
    preprocess_btn = tk.Button(east_frame, text="噪声过滤 ⚙",
                               command=lambda s=self:open_preprocess_settings(s),
                               bg='#eaeaea', relief='raised', font=('宋体', 10))
    preprocess_btn.pack(pady=5, padx=10, fill='x')

    # 检测追踪参数按钮
    trackmate_btn = tk.Button(east_frame, text="检测追踪 ⚙",
                              command=lambda s=self:open_trackmate_settings(s),
                              bg='#eaeaea', relief='raised', font=('宋体', 10))
    trackmate_btn.pack(pady=5, padx=10, fill='x')

    # 特征提取参数按钮
    features_btn = tk.Button(east_frame, text="特征提取 ⚙",
                             command=lambda s=self:open_features_settings(s),
                             bg='#eaeaea', relief='raised', font=('宋体', 10))
    features_btn.pack(pady=5, padx=10, fill='x')

    # 开始/中断按钮
    self.AST_btn_var = tk.StringVar(value="开始运行")
    self.AST_btn = tk.Button(east_frame, textvariable=self.AST_btn_var,
                               command=lambda s=self: AST_start(s), bg='#4CAF50', fg='white',
                               relief='raised', font=('宋体', 10, 'bold'))
    self.AST_btn.pack(pady=5, padx=10, fill='x', side='bottom')


    task_label = tk.Label(east_frame, text="待处理任务列表",
                          bg='#eaeaea', font=('宋体', 10))
    task_label.pack(pady=5, padx=10, fill='x')

    create_task_frame(self, east_frame)

    tk.Label(east_frame, text="待处理任务列表",
                          bg='#eaeaea', font=('宋体', 10))
    task_label.pack(pady=5, padx=10, fill='x')

def _on_canvas_configure(self, event):
    # 更新内部框架宽度以适应画布
    self.task_canvas.itemconfig(self.canvas_window, width=event.width)

def _on_mousewheel(self, event):
    # 处理鼠标滚轮滚动
    self.task_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

def browse_file(self):
    """
    浏览文件
    """

    self.filepath_list = new_file_chooser(self, self.program_start)
    self.path_entry.xview_moveto(1)

def output_browse_file(self):
    """
    浏览文件
    """

    self.output_filepath = new_file_chooser(self, 4)
    self.output_path_entry.xview_moveto(1)

def output_auto(self):
    """
    浏览文件
    """

    self.output_filepath = "auto"
    self.output_path_var.set("auto")
    self.output_path_entry.xview_moveto(1)
    prefs = Preferences.userRoot().node("/LMH/fijiCountingFaster/29/fileChooser")
    prefs.put("outputPath", "auto")

def toggle_start(self):
    """
    切换开始/中断按钮状态
    """

    if self.searching == False and self.running == False:
        if self.start_btn_var.get() == "搜索【" + self.nodes[self.program_start] + "】任务文件":
            self.searching = True
            self.start_btn_var.set("运行中")
            self.start_btn.config(bg='#E74C3C')
            self.status_var.set("正在搜索文件中……")
            self.AST_btn_var.set("正在搜索文件中……")
            self.AST_btn.config(bg='#cccccc')
            self.progress['value'] = 0
            self.task_mode = None
            self.task_canvas.update_idletasks()
            self.task_canvas.yview_moveto(0.0)
            for widget in self.scrollable_frame.winfo_children():
                if widget != self.scrollable_frame:
                    widget.destroy()
            filepath_list = self.filepath_list
            mode = self.program_start
            all_para_dict = self.all_para_dict
            path_finding_thread(self, filepath_list, mode, all_para_dict)

def AST_start(self):
    """
    切换开始/中断按钮状态
    """

    if self.searching == False and self.running == False:
        if self.AST_btn_var.get() == "开始运行":
            self.running = True
            self.AST_btn_var.set("运行中")
            self.AST_btn.config(bg='#E74C3C')
            self.status_var.set("开始运行")
            self.start_btn_var.set("正在运行中")
            self.start_btn.config(bg='#cccccc')
            self.progress['value'] = 0
            start = self.program_start
            end = self.program_end
            task_list = self.task_list
            all_para_dict = self.all_para_dict
            camera_mode_manager(self, [start, end], task_list, all_para_dict)

def open_camera_settings(self):
    """
    打开摄像参数设置
    """

    create_modal_window(self, "camera")
    self.status_var.set("打开摄像参数设置")

def open_preprocess_settings(self):
    """
    打开处理参数设置
    """

    create_modal_window(self, "preprocess")
    self.status_var.set("打开噪声过滤设置")

def open_trackmate_settings(self):
    """
    打开处理参数设置
    """

    create_modal_window(self, "trackmate")
    self.status_var.set("打开检测追踪设置")

def open_features_settings(self):
    """
    打开处理参数设置
    """

    create_modal_window(self, "features")
    self.status_var.set("打开特征提取设置")

