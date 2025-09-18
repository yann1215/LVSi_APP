import os
import threading
import tkinter as tk
from tkinter import ttk
import json


def path_finding_thread(self, filepath_list, mode, all_para_dict):
    thread = threading.Thread(target=find_all_paths, args=(self, filepath_list, mode, all_para_dict), daemon=True)
    thread.start()
    return


# 自嵌套函数，会一直搜寻到文件为止
def find_all_paths(self, filepath_list, mode, all_para_dict):
    if self.EndEvent.is_set():
        return
    path_lists = []
    if not mode == 0:
        for filepath in filepath_list:
            loop_dict = {
                "original_path": str(filepath),
                "mode": mode,
                "all_para_dict": all_para_dict,
            }
            path_list = loop(self, str(filepath), loop_dict, [])
            path_lists = path_lists + path_list
    else:
        path_lists = []
        path_dict = {
            "patient": all_para_dict['patient_keyword'],
            "group": "-" + all_para_dict['output_group'] + "-",
            "time": str(all_para_dict['output_time']) + all_para_dict['time_keyword'],
            "path": filepath_list[0],
            "task": None,
            "output": filepath_list[0],
        }
        task_frame = add_entry(self, path_dict)
        path_dict["task"] = task_frame
        if not self.output_filepath == "auto":
            path_dict["output"] = self.output_filepath
        path_lists.append(path_dict)
    self.searching = False
    self.task_mode = mode
    self.start_btn_var.set("搜索【" + self.nodes[self.program_start] + "】任务文件")
    self.start_btn.config(bg='#4CAF50')
    self.status_var.set("可运行")
    if not self.program_start == mode:
        self.AST_btn_var.set("此为【" + self.nodes[mode] + "】任务文件列表")
        self.AST_btn.config(bg='#cccccc')
    else:
        self.AST_btn_var.set("开始运行")
        self.AST_btn.config(bg='#4CAF50')
        if mode == 0 and self.camera == False:
            self.AST_btn_var.set("无相机")
            self.AST_btn.config(bg='#cccccc')
    self.task_list = path_lists
    return


def loop(self, next_path, loop_dict, path_list):
    if self.EndEvent.is_set():
        return
    filepath = next_path
    original_path = loop_dict["original_path"]
    mode = loop_dict["mode"]
    all_para_dict = loop_dict["all_para_dict"]
    patient_keyword = all_para_dict['patient_keyword']
    time_keyword = all_para_dict['time_keyword']
    try:
        extensions = json.loads(all_para_dict['extensions'])
    except:
        extensions = [".tif", ".tiff"]
        print("WARNING wrong extensions")

    if not os.path.isdir(filepath):
        path_dict = {
            "patient": patient_keyword,
            "group": "-",
            "time": time_keyword,
            "path": filepath,
            "task": None,
            "output": original_path
        }
        filepath_tosave, noneed = os.path.splitext(filepath)
        file_dir = os.path.dirname(filepath_tosave)
        file_name = os.path.basename(filepath_tosave)
        if mode == 1:
            dir_name_list = file_dir.split(os.sep)
            patient_index = 0
            time_index = -1
            for dir_name in dir_name_list:
                if patient_keyword in dir_name:
                    path_dict["patient"] = dir_name
                    path_dict["output"] = file_dir.split(dir_name)[0]
                    break
                patient_index += 1
            if patient_index >= len(dir_name_list) - 1:
                patient_index = 0
            for dir_name in reversed(dir_name_list[patient_index + 1:]):
                if time_keyword in dir_name:
                    path_dict["time"] = dir_name
                    break
                time_index -= 1
            if -time_index > len(dir_name_list[patient_index + 1:]):
                time_index = len(dir_name_list)

            for dir_name in dir_name_list[patient_index + 1:time_index]:
                path_dict["group"] = path_dict["group"] + dir_name + "-"
            if not self.output_filepath == "auto":
                path_dict["output"] = self.output_filepath
            path_dict["path"] = os.path.dirname(filepath)
        else:
            dir_name_list = file_name.split("-")
            if len(dir_name_list) >= 2:
                path_dict["patient"] = dir_name_list[0]
                path_dict["time"] = dir_name_list[-1]
            for dir_name in dir_name_list[1:-1]:
                path_dict["group"] = path_dict["group"] + dir_name + "-"
            path_dict["path"] = filepath
            path_dict["output"] = os.path.dirname(file_dir)
            if not self.output_filepath == "auto":
                path_dict["output"] = self.output_filepath
        task_frame = add_entry(self, path_dict)
        path_dict["task"] = task_frame
        path_list.append(path_dict)
    else:
        next_dir_path_list = next(os.walk(filepath))[1]
        next_file_path_list = next(os.walk(filepath))[2]
        next_file_path_list = [f for f in next_file_path_list
                               if os.path.splitext(f)[1].lower() in extensions]

        for next_dir_path in next_dir_path_list:
            next_dir_path = os.path.join(filepath, next_dir_path)
            path_list = loop(self, next_dir_path, loop_dict, path_list)

        for next_file_path in next_file_path_list:
            next_file_path = os.path.join(filepath, next_file_path)
            path_list = loop(self, next_file_path, loop_dict, path_list)
            if mode == 1:
                break

    return path_list


def add_entry(self, path_dict):
    # 创建带有删除按钮的条目
    entry_frame = ttk.Frame(self.scrollable_frame, padding=0)
    entry_frame.pack(fill="x", padx=5, pady=0)

    path_task_var = tk.StringVar()
    text = path_dict["patient"] + path_dict["group"] + path_dict["time"]
    path_task_var.set(text)
    labelEntry = tk.Entry(entry_frame, textvariable=path_task_var, width=40,
                               font=('宋体', 10), state="disabled")
    labelEntry.pack(pady=(0, 0), padx=0, side="left")

    # delete_btn = ttk.Button(
    #     entry_frame,
    #     text = "X",
    #     width = 2,
    #     command = lambda f=entry_frame, s=self: _delete_entry(s, f)
    # )
    # delete_btn.pack(side="right")

    # 自动滚动到底部
    self.task_canvas.update_idletasks()
    self.task_canvas.yview_moveto(1.0)

    return entry_frame


def _delete_entry(self, frame):
    # 删除指定条目
    frame.destroy()
    # 更新画布滚动区域
    self.task_canvas.configure(scrollregion=self.task_canvas.bbox("all"))
