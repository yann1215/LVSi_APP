# camera/camera_capture.py
from __future__ import annotations

import os
from typing import Any, Optional

import numpy as np
from PIL import Image
import tifffile
from tkinter import filedialog


def handle_new_frame(app: Any, frame) -> None:
    """
    相机回调入口：把单张相机图像写入 app.img。
    - 不做 per-frame copy（按你的要求）
    - 写入时使用 app._img_lock（如存在）
    """
    lock = getattr(app, "_img_lock", None)
    if lock is not None:
        try:
            with lock:
                app.img = frame
        except Exception:
            app.img = frame
    else:
        app.img = frame


def get_single_frame(app: Any) -> Optional[np.ndarray]:
    """
    取要保存的帧：
    - live_flag=True  -> 保存 app.img
    - live_flag=False -> 保存 app.img_froze（没有则回退 app.img）
    """
    live = bool(getattr(app, "live_flag", False))
    lock = getattr(app, "_img_lock", None)

    if lock is not None:
        try:
            with lock:
                if live:
                    src = getattr(app, "img", None)
                else:
                    src = getattr(app, "img_froze", None) or getattr(app, "img", None)
        except Exception:
            if live:
                src = getattr(app, "img", None)
            else:
                src = getattr(app, "img_froze", None) or getattr(app, "img", None)
    else:
        if live:
            src = getattr(app, "img", None)
        else:
            src = getattr(app, "img_froze", None) or getattr(app, "img", None)

    if src is None:
        return None

    # 只在“点击保存”时 copy 一次，避免保存过程中源被替换/变化
    arr = np.asarray(src.copy())

    # 兜底：如果是 3 通道，取第 1 通道
    if arr.ndim == 3:
        arr = arr[:, :, 0]

    # 兜底：确保 uint8
    if arr.dtype != np.uint8:
        arr = np.clip(arr.astype(np.float32), 0, 255).astype(np.uint8)

    return arr


def capture_single(app: Any) -> Optional[str]:
    """
    用户点击保存单张图像：
    - 允许保存 .tif/.tiff/.png/.jpg/.jpeg
    - tiff 用 tifffile 保存（不压缩）
    - png/jpg 用 PIL 保存
    返回保存路径；取消则 None。
    """
    path = filedialog.asksaveasfilename(
        parent=app,
        title="Save snapshot",
        defaultextension=".tif",
        filetypes=[
            ("TIFF image", "*.tif *.tiff"),
            ("PNG image", "*.png"),
            ("JPEG image", "*.jpg *.jpeg"),
        ],
    )
    if not path:
        return None

    arr = get_single_frame(app)
    if arr is None:
        return None

    ext = os.path.splitext(path)[1].lower()

    if ext in (".tif", ".tiff"):
        tifffile.imwrite(path, arr, photometric="minisblack")
    elif ext == ".png":
        Image.fromarray(arr, mode="L").save(path, format="PNG")
    elif ext in (".jpg", ".jpeg"):
        Image.fromarray(arr, mode="L").save(path, format="JPEG", quality=95)
    else:
        # 兜底：不支持/没扩展名，默认 tiff
        path = path + ".tif"
        tifffile.imwrite(path, arr, photometric="minisblack")

    return path
