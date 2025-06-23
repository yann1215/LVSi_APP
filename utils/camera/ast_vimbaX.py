import time
import threading
import cv2
import win32gui
import win32con
import os

check_vimba = False
if os.path.exists("C:\\Program Files\\Allied Vision\\Vimba X\\api\\bin\\VmbC.dll"):
    from vmbpy import *
    check_vimba = True


def work_thread(self, vmb):
    print("start cam work")
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
                self.AST_btn_var.set("开始运行")
                self.AST_btn.config(bg='#4CAF50')
        elif state == 0 or state == 3 or state == 4:
            self.camera = False
            self.AST_btn_var.set("无相机")
            self.AST_btn.config(bg='#cccccc')
    return print_device_id


def start_vimbaX(self):
    if check_vimba:
        with VmbSystem.get_instance() as vmb:
            self.Alltitle_var.set("大视场散射成像图像处理系统(已检测到Vimba X)")
            handler = vimbaX_finder_handler(self, vmb)
            vmb.register_camera_change_handler(handler)
            vmb.register_interface_change_handler(handler)
            if vmb.get_all_cameras():
                self.camera = True
                work_thread(self, vmb)
            self.EndEvent.wait()
    else:
        self.Alltitle_var.set("大视场散射成像图像处理系统(请安装Vimba X)")


def window_manager(self, window_name):
    cv2.namedWindow(window_name)
    self.hwnd = win32gui.FindWindow(None, window_name)
    win32gui.SetParent(self.hwnd, self.container_hwnd)
    style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
    style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX|
                  win32con.WS_BORDER | win32con.WS_SIZEBOX)
    win32gui.SetWindowLong(self.hwnd, win32con.GWL_STYLE, style)
    width = self.video_frame_width
    height = self.video_frame_height
    win32gui.MoveWindow(
        self.hwnd,
        0, 0,
        width,
        height,
        True
    )
    time_step = 0
    while True:
        time_step += 1
        if time_step > 100:
            time_step = 0
            show_img = cv2.resize(self.img, (self.img_shape[0], self.img_shape[1]))
            cv2.imshow(window_name, show_img)
            cv2.waitKey(1)
        if self.EndEvent.is_set():
            break


def vimbaX_threading(self):
    thread = threading.Thread(target=start_vimbaX, args=(self,), daemon=True)
    thread.start()
    thread = threading.Thread(target=window_manager, args=(self, "vimba X"), daemon=True)
    thread.start()
    return


def camera_settings_get(self, cam):
    self.all_para_dict['vimbaX_ExposureTime'] = cam.ExposureTime.get()
    self.all_para_dict['vimbaX_Gain'] = cam.Gain.get()
    self.all_para_dict['vimbaX_SensorBitDepth'] = cam.SensorBitDepth.get().as_tuple()[1]
    self.all_para_dict['vimbaX_AcquisitionFrameRate'] = cam.AcquisitionFrameRate.get()
