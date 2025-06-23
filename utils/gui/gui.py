import tkinter as tk
from gui_panel_center import create_center_frame
from gui_panel_north import create_north_frame
from gui_panel_west import create_west_frame
from gui_panel_east import create_east_frame
from gui_panel_south import create_south_frame
from _para import *
import cv2
from threading import Event
import time


class VideoProcessingApp:
    def __init__(self, root, event, version):
        self.EndEvent = event
        self.NonePng = cv2.imread(os.path.join(base_path, "Fiji.app\\__None__.png"))
        self.img = self.NonePng
        self.img_shape = (728, 544)
        self.west_img_shape = (364, 272)
        self.save_frame = False
        self.save_path = None
        self.save_step = 0
        self.camera_settings = False
        self.default_ID = ""

        self.all_para_dict = all_para_dict.copy()
        self.filepath_list = []
        self.output_filepath = "auto"
        self.task_list = []
        self.output_root = None
        self.task_mode = None
        self.program_start = 0
        self.program_end = 3

        self.searching = False
        self.running = False
        self.camera = False

        self.root = root
        self.root.title(version)
        self.root.geometry("1000x750")
        self.root.configure(bg='#eaeaea')

        self.nodes = ['图像获取', '噪声过滤', '检测追踪', '特征提取']
        self.object_dict_list = []

        # 设置整体布局
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # 创建未使用的区域（保持布局完整性）
        create_west_frame(self)
        create_north_frame(self)

        # 创建三个主要区域
        create_center_frame(self)
        create_east_frame(self)
        create_south_frame(self)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        print("exit")
        self.EndEvent.set()
        time.sleep(1)
        self.root.destroy()


def gui_init(version):
    root = tk.Tk()
    event = Event()
    app = VideoProcessingApp(root, event, version)
    root.mainloop()
