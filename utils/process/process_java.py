from _para import *
from pathlib import Path
import os
# import shutil

# ====== remove system java ======
def strip_from_path(substrings: list[str]):
    parts = [x for x in os.environ.get("PATH","").split(os.pathsep) if x]
    lowered = [x.lower() for x in parts]
    keep = [p for p,lp in zip(parts, lowered) if not any(s.lower() in lp for s in substrings)]
    os.environ["PATH"] = os.pathsep.join(keep)

strip_from_path([r"common files\oracle\java\java8path", r"program files (x86)\common files\oracle\java"])

# ====== load project maven&java ======
# maven path
maven_home = os.path.join(base_path, "tools", "maven", "apache-maven-3.9.11")
os.environ["MAVEN_HOME"] = maven_home
# print("[ImageJ] MAVEN_HOME =>", maven_home)

# maven bin
maven_bin = os.path.join(maven_home, "bin")
os.environ["PATH"] = maven_bin + ";" + os.environ.get("PATH","")

# java path
java_home = os.path.join(base_path, "Fiji.app", "java", "win64", "zulu8.86.0.25-ca-fx-jdk8.0.452-win_x64", "jre")
os.environ["JAVA_HOME"] = java_home
# print("[ImageJ] JAVA_HOME =>", java_home)
# java bin
java_bin = os.path.join(java_home, "bin")
os.environ["PATH"] = java_bin + ";" + os.environ["PATH"]
# print("[ImageJ] bin =>", os.environ["PATH"])

# fiji path
fiji_path = os.path.join(base_path, "Fiji.app")
# print("[ImageJ] Fiji dir  =>", fiji_path)

# place project maven&java first
def ensure_on_path(p: Path, prepend=True):
    cur = os.environ.get("PATH","")
    parts = [x for x in cur.split(os.pathsep) if x]
    sp = str(p.resolve())
    if sp not in parts:
        os.environ["PATH"] = (sp + os.pathsep + cur) if prepend else (cur + os.pathsep + sp)

ensure_on_path(Path(java_bin), prepend=True)
ensure_on_path(Path(maven_bin), prepend=True)
# print("mvn  =", shutil.which("mvn") or shutil.which("mvn.cmd"))
# print("java =", shutil.which("java"))

# ====== load scyjava&imagej ======
import scyjava
import imagej

scyjava.config.add_option('-Xmx8g')     # 调整内存
ij = imagej.init(fiji_path, mode="interactive")

scyjava.jimport("java.lang.System").setProperty("python.console.redirect", "true")
scyjava.jimport("java.lang.System").setProperty("python.redirect", "true")
JFileChooser = scyjava.jimport("javax.swing.JFileChooser")
UIManager = scyjava.jimport("javax.swing.UIManager")
Preferences = scyjava.jimport("java.util.prefs.Preferences")
File = scyjava.jimport("java.io.File")
JFrame = scyjava.jimport("javax.swing.JFrame")
Window = scyjava.jimport("java.awt.Window")


def file_chooser(self, mode):

    prefs = Preferences.userRoot().node("/LMH/fijiCountingFaster/29/file_chooser")
    key_list = ["cameraPath",
                "preprocessPath",
                "trackMatePath",
                "featuresPath",
                "outputPath",
                "browsePath"]

    filepath_list = self.filepath_list
    try:
        UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName())
    except:
        pass

    parent_frame = JFrame()
    parent_frame.setAlwaysOnTop(True)
    chooser = JFileChooser()
    last_path = prefs.get(key_list[mode] + "_last", None)
    if last_path:
        chooser.setCurrentDirectory(File(last_path))

    # ==================== 设置文件加载格式 ====================
    #                       No.     file-select     multi-select
    # "cameraPath"           0          0               0
    # "preprocessPath"       1          0               1
    # "trackMatePath"        2          1               1
    # "featuresPath"         3          1               1
    # "outputPath"           4          0               0
    # "browsePath"           5          1               0

    # file-select settings
    if mode in (0, 1, 4):
        chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY)
        # file_select_flag = False
    else:
        chooser.setFileSelectionMode(JFileChooser.FILES_AND_DIRECTORIES)
        # file_select_flag = True
    # multi-select settings
    if mode in (0, 4, 5):
        chooser.setMultiSelectionEnabled(False)
        multi_select_flag = False
    else:
        chooser.setMultiSelectionEnabled(True)
        multi_select_flag = True

    if mode == 4:
        target_var = self.output_path_var
    elif mode == 5:
        terget_var = self.current_path_var
    else:
        target_var = self.path_var

    result = chooser.showOpenDialog(parent_frame)
    if result == JFileChooser.APPROVE_OPTION:
        filepath_list = []
        current_dir = chooser.getCurrentDirectory().getAbsolutePath()
        prefs.put(key_list[mode] + "_last", str(current_dir))
        if not multi_select_flag:
            selected_file = chooser.getSelectedFile()
            if mode == 0:
                filepath_list.append(str(selected_file))
            elif mode ==4:
                filepath_list = selected_file
        else:
            selected_files = chooser.getSelectedFiles()
            for selected_file in selected_files:
                filepath_list.append(str(selected_file))

        if target_var is not None:
            target_var.set(str(filepath_list))

        # 保存到 prefs，供下次恢复
        prefs.put(key_list[mode], str(filepath_list))

    return filepath_list


def standard_script_runner(script, args):
    language = "python"
    script_output = ij.py.run_script(language, script, args)
    for window in Window.getWindows():
        if window.getTitle() == "script:script.py":
            window.dispose()

    return script_output
