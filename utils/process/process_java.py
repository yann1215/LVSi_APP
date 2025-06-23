import scyjava
from _para import *
import imagej


jre_path = os.path.join(base_path, "Fiji.app\\java\\win64\\zulu8.86.0.25-ca-fx-jdk8.0.452-win_x64\\jre")
os.environ["JAVA_HOME"] = jre_path
scyjava.config.add_option('-Xmx8g')

fiji_path = os.path.join(base_path, "Fiji.app")
ij = imagej.init(fiji_path, 'interactive')

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
