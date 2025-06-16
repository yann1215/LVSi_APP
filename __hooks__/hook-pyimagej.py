from PyInstaller.utils.hooks import copy_metadata, collect_data_files

datas = copy_metadata('pyimagej')
datas += collect_data_files('pyimagej', include_py_files=True)
# 包含依赖项
hiddenimports = [
    'scyjava',
    'imglyb',
    'jgo',
    'jnius',
    'numpy',
    'xarray',
    'scyjava.config'
]