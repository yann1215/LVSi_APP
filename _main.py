from GUI import GUI_init
from _para import *
import json
import os

if __name__ == "__main__":
    path = "fijiCountingFaster30-default"
    version = "fijiCountingFaster30.2025.06.13 --LI Minghao"
    if not os.path.exists(path):
        os.mkdir(path)
    default_data = all_para_dict
    with open(os.path.join(path, "DEFAULT.json"), 'w', encoding='utf-8') as f:
        json.dump(default_data, f, ensure_ascii=False, indent=4)
    GUI_init(version)


# pyinstaller --add-data="Fiji.app;Fiji.app" --additional-hooks-dir=__hooks__ _main.py -F -w
