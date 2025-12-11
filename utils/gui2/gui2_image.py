# gui2_image.py
import os
import json
import tkinter as tk
import threading
from utils.camera.ast_vimbaX import vimbaX_threading

class ImageMixin:
    """
    负责右侧画布的显示。包含以下内容：
    Camera:
    Original:
    Processed:
    Tracked:
    """

    # ================ 显示画布 ================

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
        在 Camera tab 被选中时调用
        启动一次 vimbaX_threading。
        """

        # 确保有 camera_container（在 _build_view_area 里创建的那个 Frame）
        container = getattr(self, "camera_container", None)
        if container is None:
            return

        # 刷新画面尺寸信息
        container.update_idletasks()
        self.video_frame_width = container.winfo_width()
        self.video_frame_height = container.winfo_height()

        # 如果相机已经启动，就不重复启动.
        if getattr(self, "_camera_running", False):
            return
        else:
            # 关键：告诉 vimbaX 把画面画到这个窗口上
            self.container_hwnd = int(container.winfo_id())

            # 调用 vimbaX_threading(self) 启动线程
            t = threading.Thread(target=vimbaX_threading, args=(self,), daemon=True)
            t.start()

            self._camera_running = True

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

    def _update_tracked_view(self):
        """
        根据 Output Path 更新 Tracked 画布。
        """
        root = self._get_output_root()
        if not root or not os.path.isdir(root):
            self.canvas_tracked.delete("content")
            setattr(self, "_tracked_photo", None)
            return

        candidates = [
            os.path.join(root, "tracked"),
            os.path.join(root, "track"),
            os.path.join(root, "trackmate"),
            root,  # 最后退回根目录
        ]

        img_path = None
        for p in candidates:
            if os.path.isdir(p):
                img_path = self._find_first_image(p)
                if img_path:
                    break

        if not img_path:
            self.canvas_tracked.delete("content")
            setattr(self, "_tracked_photo", None)
            if hasattr(self, "status_var"):
                self.status_var.set("No tracked image found in output path.")
            return

        self._show_image_on_canvas(self.canvas_tracked, img_path, "_tracked_photo")
