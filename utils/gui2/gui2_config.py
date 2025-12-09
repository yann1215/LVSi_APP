# gui2_config.py
import os
import json
from tkinter import filedialog

from _para import base_path


class ConfigMixin:
    """
    提供 Config 菜单相关功能：Save / Save As / Load
    依赖 self.all_para_dict, self.param_vars, self.status_var (可选)
    """

    # ---------- 参数：UI <-> all_para_dict 同步 ----------

    def _sync_dict_from_vars(self):
        """
        把当前 UI 上的参数写回 self.all_para_dict
        """
        if not hasattr(self, "param_vars"):
            return

        for name, var in self.param_vars.items():
            if name not in self.all_para_dict:
                continue

            old = self.all_para_dict[name]
            val = var.get()

            try:
                if isinstance(old, bool):
                    self.all_para_dict[name] = bool(val)
                elif isinstance(old, int) and not isinstance(old, bool):
                    self.all_para_dict[name] = int(val)
                elif isinstance(old, float):
                    self.all_para_dict[name] = float(val)
                else:
                    self.all_para_dict[name] = str(val)
            except Exception:
                # 转换失败就保持原值
                self.all_para_dict[name] = old

    def _sync_vars_from_dict(self):
        """
        把 self.all_para_dict 当前值刷新到 UI（加载 preset 后用）
        """
        if not hasattr(self, "param_vars"):
            return

        for name, var in self.param_vars.items():
            if name in self.all_para_dict:
                try:
                    var.set(self.all_para_dict[name])
                except Exception:
                    pass

            # 如果是枚举型参数，再把 combobox 的 StringVar 也同步一下
            if hasattr(self, "enum_meta") and name in self.enum_meta:
                mapping, combo_var = self.enum_meta[name]  # mapping: {"Adaptive":0,...}
                val_to_name = {v: k for k, v in mapping.items()}
                cur_val = self.all_para_dict.get(name)
                if cur_val in val_to_name:
                    combo_var.set(val_to_name[cur_val])

    # ---------- preset 文件路径选择 ----------

    def _ask_preset_path(self, save: bool):
        settings_dir = os.path.join(base_path, "settings")
        os.makedirs(settings_dir, exist_ok=True)

        if save:
            return filedialog.asksaveasfilename(
                title="Save Config Preset",
                initialdir=settings_dir,
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")]
            )
        else:
            return filedialog.askopenfilename(
                title="Load Config Preset",
                initialdir=settings_dir,
                filetypes=[("JSON files", "*.json")]
            )

    # ---------- 真正读写 JSON ----------

    def _write_preset(self, path: str):
        data = dict(self.all_para_dict)
        preset_name = os.path.splitext(os.path.basename(path))[0]
        data["default_ID"] = preset_name

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        if hasattr(self, "status_var"):
            self.status_var.set(f"Saved preset: {preset_name}")

    def _read_preset(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        preset_name = data.get("default_ID") or os.path.splitext(os.path.basename(path))[0]

        for k, v in data.items():
            if k == "default_ID":
                continue
            self.all_para_dict[k] = v
        self.all_para_dict["default_ID"] = preset_name

        # 刷新 UI
        self._sync_vars_from_dict()

        if hasattr(self, "status_var"):
            self.status_var.set(f"Loaded preset: {preset_name}")

    # ---------- 菜单：Configs / Save, Save As, Load ----------

    def _config_save(self):
        """保存到当前 preset（如果还没选过，就等价于 Save As）"""
        self._sync_dict_from_vars()
        if not getattr(self, "config_path", None):
            path = self._ask_preset_path(save=True)
            if not path:
                return
            self.config_path = path
        self._write_preset(self.config_path)

    def _config_save_as(self):
        self._sync_dict_from_vars()
        path = self._ask_preset_path(save=True)
        if not path:
            return
        self.config_path = path
        self._write_preset(path)

    def _config_load(self):
        path = self._ask_preset_path(save=False)
        if not path:
            return
        self.config_path = path
        self._read_preset(path)
