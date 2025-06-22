import threading
from utils.process.Util_dirSeeker import _delete_entry
from AST_runner import AST_preprocess, AST_TrackMate, AST_features, AST_impListener
import time
import os

def camera_mode_manager(self, program_list, task_list, para_dict):
    self.progress['value'] = 0
    if program_list[0] == 0:
        self.status_var.set("拍摄中")
        path_dict = task_list[0]
        output_path = (path_dict["output"] + "\\" +
                       para_dict["patient_keyword"] + "\\" +
                       para_dict["output_group"] + "\\" +
                       str(para_dict["output_time"]) + para_dict["time_keyword"])
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        self.save_path = output_path
        self.save_step = 0
        self.save_frame = True
        time.sleep(para_dict["video_duration"])
        self.save_frame = False
        time.sleep(0.5)
        self.save_step = 0
        self.progress['value'] = 20
        self.status_var.set("拍摄完成")
    thread = threading.Thread(target=ast_looper, args=(self, program_list, task_list, para_dict), daemon=True)
    thread.start()

    return


def ast_looper(self, program_list, task_list, para_dict):
    """
    (Function)

    Args:
        program_list:
        task_list:
        para_dict:

    """

    if not program_list[1] == 0:
        for task in task_list:
            path_dict = task
            AST_impListener(self, True)
            if program_list[0] == 0:
                path_dict["path"] = self.save_path
                AST_preprocess(self, path_dict, para_dict, program_list[1])
            elif program_list[0] == 1:
                AST_preprocess(self, path_dict, para_dict, program_list[1])
            elif program_list[0] == 2:
                AST_TrackMate(self, path_dict, para_dict, program_list[1])
            elif program_list[0] == 3:
                AST_features(self, path_dict, para_dict)
            AST_impListener(self, False)
            frame = task["task"]
            _delete_entry(self, frame)
            self.task_canvas.yview_moveto(0.0)
        print("done")

    self.running = False
    self.start_btn_var.set("搜索【" + self.nodes[self.program_start] + "】任务文件")
    self.start_btn.config(bg='#4CAF50')
    self.status_var.set("可运行")
    self.task_mode = None
    self.AST_btn_var.set("任务文件列表已空")
    self.AST_btn.config(bg='#cccccc')

    return
