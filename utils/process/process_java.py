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


def new_file_chooser(self, mode):

    prefs = Preferences.userRoot().node("/LMH/fijiCountingFaster/29/file_chooser")
    key_list = ["cameraPath", "preprocessPath", "trackMatePath", "featuresPath", "outputPath"]

    filepath_list = self.filepath_list
    try:
        UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName())
    except:
        pass

    parent_frame = JFrame()
    parent_frame.setAlwaysOnTop(True)
    file_chooser = JFileChooser()
    last_path = prefs.get(key_list[mode] + "_last", None)
    if last_path:
        file_chooser.setCurrentDirectory(File(last_path))

    if mode <= 1 or mode == 4:
        file_chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY)
    else:
        file_chooser.setFileSelectionMode(JFileChooser.FILES_AND_DIRECTORIES)
    if mode == 0 or mode == 4:
        file_chooser.setMultiSelectionEnabled(False)
    else:
        file_chooser.setMultiSelectionEnabled(True)
    result = file_chooser.showOpenDialog(parent_frame)
    if result == JFileChooser.APPROVE_OPTION:
        filepath_list = []
        current_dir = file_chooser.getCurrentDirectory().getAbsolutePath()
        prefs.put(key_list[mode] + "_last", str(current_dir))
        if mode == 0:
            selected_file = file_chooser.getSelectedFile()
            filepath_list.append(str(selected_file))
            self.path_var.set(str(filepath_list))
        elif not mode == 4:
            selected_files = file_chooser.getSelectedFiles()
            for selected_file in selected_files:
                filepath_list.append(str(selected_file))
            self.path_var.set(str(filepath_list))
        else:
            selected_file = file_chooser.getSelectedFile()
            filepath_list = selected_file
            self.output_path_var.set(str(filepath_list))
        prefs.put(key_list[mode], str(filepath_list))
    return filepath_list


def standard_script_runer(script, args):
    language = "python"
    script_output = ij.py.run_script(language, script, args)
    for window in Window.getWindows():
        if window.getTitle() == "script:script.py":
            window.dispose()

    return script_output
