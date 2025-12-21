# gui2_button.py
from __future__ import annotations

from ttkbootstrap import ttk


class ButtonMixin:
    """
    右侧底部按钮栏：
    - Capture 模式(0)：相机实时显示 / 暂停 / 拍照 / 录制 / 结束录制
    - Process 模式(1)：播放 / 暂停 / 回到开头 / 后退2s / 前进2s / 开始处理

    依赖宿主(App)提供：
    - self.mode: tk.IntVar
    - self._capture_actions: dict[str, callable]
    - self._process_actions: dict[str, callable]
    """

    def _build_button_bar(self, parent, capture_actions: dict, process_actions: dict):
        self._capture_actions = capture_actions or {}
        self._process_actions = process_actions or {}

        row = ttk.Frame(parent)
        row.grid(row=3, column=0, sticky="ew", pady=(6, 0))

        # 两侧留白列可伸缩，中间放按钮
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=0)
        row.columnconfigure(2, weight=1)

        btns = ttk.Frame(row, name="btns")
        btns.grid(row=0, column=1)

        self._btn_row = row
        self._btns_container = btns  # 兼容你 gui2.py 里的 _update_min_width()

        # 初次按当前 mode 建一次
        mode = 0
        try:
            mode = int(self.mode.get())
        except Exception:
            pass
        self._apply_button_mode(mode)

    def _apply_button_mode(self, mode: int):
        """外部调用：切换模式时重建按钮组。"""
        if not hasattr(self, "_btns_container"):
            return

        # 清空旧按钮
        for w in self._btns_container.winfo_children():
            w.destroy()

        if int(mode) == 0:
            self._build_capture_buttons()
        else:
            self._build_process_buttons()

    # ----------------- 内部：两套按钮 -----------------

    def _build_capture_buttons(self):
        specs = [
            ("cam_live",   "Live"),
            ("cam_live_stop",  "Stop Live"),
            ("cam_snap",   "Snapshot"),
            ("cam_rec",    "Record"),
            ("cam_rec_stop", "Stop Record"),
        ]
        for c, (key, text) in enumerate(specs):
            ttk.Button(
                self._btns_container,
                text=text,
                bootstyle="info",
                command=lambda k=key: self._invoke_action(k, mode=0),
                width=14
            ).grid(row=0, column=c, padx=(0, 12) if c != len(specs) - 1 else 0)

    def _build_process_buttons(self):
        specs = [
            ("play",       "Play"),
            ("pause",      "Pause"),
            ("to_start",   "To Begin"),
            ("back_2s",    "<< 2s"),
            ("forward_2s", ">> 2s"),
            ("run_proc",   "Process"),
        ]
        for c, (key, text) in enumerate(specs):
            ttk.Button(
                self._btns_container,
                text=text,
                bootstyle="info",
                command=lambda k=key: self._invoke_action(k, mode=1),
                width=10 if key != "run_proc" else 12
            ).grid(row=0, column=c, padx=(0, 12) if c != len(specs) - 1 else 0)

    # ----------------- 统一执行入口 -----------------

    def _invoke_action(self, key: str, mode: int):
        """
        根据 mode + key 执行 gui2.py 传来的函数。
        """
        actions = self._capture_actions if int(mode) == 0 else self._process_actions
        fn = actions.get(key)

        if fn is None:
            # 统一提示：宿主一般有 status_var / _toast
            if hasattr(self, "status_var"):
                self.status_var.set(f"[WARN] Action not bound: {key}")
            if hasattr(self, "_toast"):
                try:
                    self._toast(f"Action not bound: {key}", title="Warn", bootstyle="warning")
                except Exception:
                    pass
            return

        try:
            fn()
        except Exception as e:
            if hasattr(self, "status_var"):
                self.status_var.set(f"[ERROR] {key}: {e}")
            if hasattr(self, "_toast"):
                try:
                    self._toast(f"{key}: {e}", title="Error", bootstyle="danger")
                except Exception:
                    pass
