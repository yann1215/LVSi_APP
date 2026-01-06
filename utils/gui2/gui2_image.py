# gui2_image.py
import os
import json
import tkinter as tk
from ttkbootstrap import ttk
import threading
import numpy as np
from PIL import Image, ImageTk

from utils.camera.camera_status import start_camera


class ImageMixin:
    """
    负责右侧画布的显示。
    包含以下内容（mode == 0, capture）：
        1. Camera: 相机直接输出
        2. Preview: 预览文件
    或（mode == 1, process）：
        1. Original:（暂无）
        2. Processed:（暂无）
    """

    # ================ 显示画布 ================
    def _build_view_area(self, parent):
        # tabs = ttk.Notebook(parent, bootstyle="info")
        tabs = ttk.Notebook(parent, style="TNotebook")
        tabs.grid(row=0, column=0, sticky="nsew")

        # 保存引用，后面 tab 切换和刷新要用
        self.tabs_view = tabs
        tabs.bind("<<NotebookTabChanged>>", self._on_view_tab_changed)

        # note: 因为之前处理的代码未导出 process 和 tracked 图像，仅导出 .CSV
        #       所以此处先注释掉相关代码，仅作为占位。后续可以再启用。
        self._view_frames = {}
        for name in ["Camera", "Preview", "Original", "Processed"]:
            frame = ttk.Frame(tabs, padding=6)
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)
            self._view_frames[name] = frame

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

        # 根据当前 mode 只显示两个 tab
        try:
            mode = int(getattr(self, "mode").get())
        except Exception:
            mode = 0
        self._apply_view_mode(mode)

    def _on_view_tab_changed(self, event):
        self._refresh_current_view()

    def _refresh_current_view(self):
        tabs = getattr(self, "tabs_view", None)
        if tabs is None or tabs.index("end") == 0:
            return

        try:
            name = tabs.tab("current", "text")
        except Exception:
            return

        if name == "Camera":
            self._ensure_camera_running()
        elif name == "Preview":
            # 如果在 live,就刷新画面，否则不刷新
            if self.preview_flag and self.live_flag:
                self._update_preview_view()
        elif name == "Original":
            self._update_original_view()
        elif name == "Processed":
            self._update_processed_view()

    def _apply_view_mode(self, mode: int):
        """
        对外接口：让 gui2.py / Mode 回调调用
          mode==0: Camera + Preview
          mode==1: Original + Processed
        """
        tabs = getattr(self, "tabs_view", None)
        if tabs is None:
            return

        # 清空当前 notebook tab（不销毁 widget）
        for i in reversed(range(tabs.index("end"))):
            try:
                tabs.forget(i)
            except Exception:
                pass

        if int(mode) == 0:
            self._add_view_tab("Camera")
            self._add_view_tab("Preview")
        else:
            self._add_view_tab("Original")
            self._add_view_tab("Processed")

        if tabs.index("end") > 0:
            tabs.select(0)
            self.after_idle(self._refresh_current_view)

    def _add_view_tab(self, name: str):
        frame = getattr(self, "_view_frames", {}).get(name)
        if frame is None:
            return
        self.tabs_view.add(frame, text=name)

    def _ensure_square(self, canvas):
        w,h = canvas.winfo_width(), canvas.winfo_height(); side = min(w,h)
        canvas.delete("border")
        px,py = (w-side)//2,(h-side)//2
        canvas.create_rectangle(px,py,px+side,py+side, outline="#334155", width=2, tags="border")

    def _find_first_image(self, path: str):
        """
        输入可以是文件或目录：
        - 如果是图像文件，直接返回；
        - 如果是目录，在里面按照文件名排序找到第一个图像文件；
        - 找不到则返回 None。
        """
        if not path:
            return None

        path = os.path.abspath(str(path))
        img_exts = (".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp")

        if os.path.isfile(path):
            if os.path.splitext(path)[1].lower() in img_exts:
                return path
            return None

        if not os.path.isdir(path):
            return None

        # 只在当前目录找，不递归
        files = sorted(
            f for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f))
            and os.path.splitext(f)[1].lower() in img_exts
        )
        if not files:
            return None

        return os.path.join(path, files[0])

    def _show_image_on_canvas(self, canvas, img_path, photo_attr_name):
        """
        把 img_path 显示到指定 canvas 上，并把 PhotoImage 挂在 self 上防止被 GC。
        """

        if not img_path or not os.path.isfile(img_path):
            # 清空内容但保留边框
            canvas.delete("content")
            setattr(self, photo_attr_name, None)
            return

        try:
            img = Image.open(img_path)
        except Exception as e:
            canvas.delete("content")
            setattr(self, photo_attr_name, None)
            if hasattr(self, "status_var"):
                self.status_var.set(f"Open failed: {e}")
            return

        # 以 canvas 的短边为基准做缩放
        w = canvas.winfo_width() or 1
        h = canvas.winfo_height() or 1
        side = min(w, h)
        if side <= 0:
            side = 256

        img = img.convert("RGB")
        img.thumbnail((side, side), Image.LANCZOS)

        photo = ImageTk.PhotoImage(img)
        canvas.delete("content")
        canvas.create_image(w // 2, h // 2, image=photo, anchor="center", tags="content")

        # 保存引用，防止被垃圾回收
        setattr(self, photo_attr_name, photo)

        # 重画边框
        self._ensure_square(canvas)

    # ================== 启用相机（新：后端 + GUI 窗口嵌入分离） ==================
    def _ensure_camera_running(self):
        """
        在 Camera tab 被选中时调用：
        1) 通过 camera_status.start_camera 启动后端（只启动一次）
        2) 启动 GUI 侧 window manager（只启动一次），将 OpenCV 窗口嵌入 camera_container
        """
        container = getattr(self, "camera_container", None)
        if container is None:
            if hasattr(self, "status_var"):
                self.status_var.set("[Camera ERROR] camera_container not found.")
            return

        # 1) 启动/确保后端（由 camera_status 统一管理 container_hwnd / width / height / resize bind）
        start_camera(self, container, start_backend=True, allow_restart=True, update_status=True)

        # 2) 启动 GUI window manager（只启动一次）
        self._start_camera_window()

    def _start_camera_window(self):
        """
        启动一次 window manager 线程（OpenCV 窗口嵌入 Tk 容器 + resize + 居中显示）。
        """
        if getattr(self, "_camera_window_running", False):
            return

        self._camera_window_running = True
        t = threading.Thread(
            target=self._window_manager_loop,
            args=("vimba X",),  # window title，可自行改
            daemon=True,
            name="vimbaX-window-manager",
        )
        self._camera_window_thread = t
        t.start()

    def _window_manager_loop(self, window_name: str = "vimba X"):
        """
        GUI侧的 window manager：
        - 创建 OpenCV window
        - SetParent 到 self.container_hwnd（Tk Frame 的 HWND）
        - 循环 MoveWindow 适配容器尺寸变化
        - 将 self.img 缩放并居中（letterbox，不拉伸变形）
        """
        import os
        import time
        import cv2
        import numpy as np

        # 仅 Windows 支持 SetParent/MoveWindow
        if os.name != "nt":
            if hasattr(self, "status_var"):
                self.status_var.set("[Camera WARN] window embedding only supported on Windows.")
            return

        try:
            import win32gui
            import win32con
        except Exception as e:
            if hasattr(self, "status_var"):
                self.status_var.set(f"[Camera ERROR] pywin32 not available: {e}")
            return

        # 取容器 hwnd（camera_status.start_camera 已设置；这里做兜底）
        container = getattr(self, "camera_container", None)
        if container is None:
            if hasattr(self, "status_var"):
                self.status_var.set("[Camera ERROR] camera_container not found.")
            return

        try:
            if not getattr(self, "container_hwnd", 0):
                self.container_hwnd = int(container.winfo_id())
        except Exception:
            pass

        if not getattr(self, "container_hwnd", 0):
            if hasattr(self, "status_var"):
                self.status_var.set("[Camera ERROR] container_hwnd not ready (winfo_id==0).")
            return

        # 创建 OpenCV 窗口并确保 HWND 可被 FindWindow 找到
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        # 先显示一帧 dummy，避免 FindWindow 找不到
        dummy = np.zeros((2, 2), dtype=np.uint8)
        cv2.imshow(window_name, dummy)
        cv2.waitKey(1)

        hwnd = 0
        for _ in range(50):  # 最多约 2.5s
            hwnd = win32gui.FindWindow(None, window_name)
            if hwnd:
                break
            time.sleep(0.05)

        if not hwnd:
            if hasattr(self, "status_var"):
                self.status_var.set("[Camera ERROR] FindWindow failed for OpenCV window.")
            return

        self._camera_cv_hwnd = hwnd

        # 嵌入到 Tk 容器
        try:
            win32gui.SetParent(hwnd, int(self.container_hwnd))
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME |
                       win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX |
                       win32con.WS_BORDER | win32con.WS_SIZEBOX)
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        except Exception as e:
            if hasattr(self, "status_var"):
                self.status_var.set(f"[Camera ERROR] SetParent/style failed: {e}")
            return

        last_w, last_h = -1, -1

        # 主循环
        while True:
            # 退出条件：App 关闭时 EndEvent 会 set
            if getattr(self, "EndEvent", None) is not None and self.EndEvent.is_set():
                break

            w = int(getattr(self, "video_frame_width", 1) or 1)
            h = int(getattr(self, "video_frame_height", 1) or 1)
            w = max(2, w)
            h = max(2, h)

            # 容器尺寸变化 -> 调整 OpenCV 子窗口
            if w != last_w or h != last_h:
                try:
                    win32gui.MoveWindow(hwnd, 0, 0, w, h, True)
                    last_w, last_h = w, h
                except Exception:
                    pass

            img = getattr(self, "img", None)
            if img is None:
                frame = dummy
            else:
                frame = img

            # letterbox 居中显示（保持纵横比）
            try:
                if frame.ndim == 2:
                    ih, iw = frame.shape[:2]
                    canvas = np.zeros((h, w), dtype=frame.dtype)
                else:
                    ih, iw = frame.shape[:2]
                    canvas = np.zeros((h, w, frame.shape[2]), dtype=frame.dtype)

                scale = min(w / max(1, iw), h / max(1, ih))
                nw = max(1, int(iw * scale))
                nh = max(1, int(ih * scale))

                resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
                x0 = (w - nw) // 2
                y0 = (h - nh) // 2
                canvas[y0:y0 + nh, x0:x0 + nw] = resized
            except Exception:
                canvas = frame

            cv2.imshow(window_name, canvas)
            cv2.waitKey(1)

            time.sleep(0.01)

        # 清理
        try:
            cv2.destroyWindow(window_name)
        except Exception:
            pass

        self._camera_window_running = False

    # ============ 显示 Original/Processed/Preview ============

    def _get_output_root(self):
        """把 self.output_filepath 转成可用的本地路径（排除 'auto'）。"""
        out = getattr(self, "output_filepath", None)
        if not out or str(out) == "auto":
            return None
        return os.path.abspath(str(out))

    def _update_original_view(self):
        """
        根据 current_file 更新 Original 画布。
        """
        path = getattr(self, "current_file", "")
        if not path:
            self.canvas_original.delete("content")
            setattr(self, "_original_photo", None)
            return

        img_path = self._find_first_image(path)
        if not img_path:
            self.canvas_original.delete("content")
            setattr(self, "_original_photo", None)
            if hasattr(self, "status_var"):
                self.status_var.set("No image found in current path.")
            return

        self._show_image_on_canvas(self.canvas_original, img_path, "_original_photo")

    # note: 因为之前处理的代码未导出 process 和 tracked 图像，仅导出 .CSV
    #       此处先占位。导入和显示逻辑暂时套用 Original 的内容。
    def _update_processed_view(self):
        """
        根据 Output Path 更新 Processed 画布。
        """
        root = self._get_output_root()
        if not root or not os.path.isdir(root):
            self.canvas_processed.delete("content")
            setattr(self, "_processed_photo", None)
            return

        # 可能的子目录：processed / preprocess
        candidates = [
            root,
            os.path.join(root, "processed"),
            os.path.join(root, "preprocess"),
        ]

        img_path = None
        for p in candidates:
            if os.path.isdir(p):
                img_path = self._find_first_image(p)
                if img_path:
                    break

        if not img_path:
            self.canvas_processed.delete("content")
            setattr(self, "_processed_photo", None)
            if hasattr(self, "status_var"):
                self.status_var.set("No processed image found in output path.")
            return

        self._show_image_on_canvas(self.canvas_processed, img_path, "_processed_photo")


    def _update_preview_view(self):
        """
        Preview：这里先按最稳妥逻辑，复用 current_file 的显示（与 Original 一致）。
        """
        canvas = getattr(self, "canvas_preview", None)
        if canvas is None:
            return

        lock = getattr(self, "_img_lock", None)
        if lock is not None:
            with self._img_lock:
                temp = self.img_preview
                self._show_ndarray_on_canvas(canvas, temp)
        else:
            temp = self.img_preview
            self._show_ndarray_on_canvas(canvas, temp)


def _to_uint8_for_display(self, arr):
    """
    把任意数值类型的图像转成 uint8 便于显示（不改变原始数据用于计算）。
    """

    if arr is None:
        return None

    a = np.asarray(arr)

    # 如果是彩色且是 BGR（OpenCV 常见），这里不强制判断来源；
    # 我们在后面转 PIL 时再做 BGR->RGB（仅对 3 通道）。
    if a.dtype == np.uint8:
        return a

    a = a.astype(np.float32)
    mn = float(np.nanmin(a))
    mx = float(np.nanmax(a))
    if mx <= mn:
        return np.zeros(a.shape, dtype=np.uint8)

    a = (a - mn) * (255.0 / (mx - mn))
    return np.clip(a, 0, 255).astype(np.uint8)


def _show_ndarray_on_canvas(self, canvas, arr):
    """
    把 ndarray 显示到 Tk canvas（等比缩放 + 居中），并保存 PhotoImage 引用防止被 GC。
    """

    if arr is None:
        canvas.delete("content")
        return

    # 确保 canvas 有真实尺寸
    canvas.update_idletasks()
    cw = max(2, int(canvas.winfo_width()))
    ch = max(2, int(canvas.winfo_height()))

    a = self._to_uint8_for_display(arr)
    if a is None:
        canvas.delete("content")
        return

    # ndarray -> PIL Image
    if a.ndim == 2:
        pil = Image.fromarray(a, mode="L")
    elif a.ndim == 3 and a.shape[2] == 3:
        # OpenCV 通常是 BGR；这里按 BGR->RGB 转一下更符合直觉
        rgb = a[:, :, ::-1]
        pil = Image.fromarray(rgb, mode="RGB")
    elif a.ndim == 3 and a.shape[2] == 4:
        pil = Image.fromarray(a, mode="RGBA")
    else:
        # 兜底：强行压成灰度
        pil = Image.fromarray(a.reshape(a.shape[0], a.shape[1]), mode="L")

    iw, ih = pil.size
    scale = min(cw / max(1, iw), ch / max(1, ih))
    nw = max(1, int(iw * scale))
    nh = max(1, int(ih * scale))
    pil = pil.resize((nw, nh), Image.Resampling.LANCZOS)

    photo = ImageTk.PhotoImage(pil)

    canvas.delete("content")
    canvas.create_image(cw // 2, ch // 2, image=photo, anchor="center", tags="content")
