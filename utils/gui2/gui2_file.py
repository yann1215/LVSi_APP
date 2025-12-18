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

        # file_chooser 里会用到这两个变量
        if not hasattr(self, "path_var"):
            self.path_var = tk.StringVar(master=self, value="[]")
        if not hasattr(self, "output_path_var"):
            self.output_path_var = tk.StringVar(master=self, value="auto")

    # ------- File 区：Input / Output / Current 三个按钮 -------
    def _param_row(self, parent, r, label):
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 6))
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

        # 1) Camera Save Path：沿用旧逻辑的“输入目录”（filepath_list + path_var + Preferences）
        add_path("Camera Save Path:", "entry_camera", self.path_var, self._browse_camera_path)

        # 1) Input Path：沿用旧逻辑的“输入目录”（filepath_list + path_var + Preferences）
        add_path("Input Path:", "entry_input", self.path_var, self._browse_input_path)

        # 2) Output Path：沿用旧逻辑的“输出目录”（output_filepath + output_path_var + Preferences）
        add_path("Output Path:", "entry_output", self.output_path_var, self._browse_output_path)

        # 3) 当前浏览的单个图像文件（暂时只记录，不参与 pipeline）
        add_path("Current Browse File:", "entry_current_file", self.current_path_var, self._browse_current_file)

        # note: 增加按钮，设置 output path 为 auto

        # 文件命名输入框
        form = ttk.Frame(box)  # 容器使用 grid，两列布局
        form.pack(fill="x", pady=(14,0))

        names = ["Append 1", "Append 2", "Time"]

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
        # note: 待修改
        return

    def _browse_input_path(self, entry):
        """
        Input Path 的 “···”：
        完全沿用旧版逻辑，调用 Java JFileChooser：
            - file_chooser(self, self.program_start)
            - 回写 self.filepath_list / self.path_var / Preferences
        """
        # 调用旧逻辑
        self.filepath_list = file_chooser(self, self.program_start)
        # Entry 绑定了 self.path_var，会自动更新文本，这里只把视图拉到末尾
        entry.xview_moveto(1)

        # 状态栏提示（可选）
        if hasattr(self, "status_var") and self.filepath_list:
            first = os.path.basename(str(self.filepath_list[0]))
            self.status_var.set(f"Input path set: {first}")

    def _browse_output_path(self, entry):
        """
        Output Path 的 “···”：
        调用 file_chooser(self, 4)，完全沿用旧版“设置输出目录”的逻辑：
            - 返回值赋给 self.output_filepath
            - 回写 self.output_path_var / Preferences
        """
        self.output_filepath = file_chooser(self, 4)
        entry.xview_moveto(1)

        if hasattr(self, "status_var") and self.output_filepath not in (None, "auto"):
            self.status_var.set("Output path set.")

    def _browse_current_file(self, entry):
        """
        Current Browse Image File 的 “···”：
        暂时只选一个图像/视频文件，更新 entry 和 self.current_file，
        不参与旧 pipeline，只用来做后续预览逻辑。
        """
        # 1. 先推断一个初始目录
        init_dir = None

        # 若已有 current_file，则以它所在目录为初始目录
        cur = getattr(self, "current_file", "")
        if cur:
            if os.path.isdir(cur):
                init_dir = cur
            elif os.path.isfile(cur):
                init_dir = os.path.dirname(cur)

        # 没有 current_file，就退回 Input Path
        if not init_dir and hasattr(self, "path_var"):
            path = getattr(self.path_var, "get", lambda: "")()
            if path:
                init_dir = path

        # 还没有，就用当前工作目录
        if not init_dir:
            init_dir = os.getcwd()

        # 2. 弹出文件选择对话框（这里先做“选文件”版）
        filename = filedialog.askopenfilename(
            parent=self,
            title="Select image file",
            initialdir=init_dir,
            filetypes=[
                ("Image files", "*.tif *.tiff *.png *.jpg *.jpeg *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not filename:
            return  # 用户取消

        # 3. 更新 entry 显示 & current_file 属性
        entry.delete(0, tk.END)
        entry.insert(0, filename)

        # 这里可以是文件也可以是目录路径，_find_first_image 都能处理；
        # 当前我们通过 askopenfilename 选的是文件。
        self.current_file = filename

        # 4. 更新状态栏（可选）
        if hasattr(self, "status_var"):
            try:
                self.status_var.set(f"Current file: {os.path.basename(filename)}")
            except Exception:
                pass

        # 5. 如果 Original tab 已经存在，直接刷新一下视图
        if hasattr(self, "_update_original_view"):
            self._update_original_view()

        # 选完文件后，右侧窗口自动跳到 Original tab
        if hasattr(self, "tabs_view"):
            tabs = self.tabs_view
            for i in range(tabs.index("end")):
                if tabs.tab(i, "text") == "Original":
                    tabs.select(i)
                    break

    # ---------- 菜单栏 File -> Open ----------

    def _file_open(self):
        """
        菜单栏 File -> Open...
        默认行为：选择一个文件，更新主输入路径和 filepath_list，
        然后触发可选的 self.on_file_loaded(path) 钩子（由 App 实现具体显示逻辑）。
        """
        self._ensure_file_exsistence()

        p = filedialog.askopenfilename(
            title="Open Image",
            filetypes=[
                ("Image / Video", "*.tif;*.tiff;*.png;*.jpg;*.jpeg;*.bmp;*.avi;*.mp4"),
                ("All files", "*.*"),
            ],
        )
        if not p:
            return

        # 同步到旧版管线字段
        self.filepath_list = [p]
        self.path_var.set(str(self.filepath_list))

        # 更新左侧主路径 Entry（若存在）
        if hasattr(self, "entry_image"):
            self.entry_image.delete(0, tk.END)
            self.entry_image.insert(0, p)
            self.entry_image.xview_moveto(1)

        # 状态栏提示
        if hasattr(self, "status_var"):
            basename = os.path.basename(p)
            self.status_var.set(f"Loaded: {basename}")

        # 交给 App 自己决定如何在右侧显示
        if hasattr(self, "on_file_loaded"):
            try:
                self.on_file_loaded(p)
            except Exception as e:
                # 不让 GUI 因为预览失败直接崩
                if hasattr(self, "status_var"):
                    self.status_var.set(f"Load done, preview failed: {e}")

    # ---------- 输出目录：旧版 output_auto / output_browse_file ----------

    def _browse_output_dir(self):
        """
        如果你在新 GUI 中补了“Output Path”的 Entry，可以把按钮绑定到这个方法：
            command=self._browse_output_dir
        调用 file_chooser(mode=4) 并维护旧版的 Preferences。
        """
        self._ensure_file_exsistence()
        self.output_filepath = file_chooser(self, 4)
        # file_chooser 已写入 self.output_path_var
        if hasattr(self, "status_var") and self.output_filepath not in (None, "auto"):
            self.status_var.set(f"Output dir: {self.output_filepath}")

    def _set_output_auto(self):
        """
        对应旧版 output_auto 行为。
        如果你有一个“Auto”按钮，可以直接绑定到这个方法。
        """
        self._ensure_file_exsistence()
        self.output_filepath = "auto"
        self.output_path_var.set("auto")

        # 写回 Java Preferences，保持与旧 GUI 一致的 key
        prefs = Preferences.userRoot().node("/LMH/fijiCountingFaster/29/fileChooser")
        prefs.put("outputPath", "auto")

        if hasattr(self, "status_var"):
            self.status_var.set("Output dir: auto")

    # ---------- 从 Preferences 读回某节点的路径（旧 select_left 的路径部分） ----------

    def load_paths_for_node(self, index: int):
        """
        复刻旧版 select_left() 中“根据节点 index，从 Preferences 恢复路径”的逻辑。
        仅做路径 / 状态同步，不处理单选按钮 / 颜色等 UI。
        """
        self._ensure_file_exsistence()
        self.program_start = index

        KEY_list = ["cameraPath", "preprocessPath", "trackMatePath", "featuresPath", "outputPath"]
        prefs = Preferences.userRoot().node("/LMH/fijiCountingFaster/29/fileChooser")

        path_list_prefs = prefs.get(KEY_list[index], None)
        if not path_list_prefs:
            path_list_str = "[]"
        else:
            path_list_str = str(path_list_prefs)

        output_path_prefs = prefs.get(KEY_list[4], None)
        if not output_path_prefs or output_path_prefs == "auto":
            output_path_str = "auto"
        else:
            output_path_str = str(output_path_prefs)

        # 更新 StringVar（兼容 file_chooser 内部和旧习惯）
        self.path_var.set(path_list_str)
        self.output_path_var.set(output_path_str)

        # 把字符串转回列表
        path_list_str_json = path_list_str.replace("'", '"')
        try:
            path_list = json.loads(path_list_str_json)
        except Exception:
            path_list = []

        self.filepath_list = path_list
        self.output_filepath = output_path_str

        # 若主 Entry 存在，则更新显示
        if hasattr(self, "entry_image"):
            self.entry_image.delete(0, tk.END)
            self.entry_image.insert(0, "; ".join(map(str, path_list)))
            self.entry_image.xview_moveto(1)

        if hasattr(self, "status_var"):
            if path_list:
                node_name = None
                if hasattr(self, "nodes") and 0 <= index < len(self.nodes):
                    node_name = self.nodes[index]
                suffix = f"【{node_name}】" if node_name else f"节点 {index}"
                self.status_var.set(f"已加载 {suffix} 的路径设置")
            else:
                self.status_var.set("尚未为该节点配置路径")
