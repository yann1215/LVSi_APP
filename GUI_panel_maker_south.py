import tkinter as tk
from tkinter import ttk
import scyjava
import json

def update_node_colors(self):
    """更新节点颜色显示"""
    # 重置所有节点颜色
    for i in range(len(self.nodes)):
        x, y = self.node_positions[i]
        self.canvas.itemconfig(
            self.canvas.find_closest(x, y)[0],  # 找到节点圆形
            fill='#cccccc'
        )

    # 重置基线颜色
    self.canvas.itemconfig(self.baseline, fill='#cccccc')

    # 获取当前选择的左右索引
    left_idx = self.left_var.get()
    right_idx = self.right_var.get()

    # 如果两个索引都有效
    if left_idx >= 0 and right_idx >= 0:
        # 确定起始和结束索引
        start = min(left_idx, right_idx)
        end = max(left_idx, right_idx)
        for i in range(start, end + 1):
            x, y = self.node_positions[i]
            self.canvas.itemconfig(
                self.canvas.find_closest(x, y)[0],
                fill='#0278F8'
            )


def select_left(self, index):
    """选择左单选按钮"""
    # 更新选择
    self.left_var.set(index)
    self.program_start = index

    # 检查是否需要调整右单选按钮
    if self.right_var.get() < index:
        # 如果右单选在当前选择的左边，移动到同一节点的右单选
        select_right(self, index)
        self.program_end = index

    # 更新颜色显示
    update_node_colors(self)

    Preferences = scyjava.jimport("java.util.prefs.Preferences")
    prefs = Preferences.userRoot().node("/LMH/fijiCountingFaster/29/fileChooser")
    KEY_list = ["cameraPath", "preprocessPath", "trackMatePath", "featuresPath", "outputPath"]
    path_list_prefs = prefs.get(KEY_list[index], None)
    if not path_list_prefs:
        path_list_str = '[]'
    else:
        path_list_str = str(path_list_prefs)
    output_path_prefs = prefs.get(KEY_list[4], None)
    if not output_path_prefs or output_path_prefs == "auto":
        output_path_str = 'auto'
    else:
        output_path_str = str(output_path_prefs)
    self.path_var.set(path_list_str)
    self.path_entry.xview_moveto(1)
    self.output_path_var.set(output_path_str)
    self.output_path_entry.xview_moveto(1)
    path_list_str = path_list_str.replace('\'','\"')
    try:
        path_list = json.loads(path_list_str)
    except:
        path_list = []
    self.filepath_list = path_list
    self.output_filepath = output_path_str
    self.start_btn_var.set("搜索【" + self.nodes[self.program_start] + "】任务文件")

    if self.running == False:
        if index == self.task_mode:
            self.AST_btn_var.set("开始运行")
            self.AST_btn.config(bg='#4CAF50')
            if index == 0 and self.camera == False:
                self.AST_btn_var.set("无相机")
                self.AST_btn.config(bg='#cccccc')
        elif not self.task_mode == None:
            self.AST_btn_var.set("此为【" + self.nodes[self.task_mode] + "】任务列表")
            self.AST_btn.config(bg='#cccccc')
        else:
            self.AST_btn_var.set("任务文件列表已空")
            self.AST_btn.config(bg='#cccccc')

def select_right(self, index):
    """选择右单选按钮"""

    # 更新选择
    self.right_var.set(index)
    self.program_end = index

    # 检查是否需要调整左单选按钮
    if self.left_var.get() > index:
        # 如果左单选在当前选择的右边，移动到同一节点的左单选
        select_left(self, index)
        self.program_start = index

    # 更新颜色显示
    update_node_colors(self)

def draw_baseline(self):
    """绘制基线（细线）"""
    width = self.canvas.winfo_reqwidth()
    y = 30  # 基线的y坐标

    # 绘制灰色基线
    self.baseline = self.canvas.create_line(50, y, width - 50, y,
                                            fill='#cccccc', width=2)

    # 存储基线y坐标供后续使用
    self.baseline_y = y

def create_nodes_and_buttons(self):
    """创建节点圆形和单选按钮"""
    width = self.canvas.winfo_reqwidth()
    node_count = len(self.nodes)
    spacing = (width - 100) // (node_count - 1)  # 节点间距

    # 创建每个节点
    for i in range(node_count):
        x = 50 + i * spacing
        y = self.baseline_y

        # 绘制节点圆形（灰色）
        circle = self.canvas.create_oval(
            x - self.node_radius, y - self.node_radius,
            x + self.node_radius, y + self.node_radius,
            fill='#cccccc'
        )

        # 在节点上方添加标签（ABCD）
        label = self.canvas.create_text(
            x, y - 20,
            text=self.nodes[i],
            fill='#333333',
            font=('宋体', 10)
        )

        # 存储节点位置
        self.node_positions.append((x, y))

        # 在节点下方创建单选按钮框架
        frame = tk.Frame(self.canvas, bg='#eaeaea')
        self.canvas.create_window(x + 5, y + 15, window=frame, anchor='n')

        # 左单选按钮
        left_radio = tk.Radiobutton(
            frame, variable=self.left_var, value=i,
            command=lambda idx=i, s=self: select_left(s, idx),
            bg='#eaeaea', indicatoron=1, selectcolor='#eaeaea',
            font=('宋体', 8)
        )
        left_radio.pack(side='left', padx=2)

        # 右单选按钮
        right_radio = tk.Radiobutton(
            frame, variable=self.right_var, value=i,
            command=lambda idx=i, s=self: select_right(s, idx),
            bg='#eaeaea', indicatoron=1, selectcolor='#eaeaea',
            font=('宋体', 8)
        )
        right_radio.pack(side='left', padx=2)

def create_node_selector(self, parent):
    """创建节点选择器（使用Canvas绘制）"""

    # 创建Canvas
    self.canvas = tk.Canvas(parent, bg='#eaeaea', height=65, width=700, highlightthickness=0)
    self.canvas.pack(fill='x', padx=20, pady=5)

    # 存储单选按钮的变量
    self.left_var = tk.IntVar(value=-1)  # 左单选按钮选中的节点索引
    self.right_var = tk.IntVar(value=-1)  # 右单选按钮选中的节点索引

    # 节点名称
    self.node_positions = []  # 存储每个节点的中心坐标
    self.node_radius = 10  # 节点圆形的半径

    # 绘制基线（细线）
    draw_baseline(self)

    # 创建节点和单选按钮
    create_nodes_and_buttons(self)

    # 初始选择
    select_left(self, 0)  # 默认选择A的左单选
    select_right(self, len(self.nodes) - 1)  # 默认选择D的右单选

def create_south_frame(self):
    """创建南部的控制面板"""

    south_frame = tk.Frame(self.root, bg='#eaeaea', padx=10, pady=10)
    south_frame.grid(row=2, column=1, sticky='ew')

    # 上部分：节点选择区域
    node_frame = tk.Frame(south_frame, bg='#eaeaea', height=60)
    node_frame.pack(fill='x', pady=(0, 10))

    # 创建节点选择器
    create_node_selector(self, node_frame)

    # 下部分：进度条和状态显示
    bottom_frame = tk.Frame(south_frame, bg='#eaeaea', height=40)
    bottom_frame.pack(fill='x')

    # 进度条
    self.progress = ttk.Progressbar(bottom_frame, orient='horizontal',
                                    length=575, mode='determinate')
    self.progress.pack(side='left', padx=(25, 5), fill='x', expand=False)

    # 状态显示
    self.status_var = tk.StringVar(value="就绪")
    status_label = tk.Label(bottom_frame, textvariable=self.status_var,
                            bg='#eaeaea', font=('宋体', 10))
    status_label.pack(side='right', fill='x', expand=True)
