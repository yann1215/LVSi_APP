
# Camera/Preview 的 live更新
# 这些函数保存绑定在 button 上

def start_live(self):
    # 修改 live_flag 为 True
    self.live_flag = True

    run_live(self)

    return

def stop_live(self):
    # 修改 live_flag 为 False
    self.live_flag = False

    lock = getattr(self, "_img_lock", None)
    if lock is not None:
        with lock:
            img = getattr(self, "img", None)
            self.img_froze = None if img is None else img.copy()
    else:
        img = getattr(self, "img", None)
        self.img_froze = None if img is None else img.copy()
    return

def run_live(self):
    """
    画布上显示 self.img_live，通过 run_live() 更新
    live_flag 不影响 camera 采集 self.img/保存等相关操作，之影响显示
    """
    # import time

    if not self.live_flag:
        return

    # 取当前帧（尽量线程安全）
    frame, bg = snapshot_frame_and_bg(self)
    if self.preview_flag:
        diff = subtract_background(frame, bg)
        setattr(self, "img_preview", diff)
    return


def snapshot_frame_and_bg(self):
    frame = None
    bg = None

    lock = getattr(self, "_img_lock", None)
    # 有锁就锁，锁出故障了就不用锁
    if lock is not None:
        with lock:
            f = getattr(self, "img", None)
            b = getattr(self, "preview_background", None)
            frame = None if f is None else f.copy()
            if b is None or f.shape != b.shape:
                # 更新 self.preview_background
                bg = f.copy()
                self.preview_background = bg
            else:
                bg = b.copy()
    else:
        f = getattr(self, "img", None)
        b = getattr(self, "preview_background", None)
        frame = None if f is None else f.copy()
        if bg is None or frame.shape != bg.shape:
            # 更新 self.preview_background
            bg = f.copy()
            self.preview_background = bg
        else:
            bg = b.copy()

    return frame, bg


def subtract_background(self, frame, bg):
    import numpy as np

    if frame is None or bg is None:
        return frame
    if frame.shape != bg.shape:
        # shape 不一致就不减，避免崩溃
        return frame

    # uint8/uint16 都避免 underflow：先转更大有符号类型
    if frame.dtype == np.uint8:
        out = frame.astype(np.int16) - bg.astype(np.int16)
        out = np.clip(out, 0, 255).astype(np.uint8)
    elif frame.dtype == np.uint16:
        out = frame.astype(np.int32) - bg.astype(np.int32)
        out = np.clip(out, 0, 65535).astype(np.uint16)
    else:
        # 其它 dtype：float 等
        out = frame.astype(np.float32) - bg.astype(np.float32)
    return out
