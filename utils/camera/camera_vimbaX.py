import os, time
import threading

from utils.camera.camera_capture import handle_new_frame   # 注意你的实际模块路径


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
    # 创建一个 frame 回调函数，同时传递 self
    def frame_handler(cam, stream, frame):
        frame.convert_pixel_format(PixelFormat.Mono8)
        img = frame.as_opencv_image()  # ndarray

        handle_new_frame(self, img)  # 这里会用 _img_lock 写入 self.img（不 per-frame copy）

        cam.queue_frame(frame)

    return frame_handler


def vimbaX_finder_handler(self, vmb):
    def print_device_id(dev , state):
        """
        当相机插拔、接口状态变化时，print_device_id(dev, state) 会被 SDK 调用
        state == 1 or 2：认为设备可用;
        state == 0/3/4：认为设备不可用.
        """
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


def vimbaX_threading(self, start_window: bool = False, window_name: str = "vimba X"):
    """

    """
    print("[DEPRECATED] vimbaX_threading(): prefer camera_status.start_camera() + GUI _window_manager_loop().")

    # 1) 启动后端
    t_backend = start_vimbaX_backend_thread(self)

    # 2) 启动 window manager（使用 GUI2 的 _window_manager_loop）
    if start_window and hasattr(self, "_window_manager_loop"):
        try:
            # thread-safe：交给 Tk 主线程
            self.after(0, lambda: self._window_manager_loop(window_name))
        except Exception:
            # 没有 Tk 环境就忽略
            pass

    return t_backend


def camera_settings_get(self, cam):
    self.all_para_dict['vimbaX_ExposureTime'] = cam.ExposureTime.get()
    self.all_para_dict['vimbaX_Gain'] = cam.Gain.get()
    self.all_para_dict['vimbaX_SensorBitDepth'] = cam.SensorBitDepth.get().as_tuple()[1]
    self.all_para_dict['vimbaX_AcquisitionFrameRate'] = cam.AcquisitionFrameRate.get()
