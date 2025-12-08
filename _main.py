import json
import os
import sys, time        # debug

from _para import *
# from utils.gui.gui import gui_init  # 1st version gui
from utils.gui2.gui2 import App     # 2nd version gui - editing


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)     # debug


if __name__ == "__main__":
    path = "settings"
    version = "LVSi Image Processing System (ver 25.09.17)"        # title bar text

    log("start")        # debug

    if not os.path.exists(path):
        os.mkdir(path)

    try:
        default_data = all_para_dict
        log("before json.dump")     # debug

        tmp = json.dumps(default_data, ensure_ascii=False, indent=4)    # 先转成字符串试水
        with open(os.path.join(path, "DEFAULT.json"), 'w', encoding='utf-8') as f:
            # json.dump(default_data, f, ensure_ascii=False, indent=4)
            f.write(tmp)        # debug
        log(f"after json.dump ({len(tmp)} bytes)")      # debug

    except Exception as e:
        log(f"json step failed: {e}")

    log("before gui_init")
    # gui_init(version)
    App().mainloop()
    log("after gui_init")

# pyinstaller --add-data="Fiji.app;Fiji.app" --additional-hooks-dir=__hooks__ _main.py -F -w
