import os, sys
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as tb
from ttkbootstrap import ttk
from PIL import Image, ImageTk
import numpy as np
import importlib
from importlib.resources import files
import threading
from ttkbootstrap.toast import ToastNotification
from pathlib import Path

from gui2_file import FileMixin
from gui2_mode import ModeMixin
from gui2_config import ConfigMixin
from gui2_image import ImageMixin
from gui2_button import ButtonMixin

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
    """纵向滚动容器：内容高度不足时自动隐藏滚动条。"""

    def __init__(self, master, bg=WHITE, **kw):
        super().__init__(master, **kw)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=bg)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.vsb.grid(row=0, column=1, sticky="ns", padx=(8, 0))

        # 关键：先有 vsb，才能设置 yscrollcommand
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.content = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self._content_w = 0
        self._content_h = 0
        self._vsb_visible = True
        self._update_job = None

        self.content.bind("<Configure>", self._on_content_config, add="+")
        self.canvas.bind("<Configure>", self._on_canvas_config, add="+")
        self._bind_wheel(self)

        # 初始先判断一次（内容可能为空）
        self.after_idle(self._apply_update)

    def _on_content_config(self, event):
        self._content_w = int(event.width)
        self._content_h = int(event.height)
        self._schedule_update()

    def _on_canvas_config(self, event):
        # 让 content 宽度跟随 canvas（内容会因此换行/高度变化）
        self.canvas.itemconfig(self._win, width=int(event.width))
        self._schedule_update()

    def _schedule_update(self):
        if self._update_job is not None:
            try:
                self.after_cancel(self._update_job)
            except Exception:
                pass
        self._update_job = self.after_idle(self._apply_update)

    def _apply_update(self):
        self._update_job = None

        cw = max(1, int(self.canvas.winfo_width()))
        ch = max(1, int(self._content_h))

        # 用 content 实际尺寸设置 scrollregion（比 bbox("all") 更稳定）
        self.canvas.configure(scrollregion=(0, 0, max(cw, self._content_w), ch))

        self._update_vsb_visibility()

    def _update_vsb_visibility(self):
        canvas_h = max(1, int(self.canvas.winfo_height()))
        content_h = int(self._content_h)

        # 余量，避免临界抖动
        need_scroll = content_h > (canvas_h + 2)

        if need_scroll and not self._vsb_visible:
            self.vsb.grid()  # 恢复显示
            self._vsb_visible = True
        elif (not need_scroll) and self._vsb_visible:
            self.vsb.grid_remove()  # 隐藏但保留 grid 配置
            self._vsb_visible = False
            self.canvas.yview_moveto(0)

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
        # 不需要滚动时，直接忽略滚轮，避免“空滚”
        if not self._vsb_visible:
            return

        delta = -1 if getattr(event, "num", 0) == 4 else (1 if getattr(event, "num", 0) == 5 else -int(event.delta / 120))
        self.canvas.yview_scroll(delta, "units")

# note: 在中部 Config 列暂无子模块分区时，不需要启用 Collapsible
# class Collapsible(ttk.Labelframe):
#     def __init__(self, master, text="", toggle=False, *args, **kwargs):
#         super().__init__(master, text=text, padding=8, *args, **kwargs)
#         self.columnconfigure(0, weight=1)
#         self.body = ttk.Frame(self)
#         self.body.grid(row=0, column=0, sticky="ew")
#         self._collapsed = False
#         self._btn = None
#
#         if toggle:
#             self._btn = ttk.Button(self, text="−", width=2, command=self._toggle)
#             self._btn.place(relx=1.0, x=-8, y=-2, anchor="ne")
#
#     def _toggle(self):
#         if self._btn is None:
#             return  # 关闭了折叠功能
#         if self._collapsed:
#             self.body.grid(); self._btn.config(text="−")
#         else:
#             self.body.grid_remove(); self._btn.config(text="+")
#         self._collapsed = not self._collapsed


class App(FileMixin, ModeMixin, ConfigMixin, ImageMixin, ButtonMixin, tb.Window):
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

        # ---- 让 camera/ process 目录可 import（与 gui2 文件夹同级）----
        self._ensure_project_root_on_syspath()

        # ---- 准备按钮 actions（ButtonMixin 会调用）----
        self._capture_actions = self._make_capture_actions()
        self._process_actions = self._make_process_actions()

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

        # 确保旧版文件所需的 StringVar 存在（path_var和output_path_var等）
        self.camera_path_var = tk.StringVar(self, value="")  # 相机拍摄存储路径字符串
        self.input_path_var = tk.StringVar(self, value="")  # 输入路径字符串
        self.output_path_var = tk.StringVar(self, value="")  # 输出路径字符串
        self.current_path_var = tk.StringVar(self, value="")  # 预览图像路径字符串
        self._ensure_file_exsistence()
        # 路径 & 任务
        self.filepath_list = []
        self.output_filepath = "auto"
        # 当前预览的单个图像/视频文件（左侧第三行）
        self.current_file = ""

        self.task_list = []
        self.output_root = None
        self.task_mode = None

        # note: 旧版代码，修改中
        # 流程节点 0:图像获取 1:噪声过滤 2:检测追踪 3:特征提取
        self.nodes = ["图像获取", "噪声过滤", "检测追踪", "特征提取"]   # 节点范围（0:图像获取 → 3:特征提取）
        self.program_start = 0
        self.program_end = 3

        # 供相机模块使用的占位图 / 当前帧缓冲
        try:
            with ASSETS.joinpath("empty.png").open("rb") as f:
                img = Image.open(f).convert("RGB")
                arr = np.array(img, dtype=np.uint8)
                # _show_ndarray_on_canvas 对 3 通道默认做 BGR->RGB，
                # 所以这里建议存成 BGR，避免颜色颠倒
                self.NonePng = arr[:, :, ::-1]
        except Exception as e:
            print("[Camera WARN] empty.png load failed:", e)
            self.NonePng = np.zeros((self.img_shape[1], self.img_shape[0], 3), dtype=np.uint8)

        # 若相机未连接，self.img为None，则无法成功保存
        # self.img = self.NonePng
        self.img = None
        self._img_lock = threading.Lock()

        self.live_flag = False
        self.img_froze = None

        # 窗口缩放相关设置
        self._is_resizing = False
        self._resize_job = None
        self.bind("<Configure>", self._on_root_resize, add="+")

        # Mode 选择
        # 0: Capture(默认)  1: Process
        self.mode = tk.IntVar(value=0)
        # Capture 是否启动预览
        self.preview_flag = tk.BooleanVar(value=False)  # 默认关

        # Preview background (in-memory)
        self.preview_background = None  # numpy.ndarray or None
        # self.preview_background_meta = None  # dict: dtype/shape/pixfmt/time etc.
        self.img_preview = None

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
        self.after(80, self._update_min_constraints)
        self.bind("<Configure>", self._enforce_min_constraints)

    # =============== 顶部菜单 ===============
    def _build_menubar(self):
        # 标题行容器（放图标 + 文本标题）
        bar = ttk.Frame(self, padding=(12, 6), style="Topbar.TFrame")
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)  # 让标题文本可向右展开
        self.topbar = bar

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

        m_file.add_command(label="Camera Save Path", command=lambda: self._browse_camera_path(self.entry_camera))
        m_file.add_command(label="Process Input Path", command=lambda: self._browse_input_path(self.entry_input))
        m_file.add_command(label="Process Output Path", command=lambda: self._browse_output_path(self.entry_output))
        m_file.add_command(label="Current Browse File", command=lambda: self._browse_current_path(self.entry_current))
        m_file.add_separator()
        m_file.add_command(label="Exit", command=self.destroy)

        menubar.add_cascade(label="File", menu=m_file)

        # ---- Process ----
        m_proc = tk.Menu(menubar, tearoff=False)

        # m_proc.add_command(label="Run", command=self._run)
        # m_proc.add_command(label="Pause", command=self._pause)
        # m_proc.add_command(label="Stop", command=self._stop)

        menubar.add_cascade(label="Process", menu=m_proc)

        # ---- Config ----
        m_config = tk.Menu(menubar, tearoff=False)

        m_config.add_command(label="Save", command=self._config_save)
        m_config.add_command(label="Save As", command=self._config_save_as)
        m_config.add_command(label="Load", command=self._config_load)

        menubar.add_cascade(label="Config", menu=m_config)

        # ----- Help -----
        m_help = tk.Menu(menubar, tearoff=False)

        m_help.add_command(label="Docs", command=lambda: self._toast("Open Docs"))
        m_help.add_command(label="About", command=lambda: self._toast("Image Processing System"))

        menubar.add_cascade(label="Help", menu=m_help)

        self.configure(menu=menubar)

    # =============== 主体三列绘制 ===============
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
        self._build_mode_group(self.left, on_mode_changed=self._on_mode_changed_main)

        # 中列（可滚动）
        self.mid = ttk.Frame(wrap, width=MID_WIDTH)
        self.mid.grid(row=0, column=1, sticky="nsw", padx=8)
        self.mid.grid_propagate(False)
        self.mid.pack_propagate(False)
        self._build_config_groups(self.mid)

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
        self._build_button_bar(self.right, self._capture_actions, self._process_actions)

    # ---- 中列（可滚动参数） ----
    def _build_config_groups(self, parent):
        """
        中列参数区：直接从 all_para_settings 生成 Camera / Filter / Tracking / Features
        """

        # 绘制最外层的 Config 边框
        outer = ttk.Labelframe(parent, text="Config",
                               padding=10, style="ParentBox.TLabelframe")
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        sc = VScrolled(outer)
        sc.grid(row=0, column=0, sticky="nsew", pady=(2,0))

        # 每次重建参数界面时重置变量字典
        self.param_vars = {}
        self.enum_meta = {}

        # 绘制内部子分区的外框
        # note: 因为目前还没对 gui2_para.py 中的参数作分区适配
        #       所以暂时延用旧版分区方法，分隔显示直接在 gui2_para.py 中设置，此处先注释
        # blocks = [
        #     ("camera", "Camera"),
        #     ("preprocess", "Filter"),
        #     ("trackmate", "Tracking"),
        #     ("features", "Features"),
        # ]
        #
        # for key, title in blocks:
        #     box = Collapsible(sc.content, text=title, style="ChildBox.TLabelframe")
        #     box.pack(fill="x", pady=(0, 8))
        #     # 用 detail 模式，把该类的所有参数都展开到中列
        #     self._build_param_block(box.body, key, mode="detail")

        # 不绘制子分区外框，把参数分区在 gui2_para.py 中设置
        # 此处仅按顺序绘制出所有的参数
        section = ttk.Frame(sc.content, style="ComponentItem.TFrame")
        section.pack(fill="x", padx=6)

        # for key in all_para_settings.keys():
        #     self._build_param_block(sc.content, key, mode="detail")
        mode = int(self.mode.get()) if hasattr(self, "mode") else 0
        for key in self._config_blocks_for_mode(mode):
            if mode == 0:
                self._build_param_block(sc.content, key, mode="detail")
            else:
                self._build_param_block(sc.content, key, mode="brief")

    def _config_blocks_for_mode(self, mode: int):
        keys = list(all_para_settings.keys())

        if int(mode) == 0:
            # Capture：仅显示 camera + load
            preferred = ["camera"]
        elif int(mode) == 1:
            # Process：显示全部
            preferred = ["preprocess", "trackmate", "features"]
        else:
            return keys

        allow = [k for k in preferred if k in all_para_settings]
        if allow:
            return allow
        else:
            return keys

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

            # 参数名称显示（宽度可调整）
            ttk.Label(row, text=label_text or name,
                      style="ComponentItem.TFrame.Label",
                      width=18, anchor="w").pack(side="left")

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

    def _apply_config_mode(self, mode: int):
        # 先把当前 UI 里编辑过的参数写回 all_para_dict，避免丢修改
        try:
            self._sync_dict_from_vars()
        except Exception:
            pass

        # 重建中列（mid）
        if not hasattr(self, "mid") or self.mid is None:
            return

        for child in self.mid.winfo_children():
            child.destroy()

        self._build_config_groups(self.mid)

        # 可选：重算一次最小尺寸（你已有这套机制）
        self.after_idle(self._update_min_constraints)

    # ---- 右列：进度 + 状态 ----
    def _build_progress_and_status(self, parent):
        self.prog = ttk.Progressbar(parent, bootstyle="info-striped", mode="determinate", maximum=100, value=0)
        self.prog.grid(row=1, column=0, sticky="ew", pady=(8,2))
        self.progress = self.prog  # 旧 GUI 里用的是 self.progress

        # 状态文本：用 StringVar，兼容旧的 status_var.set(...)
        self.status_var = tk.StringVar(value="Ready.")
        self.status = ttk.Label(parent, textvariable=self.status_var, font=("Segoe UI", 9), foreground="#64748b")
        self.status.grid(row=2, column=0, sticky="ew", pady=(2,8))

    # =============== 行为占位 ===============

    def _draw_dummy(self, canvas):
        # note: 检查用处
        canvas.delete("content")
        w,h=canvas.winfo_width(),canvas.winfo_height()
        s=min(w,h)
        x0,y0=(w-s)//2,(h-s)//2
        canvas.create_rectangle(x0,y0,x0+s,y0+s, fill="#1f4f99", outline="", tags="content")

    def _toast(self, msg, title="Info", bootstyle="info"):
        ToastNotification(title=title, message=msg, duration=1800, bootstyle=bootstyle).show_toast()

    # ====== 显示的内容随 self.mode 改变 ======
    def _on_mode_changed_main(self, mode: int):
        """
        mode切换时，改变显示布局
        """

        # 切换 Config 列显示内容
        self._apply_config_mode(int(mode))

        # 切换 tab 显示
        if hasattr(self, "_apply_view_mode"):
            try:
                self._apply_view_mode(int(mode))
            except Exception:
                pass

        # 切换底部按钮
        if hasattr(self, "_apply_button_mode"):
            self._apply_button_mode(int(mode))

        # 重新计算最小宽度 & 高度
        self.after_idle(self._update_min_constraints)

    def _ensure_project_root_on_syspath(self):
        """
        你的工程结构：camera/ 与 gui2/ 同级，process/ 与 gui2/ 同级。
        这里把“gui2 文件夹的上一级”加入 sys.path，确保 `import camera.xxx` 可用。
        """
        here = Path(__file__).resolve()
        # 如果 gui2.py 在 gui2/ 目录里，则 project_root = gui2/ 的父目录
        project_root = here.parent.parent if here.parent.name.lower() == "gui2" else here.parent
        p = str(project_root)
        if p not in sys.path:
            sys.path.insert(0, p)

    def _import_func(self, module_name: str, func_name: str):
        """
        note:
        动态导入 module 并取出函数。
        你只需要把下面 _make_capture_actions/_make_process_actions 里
        的 module_name/func_name 改成你真实文件里的名字。
        """
        mod = importlib.import_module(module_name)
        fn = getattr(mod, func_name)
        return fn

    def _call_maybe_with_self(self, fn):
        """
        兼容两种实现：
        - 外部函数签名：fn(self)   （推荐，便于拿到 GUI 状态）
        - 外部函数签名：fn()       （也支持）
        """
        try:
            return fn(self)
        except TypeError:
            return fn()

    # ====== 窗口刷新相关 ======
    def _on_root_resize(self, event=None):
        # 最小化时不算 resize
        try:
            if self.state() == "iconic":
                return
        except Exception:
            pass

        self._is_resizing = True
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(180, self._end_root_resize)

    def _end_root_resize(self):
        self._resize_job = None
        self._is_resizing = False

    # ====== 最小宽度 & 高度：动态计算并强制不小于 ======
    def _calc_min_height(self) -> int:
        """
        计算最小高度：保证左侧 File + Mode 完整显示。
        """
        self.update_idletasks()

        top_h = 0
        if hasattr(self, "topbar") and self.topbar is not None:
            try:
                top_h = self.topbar.winfo_reqheight()
            except Exception:
                top_h = 0

        file_h = 0
        if hasattr(self, "file_group_box") and self.file_group_box is not None:
            try:
                file_h = self.file_group_box.winfo_reqheight()
            except Exception:
                file_h = 0

        mode_h = 0
        if hasattr(self, "mode_group_box") and self.mode_group_box is not None:
            try:
                mode_h = self.mode_group_box.winfo_reqheight()
            except Exception:
                mode_h = 0

        # wrap padding(top/bottom)=12*2；Mode pack 有 pady=(8,0) -> gap=8
        wrap_pad = 12 * 2
        gap = 8
        extra = 24  # 安全余量（OS 装饰/字体差异）

        min_h = top_h + wrap_pad + file_h + gap + mode_h + extra
        return max(BASE_MIN_H, int(min_h))

    def _update_min_constraints(self):
        """
        锁定最小宽度 + 最小高度。
        """
        self.update_idletasks()

        left_w = LEFT_WIDTH
        mid_w = MID_WIDTH
        btns_w = self._btns_container.winfo_reqwidth() if hasattr(self, "_btns_container") else 0

        # wrap padding(12)*2 + column gaps: 左列/中列/右列间 8+8
        margins = 12 * 2 + 8 + 8
        min_w = left_w + mid_w + btns_w + margins + 24
        min_h = self._calc_min_height()

        self.wm_minsize(int(min_w), int(min_h))
        self._min_w_cached = int(min_w)
        self._min_h_cached = int(min_h)

    def _enforce_min_constraints(self, event):
        """
        拖拽缩放时，防止小于最小宽/高。
        """
        if getattr(self, "_min_w_cached", None) is None or getattr(self, "_min_h_cached", None) is None:
            return

        cur_w = self.winfo_width()
        cur_h = self.winfo_height()

        min_w = self._min_w_cached
        min_h = self._min_h_cached

        if cur_w < min_w or cur_h < min_h:
            self.geometry(f"{max(cur_w, min_w)}x{max(cur_h, min_h)}")

    # 兼容旧名字（如果别处仍调用）
    def _update_min_width(self):
        self._update_min_constraints()

    def _enforce_min_width(self, event):
        self._enforce_min_constraints(event)

    # ==================== 函数映射 ====================
    # 在 gui2.py 里实现两个 action 映射（把真实函数绑进来）

    def _make_capture_actions(self) -> dict:
        """
        note:
        Capture 模式按钮 -> camera 文件夹里的功能函数
        你需要把 module/function 名称改成你真实的实现。
        """
        return {
            # 相机实时显示
            "cam_live": lambda: self._call_maybe_with_self(
                self._import_func("camera.camera_live", "start_live")
            ),

            # 相机暂停实时显示
            "cam_stop_live": lambda: self._call_maybe_with_self(
                self._import_func("camera.camera_live", "stop_live")
            ),

            # 拍摄单张图像
            "cam_snap": lambda: self._call_maybe_with_self(
                self._import_func("camera.camera_capture", "capture_single")
            ),

            # 录制视频
            "cam_rec": lambda: self._call_maybe_with_self(
                self._import_func("camera.camera_record", "start_record")
            ),

            # 结束录制视频
            "cam_rec_stop": lambda: self._call_maybe_with_self(
                self._import_func("camera.camera_record", "stop_record")
            ),
        }

    def _make_process_actions(self) -> dict:
        """
        Process 模式按钮 -> process 文件夹里的功能函数
        你需要把 module/function 名称改成你真实的实现。
        """
        return {
            "play": lambda: self._call_maybe_with_self(
                self._import_func("process.process_player", "play")
            ),
            "pause": lambda: self._call_maybe_with_self(
                self._import_func("process.process_player", "pause")
            ),
            "to_start": lambda: self._call_maybe_with_self(
                self._import_func("process.process_player", "seek_to_start")
            ),
            "back_2s": lambda: self._call_maybe_with_self(
                self._import_func("process.process_player", "seek_back_2s")
            ),
            "forward_2s": lambda: self._call_maybe_with_self(
                self._import_func("process.process_player", "seek_forward_2s")
            ),
            "run_proc": lambda: self._call_maybe_with_self(
                self._import_func("process.process_runner", "run_processing")
            ),
        }


if __name__ == "__main__":
    App().mainloop()
