import tkinter as tk

def create_west_frame(self):
    """创建西部的空白区域"""
    west_frame = tk.Frame(self.root, bg='#eaeaea', width=10)
    west_frame.grid(row=1, column=0, sticky='ns')

    # self.pre_video_frame = tk.Frame(west_frame, bg='black', width=364, height=272)
    # self.pre_video_frame.grid(row=0, column=0, sticky='w', padx = 5, pady = 5)
    #
    # self.trackmate_video_frame = tk.Frame(west_frame, bg='black', width=364, height=272)
    # self.trackmate_video_frame.grid(row=1, column=0, sticky='w', padx = 5, pady = 5)

