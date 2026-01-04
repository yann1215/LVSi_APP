# gui2_image.py
import os
import json
import tkinter as tk
from ttkbootstrap import ttk
import threading
from utils.camera.camera_vimbaX import vimbaX_threading

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
            self._start_camera()
        elif name == "Preview":
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
        from PIL import Image, ImageTk  # gui2 顶部已经 import 过，这里再 import 一次也没关系

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

    # ================== 启用相机 ==================
    def _start_camera(self):
        """
        在 Camera tab 被选中时调用     # note: 把启动条件修改了，改在gui.py进行app_init的时候启动？
        启动一次 vimbaX_threading。
        """

        # 确保有 camera_container（在 _build_view_area 里创建的那个 Frame）
        container = getattr(self, "camera_container", None)
        if container is None:
            print("[Camera ERROR] Camera container not found.")
            return

        # 刷新画面尺寸信息
        container.update_idletasks()
        self.video_frame_width = container.winfo_width()
        self.video_frame_height = container.winfo_height()

        # 如果相机已经启动，就不重复启动.
        if getattr(self, "_camera_running", False):
            return
        else:
            self.status_var.set("Starting camera…")

            # 关键：告诉 vimbaX 把画面画到这个窗口上
            self.container_hwnd = int(container.winfo_id())

            # 调用 vimbaX_threading(self) 启动线程
            t = threading.Thread(target=vimbaX_threading, args=(self,), daemon=True)
            t.start()

            self._camera_running = True
            self.status_var.set("Camera running.")

    # ============ 显示 Camera/Original/Processed/Tracked ============

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

        path = getattr(self, "current_file", "")
        img_path = self._find_first_image(path) if path else None

        if not img_path:
            canvas.delete("content")
            setattr(self, "_preview_photo", None)
            if hasattr(self, "status_var") and path:
                self.status_var.set("No image found for Preview.")
            return

        self._show_image_on_canvas(canvas, img_path, "_preview_photo")
