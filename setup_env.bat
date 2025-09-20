@echo on
setlocal EnableExtensions
cd /d "%~dp0"

set "VENV=.venv"
set "VENV_PY=%VENV%\Scripts\python.exe"

REM 0) 检查 py 启动器
where py >NUL 2>NUL
if errorlevel 1 (
  echo [ERROR] Python Launcher 'py' not found.
  echo 请先安装 Windows Python Launcher（或从 python.org 安装 Python 并勾选 "Install launcher for all users"）。
  goto :fail
)

REM 1) 检查是否已有 Python 3.11
py -3.11 -V >NUL 2>&1
if errorlevel 1 (
  echo [INFO] 未检测到 Python 3.11，开始安装：py install 3.11
  py install 3.11
  if errorlevel 1 (
    echo [ERROR] 安装 Python 3.11 失败（py install 3.11 返回 %errorlevel%）。
    echo 请确认网络可用，或手动从 python.org 安装 3.11（x86-64），再重试。
    goto :fail
  )
  echo [INFO] 验证安装结果...
  py -3.11 -V || goto :fail
)

REM 2) venv：如已存在，询问复用/重建
if exist "%VENV_PY%" (
  echo Detected existing venv: "%VENV_PY%"
  choice /M "Reuse the existing venv? (Y to reuse, N to recreate)"
  if errorlevel 2 (
    echo Recreating venv...
    rd /s /q "%VENV%"
  )
)

REM 3) 用 3.11 创建 venv
py -3.11 -m venv "%VENV%" || goto :fail

REM 4) 激活 venv
call "%VENV%\Scripts\activate.bat" || goto :fail

REM 5) 升级基础工具并安装依赖
python -m pip install pip wheel setuptools || goto :fail
if exist "requirements.txt" (
  echo Installing from requirements.txt...
  pip install -r requirements.txt || goto :fail
) else (
  echo [INFO] requirements.txt 未找到，跳过依赖安装。
)

echo.
python -c "import sys;print('Python:',sys.version);print('Exe:',sys.executable)"
echo Environment ready.
goto :end

:fail
echo.
echo Failed (error %errorlevel%).
echo 如遇网络/权限问题：可在管理员 CMD 中重试，或手动安装 Python 3.11。
goto :end

:end
echo.
echo Press any key to exit...
pause >nul
endlocal
