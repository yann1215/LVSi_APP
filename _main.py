import json
import time

from _para import *
# from utils.gui.gui import gui_init
from utils.gui2.gui2 import App


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)     # debug


if __name__ == "__main__":
    path = "settings"
    version = "LVSi Image Processing System"        # title bar text

    log("Welcome: LVSi Image Processing System.")        # debug

    if not os.path.exists(path):
        os.mkdir(path)

    try:
        default_data = all_para_dict
        # log("before json.dump")     # debug

        tmp = json.dumps(default_data, ensure_ascii=False, indent=4)    # 先转成字符串试水
        with open(os.path.join(path, "DEFAULT.json"), 'w', encoding='utf-8') as f:
            # json.dump(default_data, f, ensure_ascii=False, indent=4)
            f.write(tmp)        # debug
        # log(f"after json.dump ({len(tmp)} bytes)")      # debug

    except Exception as e:
        log(f"JSON init failed: {e}")

    log("GUI online.")
    # gui_init(version)
    App().mainloop()
    log("GUI offline.")

# pyinstaller --add-data="Fiji.app;Fiji.app" --additional-hooks-dir=__hooks__ _main.py -F -w
