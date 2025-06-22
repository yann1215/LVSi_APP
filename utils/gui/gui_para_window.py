import os
import tkinter as tk
from tkinter import ttk
from gui_para_settings import all_para_settings
from _para import *
import json


def create_modal_window(self, params):
    self.detail_button_state = False
    self.modal = tk.Toplevel(self.root)
    modal = self.modal
    modal.title("参数设置")
    modal.geometry("500x400")
    modal.resizable(False, False)
    modal.configure(bg="#eaeaea")
    modal.grab_set()  # 设置为模态窗口

    left_frame = tk.Frame(modal, bg="#eaeaea", width=240)
    left_frame.pack(side="left", fill="y", padx=(0, 5), pady=0)
    right_frame = tk.Frame(modal, bg="#eaeaea", width=240)
    right_frame.pack(side="right",fill="y", padx=(0, 5), pady=0)

    create_left_frame(self, left_frame, params)
    create_right_frame(self, right_frame)


def create_left_frame(self, left_frame, params):
    # ===== 顶部标题栏 =====
    header = tk.Frame(left_frame, bg="#0278f8", height=20)
    header.pack(fill="x", padx=0, pady=0)
    tk.Label(header,
             text="高级参数设置",
             bg="#0278f8",
             fg="white",
             font=("宋体", 12, "bold")).pack(pady=5)

    # ===== 中间可滚动区域 =====
    main_frame = tk.Frame(left_frame, bg="#eaeaea")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # 创建画布和滚动条
    self.modal_canvas = tk.Canvas(main_frame, bg="#eaeaea", highlightthickness=0, height=50, width=210)
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.modal_canvas.yview)
    self.modal_scrollable_frame = tk.Frame(self.modal_canvas, bg="#eaeaea")

    # 配置画布
    self.modal_scrollable_frame.bind(
        "<Configure>",
        lambda e: self.modal_canvas.configure(scrollregion=self.modal_canvas.bbox("all")))
    self.modal_canvas.create_window((0, 0), window=self.modal_scrollable_frame, anchor="nw")
    self.modal_canvas.configure(yscrollcommand=scrollbar.set)

    # 布局
    self.modal_canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    create_param_controls(self, self.modal_scrollable_frame, params, all_para_settings[params], self.detail_button_state)

    # ===== 底部按钮区域 =====
    footer = tk.Frame(left_frame, bg="#eaeaea", height=40)
    footer.pack(fill="x", padx=10, pady=10, side="bottom")

    # 左：确认按钮
    tk.Button(footer,
              text="确认",
              width=5,
              bg="#4CAF50",
              fg="white",
              command=lambda s=self:confrim(s)).pack(side="left", padx=(0,5))

    # 右：详细/简略按钮
    self.detail_button = tk.Button(footer,
                              text="详细",
                              width=5,
                              command=lambda s=self, p=params: toggle_detail(s, p))
    self.detail_button.pack(side="right", padx=5)


def create_right_frame(self, right_frame):
    # ===== 顶部标题栏 =====
    header = tk.Frame(right_frame, bg="#0278f8", height=20)
    header.pack(fill="x", padx=0, pady=0)
    tk.Label(header,
             text="默认参数喜好",
             bg="#0278f8",
             fg="white",
             font=("宋体", 12, "bold")).pack(pady=5)

    # ===== 中间可滚动区域 =====
    main_frame = tk.Frame(right_frame, bg="#eaeaea")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # 创建画布和滚动条
    self.default_modal_canvas = tk.Canvas(main_frame, bg="#cccccc", highlightthickness=0, height=50, width=210)
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.default_modal_canvas.yview)
    self.default_modal_scrollable_frame = tk.Frame(self.default_modal_canvas, bg="#cccccc")

    # 配置画布
    self.default_modal_scrollable_frame.bind(
        "<Configure>",
        lambda e: self.default_modal_canvas.configure(scrollregion=self.default_modal_canvas.bbox("all")))
    self.default_modal_canvas.create_window((0, 0), window=self.default_modal_scrollable_frame, anchor="nw")
    self.default_modal_canvas.configure(yscrollcommand=scrollbar.set)

    # 布局
    self.default_modal_canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # ===== 底部按钮区域 =====
    footer = tk.Frame(right_frame, bg="#eaeaea", height=40)
    footer.pack(fill="x", padx=10, pady=10, side="bottom")

    # 左：确认按钮
    tk.Button(footer,
              text="保存",
              width=5,
              command=lambda s=self : save(s)).pack(side="left", padx=(0,5))

    self.default_setting_name_var = tk.StringVar()
    tk.Entry(footer,
             width=15,
             textvariable = self.default_setting_name_var).pack(side="left",fill="x", expand=True)

    # 中：默认按钮
    tk.Button(footer,
              text="应用",
              width=5,
              command=lambda s=self : load(s)).pack(side="right", padx=5)

    create_default_settings(self)


def create_param_controls(self, parent, title, params, mode):
    self.object_dict_list = []
    for widget in parent.winfo_children():
        if widget != parent:
            widget.destroy()
    if mode:
        para_show_mode = "detail"
    else:
        para_show_mode = "brief"
    para_show_list = params[para_show_mode]

    self.entry_list = []
    for para_show in para_show_list:
        frame = tk.Frame(parent, bg="#eaeaea")
        frame.pack(fill="x", pady=5)
        type = para_show["type"]
        name = para_show["name"]
        str = para_show["str"]

        if type == "label":
            show_label = ""
            font_size = 8
            font_weight = ""
            if str == "":
                show_label = name
                font_size = 8
                font_weight = "normal"
            elif name == "":
                show_label = str
                font_size = 15
                font_weight = "bold"
            lbl = tk.Label(frame, text=show_label + ":", bg="#eaeaea", width=40, anchor="w", font=("宋体", font_size, font_weight))
            lbl.pack(fill="x", padx=(0, 0), expand=True)

        else:
            # 左侧标签
            lbl = tk.Label(frame, text=str + ":", bg="#eaeaea", width=15, anchor="w", font=("宋体", 10, "bold"))
            lbl.pack(side="left", padx=(0, 5))

            # 右侧输入框
            object = create_value(self, frame, type, name)

            self.object_dict_list.append({
                "name": name,
                "type": type,
                "object": object
            })
    self.modal_canvas.update_idletasks()
    self.modal_canvas.yview_moveto(0.0)


def create_default_settings(self):
    default_path = "../../settings"
    if not os.path.exists(default_path):
        os.makedirs(default_path)
    default_json_list = os.listdir(default_path)
    for default_json in default_json_list:
        # 创建带有删除按钮的条目
        Label_frame = tk.Frame(self.default_modal_scrollable_frame, bg="#eaeaea")
        Label_frame.pack(fill="x", padx=0, pady=0)
        default = json.load(open(os.path.join(default_path, default_json)))
        default_name = default["default_ID"]
        labelLabel = tk.Label(Label_frame, text=default_name, width=30,
                              font=('宋体', 15), state="disabled", anchor="w")
        labelLabel.pack(pady=(0, 5), padx=0, side="left")
        labelLabel.bind("<Button-1>", lambda e, s=self, t=default_name: get_default_name(e, s, t))

    # 自动滚动到底部
    self.default_modal_canvas.update_idletasks()
    self.default_modal_canvas.yview_moveto(0.0)


def toggle_detail(self, params):
    if not self.detail_button_state:
        self.detail_button_state = True
        create_param_controls(self, self.modal_scrollable_frame, params, all_para_settings[params], self.detail_button_state)
        self.detail_button.config(text="简略")
    else:
        self.detail_button_state = False
        create_param_controls(self, self.modal_scrollable_frame, params, all_para_settings[params], self.detail_button_state)
        self.detail_button.config(text="详细")


def create_value(self, frame, value_type, name):
    object = None
    if value_type == "int":
        object = tk.IntVar()
        object.set(self.all_para_dict[name])
        validate_cmd = frame.register(validate_numeric_input)
        intInput = tk.Entry(frame, width=10, validate="key", validatecommand=(validate_cmd, '%P'), textvariable = object)
        intInput.bind("<FocusOut>", lambda e, s=intInput :on_focus_out(e, s))
        intInput.pack(side="left", fill="x", padx=(0, 5))
    elif value_type == "float":
        object = tk.DoubleVar()
        object.set(self.all_para_dict[name])
        validate_cmd = frame.register(validate_numeric_input)
        doubleInput = tk.Entry(frame, width=10, validate="key", validatecommand=(validate_cmd, '%P'), textvariable = object)
        doubleInput.bind("<FocusOut>", lambda e, s=doubleInput :on_focus_out(e, s))
        doubleInput.insert(0, self.all_para_dict[name])
        doubleInput.pack(side="left", fill="x", padx=(0, 5))
    elif value_type == "bool":
        object = tk.BooleanVar()
        object.set(self.all_para_dict[name])
        booleanInput = tk.Checkbutton(frame, bg="#eaeaea", onvalue = True, offvalue = False, width = 5, variable = object)
        booleanInput.pack(side="left", fill="x", padx=(0, 5))
    elif value_type == "str":
        object = tk.StringVar()
        object.set(self.all_para_dict[name])
        stringInput = tk.Entry(frame, width=10, textvariable = object)
        stringInput.pack(side="left", fill="x", padx=(0, 5))
    elif type(value_type) == dict:
        object = tk.IntVar()
        object.set(self.all_para_dict[name])
        radioBar = tk.Frame(frame, bg="#eaeaea", width = 5)
        radioBar.pack(side="left", fill="x", padx=(0, 5))
        row_num = 0
        for key, value in value_type.items():
            radio = tk.Radiobutton(radioBar, bg="#eaeaea", text=key, value=value, variable=object)
            radio.grid(row=row_num, column=0, sticky='W')
            row_num += 1
    return object


def validate_numeric_input(new_value):
    """
    验证输入是否为数字或空字符串
    """

    # 允许空字符串（删除操作）和数字
    if new_value == "":
        return True
    try:
        # 尝试将输入转换为浮点数（支持小数）
        float(new_value)
        return True
    except ValueError:
        # 如果转换失败，拒绝输入
        return False


def on_focus_out(event, self):
    if self.get().strip() == "":
        self.delete(0, tk.END)
        self.insert(0, "0")


def confrim(self):
    for object_dict in self.object_dict_list:
        object = object_dict["object"]
        name = object_dict["name"]
        self.all_para_dict[name] = object.get()
    self.camera_settings = True
    self.modal.destroy()


def save(self):
    for widget in self.default_modal_scrollable_frame.winfo_children():
        if widget != self.default_modal_scrollable_frame:
            widget.destroy()
    path = "../../settings"
    for object_dict in self.object_dict_list:
        object = object_dict["object"]
        name = object_dict["name"]
        self.all_para_dict[name] = object.get()
    default_data = self.all_para_dict
    default_data["default_ID"] = self.default_setting_name_var.get()
    default_save_path = os.path.join(path, default_data["default_ID"] + ".json")
    try:
        with open(default_save_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        create_default_settings(self)
    except:
        print("error")


def load(self):
    path = "../../settings"
    default_ID = self.default_setting_name_var.get()
    try:
        with open(os.path.join(path, default_ID + ".json"), 'r', encoding='utf-8') as f:
            default_data = json.load(f)
        self.all_para_dict = default_data
        for object_dict in self.object_dict_list:
            object = object_dict["object"]
            name = object_dict["name"]
            object.set(self.all_para_dict[name])
    except:
        print("error")


def get_default_name(event, self, params):
    self.default_setting_name_var.set(params)