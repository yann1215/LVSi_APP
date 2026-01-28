# utils/camera/camera_record.py
from __future__ import annotations

import os
import threading
import time
from typing import Any, Optional
import numpy as np
import tifffile

# 电机底层：可选依赖（无电机也能跑）
try:
    from utils.motor.motor import move_forward as _motor_next_group_impl
    from utils.motor.motor import motor_reset as _motor_reset_impl
except Exception:
    _motor_next_group_impl = None
    _motor_reset_impl = None

MOTOR_WAIT_S = 4.0
CAMERA_WAIT_S = 5.0       # 相机线程参数更新等待时间
_BITDEPTH_INT_TO_BITS = {1: 8, 2: 10, 3: 12}   # 0=Adaptive
_BITDEPTH_INT_TO_NAME = {0: "Adaptive", 1: "Bpp8", 2: "Bpp10", 3: "Bpp12"}


def start_record(app):
    # 1) 防重入
    if getattr(app, "recording_flag", False):
        print("已有进行中的录制，请勿重复开始录制。")
        return

    # 2) 同步 configs -> all_para_dict（录制前快照）
    if hasattr(app, "_sync_dict_from_vars"):
        app._sync_dict_from_vars()

    # 3) 录制前校验（你之前要求的 interval/period、fps/exposure 校验）
    try:
        check_value_validation(app)
    except:
        _abort_recording(app, "Value ERROR: 变量设置异常。")
        return

    # 4) 上锁（但要确保 Stop Record 仍可点击：不要把 Stop 按钮加入锁列表）
    if hasattr(app, "_lock_ui_for_recording"):
        app._lock_ui_for_recording()
    app.recording_flag = True
    if hasattr(app, "_update_record_buttons_state"):
        app._update_record_buttons_state()
    if hasattr(app, "_sync_vars_from_dict"):
        app._sync_vars_from_dict()

    # 5) 触发相机参数下发，并等待完成
    app._cam_settings_applied_ts = getattr(app, "_cam_settings_applied_ts", 0.0)
    app.camera_settings = True

    # 6) 等待相机线程把 camera_settings 清掉并更新 applied_ts
    _wait_camera_settings_then_start(app, t_start=time.monotonic(), timeout_s=CAMERA_WAIT_S)


def stop_record(app):
    # 停止当前帧保存/计划
    app.save_frame = False
    app.save_until_ts = None

    if hasattr(app, "_record_groups_running"):
        app._record_groups_running = False

    # 解锁
    app.recording_flag = False
    if hasattr(app, "_update_record_buttons_state"):
        app._update_record_buttons_state()
    if hasattr(app, "_unlock_ui_after_recording"):
        app._unlock_ui_after_recording()


def check_value_validation(app):
    root = _ensure_camera_path(app)
    d = getattr(app, "all_para_dict", {}) or {}

    # --- 参数读取 ---
    sample_num = d.get("sample_num", None)
    video_interval = d.get("video_interval", None)  # minutes
    video_end_time = d.get("video_end_time", None)  # minutes
    vp = d.get("video_period", None)  # seconds

    fps = d.get("vimbaX_AcquisitionFrameRate", None)  # Hz
    exp = d.get("vimbaX_ExposureTime", None)  # 通常是 us（Vimba 常见单位）

    # --- 基本合法性 ---
    if sample_num is None or video_interval is None or video_end_time is None or vp is None:
        raise ValueError(
            "Config ERROR: record_groups 参数缺失，需要 sample_num, video_interval, video_end_time, video_period。")

    if sample_num < 1:
        raise ValueError("Config ERROR: sample_num 必须 >= 1。")
    if video_interval <= 0:
        raise ValueError("Config ERROR: video_interval 必须为正数（min）。")
    if video_end_time < 0:
        raise ValueError("Config ERROR: video_end_time 必须 >= 0（min）。")
    if vp <= 0:
        raise ValueError("Config ERROR: video_period 必须为正数（sec）。")

    # --- 校验 1：video_interval 是否能容纳 sample_num * video_period ---
    need_s = sample_num * (vp + MOTOR_WAIT_S)
    slot_s = video_interval * 60.0
    if need_s > slot_s:
        raise ValueError("Config ERROR: 样本数量过多，或每组拍摄时间过长，或两组间隔过小。")

    # --- 校验 2：fps 是否能满足曝光时间 ---
    # 这里按 Vimba 常见单位：ExposureTime 为 microseconds
    if fps is None or exp is None:
        raise ValueError("Config ERROR: 缺少相机参数，需要 vimbaX_AcquisitionFrameRate 与 vimbaX_ExposureTime 用于校验。")
    fps = float(fps)
    exp_us = float(exp)
    if fps <= 0:
        raise ValueError("Config ERROR: vimbaX_AcquisitionFrameRate 必须为正数（Hz）。")

    frame_period_s = 1.0 / fps
    exp_s = exp_us / 1e6
    if exp_s > frame_period_s:
        raise ValueError("Config ERROR: 帧率过高，或曝光时间过长。")


def _wait_camera_settings_then_start(app, t_start: float, timeout_s: float):
    # 超时保护：相机线程未响应时解锁并报错
    if time.monotonic() - t_start > timeout_s:
        _abort_recording(app, "Camera ERROR: 相机线程未响应（相机参数下发超时）。")
        return

    # 完成条件：camera_settings 已变 False 且 applied_ts 有更新
    applied_ts = getattr(app, "_cam_settings_applied_ts", 0.0)
    if (not getattr(app, "camera_settings", False)) and applied_ts > 0:
        # 可选：给一点缓冲，确保 streaming 稳定
        app.after(100, lambda: _start_recording_core(app))
        return

    app.after(50, lambda: _wait_camera_settings_then_start(app, t_start, timeout_s))


def _start_recording_core(app):
    """
    这里开始真正的录制。
    先只解决 record_single / record_groups 的启动即可；
    record_groups 内部完成后记得调用 stop_record/app.unlock。
    """
    try:
        # 例如：先录第一组（示例）
        # record_single(app, cg=1, ct=0.0)
        record_groups(app)  # 如果你已有 record_groups
    except Exception as e:
        _abort_recording(app, f"Record ERROR: 开始录制失败，{e}")


def record_single(app, cg: int, ct: float, vp: Optional[float] = None) -> str:
    """
    连续录制一组数据：
        - 保存目录：{camera save path}/{name}_{append1}_{append2}/{cg}/{ct}min
          若 name/append1/append2 全空：{camera save path}/{cg}/{ct}min
        - 文件名沿用旧逻辑：1_<step>.tiff
        - 录制时长：vp 秒（到时自动停止保存）

    返回：本组保存目录

    cg: current group
    ct: current time
    vp: video period

    """

    # 1) vp：优先参数，否则从 all_para_dict 读取
    if vp is None:
        vp = (getattr(app, "all_para_dict", {}) or {}).get("video_period")
    if vp is None:
        raise ValueError("未设置 video_period")
    vp = float(vp)

    # 2) 生成保存目录
    save_dir = _build_save_dir(app, cg, ct)
    os.makedirs(save_dir, exist_ok=True)

    # 3) 设置录制状态
    app.save_path = save_dir
    app.save_step = 1
    app.save_until_ts = time.monotonic() + vp
    app.save_frame = True

    return save_dir

def record_save_frame(app, frame) -> None:
    if not getattr(app, "save_frame", False):
        return

    until_ts = getattr(app, "save_until_ts", None)
    if until_ts is not None and time.monotonic() >= float(until_ts):
        app.save_frame = False
        app.save_until_ts = None
        return

    save_dir = getattr(app, "save_path", None)
    if not save_dir:
        return

    step = int(getattr(app, "save_step", 1) or 1)
    out_path = os.path.join(save_dir, f"1_{step}.tiff")

    # 关键：不做任何位深转换，直接保存相机输出
    tifffile.imwrite(out_path, np.asarray(frame), photometric="minisblack")

    app.save_step = step + 1


def record_groups(app: Any) -> None:
    """
    从 0min 开始，每间隔 video_interval(min)，在该时间点依次录制 sample_num 组。
    时间点序列：0, video_interval, 2*video_interval, ... <= video_end_time

    每组录制内容等价于 record_single(app, cg, ct)：
      - 录制 vp=video_period 秒
      - 保存到 .../{cg}/{ct}min 下
      - 文件名仍为 1_<step>.tiff
    """
    d = getattr(app, "all_para_dict", {}) or {}

    # --- 参数读取 ---
    sample_num = d.get("sample_num", None)
    video_interval = d.get("video_interval", None)       # minutes
    video_end_time = d.get("video_end_time", None)       # minutes
    vp = d.get("video_period", None)                     # seconds

    # --- 生成计划：timepoints <= end_time；每个 timepoint 录制 sample_num 组 ---
    timepoints = []
    ct = 0.0
    eps = 1e-9
    while ct <= video_end_time + eps:
        # 保留一个稳定的小数表示（避免 0.30000000004）
        timepoints.append(round(ct, 6))
        ct += video_interval

    plan = []  # 每个元素：{cg, ct_min, start_offset_s}
    for ct_min in timepoints:
        base = ct_min * 60.0
        for cg in range(1, sample_num + 1):
            plan.append({
                "cg": cg,
                "ct": ct_min,
                "start_offset_s": base + (cg - 1) * (vp + MOTOR_WAIT_S),
            })

    # --- 启动调度 ---
    # 相机相关
    app._record_groups_running = True
    app._rg_plan = plan
    app._rg_idx = 0
    app._rg_t0 = time.monotonic()
    app._rg_vp = vp
    # 电机相关
    app._rg_sample_num = sample_num
    app._rg_motor_wait_s = MOTOR_WAIT_S
    app._rg_reset_wait_s = MOTOR_WAIT_S
    app._rg_pending_action = None
    app._rg_motor_inflight = False
    app._rg_wait_until_ts = None

    _record_groups_tick(app)

    return


def stop_record_groups(app: Any) -> None:
    """
    停止 record_groups（并停止当前组录制）。
    """
    app._record_groups_running = False
    app._rg_plan = []
    app._rg_idx = 0
    app._rg_t0 = None
    app._rg_vp = None

    # 停止当前组
    app.save_frame = False
    app.save_until_ts = None
    return


def _abort_recording(app, msg: str):
    # 停止并解锁 + 提示
    app.save_frame = False
    app.save_until_ts = None
    app.recording_flag = False
    if hasattr(app, "_unlock_ui_after_recording"):
        app._unlock_ui_after_recording()
    if hasattr(app, "status_var"):
        app.status_var.set(f"[Record ERROR] {msg}")
    if hasattr(app, "_toast"):
        try:
            app._toast(msg, title="Record Error", bootstyle="danger")
        except Exception:
            pass


def _record_groups_tick(app: Any) -> None:
    """
    Tk after 调度推进：不阻塞 UI。
    """
    if not getattr(app, "_record_groups_running", False):
        return

    # 当前组还在录制：等它结束
    if getattr(app, "save_frame", False):
        app.after(30, lambda: _record_groups_tick(app))
        return

    # 电机正在动：轮询
    if getattr(app, "_rg_motor_inflight", False):
        app.after(30, lambda: _record_groups_tick(app))
        return

    # 电机动完后的稳定等待：轮询
    wait_until = getattr(app, "_rg_wait_until_ts", None)
    if wait_until is not None:
        if time.monotonic() < float(wait_until):
            app.after(30, lambda: _record_groups_tick(app))
            return
        app._rg_wait_until_ts = None

    # 如果上一组录完后需要执行电机动作（move/reset），先做动作，再回来
    pending = getattr(app, "_rg_pending_action", None)
    if pending in ("move", "reset"):
        app._rg_pending_action = None

        if pending == "move":
            wait_s = float(getattr(app, "_rg_motor_wait_s", MOTOR_WAIT_S) or MOTOR_WAIT_S)
            if _motor_next_group_impl is None:
                # 无电机：仅软件等待，保持时序
                app._rg_wait_until_ts = time.monotonic() + wait_s
            else:
                _rg_run_motor_async(app, lambda: _motor_next_group_impl(), wait_s_after=wait_s)
            app.after(10, lambda: _record_groups_tick(app))
            return

        if pending == "reset":
            wait_s = float(getattr(app, "_rg_reset_wait_s", MOTOR_WAIT_S) or MOTOR_WAIT_S)
            if _motor_reset_impl is None:
                app._rg_wait_until_ts = time.monotonic() + wait_s
            else:
                _rg_run_motor_async(app, lambda: _motor_reset_impl(), wait_s_after=wait_s)
            app.after(10, lambda: _record_groups_tick(app))
            return

    plan = getattr(app, "_rg_plan", []) or []
    idx = int(getattr(app, "_rg_idx", 0) or 0)
    if idx >= len(plan):
        # 计划完成
        stop_record(app)
        return

    t0 = getattr(app, "_rg_t0", None)
    if t0 is None:
        app._record_groups_running = False
        return

    item = plan[idx]
    now_offset = time.monotonic() - float(t0)
    start_offset = float(item["start_offset_s"])

    # 还没到该项计划时间：等待
    if now_offset + 1e-3 < start_offset:
        wait_ms = int(max(10.0, min(200.0, (start_offset - now_offset) * 1000.0)))
        app.after(wait_ms, lambda: _record_groups_tick(app))
        return

    # 到时间：启动该组录制（record_single 会置 save_frame=True，持续 vp 秒）
    vp = float(getattr(app, "_rg_vp", 0.0) or 0.0)
    record_single(app, int(item["cg"]), float(item["ct"]), vp=vp)

    # 一组结束后：
    # - 若不是本 timepoint 最后一组：move + 等待
    # - 若是本 timepoint 最后一组：reset + 等待（然后再判断是否要进入下一个 timepoint）
    sample_num = int(getattr(app, "_rg_sample_num", 1) or 1)
    if int(item["cg"]) < sample_num:
        app._rg_pending_action = "move"
    else:
        app._rg_pending_action = "reset"

    # 一组结束后执行 move + wait
    # app._rg_post_record = True

    # 推进到下一项
    app._rg_idx = idx + 1
    app.after(10, lambda: _record_groups_tick(app))


def _ensure_camera_path(app: Any) -> str:
    """
    从 app.camera_path_var 取路径；为空则调用 app._browse_camera_path 让用户选择。
    """
    camera_var = getattr(app, "camera_path_var", None)
    camera_path = camera_var.get().strip() if camera_var is not None else ""

    if camera_path:
        return camera_path

    browse = getattr(app, "_browse_camera_path", None)
    if callable(browse):
        entry = getattr(app, "entry_camera", None)
        browse(entry)

    camera_path = camera_var.get().strip() if camera_var is not None else ""
    if not camera_path:
        raise ValueError("Camera Save Path 为空：用户未选择保存路径，无法开始录制。")
    return camera_path


def _format_ct_minutes(ct: float) -> str:
    try:
        x = float(ct)
    except Exception:
        x = 0.0
    s = f"{x:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


# ============== 创建目标文件夹 ==============

def _build_save_dir(app: Any, cg: int, ct: float) -> str:
    root = _ensure_camera_path(app)

    cg_int = int(cg)
    if cg_int < 1:
        raise ValueError("cg 必须是从 1 开始的整数。")

    leaf = f"{_format_ct_minutes(ct)}min"

    # file_params：dict
    # {"Name":Entry,"Append 1":Entry,"Append 2":Entry}
    parts = []
    fp = getattr(app, "file_params", None)
    if fp is None:
        fp = {}
    elif not isinstance(fp, dict):
        raise TypeError(f"app.file_params must be dict, got {type(fp)}")

    for key in ("Name", "Append 1", "Append 2"):
        ent = fp.get(key)
        if ent is None or not hasattr(ent, "get"):
            continue
        try:
            v = ent.get()
        except Exception:
            continue
        v = _sanitize_folder_part(v)
        if v:
            parts.append(v)

    if not parts:
        # 全空：{camera save path}/{cg}/{ct}min
        return os.path.join(root, str(cg_int), leaf)

    # 非空：{camera save path}/{name}_{append1}_{append2}/{cg}/{ct}min
    exp_folder = "_".join(parts)
    return os.path.join(root, exp_folder, str(cg_int), leaf)


def _sanitize_folder_part(s: str) -> str:
    """
    把用户输入变成安全的文件夹名（尤其针对 Windows）。
    """
    s = (s or "").strip()
    if not s:
        return ""

    # 禁止路径分隔符
    s = s.replace("/", "_").replace("\\", "_")

    # Windows 非法字符: < > : " / \ | ? *
    for ch in '<>:"|?*':
        s = s.replace(ch, "_")

    # 结尾的点/空格在 Windows 也不友好
    s = s.rstrip(" .")
    return s


# ============== 组间电机移动 ==============

def _run_bg(app, fn, *, on_done=None, on_error=None, name="bg-task"):
    """
    后台线程执行 fn；回主线程用 app.after。
    """
    def worker():
        try:
            fn()
        except Exception as e:
            if callable(on_error):
                app.after(0, lambda: on_error(e))
            return
        if callable(on_done):
            app.after(0, on_done)

    threading.Thread(target=worker, daemon=True, name=name).start()


def _rg_start_motor_next_group(app) -> bool:
    """move -> 完成后进入 2s 稳定等待（不阻塞 UI/live）。"""
    if getattr(app, "_rg_motor_inflight", False):
        return True
    if _motor_next_group_impl is None:
        return False

    app._rg_motor_inflight = True
    wait_s = MOTOR_WAIT_S

    def done():
        app._rg_motor_inflight = False
        app._rg_wait_until_ts = time.monotonic() + wait_s

    def err(e: Exception):
        app._rg_motor_inflight = False
        if hasattr(app, "status_var"):
            app.status_var.set(f"[Motor ERROR] {e}")

    _run_bg(app, _motor_next_group_impl, on_done=done, on_error=err, name="motor-next-group")
    return True


def _rg_run_motor_async(app: Any, fn, wait_s_after: float) -> None:
    """
    后台线程跑阻塞式电机动作；完成后进入 wait_s_after 的“非阻塞等待”阶段。
    """
    app._rg_motor_inflight = True

    def worker():
        try:
            fn()
        except Exception as e:
            def _err():
                app._rg_motor_inflight = False
                if hasattr(app, "status_var"):
                    app.status_var.set(f"[Motor ERROR] {e}")
            app.after(0, _err)
            return

        def _done():
            app._rg_motor_inflight = False
            app._rg_wait_until_ts = time.monotonic() + float(wait_s_after)
        app.after(0, _done)

    threading.Thread(target=worker, daemon=True, name="motor-action").start()
