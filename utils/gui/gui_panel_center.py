import tkinter as tk
from utils.camera.ast_vimbaX import vimbaX_threading

def create_center_frame(self):
    """
    创建中间的视频展示区域
    """

    center_frame = tk.Frame(self.root, bg='#eaeaea', padx=10, pady=10)
    center_frame.grid(row=1, column=1, sticky='nsew')

    # 视频展示区域
    video_frame = tk.Frame(center_frame, bg='black', width=728, height=544)
    video_frame.pack(padx=0, pady=0)
    self.video_frame_width = video_frame.winfo_width()
    self.video_frame_height = video_frame.winfo_height()
    self.container_hwnd = int(video_frame.winfo_id())
    vimbaX_threading(self)
