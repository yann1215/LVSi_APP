import os, time
import threading
import cv2


# Vinma X download website: https://www.alliedvision.com/en/products/software/vimba-x-sdk/#c13326
VIMBAX_FLAG = False
# VIMBAX_PATH = "C:\\Program Files\\Allied Vision\\Vimba X\\api\\bin\\VmbC.dll"
VIMBAX_PATH = "D:\\Vimba X\\api\\bin\\VmbC.dll"     # D盘安装补丁（路径选择待后续优化）
# VIMBAX_PATH = "D:\\Allied Vision\\Vimba X\\api\\bin\\VmbC.dll"

if os.path.exists(VIMBAX_PATH):
    from vmbpy import *
    VIMBAX_FLAG = True


def work_thread(self, vmb):
    print("Camera starting...")
    handler = vimbaX_photo_handler(self)
    cams = vmb.get_all_cameras()
    with cams[0] as cam:
        camera_settings_get(self, cam)
        cam.start_streaming(handler)
        while self.camera:
            if self.camera_settings:
                cam.stop_streaming()
                time.sleep(0.1)
                cam.AcquisitionFrameRateEnable.set(True)
                cam.AcquisitionFrameRate.set(self.all_para_dict['vimbaX_AcquisitionFrameRate'])
                cam.ExposureTime.set(self.all_para_dict['vimbaX_ExposureTime'])
                cam.Gain.set(self.all_para_dict['vimbaX_Gain'])
                cam.SensorBitDepth.set(self.all_para_dict['vimbaX_SensorBitDepth'])
                time.sleep(0.1)
                cam.start_streaming(handler)
                self.camera_settings = False
            else:
                time.sleep(1)
        cam.stop_streaming()
    self.img = self.NonePng
    print("stop cam work")


def vimbaX_photo_handler(self):
    def frame_handler(cam: Camera, stream: Stream, frame: Frame):
        frame.convert_pixel_format(PixelFormat.Mono8)
        self.img = frame.as_opencv_image()
        if self.save_frame:
            cv2.imwrite(self.save_path + "\\" + "1_" + str(self.save_step) +'.tiff', self.img)
        self.save_step += 1
        cam.queue_frame(frame)
    return frame_handler


def vimbaX_finder_handler(self, vmb):
    def print_device_id(dev , state):
        print(state)
        if state == 1 or state == 2:
            self.camera = True
            thread = threading.Thread(target=work_thread, args=(self, vmb), daemon=True)
            thread.start()
            if self.searching == False and self.running == False and (self.program_start == self.task_mode):
                self.AST_btn_var.set("Camera started")
                self.AST_btn.config(bg='#4CAF50')
        elif state == 0 or state == 3 or state == 4:
            self.camera = False
            self.AST_btn_var.set("Camera not found.")
            self.AST_btn.config(bg='#cccccc')
    return print_device_id


def _safe_set_tk_var(self, var_name: str, value: str):
    var = getattr(self, var_name, None)
    if var is None:
        return
    try:
        if hasattr(self, "after"):
            self.after(0, lambda: var.set(value))
        else:
            var.set(value)
    except Exception:
        pass


def start_vimbaX(self):
    if VIMBAX_FLAG:
        try:
            # note: 这里内部出现了VmbTransportLayerError
            with VmbSystem.get_instance() as vmb:
                print("Vimba X installed. Camera starting...")
                # self.Alltitle_var.set("LVSi System ( Vimba X Installed )")
                _safe_set_tk_var(self, "Alltitle_var", "LVSi System ( Vimba X Installed )")
                # 找相机并启用
                handler = vimbaX_finder_handler(self, vmb)
                vmb.register_camera_change_handler(handler)
                vmb.register_interface_change_handler(handler)
                if vmb.get_all_cameras():
                    self.camera = True
                    work_thread(self, vmb)
                self.EndEvent.wait()
        except VmbTransportLayerError as e:
            # Vimba X 没装好 / 没有 TL的情况
            if hasattr(self, "Alltitle_var"):
                # self.Alltitle_var.set("LVSi System ( Require Vimba X Installation ! )")
                _safe_set_tk_var(self, "Alltitle_var", "LVSi System ( Require Vimba X Installation ! )")
            print("Vimba X TransportLayerError:", e)
            return      # 直接 return，不再调用 window_manager
        except Exception as e:
            # 其它未知错误
            print("Vimba X error:", e)
            return
    else:
        # self.Alltitle_var.set("LVSi System ( Require Vimba X Installation ! )")
        _safe_set_tk_var(self, "Alltitle_var", "LVSi System ( Require Vimba X Installation ! )")


def start_vimbaX_backend_thread(self):
    """
    新接口：仅启动相机后端采集线程（不启动任何 window_manager）。
    推荐由 camera_status.start_camera() 调用。
    """
    t = threading.Thread(target=start_vimbaX, args=(self,), daemon=True, name="vimbaX-backend")
    t.start()
    return t


def window_manager_legacy(self, window_name):
    """
       LEGACY ONLY：旧版 window_manager。
       新版 GUI2 请使用 gui2_image.ImageMixin._window_manager_loop。
       """
    import time
    import cv2

    try:
        import win32gui
        import win32con
    except Exception as e:
        print("[LEGACY window_manager] pywin32 not available:", e)
        return

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    hwnd = win32gui.FindWindow(None, window_name)
    if not hwnd:
        # 给一点时间让窗口创建出来
        cv2.imshow(window_name, getattr(self, "img", None))
        cv2.waitKey(1)
        for _ in range(20):
            hwnd = win32gui.FindWindow(None, window_name)
            if hwnd:
                break
            time.sleep(0.05)

    if not hwnd:
        print("[LEGACY window_manager] FindWindow failed.")
        return

    win32gui.SetParent(hwnd, int(getattr(self, "container_hwnd", 0) or 0))

    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME |
               win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX |
               win32con.WS_BORDER | win32con.WS_SIZEBOX)
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

    last_w, last_h = -1, -1

    while True:
        if getattr(self, "EndEvent", None) is not None and self.EndEvent.is_set():
            break

        w = int(getattr(self, "video_frame_width", 1) or 1)
        h = int(getattr(self, "video_frame_height", 1) or 1)
        w = max(2, w)
        h = max(2, h)

        if w != last_w or h != last_h:
            try:
                win32gui.MoveWindow(hwnd, 0, 0, w, h, True)
                last_w, last_h = w, h
            except Exception:
                pass

        img = getattr(self, "img", None)
        if img is not None:
            cv2.imshow(window_name, img)
            cv2.waitKey(1)

        time.sleep(0.01)

    try:
        cv2.destroyWindow(window_name)
    except Exception:
        pass


def vimbaX_threading(self, start_window: bool = True, window_name: str = "vimba X"):
    """
    DEPRECATED（兼容旧调用）：
    - 旧逻辑：同时启动 start_vimbaX + window_manager（在本文件）
    - 新逻辑：只推荐启动后端 start_vimbaX_backend_thread；
            window_manager 由 GUI（gui2_image.py）提供的 _window_manager_loop 管理。

    参数：
    - start_window: 为兼容旧 GUI，默认仍尝试启动窗口管理
    - window_name: OpenCV 窗口名称
    """
    print("[DEPRECATED] vimbaX_threading(): prefer camera_status.start_camera() + GUI _window_manager_loop().")

    # 1) 启动后端
    t_backend = start_vimbaX_backend_thread(self)

    # 2) 启动 window manager（优先 GUI 的 _window_manager_loop；否则退回 legacy）
    if start_window:
        if hasattr(self, "_window_manager_loop"):
            t_win = threading.Thread(
                target=self._window_manager_loop,
                args=(window_name,),
                daemon=True,
                name="vimbaX-window-manager(GUI)",
            )
            t_win.start()
        else:
            # 兼容旧 GUI：仍提供 legacy window_manager
            t_win = threading.Thread(
                target=window_manager_legacy,
                args=(self, window_name),
                daemon=True,
                name="vimbaX-window-manager(legacy)",
            )
            t_win.start()

    return t_backend


def camera_settings_get(self, cam):
    self.all_para_dict['vimbaX_ExposureTime'] = cam.ExposureTime.get()
    self.all_para_dict['vimbaX_Gain'] = cam.Gain.get()
    self.all_para_dict['vimbaX_SensorBitDepth'] = cam.SensorBitDepth.get().as_tuple()[1]
    self.all_para_dict['vimbaX_AcquisitionFrameRate'] = cam.AcquisitionFrameRate.get()
