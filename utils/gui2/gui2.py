import os
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as tb
from ttkbootstrap import ttk
from importlib.resources import files
from PIL import Image, ImageTk
import cv2
import threading

from _para import all_para_dict, base_path
from utils.process.process_java import new_file_chooser
from utils.process.process_dir_seeker import path_finding_thread
from utils.camera.ast_loop import camera_mode_manager
from utils.gui.gui_para_window import create_modal_window


# LIGHT_BLUE = "#53a7d8"
DARK_BLUE = "#135ecb"
# LIGHT_GREY = "#f4f7fb"
LIGHT_GREY = "#ffffff"      # background color, temporary changed to white
MID_GREY = "#e9eef5"
DARK_GREY = "#53a7d8"

LEFT_WIDTH = 360          # 左列固定宽度
MID_WIDTH  = 480          # 中列固定宽度=左列
BASE_MIN_H = 760          # 最小高度
INIT_W, INIT_H = 1520, 940  # 初始窗口更大，右侧图像区更宽
# INIT_W, INIT_H = 1680, 945  # OBS采集比例

ASSETS = files("utils.gui2.gui_assets")  # 指向包
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

    # def _toggle(self):
    #     self._collapsed = not self._collapsed
    #     (self.body.grid_remove() if self._collapsed else self.body.grid())
    #     self._btn.config(text="+" if self._collapsed else "−")

class App(tb.Window):
    def __init__(self):
        super().__init__(themename="minty")
        # Tk/ttk 本身没有“设置圆角半径”的选项。控件的圆角/直角是由主题的元素贴图决定的。
        # 尝试了几个主题，没有圆角矩形的按钮

        # ===== 兼容旧 GUI 的核心状态 =====
        # 兼容旧代码写法
        self.root = self

        # 关闭窗口时用来通知后台线程
        self.EndEvent = threading.Event()

        # 图像尺寸、保存相关标志 —— 保持和旧 gui 一致
        self.img_shape = (728, 544)
        self.west_img_shape = (364, 272)

        self.save_frame = False
        self.save_path = None
        self.save_step = 0
        self.camera_settings = False
        self.default_ID = ""

        # 参数字典
        self.all_para_dict = all_para_dict.copy()

        # 路径 & 任务
        self.filepath_list = []
        self.output_filepath = "auto"
        self.task_list = []
        self.output_root = None
        self.task_mode = None

        # 流程节点 0:图像获取 1:噪声过滤 2:检测追踪 3:特征提取
        # note: not sure
        self.nodes = ['图像获取', '噪声过滤', '检测追踪', '特征提取']
        # 节点范围（0:图像获取 → 3:特征提取）
        self.program_start = 0
        self.program_end = 3

        # 运行状态（防止重复启动）
        self.searching = False
        self.running = False
        self.camera = False

        # 与参数弹窗共享的列表
        self.object_dict_list = []

        # ========= 新 GUI 的组件 =========
        self.title("Image Processing System")
        self.geometry(f"{INIT_W}x{INIT_H}")
        self.minsize(LEFT_WIDTH + MID_WIDTH + 420, BASE_MIN_H)  # 初始一个保守最小宽度

        style = tb.Style(theme="minty")

        # 改“info/primary”语义色
        style.colors.set("info", DARK_BLUE)
        style.colors.set("primary", DARK_BLUE)
        # style.colors.set("secondary", DARK_GREY)

        # 顶部标题的样式
        style.configure("Topbar.TFrame", background=MID_GREY)
        style.configure("Topbar.TFrame.Label",
                        font=("Segoe UI Semibold", 16))
        # 左中右部件外层框架的样式
        style.configure("ParentBox.TLabelframe", background=LIGHT_GREY)
        style.configure("ParentBox.TLabelframe.Label",
                        font=("Segoe UI Semibold", 14),
                        background=LIGHT_GREY,
                        foreground=DARK_BLUE)
        # 子框架的样式
        style.configure("ChildBox.TLabelframe", background=LIGHT_GREY)
        style.configure("ChildBox.TLabelframe.Label",
                        font=("Segoe UI Semibold", 12),
                        background=LIGHT_GREY)
        # 标签的样式
        # cur_font_name = style.lookup("TNotebook.Tab", "font") or "TkDefaultFont"
        # cur_font = tkfont.nametofont(cur_font_name)
        style.configure("TNotebook.Tab",
                        font=("Segoe UI Semibold",10))      # 未选中的默认色
        style.map("TNotebook.Tab",
                  background=[("selected", DARK_BLUE)],
                  foreground=[("selected", "#ffffff")])

        # 组件的样式
        style.configure("ComponentItem.TFrame", background=LIGHT_GREY)
        style.configure("ComponentItem.TFrame.Label",
                        # font=("Segoe UI Semibold", 10),
                        background=LIGHT_GREY)

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
            text="Image Processing System",
            font=("Segoe UI Semibold", 16),
            background=MID_GREY
        ).grid(row=0, column=1, sticky="w")

        # 4) 系统菜单栏（位置固定在窗口顶，不在 bar 里显示）
        menubar = tk.Menu(self)  # 绑定到窗口本身，而不是 bar
        m_file = tk.Menu(menubar, tearoff=False)
        for lbl, cmd in [("Open...", self._file_open), ("Save", lambda: self._toast("Saved")),
                         ("Save As...", lambda: self._toast("Save As")), (None, None), ("Exit", self.destroy)]:
            (m_file.add_separator() if lbl is None else m_file.add_command(label=lbl, command=cmd))
        menubar.add_cascade(label="File", menu=m_file)

        m_proc = tk.Menu(menubar, tearoff=False)
        for lbl, cmd in [("Run", self._run), ("Pause", self._pause), ("Stop", self._stop)]:
            m_proc.add_command(label=lbl, command=cmd)
        menubar.add_cascade(label="Process", menu=m_proc)

        m_param = tk.Menu(menubar, tearoff=False)
        m_param.add_command(label="Save", command=lambda: self._toast("Save Preset"))
        m_param.add_command(label="Save As", command=lambda: self._toast("Save As Preset"))
        m_param.add_command(label="Load", command=lambda: self._toast("Load Preset"))
        menubar.add_cascade(label="Configs", menu=m_param)

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
    def _build_file_group(self, parent):
        box = ttk.Labelframe(parent, text="File", padding=10, style="ParentBox.TLabelframe")
        box.pack(side="top", fill="x")

        def add_path(label_text, attr_name):
            ttk.Label(box, text=label_text).pack(anchor="w", pady=(6, 2))
            row = ttk.Frame(box); row.pack(fill="x", pady=(0,4)); row.columnconfigure(0, weight=1)
            entry = ttk.Entry(row); entry.grid(row=0, column=0, sticky="ew")
            ttk.Button(row, text="···", width=3, bootstyle="info",
                       command=lambda e=entry: self._browse_file(e)).grid(row=0, column=1, padx=(6,0))
            setattr(self, attr_name, entry)

        add_path("Image Path:", "entry_image")
        add_path("Processed Image Path:", "entry_processed")
        add_path("CSV Path:", "entry_csv")

        # 文件命名输入框
        form = ttk.Frame(box)  # 容器使用 grid，两列布局
        form.pack(fill="x", pady=(14,0))

        # 让右边输入框可拉伸
        form.columnconfigure(1, weight=1)

        names = ["Bacteria", "Drug", "Time"]

        self.file_params = {}  # 保存引用，便于后面取值
        for i, name in enumerate(names):
            # 直接复用你已有的行渲染方法
            self._param_row(form, i, name)  # ← 左标签 + 右 Entry
            # 把刚刚创建的 Entry 引用取出来保存（可选）
            # _param_row 创建的是该行最后一个 Entry，grid(row=i, column=1)
            entry = form.grid_slaves(row=i, column=1)[0]
            self.file_params[name] = entry

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
        outer = ttk.Labelframe(parent, text="Configs",
                               padding=10, style="ParentBox.TLabelframe")
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        sc = VScrolled(outer)
        sc.grid(row=0, column=0, sticky="nsew", pady=(2,0))

        cam = Collapsible(sc.content, text="Camera", style="ChildBox.TLabelframe")
        cam.pack(fill="x", pady=(0,8))
        for i,n in enumerate(["Exposure (μs)",
                              "Gain (dB)",
                              "SensorBitDepth",
                              "FPS",
                              "Duration"]):
            self._param_row(cam.body,i,n)

        fil = Collapsible(sc.content, text="Filter", style="ChildBox.TLabelframe")
        fil.pack(fill="x", pady=(0,8))
        for i,n in enumerate(["Kernel Size",
                              "Sigma",
                              "Threshold Low",
                              "Threshold High"]):
            self._param_row(fil.body,i,n)

        trk = Collapsible(sc.content, text="Tracking", style="ChildBox.TLabelframe")
        trk.pack(fill="x", pady=(0,8))
        for i,n in enumerate(["Time Window",
                              "Long-Cell Radius",
                              "Long Threshold",
                              "Long Area-Filter",
                              "Long Link-Distance",
                              "Long Track-Ratio",
                              "Short-Cell Radius",
                              "Short Threshold",
                              "Short SNR-Filter",
                              "Short Link-Distance",
                              "Short Track-Ratio"]):
            self._param_row(trk.body,i,n)

        feat = Collapsible(sc.content, text="Feature", style="ChildBox.TLabelframe")
        feat.pack(fill="x")
        for i,n in enumerate(["Start Frame",
                              "End Frame",
                              "Frame Interval"]):
            self._param_row(feat.body,i,n)

    def _param_row(self, parent, r, label):
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=4, padx=(0,6))
        ttk.Entry(parent).grid(row=r, column=1, sticky="ew", pady=4)

    # ---- 右列：图像 + 标签 ----
    def _build_view_area(self, parent):
        # tabs = ttk.Notebook(parent, bootstyle="info")
        tabs = ttk.Notebook(parent, style="TNotebook")
        tabs.grid(row=0, column=0, sticky="nsew")

        for name in ["Direct","Processed","Tracked"]:
            frame = ttk.Frame(tabs, padding=6)
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)
            tabs.add(frame, text=name)

            canvas = tk.Canvas(frame, bg="#0b0c0e", highlightthickness=0)
            canvas.grid(row=0, column=0, sticky="nsew")
            canvas.bind("<Configure>", lambda e, c=canvas: self._ensure_square(c))
            setattr(self, f"canvas_{name.lower()}", canvas)

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
        self.status = ttk.Label(parent, text=self.status_var, font=("Segoe UI", 9), foreground="#64748b")
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
    def _browse_file(self, entry):
        path = filedialog.askopenfilename(title="Choose File")
        if path: entry.delete(0, tk.END)
        entry.insert(0, path)

    def _file_open(self):
        p = filedialog.askopenfilename(title="Open Image")
        if p:
            self.status_var.set(f"Loaded: {os.path.basename(p)}")
            self._draw_dummy(self.canvas_direct)

    def _draw_dummy(self, canvas):
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
        tb.ToastNotification(title=title, message=msg, duration=1800, bootstyle=bootstyle).show_toast()

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
