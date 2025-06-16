import tkinter as tk

def create_north_frame(self):
    """创建北部的空白区域"""
    north_frame = tk.Frame(self.root, bg='#0278f8', height=30)
    north_frame.grid(row=0, column=1, sticky='ew')

    # 添加标题
    self.Alltitle_var = tk.StringVar()
    self.Alltitle_var.set("大视场散射成像图像处理系统")
    Alltitle = tk.Label(north_frame, textvariable=self.Alltitle_var, bg='#0278f8',
                     font=('宋体', 16, 'bold'), fg='#ffffff')
    Alltitle.pack(pady=5)