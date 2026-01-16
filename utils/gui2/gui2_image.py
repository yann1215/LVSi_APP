# gui2_image.py
import os, json, time
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

        self._view_frames = {}
        for name in ["Camera", "Preview", "Original", "Processed"]:
            frame = ttk.Frame(tabs, padding=6)
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)
            self._view_frames[name] = frame

            # 创建四个 tab 的 canvas
            canvas = tk.Canvas(frame, bg="#0b0c0e", highlightthickness=0)
            canvas.grid(row=0, column=0, sticky="nsew")
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
            self._draw_live_view_once()
        elif name == "Preview":
            self._ensure_camera_running()
            self._draw_live_view_once()
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
        canvas.delete("border")
        canvas.create_image(w // 2, h // 2, image=photo, anchor="center", tags="content")

        # 保存引用，防止被垃圾回收
        setattr(self, photo_attr_name, photo)


    # ================== 启用相机（新：后端 + GUI 窗口嵌入分离） ==================
    def _ensure_camera_running(self):
        """
        在 Camera tab 被选中时调用：
        1) 通过 camera_status.start_camera 启动后端（只启动一次）
        2) 启动 GUI 侧 window manager（只启动一次）
        """

        # 1) 用 Canvas 作为“容器”（Camera/Preview 同理）
        container = getattr(self, "canvas_camera", None)
        if container is None:
            if hasattr(self, "status_var"):
                self.status_var.set("[Camera ERROR] camera_canvas not found.")
            return

        # 2) 启动/确保后端（由 camera_status 统一管理 container_hwnd / width / height / resize bind）
        start_camera(self, container, start_backend=True, allow_restart=True, update_status=True)

        # 3) Pillow 刷新循环：一定要启动（否则只会 single_shot 刷一次）
        self._start_live_view_loop()

    def _window_manager_loop(self, *args, **kwargs):
        """
        兼容旧接口（camera_vimbaX.vimbaX_threading 可能会调用）：
        Pillow/Canvas 模式下不需要任何 window embedding。
        这里仅确保 UI 刷新 loop 已启动，并返回。
        注意：可能被后台线程调用，所以只做 thread-safe 的 after 调度。
        """
        try:
            self.after(0, self._start_live_view_loop)
            self.after(0, self._draw_live_view_once)
        except Exception:
            pass
        return

    # ============ 显示各窗口 ============

    def _start_live_view_loop(self):
        """
        启动一次 after loop：只刷新当前可见的 Camera/Preview canvas。
        """
        if getattr(self, "_live_view_loop_running", False):
            return
        self._live_view_loop_running = True
        self.after(0, self._live_view_tick)

    def _draw_live_view_once(self):
        """
        切 tab 时主动刷新一次（不依赖定时器节拍）。
        """
        try:
            self._live_view_tick(single_shot=True)
        except Exception:
            pass

    def _snapshot_frame(self, attr: str):
        """
        锁内取图，返回 copy；无图则 None。
        """
        lock = getattr(self, "_img_lock", None)
        if lock is not None:
            try:
                with lock:
                    v = getattr(self, attr, None)
                    return None if v is None else v.copy()
            except Exception:
                v = getattr(self, attr, None)
                return None if v is None else v.copy()
        v = getattr(self, attr, None)
        return None if v is None else v.copy()

    def _get_empty_frame(self):
        """
        无信号时显示的占位图（优先使用 gui2.py 里加载的 empty.png）。
        """
        empty = getattr(self, "NonePng", None)
        if empty is None:
            return None
        try:
            return empty.copy()
        except Exception:
            return empty

    def _live_view_tick(self, single_shot: bool = False):
        """
        after loop：只刷新当前可见 tab 的 canvas。
        single_shot 让 _live_view_tick() “只执行一轮绘制，不再自己 after() 安排下一次”。
        目前只有 Camera 和 Preview 相关的显示代码。
        """

        # 退出条件：程序结束就停止 loop
        if getattr(self, "EndEvent", None) is not None and self.EndEvent.is_set():
            self._live_view_loop_running = False
            return

        # 窗口最小化时，不刷新
        try:
            if not self.winfo_viewable() or self.state() == "iconic":
                if not single_shot:
                    self.after(200, self._live_view_tick)
                return
        except Exception:
            pass

        # 保护性检查：tabs 不存在或还没建好就延迟再试
        tabs = getattr(self, "tabs_view", None)
        if tabs is None or tabs.index("end") == 0:
            if not single_shot:
                self.after(200, self._live_view_tick)
            return

        # 获取当前 tab 名称
        try:
            name = tabs.tab("current", "text")
        except Exception:
            name = ""

        # 非实时视图：不刷新
        # 降低 CPU、降低锁竞争、避免后台浪费
        if name not in ("Camera", "Preview"):
            if not single_shot:
                self.after(200, self._live_view_tick)
            return

        # 选择要刷新的 Canvas（Camera / Preview 各自一个）
        canvas = getattr(self, "canvas_camera" if name == "Camera" else "canvas_preview", None)
        if canvas is None:
            if not single_shot:
                self.after(200, self._live_view_tick)
            return

        # live_flag=False 时，Camera 优先显示冻结帧（不影响相机后端采集）
        live_flag = bool(getattr(self, "live_flag", True))
        if live_flag:
            if name == "Camera":
                frame = self._snapshot_frame("img")
                frame_to_show = frame

            elif name == "Preview":
                try:
                    p_flag = bool(getattr(self, "preview_flag").get())  # BooleanVar
                except Exception:
                    p_flag = False

                if p_flag:
                    preview = self._snapshot_frame("img_preview")
                    frame_to_show = preview
                else:
                    if not single_shot:
                        self.after(200, self._live_view_tick)
                    return

        else:
            frame_to_show = self._snapshot_frame("img_froze") or self._snapshot_frame("img")
            if frame_to_show is None:
                frame_to_show = self._get_empty_frame()

            _show_ndarray_on_canvas(canvas, frame_to_show)

            if not single_shot:
                self.after(200, self._live_view_tick)

            return

        if frame_to_show is None:
            frame_to_show = self._get_empty_frame()

        _show_ndarray_on_canvas(canvas, frame_to_show)

        if not single_shot:
            interval_ms = _calc_live_view_delay_ms(self)
            self.after(interval_ms, self._live_view_tick)  # 显示的最大刷新率为 30 fps


    def _get_output_root(self):
        """
        把 self.output_filepath 转成可用的本地路径（排除 'auto'）。
        """
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


def _to_uint8_for_display(arr):
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


def _show_ndarray_on_canvas(canvas, arr):
    """
    把 ndarray 显示到 Tk canvas（等比缩放 + 居中），并保存 PhotoImage 引用防止被 GC。
    """

    if arr is None:
        canvas.delete("content")
        canvas.delete("border")
        return

    # 确保 canvas 有真实尺寸
    canvas.update_idletasks()
    cw = max(2, int(canvas.winfo_width()))
    ch = max(2, int(canvas.winfo_height()))

    a = _to_uint8_for_display(arr)
    if a is None:
        canvas.delete("content")
        canvas.delete("border")
        canvas._photo = None
        canvas._img_item = None
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

    # 窗口缩放期间使用 BILINEAR 降低刷新压力
    resample = Image.Resampling.BILINEAR if getattr(canvas.winfo_toplevel(), "_is_resizing",
                                                    False) else Image.Resampling.LANCZOS
    pil = pil.resize((nw, nh), resample)

    photo = ImageTk.PhotoImage(pil)

    # canvas.delete("content")
    # canvas.delete("border")
    # canvas.create_image(cw // 2, ch // 2, image=photo, anchor="center", tags="content")
    item = getattr(canvas, "_img_item", None)
    if item is None:
        canvas._img_item = canvas.create_image(cw // 2, ch // 2, image=photo, anchor="center", tags="content")
    else:
        canvas.itemconfig(item, image=photo)
        canvas.coords(item, cw // 2, ch // 2)

    # 关键：必须保存引用，否则会被 GC 回收，出现“偶尔空白/闪烁”
    # 强引用（strong reference）保活 ImageTk.PhotoImage 对象，防止被 Python 垃圾回收
    canvas._photo = photo


def _calc_live_view_delay_ms(app, cap_fps: float = 30.0, fallback_fps: float = 5.0) -> int:
    """
    根据相机采集帧率动态决定 UI 刷新间隔（ms）。
    建议设置显示上限(30fps)，避免 120fps 在 Tk+PIL 下过载。
    """

    # 如果窗口正在缩放，使用低帧率
    if getattr(app, "_is_resizing", False):
        return 80  # ~12.5 fps

    # 相机 fps
    try:
        fps = float(getattr(app, "all_para_dict", {}).get("vimbaX_AcquisitionFrameRate", fallback_fps))
    except Exception:
        fps = None

    if fps is None or fps <= 0:
        fps = fallback_fps

    # 设置显示 fps 的下限为 1 fps，上限为 30 fps
    # 不影响保存 fps
    fps = max(1.0, min(fps, float(cap_fps)))

    interval_ms = max(1, int(round(1000.0 / fps)))

    # 计算间隔（ms），至少 1ms
    return interval_ms
