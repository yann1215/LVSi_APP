
import numpy as np

# Camera/Preview 的 live更新
# 这些函数保存绑定在 button 上

def start_live(app):
    # 修改 live_flag 为 True
    lf = bool(getattr(app, "live_flag", False))
    if not lf:
        app.live_flag = True
        if hasattr(app, "_update_live_buttons_state"):
            app._update_live_buttons_state()
    update_preview(app)   # 其实只影响 preview 画面的刷新
    return

def stop_live(app):
    # 修改 live_flag 为 False
    lf = bool(getattr(app, "live_flag", False))
    if lf:
        app.live_flag = False
        if hasattr(app, "_update_live_buttons_state"):
            app._update_live_buttons_state()
    return


def update_preview(app):
    """
    更新 img_preview 画面
    live_flag 不影响 camera 采集 app.img/保存等相关操作，之影响显示
    """
    # import time

    # note: debug
    # app._dbg_run_live = getattr(app, "_dbg_run_live", 0) + 1
    # print("run_live calls =", app._dbg_run_live)

    lf = bool(getattr(app, "live_flag", False))
    pf = bool(getattr(app, "preview_flag").get())

    # 如果在 live，就更新 preview_background 内容
    # 取当前帧（尽量线程安全）
    if lf and pf:
        frame, bg = snapshot_frame_and_bg(app)
        diff = subtract_background(frame, bg)
        diff_disp = auto_contrast(diff, saturated=0.35)

        setattr(app, "img_preview", diff_disp)

        # note: debug
        if diff is not None:
            print(f"Preview raw: shape={diff.shape}, dtype={diff.dtype}, min={diff.min()}, max={diff.max()}, mean={diff.mean():.2f}")
        if diff_disp is not None:
            print(f"Preview disp: shape={diff_disp.shape}, dtype={diff_disp.dtype}, min={diff_disp.min()}, max={diff_disp.max()}, mean={diff_disp.mean():.2f}")

    return


def snapshot_frame_and_bg(app):
    # frame = None
    # bg = None

    def align_shape(x):
        try:
            if x is not None and getattr(x, "ndim", 0) == 3 and x.shape[2] == 1:
                return x[:, :, 0]
        except Exception:
            pass
        return x

    lock = getattr(app, "_img_lock", None)
    # 有锁就锁，锁出故障了就不用锁
    if lock is not None:
        with lock:
            f = getattr(app, "img", None)
            b = getattr(app, "preview_background", None)

            if f is None:
                return None, None

            # 控制 frame 和 preview_background 始终为 2D
            f2 = align_shape(f)
            b2 = align_shape(b) if b is not None else None

            frame = f2.copy()

            if b2 is None or b2.shape != f2.shape:
                # 更新 app.preview_background
                bg = frame.copy()
                setattr(app, "preview_background", bg)

                print("shapes:", getattr(f, "shape", None),
                      getattr(b, "shape", None) if b is not None else None,
                      getattr(frame, "shape", None))

                print("Preview background not found. Auto set.")
            else:
                bg = b2.copy()
    else:
        f = getattr(app, "img", None)
        b = getattr(app, "preview_background", None)

        if f is None:
            return None, None

        # 控制 frame 和 preview_background 始终为 2D
        f2 = align_shape(f)
        b2 = align_shape(b) if b is not None else None

        frame = f2.copy()

        if b2 is None or b2.shape != f2.shape:
            # 更新 app.preview_background
            bg = frame.copy()
            setattr(app, "preview_background", bg)

            print("shapes:", getattr(f, "shape", None),
                  getattr(b, "shape", None) if b is not None else None,
                  getattr(frame, "shape", None))

            print("Preview background not found. Auto set.")
        else:
            bg = b2.copy()

    return frame, bg


def subtract_background(frame, bg):
    import numpy as np

    if frame is None or bg is None:
        return frame
    if frame.shape != bg.shape:
        # shape 不一致就不减，避免崩溃
        return None

    print("frame(min,max)=", frame.min(), frame.max(),
          "bg(min,max)=", bg.min(), bg.max(),
          "any(frame>bg)=", bool(np.any(frame > bg)),
          "any(frame<bg)=", bool(np.any(frame < bg)))

    # uint8/uint16 都避免 underflow：先转更大有符号类型
    # 关键：返回“有符号差分”，不要裁剪到 0
    # 这样后续显示端可以做 min-max / percentile 拉伸（类似 Fiji auto contrast）
    if frame.dtype == np.uint8:
        out = frame.astype(np.int16) - bg.astype(np.int16)  # int16，可正可负
    elif frame.dtype == np.uint16:
        out = frame.astype(np.int32) - bg.astype(np.int32)  # int32，可正可负
    else:
        out = frame.astype(np.float32) - bg.astype(np.float32)

    return out


def auto_contrast(arr, saturated: float = 0.35, sample_max: int = 200_000):
    """
    仿 Fiji 的 Auto Contrast/Enhance Contrast（饱和像素百分比 saturated）。
    输出 uint8（用于显示），只建议用于 preview，不建议用于定量计算。
    - saturated=0.35 表示两端各裁剪 0.35%（近似 Fiji 常用默认值）
    - sample_max: 大图时抽样估计阈值，减少每帧开销
    """

    if arr is None:
        return None

    a = np.asarray(arr)
    if a.size == 0:
        return None

    # 只处理灰度：如果是彩色就取第一通道（你的相机/preview一般是灰度）
    if a.ndim == 3 and a.shape[2] >= 1:
        a = a[..., 0]

    flat = a.reshape(-1)

    # 抽样（提升速度）
    if flat.size > sample_max:
        step = max(1, flat.size // sample_max)
        sample = flat[::step]
    else:
        sample = flat

    # 去掉 NaN/Inf
    if np.issubdtype(sample.dtype, np.floating):
        sample = sample[np.isfinite(sample)]
        if sample.size == 0:
            return np.zeros(a.shape, dtype=np.uint8)

    sat = float(saturated)
    sat = max(0.0, min(49.0, sat))  # 防止极端值
    lo_q = sat
    hi_q = 100.0 - sat

    # 稀疏亮点场景：如果非零像素占比很低，用“非零分布”估计上限更符合直觉
    # （否则 99.65% 分位可能仍是 0，导致全黑）
    if np.issubdtype(sample.dtype, np.integer):
        nz = sample[sample > 0]
        if nz.size >= 1024 and nz.size < sample.size * 0.01:
            lo = 0.0
            hi = float(np.percentile(nz, hi_q))
        else:
            lo = float(np.percentile(sample, lo_q))
            hi = float(np.percentile(sample, hi_q))
    else:
        lo = float(np.percentile(sample, lo_q))
        hi = float(np.percentile(sample, hi_q))

    if not np.isfinite(hi) or hi <= lo:
        return np.zeros(a.shape, dtype=np.uint8)

    x = a.astype(np.float32)
    x = (x - lo) * (255.0 / (hi - lo))
    return np.clip(x, 0, 255).astype(np.uint8)
