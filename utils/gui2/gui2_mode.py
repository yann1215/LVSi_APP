# gui2_mode.py
import tkinter as tk
from ttkbootstrap import ttk


class ModeMixin:
    """
    左侧 Mode/Process 区域（Capture / Process 两种模式互斥）
    - self.mode: IntVar (0=Capture, 1=Process)
    - self.preview_flag: BooleanVar
    - self.var_noise / self.var_track / self.var_feat: BooleanVar
    - self.program_start / self.program_end: pipeline range
    """

    def _build_mode_group(self, parent, on_mode_changed=None):
        """
        替代原 _build_process_group。
        on_mode_changed: 可选回调，由 gui2.py 传入；签名建议 on_mode_changed(mode:int)
        """
        self._mode_change_cb = on_mode_changed  # 保存回调

        proc = ttk.Labelframe(parent, text="Process", padding=10, style="ParentBox.TLabelframe")
        proc.pack(side="top", fill="both", expand=True, pady=(8, 0))
        self.mode_group_box = proc

        # ---- 确保核心变量存在（也可以放在 gui2.py __init__ 里初始化）----
        if not hasattr(self, "mode"):
            self.mode = tk.IntVar(value=0)  # 0=Capture, 1=Process
        if not hasattr(self, "preview_flag"):
            self.preview_flag = tk.BooleanVar(value=False)

        if not hasattr(self, "var_noise"):
            self.var_noise = tk.BooleanVar(value=True)
        if not hasattr(self, "var_track"):
            self.var_track = tk.BooleanVar(value=True)
        if not hasattr(self, "var_feat"):
            self.var_feat = tk.BooleanVar(value=True)

        # ---- Mode（互斥单选）----
        mode_row = ttk.Frame(proc)
        mode_row.pack(fill="x", pady=(2, 10))

        # ttk.Label(mode_row, text="Mode:").pack(side="left")

        ttk.Radiobutton(
            mode_row, text="Capture", value=0, variable=self.mode,
            command=self._on_mode_changed
        ).pack(side="left", padx=(10, 0))

        ttk.Radiobutton(
            mode_row, text="Process", value=1, variable=self.mode,
            command=self._on_mode_changed
        ).pack(side="left", padx=(10, 0))

        # ---- Capture ChildBox ----
        cap_box = ttk.Labelframe(proc, text="Capture", padding=10, style="ChildBox.TLabelframe")
        cap_box.pack(fill="x", pady=(0, 10))
        self.capture_box = cap_box

        ttk.Checkbutton(
            cap_box, text="Preview", variable=self.preview_flag,
            bootstyle="round-toggle",
        ).pack(anchor="w", pady=6)
        ttk.Button(
            cap_box, text="Update Preview Background",
            command=self._update_preview_background
        ).pack(anchor="w", pady=(6, 0))

        # ---- Process ChildBox ----
        pro_box = ttk.Labelframe(proc, text="Process", padding=10, style="ChildBox.TLabelframe")
        pro_box.pack(fill="x")
        self.process_box = pro_box

        for v, t in [
            (self.var_noise, "Noise Filter"),
            (self.var_track, "Cell Tracking"),
            (self.var_feat,  "Feature Extraction"),
        ]:
            ttk.Checkbutton(
                pro_box, text=t, variable=v,
                bootstyle="round-toggle",
                command=self._update_program_range
            ).pack(anchor="w", pady=6)

        # 初始化一次状态（禁用另一侧 + program_range）
        self._on_mode_changed()

    def _update_preview_background(self):
        """
        将当前相机帧保存为 preview background（内存 numpy.ndarray）。
        后续 Preview tab 可以用 frame - background 实时显示。
        """
        import time
        import numpy as np

        # 取当前帧（尽量线程安全）
        if hasattr(self, "_img_lock") and self._img_lock is not None:
            with self._img_lock:
                frame = getattr(self, "img", None)
                frame = None if frame is None else frame.copy()
        else:
            frame = getattr(self, "img", None)
            frame = None if frame is None else frame.copy()

        if frame is None:
            if hasattr(self, "status_var"):
                self.status_var.set("[Preview] No camera frame available; cannot update background.")
            return

        if hasattr(self, "status_var"):
            self.status_var.set(f"[Preview] Background updated: {frame.shape}, {frame.dtype}")

    # ----------------- 互斥模式控制 -----------------
    def _set_children_state(self, parent, enabled: bool):
        """
        递归设置 parent 下面所有 ttk 控件的 enabled/disabled
        """
        def set_state(w):
            try:
                if enabled:
                    w.state(["!disabled"])
                else:
                    w.state(["disabled"])
            except Exception:
                try:
                    w.configure(state=("normal" if enabled else "disabled"))
                except Exception:
                    pass

        for child in parent.winfo_children():
            set_state(child)
            # 容器类递归进去（Frame/Labelframe）
            if isinstance(child, (ttk.Frame, ttk.Labelframe)):
                self._set_children_state(child, enabled)

    def _on_mode_changed(self):
        """
        Capture / Process 二选一：
        - Capture：启用 Capture box，禁用 Process box，program_range 强制为 0..0
        - Process：启用 Process box，禁用 Capture box，program_range 由 1..3 决定
        """
        mode = int(self.mode.get())

        if hasattr(self, "capture_box") and hasattr(self, "process_box"):
            if mode == 0:
                self._set_children_state(self.capture_box, True)
                self._set_children_state(self.process_box, False)
            else:
                self._set_children_state(self.capture_box, False)
                self._set_children_state(self.process_box, True)

        self._update_program_range()

        cb = getattr(self, "_mode_change_cb", None)
        if callable(cb):
            cb(mode)

    # ----------------- pipeline range -----------------
    def _update_program_range(self):
        """
        - Capture 模式：强制 0..0
        - Process 模式：由 Noise/Track/Feat 三开关决定 1..3（若全不选则默认 1..3）
        """
        mode = int(self.mode.get())

        if mode == 0:
            self.program_start, self.program_end = 0, 0
            return

        flags = [self.var_noise.get(), self.var_track.get(), self.var_feat.get()]
        selected = [i for i, f in enumerate(flags, start=1) if f]  # 对应节点 1/2/3

        if not selected:
            self.program_start, self.program_end = 1, 3
        else:
            self.program_start, self.program_end = min(selected), max(selected)
