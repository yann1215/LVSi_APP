import serial
import tkinter as tk
import time

# 连接串口 (请确保是 COM7)
# USB_PORT = "COM3"         # sy 笔记本
USB_PORT = "COM7"         # AST 电脑
ser = None

def motor_connect(port=USB_PORT, baud=9600, timeout=1):
    global ser
    if ser is not None and ser.is_open:
        return True
    try:
        ser = serial.Serial(port, baud, timeout=timeout)
        time.sleep(2)  # 仅在首次连接时等待
        print("Motor connected.")
        return True
    except Exception as e:
        ser = None
        print(f"Motor connection failed: {e}")
        return False


# 定义功能
def move_forward():
    if not motor_connect():
        return False

    ser.write(b'G')
    # print("指令：正转 12 度")

    return True

def move_backward():
    if not motor_connect():
        return False

    ser.write(b'B')
    # print("指令：反转 12 度")

    return True

def motor_reset():
    if not motor_connect():
        return False

    ser.write(b'R')
    # print("指令：电机复位归零")

    return True


if __name__ == "__main__":
    # 3. 创建界面
    root = tk.Tk()
    root.title("步进电机三键控制版")
    root.geometry("300x250")

    # 正转按钮
    btn_fwd = tk.Button(root, text="正转", command=move_forward,
                       width=20, height=2, bg="#4CAF50", fg="white") # 绿色
    btn_fwd.pack(pady=10)

    # 反转按钮
    btn_bwd = tk.Button(root, text="反转", command=move_backward,
                       width=20, height=2, bg="#2196F3", fg="white") # 蓝色
    btn_bwd.pack(pady=10)

    # 复位按钮
    btn_reset = tk.Button(root, text="一键复位归零", command=motor_reset,
                          width=20, height=2, bg="#f44336", fg="white") # 红色
    btn_reset.pack(pady=10)

    root.mainloop()