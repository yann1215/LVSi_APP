# gui2_file.py
import os
import json
import tkinter as tk
from tkinter import filedialog
from ttkbootstrap import ttk

from utils.process.process_java import file_chooser, Preferences


class FileMixin:
    """
    复刻旧版 GUI 的“文件路径加载 + 输出路径（auto / 手动）+ per-node 记忆”行为。

    依赖外部（在 App.__init__ 中完成）：
        - self.filepath_list: list
        - self.output_filepath: str or java.io.File or "auto"
        - self.program_start: int   # 当前流程起始节点（0~3）
        - self.nodes: list[str]     # 用于状态提示
        - self.status_var: tk.StringVar (暂无？用于底部状态栏显示）

    依赖 UI 元件（在 _build_file_group 等 UI 构造函数中创建）：
        - self.entry_image: 主输入路径 Entry
        - （可选）self.entry_processed, self.entry_csv
        - self.path_var: tk.StringVar  （仅供 file_chooser 内部调用，可与 entry 绑定）
        - self.output_path_var: tk.StringVar  （仅供 file_chooser 内部调用）
    """

    # ---------- 初始化 / 兼容旧版字段 ----------

    def _ensure_file_exsistence(self):
        """
        确保所需的属性存在。
        不存在也不会有太大影响，但是存在的话可以让代码更稳定一点。
        """
        if not hasattr(self, "filepath_list"):
            self.filepath_list = []
        if not hasattr(self, "output_filepath"):
            self.output_filepath = "auto"
        if not hasattr(self, "current_file"):
            self.current_file = ""

            # var_name -> entry_attr（如果 Entry 已经创建，则需要 rebind）
            var_entry_map = {
                "camera_path_var": ("entry_camera", ""),
                "input_path_var": ("entry_input", ""),
                "output_path_var": ("entry_output", ""),
                "current_path_var": ("entry_current", ""),
            }

            for var_name, (entry_attr, default) in var_entry_map.items():
                v = getattr(self, var_name, None)
                if not isinstance(v, tk.StringVar):
                    new_v = tk.StringVar(master=self, value=str(default))
                    setattr(self, var_name, new_v)
                    if hasattr(self, entry_attr):
                        try:
                            getattr(self, entry_attr).configure(textvariable=new_v)
                        except Exception:
                            pass

            # UI 值与业务值对齐（尤其是 output auto）
            try:
                if isinstance(self.output_path_var, tk.StringVar):
                    out = getattr(self, "output_filepath", "auto") or "auto"
                    if self.output_path_var.get() == "":
                        self.output_path_var.set(str(out))
                if isinstance(self.current_path_var, tk.StringVar):
                    cur = getattr(self, "current_file", "") or ""
                    if self.current_path_var.get() == "" and cur:
                        self.current_path_var.set(cur)
            except Exception:
                pass

    # ------- File 区：Camrea / Input / Output / Current -------
    def _param_row(self, parent, r, label):
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 6))
        ttk.Entry(parent).grid(row=r, column=1, sticky="ew", pady=4)

    def _build_file_group(self, parent):
        box = ttk.Labelframe(parent, text="File", padding=10, style="ParentBox.TLabelframe")
        box.pack(side="top", fill="x")
        self.file_group_box = box

        def add_path(label_text, attr_name, text_var, callback):
            ttk.Label(box, text=label_text).pack(anchor="w", pady=(6, 2))
            row = ttk.Frame(box)
            row.pack(fill="x", pady=(0,4))
            row.columnconfigure(0, weight=1)

            if text_var is not None:
                entry = ttk.Entry(row, textvariable=text_var, state="readonly")
            else:
                entry = ttk.Entry(row, state="readonly")
            entry.grid(row=0, column=0, sticky="ew")

            if attr_name == "entry_camera":
                self.b_sp_camera = ttk.Button(row, text="···", width=3, bootstyle="info",
                           command=lambda e=entry: callback(e))
                self.b_sp_camera.grid(row=0, column=1, padx=(6,0))
            else:
                ttk.Button(row, text="···", width=3, bootstyle="info",
                           command=lambda e=entry: callback(e)).grid(row=0, column=1, padx=(6, 0))
            setattr(self, attr_name, entry)

        # 1) Camera Save Path：沿用旧逻辑的“输入目录”（filepath_list + path_var + Preferences）
        add_path("Camera Save Path:", "entry_camera", self.camera_path_var, self._browse_camera_path)

        # 2) Input Path：沿用旧逻辑的“输入目录”（filepath_list + path_var + Preferences）
        add_path("Process Input Path:", "entry_input", self.input_path_var, self._browse_input_path)

        # 3) Output Path：沿用旧逻辑的“输出目录”（output_filepath + output_path_var + Preferences）
        add_path("Process Output Path:", "entry_output", self.output_path_var, self._browse_output_path)

        # 4) 当前浏览的单个图像文件（暂时只记录，不参与 pipeline）
        add_path("Current Browse File:", "entry_current", self.current_path_var, self._browse_current_path)

        # note: 增加按钮，设置 output path 为 auto

        # 文件命名输入框
        form = ttk.Frame(box)  # 容器使用 grid，两列布局
        form.pack(fill="x", pady=(14,0))

        names = ["Name", "Append 1", "Append 2"]

        # 让右边输入框可拉伸
        form.columnconfigure(1, weight=1)

        self.file_params = {}  # 保存引用，便于后面取值
        for i, name in enumerate(names):
            # 直接复用你已有的行渲染方法
            self._param_row(form, i, name)  # ← 左标签 + 右 Entry
            # 把刚刚创建的 Entry 引用取出来保存（可选）
            # _param_row 创建的是该行最后一个 Entry，grid(row=i, column=1)
            entry = form.grid_slaves(row=i, column=1)[0]
            self.file_params[name] = entry

    def _browse_camera_path(self, entry):
        if getattr(self, "record_lock", False):
            return

        self._ensure_file_exsistence()
        sel = file_chooser(self, 0)
        if not sel:
            return

        cam_dir = str(sel)
        # 业务值（供相机保存用）
        self.camera_save_dir = cam_dir

        # UI 显示（Entry 绑定 StringVar）
        self.camera_path_var.set(cam_dir)

        # 把视图拉到末尾
        entry.xview_moveto(1)

        if hasattr(self, "status_var"):
            path_name = os.path.basename(os.path.normpath(cam_dir))
            self.status_var.set(f"Camera save path set: {path_name}")

    def _browse_input_path(self, entry):
        self._ensure_file_exsistence()
        sel = file_chooser(self, 1)
        if not sel:
            return

        if isinstance(sel, list):
            paths = [str(p) for p in sel]
        else:
            paths = [str(sel)]

        # 业务值（供 process pipeline 用）
        self.filepath_list = paths

        # UI 显示：建议用 ; 分隔（比 \"['a','b']\" 更可读，也不依赖 json/replace）
        self.input_path_var.set("; ".join(paths))

        entry.xview_moveto(1)

        # 状态栏提示（可选）
        if hasattr(self, "status_var"):
            path_name = os.path.basename(os.path.normpath(paths[0]))
            self.status_var.set(f"Process input path set: {path_name}")

    def _browse_output_path(self, entry):
        self._ensure_file_exsistence()
        sel = file_chooser(self, 2)
        if not sel:
            return

        out_dir = str(sel)
        # 业务值（供右侧 Processed/导出用）
        self.output_filepath = out_dir

        # UI 显示
        self.output_path_var.set(out_dir)

        entry.xview_moveto(1)

        if hasattr(self, "status_var"):
            path_name = os.path.basename(os.path.normpath(out_dir))
            self.status_var.set(f"Process output path set: {path_name}")

    def _browse_current_path(self, entry):
        self._ensure_file_exsistence()
        sel = file_chooser(self, 3)
        if not sel:
            return

        cur = str(sel)
        # 业务值（gui2_image._update_original_view 用的是 current_file）
        self.current_file = cur

        # UI 显示
        self.current_path_var.set(cur)

        entry.xview_moveto(1)

        if hasattr(self, "status_var"):
            path_name = os.path.basename(cur)
            self.status_var.set(f"Browsing file: {path_name}")

        try:
            if int(self.mode.get()) == 1:
                # 如果 Original tab 已经存在，直接刷新一下视图
                if hasattr(self, "_update_original_view"):
                    self._update_original_view()

                # 选完文件后，右侧窗口自动跳到 Original tab
                if hasattr(self, "tabs_view"):
                    tabs = self.tabs_view
                    for i in range(tabs.index("end")):
                        if tabs.tab(i, "text") == "Original":
                            tabs.select(i)
                            break
        except Exception:
            pass
