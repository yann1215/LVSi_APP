import os, time
import threading

from utils.camera.camera_capture import handle_new_frame   # 注意你的实际模块路径


# Vinma X download website: https://www.alliedvision.com/en/products/software/vimba-x-sdk/#c13326
VIMBAX_FLAG = False
_VMBPY_IMPORT_ERROR = None

# ---- BitDepth / PixelFormat mapping helpers ----
_BITDEPTH_INT_TO_NAME = {
    0: "Adaptive",
    1: "Bpp8",
    2: "Bpp10",
    3: "Bpp12",
}
# 用 SensorBitDepth 选择来驱动输出 PixelFormat
_BITDEPTH_NAME_TO_PF_CANDIDATES = {
    "Bpp8":  ["Mono8"],
    "Bpp10": ["Mono10", "Mono10p", "Mono16"],   # Mono10p/Mono16 作为兼容回退
    "Bpp12": ["Mono12", "Mono12p", "Mono16"],   # Mono12p/Mono16 作为兼容回退
}


def _init_vmbpy():
    """
    vimba X 软件初始化；在start_vimvaX()中调用
    """

    global VIMBAX_FLAG, _VMBPY_IMPORT_ERROR
    global VmbSystem, VmbTransportLayerError, PixelFormat

    if VIMBAX_FLAG:
        return True

    try:
        from vmbpy import VmbSystem, VmbTransportLayerError, PixelFormat
        VIMBAX_FLAG = True
        _VMBPY_IMPORT_ERROR = None
        return True
    except Exception as e:
        _VMBPY_IMPORT_ERROR = e

    # Windows：可选地尝试把 VimbaX 的 api\bin 加进 DLL 搜索路径
    if os.name == "nt":
        dll_dirs = [
            os.environ.get("VIMBAX_API_BIN"),  # 允许你用环境变量指定
            r"C:\Program Files\Allied Vision\Vimba X\api\bin",
            r"C:\Program Files\Allied Vision\Vimba X\api\bin\x64",
            r"D:\Vimba X\api\bin",
        ]
        for d in filter(None, dll_dirs):
            if os.path.isdir(d):
                try:
                    os.add_dll_directory(d)
                except Exception:
                    pass
        try:
            from vmbpy import VmbSystem, VmbTransportLayerError, PixelFormat
            VIMBAX_FLAG = True
            _VMBPY_IMPORT_ERROR = None
            return True
        except Exception as e:
            _VMBPY_IMPORT_ERROR = e

    VIMBAX_FLAG = False
    return False


def work_thread(app, vmb):
    print("Camera starting...")
    handler = vimbaX_photo_handler(app)
    cams = vmb.get_all_cameras()
    with cams[0] as cam:
        camera_settings_get(app, cam)

        # 第一次 start_streaming 前就下发位深
        _apply_bitdepth_and_pixelformat(app, cam)

        cam.start_streaming(handler)
        while app.camera:
            # 参数需要更新
            if app.camera_settings:
                cam.stop_streaming()
                time.sleep(0.1)
                cam.AcquisitionFrameRateEnable.set(True)
                cam.AcquisitionFrameRate.set(app.all_para_dict['vimbaX_AcquisitionFrameRate'])
                cam.ExposureTime.set(app.all_para_dict['vimbaX_ExposureTime'])
                cam.Gain.set(app.all_para_dict['vimbaX_Gain'])
                # cam.SensorBitDepth.set(app.all_para_dict['vimbaX_SensorBitDepth'])
                _apply_bitdepth_and_pixelformat(app, cam)

                time.sleep(0.1)
                cam.start_streaming(handler)

                app.camera_settings = False
                app._cam_settings_applied_ts = time.monotonic()
            else:
                time.sleep(1)
        cam.stop_streaming()
    app.img = app.NonePng
    print("stop cam work")


def _apply_bitdepth_and_pixelformat(app, cam) -> None:
    bd_name = _resolve_bitdepth_name(app)

    # 1) SensorBitDepth
    if bd_name != "Adaptive":
        try:
            cam.SensorBitDepth.set(bd_name)  # 'Bpp8'/'Bpp10'/'Bpp12'
        except Exception:
            try:
                raw = (getattr(app, "all_para_dict", {}) or {}).get("vimbaX_SensorBitDepth")
                cam.SensorBitDepth.set(raw)
            except Exception as e:
                print("Warning: set SensorBitDepth failed:", e)

    # 2) PixelFormat
    try:
        pf_feature = getattr(cam, "PixelFormat")
    except Exception:
        pf_feature = None

    if pf_feature is None or bd_name == "Adaptive":
        return

    candidates = _BITDEPTH_NAME_TO_PF_CANDIDATES.get(bd_name, ["Mono8"])
    PF = globals().get("PixelFormat", None)

    for name in candidates:
        try:
            pf_feature.set(name)          # 先尝试字符串
            return
        except Exception:
            pass

        if PF is not None:
            enum_val = getattr(PF, name, None)
            if enum_val is not None:
                try:
                    pf_feature.set(enum_val)  # 再尝试枚举
                    return
                except Exception:
                    pass

    print(f"Warning: unable to set PixelFormat for {bd_name}; keeping current PixelFormat.")


def vimbaX_photo_handler(app):
    # 创建一个 frame 回调函数，同时传递 app
    def frame_handler(cam, stream, frame):
        # 不会因为异常导致回调链路不稳定；无效帧会被跳过并回收
        # img = frame.as_opencv_image()  # ndarray
        try:
            img = frame.as_opencv_image()  # ndarray
        except ValueError:
            # 收到不完整帧/切流期间的帧时，pixelFormat 可能为 0
            try:
                cam.queue_frame(frame)
            except Exception:
                pass
            return
        except Exception:
            # 任何转换失败都不要炸回调
            try:
                cam.queue_frame(frame)
            except Exception:
                pass
            return

        handle_new_frame(app, img)  # 这里会用 _img_lock 写入 app.img
        cam.queue_frame(frame)

    return frame_handler


def _resolve_bitdepth_name(app) -> str:
    """
    把 all_para_dict['vimbaX_SensorBitDepth'] 解析成 'Adaptive'/'Bpp8'/'Bpp10'/'Bpp12'。
    """
    d = getattr(app, "all_para_dict", None) or {}
    v = d.get("vimbaX_SensorBitDepth", "Bpp8")

    # 兼容 int / str(int) / str(name)
    if isinstance(v, int):
        return _BITDEPTH_INT_TO_NAME.get(v, "Bpp8")

    s = str(v).strip()
    if s in _BITDEPTH_INT_TO_NAME.values():
        return s

    try:
        iv = int(s)
        return _BITDEPTH_INT_TO_NAME.get(iv, "Bpp8")
    except Exception:
        return "Bpp8"


def vimbaX_finder_handler(app, vmb):
    def print_device_id(dev , state):
        """
        当相机插拔、接口状态变化时，print_device_id(dev, state) 会被 SDK 调用
        state == 1 or 2：认为设备可用;
        state == 0/3/4：认为设备不可用.
        """
        print(state)
        if state == 1 or state == 2:
            app.camera = True
            thread = threading.Thread(target=work_thread, args=(app, vmb), daemon=True)
            thread.start()
            if app.searching == False and app.running == False and (app.program_start == app.task_mode):
                app.AST_btn_var.set("Camera started.")
                app.AST_btn.config(bg='#4CAF50')
        elif state == 0 or state == 3 or state == 4:
            app.camera = False
            app.AST_btn_var.set("Camera not found.")
            app.AST_btn.config(bg='#cccccc')
    return print_device_id


def _safe_set_tk_var(app, var_name: str, value: str):
    var = getattr(app, var_name, None)
    if var is None:
        return
    try:
        if hasattr(app, "after"):
            app.after(0, lambda: var.set(value))
        else:
            var.set(value)
    except Exception:
        pass


def start_vimbaX(app):

    if not _init_vmbpy():
        _safe_set_tk_var(app, "Alltitle_var", "LVSi System ( Vimba X not available )")
        # 把 _VMBPY_IMPORT_ERROR 打印出来, 便于定位 bug
        print("VimbaX/vmbpy init failed:", _VMBPY_IMPORT_ERROR)
        return

    if VIMBAX_FLAG:
        try:
            # note: 这里内部出现了VmbTransportLayerError
            with VmbSystem.get_instance() as vmb:
                print("Vimba X connected.")
                # app.Alltitle_var.set("LVSi System ( Vimba X Installed )")
                _safe_set_tk_var(app, "Alltitle_var", "LVSi System")
                # 找相机并启用
                handler = vimbaX_finder_handler(app, vmb)
                vmb.register_camera_change_handler(handler)
                vmb.register_interface_change_handler(handler)
                if vmb.get_all_cameras():
                    app.camera = True
                    work_thread(app, vmb)
                app.EndEvent.wait()
        except VmbTransportLayerError as e:
            # Vimba X 没装好 / 没有 TL的情况
            if hasattr(app, "Alltitle_var"):
                # app.Alltitle_var.set("LVSi System ( Require Vimba X Installation ! )")
                _safe_set_tk_var(app, "Alltitle_var", "LVSi System ( Require Vimba X Installation ! )")
            print("Vimba X TransportLayerError:", e)
            return      # 直接 return，不再调用 window_manager
        except Exception as e:
            # 其它未知错误
            print("Vimba X error:", e)
            return
    else:
        # app.Alltitle_var.set("LVSi System ( Require Vimba X Installation ! )")
        _safe_set_tk_var(app, "Alltitle_var", "LVSi System ( Require Vimba X Installation ! )")


def start_vimbaX_backend_thread(app):
    """
    新接口：仅启动相机后端采集线程（不启动任何 window_manager）。
    推荐由 camera_status.start_camera() 调用。
    """
    t = threading.Thread(target=start_vimbaX, args=(app,), daemon=True, name="vimbaX-backend")
    t.start()
    return t


def vimbaX_threading(app, start_window: bool = False, window_name: str = "vimba X"):
    """

    """
    print("[DEPRECATED] vimbaX_threading(): prefer camera_status.start_camera() + GUI _window_manager_loop().")

    # 1) 启动后端
    t_backend = start_vimbaX_backend_thread(app)

    # 2) 启动 window manager（使用 GUI2 的 _window_manager_loop）
    if start_window and hasattr(app, "_window_manager_loop"):
        try:
            # thread-safe：交给 Tk 主线程
            app.after(0, lambda: app._window_manager_loop(window_name))
        except Exception:
            # 没有 Tk 环境就忽略
            pass

    return t_backend


def camera_settings_get(app, cam):
    app.all_para_dict['vimbaX_ExposureTime'] = cam.ExposureTime.get()
    app.all_para_dict['vimbaX_Gain'] = cam.Gain.get()
    app.all_para_dict['vimbaX_SensorBitDepth'] = cam.SensorBitDepth.get().as_tuple()[1]
    app.all_para_dict['vimbaX_AcquisitionFrameRate'] = cam.AcquisitionFrameRate.get()
