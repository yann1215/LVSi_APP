# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as tb
from ttkbootstrap import ttk
from ttkbootstrap.constants import *

# 可选引入 Pillow, 让更多格式（jpg/tiff）可显示；没有也能跑（png/gif 走 Tk 原生）
try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False

class App(tb.Window):
    def __init__(self):
        super().__init__(themename="flatly")
        self.title("IVD Analyzer - ttkbootstrap Layout")
        self.geometry("1200x720")
        self.minsize(1000, 640)

        # —— 顶层网格：两行导航 + 中间图像区 + 底部控件 —— #
        self.rowconfigure(2, weight=1)   # 中间图像区可扩展
        self.columnconfigure(0, weight=1)

        # 两行导航栏
        self._build_navbar_row1()
        self._build_navbar_row2()

        # 中间：左右图像区
        self._build_center_images()

        # 底部：左80% 文件选择器（两行）+ 右20% 操作按钮（两行）
        self._build_bottom_panel()

        # 用于保存 PhotoImage 引用，防止被回收
        self._img_left_ref = None
        self._img_right_ref = None

    # =============== 顶部导航栏（第1行） =============== #
    def _build_navbar_row1(self):
        bar = ttk.Frame(self, padding=(8, 6))
        bar.grid(row=0, column=0, sticky=EW)
        for i in range(6):
            bar.columnconfigure(i, weight=0)
        bar.columnconfigure(6, weight=1)  # 右侧撑开

        # 行内放多个 Menubutton，每个都有下拉子菜单
        self._add_menu(bar, 0, "文件", [
            ("新建项目", lambda: None),
            ("打开项目…", lambda: self._open_project()),
            ("保存", lambda: None),
            ("另存为…", lambda: None),
            (None, None),
            ("退出", self.destroy),
        ])

        self._add_menu(bar, 1, "编辑", [
            ("撤销", lambda: None),
            ("重做", lambda: None),
            (None, None),
            ("首选项…", lambda: None),
        ])

        self._add_menu(bar, 2, "视图", [
            ("重置布局", lambda: self._reset_layout()),
            ("切换暗色模式", self._toggle_theme),
        ])

        self._add_menu(bar, 3, "工具", [
            ("图像预处理", lambda: None),
            ("批量分析", lambda: None),
        ])

        self._add_menu(bar, 4, "帮助", [
            ("查看日志", lambda: None),
            ("关于", lambda: None),
        ])

        # 右侧占位（比如搜索框/状态）
        ttk.Label(bar, text="IVD • Row 1", foreground="#64748b").grid(row=0, column=6, sticky=E)

    # =============== 顶部导航栏（第2行） =============== #
    def _build_navbar_row2(self):
        bar = ttk.Frame(self, padding=(8, 0))
        bar.grid(row=1, column=0, sticky=EW)
        for i in range(6):
            bar.columnconfigure(i, weight=0)
        bar.columnconfigure(6, weight=1)

        self._add_menu(bar, 0, "样本", [
            ("导入 CSV…", lambda: self._browse_and_load(self.entry_left, target="left")),
            ("导入图像…", lambda: self._browse_and_load(self.entry_right, target="right")),
        ])

        self._add_menu(bar, 1, "QC", [
            ("运行质控", lambda: None),
            ("查看 QC 历史", lambda: None),
        ])

        self._add_menu(bar, 2, "报告", [
            ("生成报告", lambda: None),
            ("导出 PDF…", lambda: None),
        ])

        self._add_menu(bar, 3, "窗口", [
            ("并排显示", lambda: self._side_by_side()),
            ("仅左图", lambda: self._show_only("left")),
            ("仅右图", lambda: self._show_only("right")),
        ])

        ttk.Label(bar, text="IVD • Row 2", foreground="#94a3b8").grid(row=0, column=6, sticky=E, pady=6)

    def _add_menu(self, parent, col, text, items):
        mb = ttk.Menubutton(parent, text=text, bootstyle="secondary")
        menu = tk.Menu(mb, tearoff=False)
        for label, cmd in items:
            if label is None:
                menu.add_separator()
            else:
                menu.add_command(label=label, command=cmd)
        mb["menu"] = menu
        mb.grid(row=0, column=col, padx=(0, 8), pady=6, sticky=W)

    # =============== 中间左右图像显示区 =============== #
    def _build_center_images(self):
        wrap = ttk.Frame(self, padding=(10, 8))
        wrap.grid(row=2, column=0, sticky=NSEW)
        wrap.columnconfigure(0, weight=1)
        wrap.columnconfigure(1, weight=1)
        wrap.rowconfigure(0, weight=1)

        # 左侧图像区
        left_card = ttk.Labelframe(wrap, text="左侧图像", padding=8, bootstyle="secondary")
        left_card.grid(row=0, column=0, sticky=NSEW, padx=(0, 6))
        left_card.rowconfigure(0, weight=1)
        left_card.columnconfigure(0, weight=1)

        self.canvas_left = tk.Canvas(left_card, bg="#0b0c0e")
        self.canvas_left.grid(row=0, column=0, sticky=NSEW)

        # 右侧图像区
        right_card = ttk.Labelframe(wrap, text="右侧图像", padding=8, bootstyle="secondary")
        right_card.grid(row=0, column=1, sticky=NSEW, padx=(6, 0))
        right_card.rowconfigure(0, weight=1)
        right_card.columnconfigure(0, weight=1)

        self.canvas_right = tk.Canvas(right_card, bg="#0b0c0e")
        self.canvas_right.grid(row=0, column=0, sticky=NSEW)

        # 在尺寸变化时自适应重绘（保持居中）
        self.canvas_left.bind("<Configure>", lambda e: self._redraw_canvas("left"))
        self.canvas_right.bind("<Configure>", lambda e: self._redraw_canvas("right"))

    # =============== 底部：左（80%）路径选择 + 右（20%）按钮 =============== #
    def _build_bottom_panel(self):
        bottom = ttk.Frame(self, padding=(10, 10))
        bottom.grid(row=3, column=0, sticky=EW)
        bottom.columnconfigure(0, weight=4)  # 左 80%
        bottom.columnconfigure(1, weight=1)  # 右 20%

        # 左侧：两行文件选择器
        left = ttk.Frame(bottom)
        left.grid(row=0, column=0, sticky=EW, padx=(0, 8))
        left.columnconfigure(1, weight=1)

        ttk.Label(left, text="左图路径：").grid(row=0, column=0, sticky=W, padx=(0, 6), pady=4)
        self.entry_left = ttk.Entry(left)
        self.entry_left.grid(row=0, column=1, sticky=EW, pady=4)
        ttk.Button(left, text="浏览…", bootstyle="secondary",
                   command=lambda: self._browse_and_load(self.entry_left, target="left")).grid(row=0, column=2, padx=(6, 0))

        ttk.Label(left, text="右图路径：").grid(row=1, column=0, sticky=W, padx=(0, 6), pady=4)
        self.entry_right = ttk.Entry(left)
        self.entry_right.grid(row=1, column=1, sticky=EW, pady=4)
        ttk.Button(left, text="浏览…", bootstyle="secondary",
                   command=lambda: self._browse_and_load(self.entry_right, target="right")).grid(row=1, column=2, padx=(6, 0))

        # 右侧：两行按钮
        right = ttk.Frame(bottom)
        right.grid(row=0, column=1, sticky=E)
        ttk.Button(right, text="开始分析", bootstyle="primary", width=14, command=self._run_analysis)\
            .grid(row=0, column=0, sticky=E, pady=(0, 6))
        ttk.Button(right, text="导出报告", bootstyle="success", width=14, command=self._export_report)\
            .grid(row=1, column=0, sticky=E)

    # =============== 业务方法 =============== #
    def _browse_and_load(self, entry, target="left"):
        path = filedialog.askopenfilename(
            title="选择图像文件",
            filetypes=[("图像文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tif;*.tiff"),
                       ("所有文件", "*.*")]
        )
        if not path:
            return
        entry.delete(0, tk.END)
        entry.insert(0, path)
        if target == "left":
            self._load_image_to_canvas(path, self.canvas_left, side="left")
        else:
            self._load_image_to_canvas(path, self.canvas_right, side="right")

    def _load_image_to_canvas(self, path, canvas, side="left"):
        if not os.path.exists(path):
            return
        try:
            if PIL_OK:
                img = Image.open(path)
                # 先按画布大小缩放
                cw, ch = max(canvas.winfo_width(), 1), max(canvas.winfo_height(), 1)
                img.thumbnail((cw, ch))
                tk_img = ImageTk.PhotoImage(img)
            else:
                # Tk 原生：只保证 png/gif
                tk_img = tk.PhotoImage(file=path)
        except Exception:
            return

        canvas.delete("all")
        # 居中放置
        x = canvas.winfo_width() // 2
        y = canvas.winfo_height() // 2
        canvas.create_image(x, y, image=tk_img, anchor="center")

        # 保存引用
        if side == "left":
            self._img_left_ref = tk_img
        else:
            self._img_right_ref = tk_img

    def _redraw_canvas(self, side):
        # 窗口尺寸变化时，尝试按路径重绘（保证缩放后仍居中）
        entry = self.entry_left if side == "left" else self.entry_right
        path = entry.get().strip()
        canvas = self.canvas_left if side == "left" else self.canvas_right
        if path and os.path.exists(path):
            self._load_image_to_canvas(path, canvas, side)

    def _toggle_theme(self):
        # 在 light/dark 主题间切换
        style = tb.Style()
        cur = style.theme.name
        style.theme_use("superhero" if cur != "superhero" else "flatly")

    def _open_project(self):
        filedialog.askopenfilename(title="打开项目文件", filetypes=[("项目文件", "*.ivd;*.json;*.yaml;*.yml"), ("所有文件", "*.*")])

    def _reset_layout(self):
        # 这里可以重置左右显示或清空图像等
        self.canvas_left.delete("all")
        self.canvas_right.delete("all")
        self._img_left_ref = None
        self._img_right_ref = None

    def _side_by_side(self):
        # 这里预留：如果后面想切换布局，可在此修改网格/权重
        pass

    def _show_only(self, which):
        # 简单隐藏/显示
        if which == "left":
            self.canvas_left.master.grid()   # 父容器是 Labelframe
            self.canvas_right.master.grid_remove()
        elif which == "right":
            self.canvas_right.master.grid()
            self.canvas_left.master.grid_remove()
        else:
            self.canvas_left.master.grid()
            self.canvas_right.master.grid()

    def _run_analysis(self):
        tb.ToastNotification(
            title="任务开始", message="正在分析当前图像/样本…", duration=2500, bootstyle="info"
        ).show_toast()

    def _export_report(self):
        tb.ToastNotification(
            title="已导出", message="报告导出到预设目录（示例）。", duration=2000, bootstyle="success"
        ).show_toast()


if __name__ == "__main__":
    App().mainloop()
