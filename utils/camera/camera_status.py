# utils/camera/camera_status.py
from __future__ import annotations

import threading
from typing import Any, Optional


def set_status(app: Any, msg: str) -> None:
    """
    可选的状态更新：如果 app 有 status_var，就更新；否则静默跳过。
    注意：start_camera 通常在 Tk 主线程被调用，因此直接 set 一般是安全的。
    """
    var = getattr(app, "status_var", None)
    if var is None:
        return
    try:
        var.set(msg)
    except Exception:
        # 避免因为状态栏缺失/已销毁导致异常
        pass


def _ensure_resize_binding(app: Any, container: Any) -> None:
    """
    绑定一次 <Configure>，让 Tk 主线程把容器尺寸变化写入 app.video_frame_width/height。
    window_manager / 后台线程只读这些数值，避免跨线程调用 Tk API。
    """
    if getattr(app, "_camera_resize_bound", False):
        return

    def _on_resize(e: Any) -> None:
        try:
            app.video_frame_width = max(1, int(e.width))
            app.video_frame_height = max(1, int(e.height))
        except Exception:
            pass

    try:
        container.bind("<Configure>", _on_resize, add="+")
        app._camera_resize_bound = True
    except Exception:
        # 极少数情况下 container 不支持 bind；此处不强制失败
        pass


def _sync_container_metrics(app: Any, container: Any) -> None:
    """
    启动时同步一次容器的尺寸与 HWND（winfo_id）。
    """
    try:
        container.update_idletasks()
    except Exception:
        pass

    # width / height
    try:
        w = int(container.winfo_width() or 1)
        h = int(container.winfo_height() or 1)
    except Exception:
        w, h = 1, 1

    app.video_frame_width = max(1, w)
    app.video_frame_height = max(1, h)

    # HWND / winfo_id
    try:
        hwnd = int(container.winfo_id())
    except Exception:
        hwnd = 0

    # hwnd==0 通常意味着控件尚未真正创建映射；先不强制报错
    if hwnd > 0:
        app.container_hwnd = hwnd


def _backend_alive(app: Any) -> bool:
    # 判断 backend 是否正在运行
    t = getattr(app, "_camera_backend_thread", None)
    return bool(t) and getattr(t, "is_alive", lambda: False)()


def _start_backend_thread(app: Any) -> threading.Thread:
    """
    只启动相机后端采集线程（不启动 window_manager）。
    """
    # 相对导入：camera_status.py 与 ast_vimbaX.py 在同一 package 下
    from .camera_vimbaX import start_vimbaX

    t = threading.Thread(
        target=start_vimbaX,
        args=(app,),
        daemon=True,
        name="vimbaX-backend",
    )
    t.start()
    app._camera_backend_thread = t
    return t


def start_camera(
    app: Any,
    container: Optional[Any] = None,
    *,
    start_backend: bool = True,
    allow_restart: bool = True,
    update_status: bool = True,
) -> bool:
    """
    对外入口：在 Camera tab 被选中时调用（或你希望提前启动时调用）。

    它负责：
    2) 绑定 container 的 <Configure> 以便后续 resize 自动更新 width/height
    3) 防重复启动
    4) 启动 VimbaX 后端采集线程（仅后端，不包含 window_manager）

    返回值：
    - True: 本次确实触发了“启动/重启”逻辑
    - False: 已在运行且无需重启
    """

    # container 的获取已在 start_camera() 调用前进行确保

    # 先同步一次当前尺寸 + HWND
    _sync_container_metrics(app, container)
    # 绑定 resize（只绑定一次）
    _ensure_resize_binding(app, container)

    # 已经标记运行：判断是否需要允许“后端已死 -> 重启”
    camera_running_flag = bool(getattr(app, "_camera_running", False))
    # 判断 backend 是否存在且正在运行
    backend_is_alive = _backend_alive(app)
    if camera_running_flag:
        if backend_is_alive:
            # 正常在跑：不重复启动
            return False
        else:
            # 标记在跑但线程死了：允许重启时清 flag
            if allow_restart:
                try:
                    app._camera_running = False
                except Exception:
                    pass
            else:
                return False

    # 这里开始执行启动
    print("Starting camera...")
    if update_status:
        set_status(app, "Starting camera...")

    if start_backend and not backend_is_alive:
        # 若 vimba X 后端线程不在跑，则启动
        print("Starting vimba X...")
        if update_status:
            set_status(app, "Starting vimba X...")
        _start_backend_thread(app)

    # 相机开始尝试启动
    app._camera_running = True

    return True
