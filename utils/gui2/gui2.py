import os
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as tb
from ttkbootstrap import ttk
from PIL import Image, ImageTk
import cv2
from importlib.resources import files
import threading
from ttkbootstrap.toast import ToastNotification

from gui2_file import FileMixin
from gui2_config import ConfigMixin
from gui2_image import ImageMixin

from _para import all_para_dict, base_path
from utils.gui2.gui2_para import all_para_settings
from utils.process.process_dir_seeker import path_finding_thread
from utils.camera.ast_loop import camera_mode_manager


# LIGHT_BLUE = "#53a7d8"
DARK_BLUE = "#135ecb"
WHITE = "#ffffff"
LIGHT_GREY = "#f4f7fb"
MID_GREY = "#e9eef5"
DARK_GREY = "#53a7d8"

LEFT_WIDTH = 360          # 左列固定宽度
MID_WIDTH  = 480          # 中列固定宽度=左列
BASE_MIN_H = 760          # 最小高度
INIT_W, INIT_H = 1520, 940  # 初始窗口更大，右侧图像区更宽
# INIT_W, INIT_H = 1680, 945  # OBS采集比例

ASSETS = files("utils.gui2.gui_assets")  # 指向GUI2使用的资源包
ICON_SIZE = 24


# ---- 纵向滚动容器 ----
class VScrolled(ttk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns", padx=(8,0))
        self.rowconfigure(0, weight=1)

        self.content = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_config)
        self._bind_wheel(self)

    def _on_canvas_config(self, event):
        self.canvas.itemconfig(self._win, width=event.width)

    def _bind_wheel(self, widget):
        widget.bind("<Enter>", lambda e: self._wheel_bind(True), add="+")
        widget.bind("<Leave>", lambda e: self._wheel_bind(False), add="+")

    def _wheel_bind(self, on):
        if on:
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
            self.canvas.bind_all("<Button-4>", self._on_mousewheel, add="+")
            self.canvas.bind_all("<Button-5>", self._on_mousewheel, add="+")
        else:
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        # 鼠标滚轮进入组件时 bind_all，离开时 unbind_all
        # 兼容 Win（<MouseWheel>）和类 Unix（<Button-4/5>）
        delta = -1 if getattr(event, "num", 0) == 4 else (1 if getattr(event, "num", 0) == 5 else -int(event.delta/120))
        self.canvas.yview_scroll(delta, "units")

class Collapsible(ttk.Labelframe):
    def __init__(self, master, text="", toggle=False, *args, **kwargs):
        super().__init__(master, text=text, padding=8, *args, **kwargs)
        self.columnconfigure(0, weight=1)
        self.body = ttk.Frame(self)
        self.body.grid(row=0, column=0, sticky="ew")
        self._collapsed = False
        self._btn = None

        if toggle:
            self._btn = ttk.Button(self, text="−", width=2, command=self._toggle)
            self._btn.place(relx=1.0, x=-8, y=-2, anchor="ne")

    def _toggle(self):
        if self._btn is None:
            return  # 关闭了折叠功能
        if self._collapsed:
            self.body.grid(); self._btn.config(text="−")
        else:
            self.body.grid_remove(); self._btn.config(text="+")
        self._collapsed = not self._collapsed


class App(FileMixin, ConfigMixin, ImageMixin, tb.Window):
    def __init__(self):

        super().__init__()

        # ========== GUI: 参数、路径、设置 ==========

        # 兼容旧代码写法
        self.root = self

        # 标题字符参数
        self.Alltitle_var = tk.StringVar(self)
        # Large Volume Solution Scattering Imaging System 太长了，会看着奇怪
        self.Alltitle_var.set("LVSi System")

        # 关闭窗口时用来通知后台线程
        self.EndEvent = threading.Event()

        # 图像尺寸、保存相关标志 —— 保持和旧 gui 一致
        self.img_shape = (728, 544)
        # self.west_img_shape = (364, 272)      # 旧版本GUI使用的参数；现在似乎不需要使用

        # 供相机模块使用的占位图 / 当前帧缓冲
        self.NonePng = cv2.imread(os.path.join(ASSETS.joinpath("empty.png")))
        if self.NonePng is None:
            import numpy as np
            self.NonePng = np.zeros((self.img_shape[1], self.img_shape[0], 3), dtype="uint8")
        self.img = self.NonePng

        self.save_frame = False
        self.save_path = None
        self.save_step = 0
        self.camera_settings = False
        self.default_ID = ""

        # 参数字典
        self.config_path = None  # 记住当前使用的“参数预设文件”的路径
        self.all_para_dict = all_para_dict.copy()
        self.param_vars = {}
        self.enum_meta = {}     # 记录枚举型参数的 mapping + combobox 变量

        # 路径 & 任务
        self.filepath_list = []
        self.output_filepath = "auto"
        # 兼容旧版 JFileChooser 的路径变量（process_java.file_chooser 会用到）
        self.path_var = tk.StringVar(self, value="")  # 输入路径字符串
        self.output_path_var = tk.StringVar(self, value="auto")  # 输出路径字符串
        self.current_path_var = tk.StringVar(self, value="")   # 预览图像路径字符串
        # 确保旧版文件所需的 StringVar 存在（path_var和output_path_var等）
        self._ensure_file_exsistence()
        # 当前预览的单个图像/视频文件（左侧第三行）
        self.current_file = ""

        self.task_list = []
        self.output_root = None
        self.task_mode = None

        # 流程节点 0:图像获取 1:噪声过滤 2:检测追踪 3:特征提取
        self.nodes = ["图像获取", "噪声过滤", "检测追踪", "特征提取"]   # 节点范围（0:图像获取 → 3:特征提取）
        self.program_start = 0
        self.program_end = 3

        # 运行状态（防止重复启动）
        self.searching = False
        self.running = False
        self.camera = False

        # 与参数弹窗共享的列表
        self.object_dict_list = []

        # =========== GUI：主题、配色、组件 ===========

        self.title("Image Processing System")
        self.geometry(f"{INIT_W}x{INIT_H}")
        self.minsize(LEFT_WIDTH + MID_WIDTH + 420, BASE_MIN_H)  # 初始一个保守最小宽度

        # Tk/ttk 本身没有“设置圆角半径”的选项。控件的圆角/直角是由主题的元素贴图决定的。
        # 尝试了几个主题，没有圆角矩形的按钮
        style = tb.Style(theme="flatly")        # 选中项的背景是灰色
        # style = tb.Style(theme="minty")

        # 改“info/primary”语义色
        style.colors.set("info", DARK_BLUE)
        style.colors.set("primary", DARK_BLUE)
        # style.colors.set("secondary", DARK_GREY)
        # style.colors.set("selectbg", MID_GREY)    # 修改combobox和menubar的选中背景

        # 顶部标题的样式
        style.configure("Topbar.TFrame", background=MID_GREY)
        style.configure("Topbar.TFrame.Label",
                        font=("Segoe UI Semibold", 16))

        # 左中右部件外层框架的样式
        style.configure("ParentBox.TLabelframe", background=WHITE)
        style.configure("ParentBox.TLabelframe.Label",
                        font=("Segoe UI Semibold", 14),
                        background=WHITE,
                        foreground=DARK_BLUE)
        # 子框架的样式
        style.configure("ChildBox.TLabelframe", background=WHITE)
        style.configure("ChildBox.TLabelframe.Label",
                        font=("Segoe UI Semibold", 12),
                        background=WHITE)
        # 标签的样式
        # cur_font_name = style.lookup("TNotebook.Tab", "font") or "TkDefaultFont"
        # cur_font = tkfont.nametofont(cur_font_name)
        style.configure("TNotebook.Tab",
                        font=("Segoe UI Semibold",10))      # 未选中的默认色
        style.map("TNotebook.Tab",
                  background=[("selected", DARK_BLUE)],
                  foreground=[("selected", "#ffffff")])

        # 组件的样式
        style.configure("ComponentItem.TFrame", background=WHITE)
        style.configure("ComponentItem.TFrame.Label",
                        # font=("Segoe UI Semibold", 10),   # 会同时修改所有的 label
                        background=WHITE)
        # Combobox 组件样式修改
        style.configure("TCombobox", background=WHITE)
        style.configure("TCombobox", arrowsize=14)
        style.configure("TCombobox", padding=(2, 4, 2, 4))

        # 让已经创建的风格刷新（若先设色再建控件，可以不用这行）
        style.theme_use(style.theme.name)

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self._build_menubar()
        self._build_main_layout()

        # 根据按钮实际宽度“动态锁定”最小宽度；并在窗口尺寸变化时强制不小于该宽度
        self.after(80, self._update_min_width)
        self.bind("<Configure>", self._enforce_min_width)


    # =============== 顶部菜单 ===============
    def _build_menubar(self):
        # 标题行容器（放图标 + 文本标题）
        bar = ttk.Frame(self, padding=(12, 6), style="Topbar.TFrame")
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)  # 让标题文本可向右展开

        # 1) 先创建“图标 Label”
        style = tb.Style()
        style.configure("TopbarIcon.TLabel", background=MID_GREY, borderwidth=0)
        self.title_img_label = ttk.Label(bar, style="TopbarIcon.TLabel")  # 先有这个控件，再去 config
        self.title_img_label.grid(row=0, column=0, sticky="w", padx=(0, 8))

        # 2) 再加载图标并设置（记得保存引用）
        def load_title_icon(icon_w, icon_h):  # 修改图标尺寸
            res = ASSETS.joinpath("logo.png")
            img = Image.open(res.open("rb")).convert("RGBA")
            # 裁成正方形并缩放
            s = min(img.width, img.height)
            x = (img.width - s) // 2;
            y = (img.height - s) // 2
            img = img.crop((x, y, x + s, y + s)).resize((icon_w, icon_h), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)

        self._title_icon = load_title_icon(100, 100)  # 你的函数：返回 PhotoImage
        if self._title_icon:
            self.title_img_label.configure(image=self._title_icon)
        else:
            # 加载失败就把图标位隐藏掉
            self.title_img_label.grid_remove()

        # 3) 标题文字
        ttk.Label(
            bar,
            textvariable=self.Alltitle_var,
            font=("Segoe UI Semibold", 16),
            background=MID_GREY
        ).grid(row=0, column=1, sticky="w")

        # 4) 系统菜单栏（位置固定在窗口顶，不在 bar 里显示）
        menubar = tk.Menu(self)  # 绑定到窗口本身，而不是 bar

        # ----- File -----
        m_file = tk.Menu(menubar, tearoff=False)

        m_file.add_command(label="Input Path", command=lambda: self._browse_input_path(self.entry_input))
        m_file.add_command(label="Output Path", command=lambda: self._browse_output_path(self.entry_output))
        m_file.add_separator()
        m_file.add_command(label="Exit", command=self.destroy)

        menubar.add_cascade(label="File", menu=m_file)

        # ---- Process ----
        m_proc = tk.Menu(menubar, tearoff=False)

        m_proc.add_command(label="Run", command=self._run)
        m_proc.add_command(label="Pause", command=self._pause)
        m_proc.add_command(label="Stop", command=self._stop)

        menubar.add_cascade(label="Process", menu=m_proc)

        # ---- Config ----
        m_config = tk.Menu(menubar, tearoff=False)

        m_config.add_command(label="Save", command=self._config_save)
        m_config.add_command(label="Save As", command=self._config_save_as)
        m_config.add_command(label="Load", command=self._config_load)

        menubar.add_cascade(label="Configs", menu=m_config)

        # ----- Help -----
        m_help = tk.Menu(menubar, tearoff=False)

        m_help.add_command(label="Docs", command=lambda: self._toast("Open Docs"))
        m_help.add_command(label="About", command=lambda: self._toast("Image Processing System"))

        menubar.add_cascade(label="Help", menu=m_help)

        self.configure(menu=menubar)

    # =============== 主体三列 ===============
    def _build_main_layout(self):
        wrap = ttk.Frame(self, padding=(12, 12))
        wrap.grid(row=1, column=0, sticky="nsew")

        # 左/中固定宽度，右列自适应
        wrap.columnconfigure(0, weight=0, minsize=LEFT_WIDTH)
        wrap.columnconfigure(1, weight=0, minsize=MID_WIDTH)
        wrap.columnconfigure(2, weight=1)
        wrap.rowconfigure(0, weight=1)

        # 左列
        self.left = ttk.Frame(wrap, width=LEFT_WIDTH)
        self.left.grid(row=0, column=0, sticky="nsw", padx=(0,8))
        self.left.grid_propagate(False)
        self.left.pack_propagate(False)
        self._build_file_group(self.left)
        self._build_process_group(self.left)

        # 中列（可滚动）
        self.mid = ttk.Frame(wrap, width=MID_WIDTH)
        self.mid.grid(row=0, column=1, sticky="nsw", padx=8)
        self.mid.grid_propagate(False)
        self.mid.pack_propagate(False)
        self._build_parameter_groups(self.mid)

        # 右列
        self.right = ttk.Frame(wrap)
        self.right.grid(row=0, column=2, sticky="nsew", padx=(8,0))
        self.right.columnconfigure(0, weight=1)
        self.right.rowconfigure(0, weight=8)
        self.right.rowconfigure(1, weight=0)
        self.right.rowconfigure(2, weight=0)
        self.right.rowconfigure(3, weight=0)

        self._build_view_area(self.right)
        self._build_progress_and_status(self.right)
        self._build_run_buttons(self.right)

    # ---- 左列：File（两行形式） ----
    def _param_row(self, parent, r, label):
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=4, padx=(0,6))
        ttk.Entry(parent).grid(row=r, column=1, sticky="ew", pady=4)

    def _build_file_group(self, parent):
        box = ttk.Labelframe(parent, text="File", padding=10, style="ParentBox.TLabelframe")
        box.pack(side="top", fill="x")

        def add_path(label_text, attr_name, text_var, callback):
            ttk.Label(box, text=label_text).pack(anchor="w", pady=(6, 2))
            row = ttk.Frame(box)
            row.pack(fill="x", pady=(0,4))
            row.columnconfigure(0, weight=1)

            # 绑定 StringVar 的行（Input / Output），Current 文件单独一个 entry
            if text_var is not None:
                entry = ttk.Entry(row, textvariable=text_var)
            else:
                entry = ttk.Entry(row)
            entry.grid(row=0, column=0, sticky="ew")

            ttk.Button(row, text="···", width=3, bootstyle="info",
                       command=lambda e=entry: callback(e)).grid(row=0, column=1, padx=(6,0))

            setattr(self, attr_name, entry)

        # 1) Input Path：沿用旧逻辑的“输入目录”（filepath_list + path_var + Preferences）
        add_path("Input Path:", "entry_input", self.path_var, self._browse_input_path)

        # 2) Output Path：沿用旧逻辑的“输出目录”（output_filepath + output_path_var + Preferences）
        add_path("Output Path:", "entry_output", self.output_path_var, self._browse_output_path)

        # 3) 当前浏览的单个图像文件（暂时只记录，不参与 pipeline）
        add_path("Current Browse Image File:", "entry_current_file", self.current_path_var, self._browse_current_file)

        # note: 增加按钮，设置 output path 为 auto

        # # 文件命名输入框
        # form = ttk.Frame(box)  # 容器使用 grid，两列布局
        # form.pack(fill="x", pady=(14,0))
        #
        # names = ["Bacteria", "Drug", "Time"]
        #
        # # 让右边输入框可拉伸
        # form.columnconfigure(1, weight=1)
        #
        # self.file_params = {}  # 保存引用，便于后面取值
        # for i, name in enumerate(names):
        #     # 直接复用你已有的行渲染方法
        #     self._param_row(form, i, name)  # ← 左标签 + 右 Entry
        #     # 把刚刚创建的 Entry 引用取出来保存（可选）
        #     # _param_row 创建的是该行最后一个 Entry，grid(row=i, column=1)
        #     entry = form.grid_slaves(row=i, column=1)[0]
        #     self.file_params[name] = entry

    def _build_process_group(self, parent):
        proc = ttk.Labelframe(parent, text="Process", padding=10, style="ParentBox.TLabelframe")
        proc.pack(side="top", fill="both", expand=True, pady=(8,0))

        # Process各步骤的初始值（默认进行全部操作）
        self.var_photo=tk.BooleanVar(value=True)
        self.var_noise=tk.BooleanVar(value=True)
        self.var_track=tk.BooleanVar(value=True)
        self.var_feat=tk.BooleanVar(value=True)

        for v,t in [(self.var_photo,"Image Acquisition"),
                    (self.var_noise,"Noise Filter"),
                    (self.var_track,"Cell Tracking"),
                    (self.var_feat,"Feature Extraction")]:
            ttk.Checkbutton(proc, text=t, variable=v,
                            bootstyle="round-toggle").pack(anchor="w", pady=8)

    def _update_program_range(self):
        """
        获取Process各步骤
        暂时不能跳步骤执行操作，如果运行了step2和step4，默认会把中间的step3也运行
        note: 后续把这部分的功能也拆出gui2.py
        """

        flags = [self.var_photo.get(),
                 self.var_noise.get(),
                 self.var_track.get(),
                 self.var_feat.get()]
        indices = [i for i, f in enumerate(flags) if f]
        if not indices:
            # 如果一个都没选，默认全流程
            self.program_start, self.program_end = 0, 3
        else:
            self.program_start = indices[0]
            self.program_end   = indices[-1]

    # ---- 中列（可滚动参数） ----
    def _build_parameter_groups(self, parent):
        """
        中列参数区：直接从 all_para_settings 生成 Camera / Filter / Tracking / Features
        """

        outer = ttk.Labelframe(parent, text="Configs",
                               padding=10, style="ParentBox.TLabelframe")
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        sc = VScrolled(outer)
        sc.grid(row=0, column=0, sticky="nsew", pady=(2,0))

        # 每次重建参数界面时重置变量字典
        self.param_vars = {}
        self.enum_meta = {}

        blocks = [
            ("camera", "Camera"),
            ("preprocess", "Filter"),
            ("trackmate", "Tracking"),
            ("features", "Features"),
        ]

        for key, title in blocks:
            box = Collapsible(sc.content, text=title, style="ChildBox.TLabelframe")
            box.pack(fill="x", pady=(0, 8))
            # 用 detail 模式，把该类的所有参数都展开到中列
            self._build_param_block(box.body, key, mode="detail")

    def _build_param_block(self, parent, block_key: str, mode: str = "detail"):
        """
        按 all_para_settings[block_key][mode] 在 parent 里生成控件
        """
        settings = all_para_settings.get(block_key, {})
        items = settings.get(mode, [])

        for item in items:
            # e.g. {"str": "噪声过滤", "name": "", "type": "label"}
            value_type = item["type"]
            name = item["name"]
            label_text = item["str"]

            # 1) 纯 label 型：只显示分组标题/小节标题（进行字体加粗）
            if value_type == "label":
                text = label_text or name or ""
                if not text:
                    continue
                ttk.Label(parent, text=text, style="ComponentItem.TFrame.Label",
                          font=("Segoe UI Semibold", 10)).pack(fill="x", pady=(12, 8))
                continue

            # 2) 其他类型：一行一个“名称 + 控件”
            row = ttk.Frame(parent, style="ComponentItem.TFrame")
            row.pack(fill="x", pady=4)

            ttk.Label(row, text=label_text or name,
                      style="ComponentItem.TFrame.Label",
                      width=26, anchor="w").pack(side="left")

            var = self._create_param_var(name, value_type)

            # 数值/字符串：Entry
            if value_type in ("int", "float", "str"):
                entry = ttk.Entry(row, textvariable=var, width=12)
                entry.pack(side="left", fill="x", expand=True)

            # 布尔量：Checkbutton
            elif value_type == "bool":
                chk = ttk.Checkbutton(row, variable=var, bootstyle="round-toggle")
                chk.pack(side="left", padx=4)

            # 字典：Combobox
            elif isinstance(value_type, dict):
                # val: 数字类型存储
                # name: 字符类型存储

                # 1. 真实存储用 IntVar，初始值仍然来自 all_para_dict[name]（0/1/2/3）
                var_val = self._create_param_var(name, "int")

                # 2. 显示用的选项名列表 & 数值映射
                # value_type 形如 {"Adaptive":0,"Bpp8":1,"Bpp10":2,"Bpp12":3}
                options = list(value_type.keys())
                val_to_name = {i: j for j, i in value_type.items()}     # type == dict
                name_to_val = {i: j for i, j in value_type.items()}     # type == dict

                # 获取当前选项的 val
                cur_val = var_val.get()
                # 通过 val_to_name 字典获取当前选项的 name
                cur_name = val_to_name.get(cur_val, options[0])

                # 3. 下拉框用 StringVar 保存 "Adaptive"/"Bpp8"...
                combo_list = tk.StringVar(value=cur_name)
                combo = ttk.Combobox(row, textvariable=combo_list,
                    values=options, state="readonly", width=12)
                combo.pack(side="left", fill="x", expand=True)

                # 4. 当用户选择变化时：反向写回 IntVar
                def on_combo_changed(*_):
                    # 获取当前选项的 name
                    sel_name = combo_list.get()
                    # 通过 name_to_val 字典获取当前选项的 val
                    if sel_name in options:
                        sel_val = name_to_val.get(sel_name, options[0])
                        var_val.set(sel_val)

                combo_list.trace_add("write", on_combo_changed)

                # 记录这个枚举参数的 mapping + combobox 变量，方便 Load 时反向同步
                if not hasattr(self, "enum_meta"):
                    self.enum_meta = {}
                self.enum_meta[name] = (value_type, combo_list)

    def _create_param_var(self, name: str, value_type):
        """
        创建或复用一个 tk.Variable，并用 all_para_dict 里的当前值初始化
        value_type 可以是 "int"/"float"/"str"/"bool" 或 dict(枚举)
        """
        if name in self.param_vars:
            return self.param_vars[name]

        current = self.all_para_dict.get(name)

        if isinstance(value_type, dict):
            # 枚举，用 IntVar 保存索引/编号
            v = tk.IntVar(value=int(current) if current is not None else 0)
        elif value_type == "int":
            v = tk.IntVar(value=int(current) if current is not None else 0)
        elif value_type == "float":
            v = tk.DoubleVar(value=float(current) if current is not None else 0.0)
        elif value_type == "bool":
            v = tk.BooleanVar(value=bool(current) if current is not None else False)
        else:  # "str" 或其他
            v = tk.StringVar(value="" if current is None else str(current))

        self.param_vars[name] = v
        return v


    # ---- 右列：图像 + 标签 ----
    def _build_view_area(self, parent):
        # tabs = ttk.Notebook(parent, bootstyle="info")
        tabs = ttk.Notebook(parent, style="TNotebook")
        tabs.grid(row=0, column=0, sticky="nsew")

        # 保存引用，后面 tab 切换和刷新要用
        self.tabs_view = tabs
        tabs.bind("<<NotebookTabChanged>>", self._on_view_tab_changed)

        for name in ["Camera", "Original","Processed","Tracked"]:
            frame = ttk.Frame(tabs, padding=6)
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)
            tabs.add(frame, text=name)

            if name == "Camera":
                # 相机专用容器，用来拿 HWND 给 vimbaX
                cam_frame = tk.Frame(frame, bg="black")
                cam_frame.grid(row=0, column=0, sticky="nsew")

                # 保存起来，ImageMixin 里会用到
                self.camera_container = cam_frame
            else:
                canvas = tk.Canvas(frame, bg="#0b0c0e", highlightthickness=0)
                canvas.grid(row=0, column=0, sticky="nsew")
                canvas.bind("<Configure>", lambda e, c=canvas: self._ensure_square(c))
                setattr(self, f"canvas_{name.lower()}", canvas)

    def _on_view_tab_changed(self, event):
        """
        切换 Camera / Original / Processed / Tracked 时调用对应更新函数。
        """
        tabs = event.widget
        idx = tabs.index("current")
        name = tabs.tab(idx, "text")

        if name == "Camera":
            # 调用 ImageMixin 里的函数，启动相机
            self._start_camera()
        elif name == "Original":
            self._update_original_view()
        elif name == "Processed":
            self._update_processed_view()
        elif name == "Tracked":
            self._update_tracked_view()

    def _ensure_square(self, canvas):
        w,h = canvas.winfo_width(), canvas.winfo_height(); side = min(w,h)
        canvas.delete("border")
        px,py = (w-side)//2,(h-side)//2
        canvas.create_rectangle(px,py,px+side,py+side, outline="#334155", width=2, tags="border")

    # ---- 右列：进度 + 状态 ----
    def _build_progress_and_status(self, parent):
        self.prog = ttk.Progressbar(parent, bootstyle="info-striped", mode="determinate", maximum=100, value=0)
        self.prog.grid(row=1, column=0, sticky="ew", pady=(8,2))
        self.progress = self.prog  # 旧 GUI 里用的是 self.progress

        # 状态文本：用 StringVar，兼容旧的 status_var.set(...)
        self.status_var = tk.StringVar(value="Ready.")
        self.status = ttk.Label(parent, textvariable=self.status_var, font=("Segoe UI", 9), foreground="#64748b")
        self.status.grid(row=2, column=0, sticky="ew", pady=(2,8))

    # ---- 右列：按钮 ----
    def _build_run_buttons(self, parent):
        row = ttk.Frame(parent)
        row.grid(row=3, column=0, sticky="ew", pady=(6,0))

        # 两侧留白列可伸缩，中间放按钮
        row.columnconfigure(0, weight=1)  # 左留白
        row.columnconfigure(1, weight=0)  # 中间按钮容器
        row.columnconfigure(2, weight=1)  # 右留白

        btns = ttk.Frame(row, name="btns")
        btns.grid(row=0, column=1)      # 按钮放在中间列

        self.btn_run = ttk.Button(btns, text="Run",   bootstyle="info", width=8, command=self._run)
        self.btn_run.grid(row=0, column=0, padx=(0, 20))
        self.btn_pause = ttk.Button(btns, text="Pause", bootstyle="info", width=8, command=self._pause)
        self.btn_pause.grid(row=0, column=1, padx=(0, 20))
        self.btn_stop = ttk.Button(btns, text="Stop",  bootstyle="info",  width=8, command=self._stop)
        self.btn_stop.grid(row=0, column=2)

        self._btns_container = btns

    # =============== 行为占位 ===============

    def _draw_dummy(self, canvas):
        # note: 检查用处
        canvas.delete("content")
        w,h=canvas.winfo_width(),canvas.winfo_height()
        s=min(w,h)
        x0,y0=(w-s)//2,(h-s)//2
        canvas.create_rectangle(x0,y0,x0+s,y0+s, fill="#1f4f99", outline="", tags="content")

    def _run(self):
        self.status_var.set("Running…")
        self.prog.configure(value=10)
        self.after(120, lambda: self.prog.configure(value=35))

    def _pause(self):
        self.status_var.set("Paused.")

    def _stop(self):
        self.status_var.set("Stopped.")
        self.prog.configure(value=0)

    def _toast(self, msg, title="Info", bootstyle="info"):
        ToastNotification(title=title, message=msg, duration=1800, bootstyle=bootstyle).show_toast()

    # ====== 最小宽度：动态计算并强制不小于 ======
    def _update_min_width(self):
        """
        根据左/中固定宽度 + 右侧按钮所需宽度 + 边距，计算并锁定窗口最小宽度
        """
        self.update_idletasks()
        left_w = LEFT_WIDTH
        mid_w  = MID_WIDTH
        btns_w = self._btns_container.winfo_reqwidth()
        # 外层左右内边距：wrap 的 padding(12) × 2，加三列之间的 padx：8+8
        margins = 12*2 + 8 + 8
        min_w = left_w + mid_w + btns_w + margins + 24  # 额外余量
        # 锁定：不能小于 min_w
        self.wm_minsize(min_w, BASE_MIN_H)
        self._min_w_cached = min_w

    def _enforce_min_width(self, event):
        """
        拖拽缩放时，若宽度小于计算值，立即回弹到最小宽度
        """
        if getattr(self, "_min_w_cached", None) is None:
            return
        cur_w = self.winfo_width()
        if cur_w < self._min_w_cached:
            self.geometry(f"{self._min_w_cached}x{max(self.winfo_height(), BASE_MIN_H)}")

if __name__ == "__main__":
    App().mainloop()
