from PyInstaller.utils.hooks import collect_data_files

# 包含 Java 运行时文件
datas = collect_data_files('jgo')
datas += collect_data_files('scyjava')
