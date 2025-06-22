from utils.process.Util_Java import standardScriptRuner
from utils.process.Util_csvOutputer import csv_manager, ID_csv_outputer
from utils.track.Script_shakePart import script_shakePart
from utils.track.Script_preProcess import script_preProcess
from utils.track.Script_LongbacTrackmate import script_LongbacTrackmate
from utils.track.Script_subLongbac import script_subLongbac
from utils.track.Script_NormalTrackmate import script_NormalTrackmate
from utils.track.Script_ReChooser import script_ReChooser
from utils.track.Script_impListener import script_impListener


def AST_preprocess(self, path_dict, para_dict, program_end):
    if self.EndEvent.is_set():
        return
    self.status_var.set("开始噪声过滤")
    try:
        args_shakePart = {
            "frame_step": para_dict["frame_step"],
            "shake_binary_threshold": para_dict["shake_binary_threshold"],
            "min_filter_len": para_dict["min_filter_len"],
            "iteration_limit": para_dict["iteration_limit"],
            "iteration_step": para_dict["iteration_step"],
            "sus_threshold": para_dict["sus_threshold"],
            "shake_threshold": para_dict["shake_threshold"],
            "patient": path_dict["patient"],
            "group": path_dict["group"],
            "time": path_dict["time"],
            "path": path_dict["path"],
            "output": path_dict["output"],
        }
        output_shakePart = standardScriptRuner(script_shakePart, args_shakePart)
        toStart = output_shakePart.getOutput("toStart")
        toEnd = output_shakePart.getOutput("toEnd")
        update_dict = output_shakePart.getOutput("update_dict")
        para_dict.update(update_dict)
        args_preProcess = {
            "toStart": toStart,
            "toEnd": toEnd,
            "frame_step": para_dict["frame_step"],
            "local_min_len": para_dict["local_min_len"],
            "subtract_rolling": para_dict["subtract_rolling"],
            "outliers_radius_1": para_dict["outliers_radius_1"],
            "outliers_threshold_1": para_dict["outliers_threshold_1"],
            "outliers_radius_2": para_dict["outliers_radius_2"],
            "outliers_threshold_2": para_dict["outliers_threshold_2"],
            "zero_part_threshold": para_dict["zero_part_threshold"],
            "close_iteration": para_dict["close_iteration"],
            "close_count": para_dict["close_count"],
            "dilate_iteration": para_dict["dilate_iteration"],
            "dilate_count": para_dict["dilate_count"],
            "enhance_brightness": para_dict["enhance_brightness"],
            "patient": path_dict["patient"],
            "group": path_dict["group"],
            "time": path_dict["time"],
            "path": path_dict["path"],
            "output": path_dict["output"],
            "contrast_max": para_dict["contrast_max"],
            "contrast_min": para_dict["contrast_min"],
        }
        output_preProcess = standardScriptRuner(script_preProcess, args_preProcess)
        imp_path = output_preProcess.getOutput("imp_path")
        path_dict.update({
            "path": imp_path,
        })
        self.progress['value'] = 45
        self.status_var.set("噪声过滤完成")
        if program_end > 1:
            AST_TrackMate(self, path_dict, para_dict, program_end)
    except:
        self.status_var.set("噪声过滤出错")
    return


def AST_TrackMate(self, path_dict, para_dict, program_end):
    if self.EndEvent.is_set():
        return
    self.status_var.set("开始检测追踪")

    try:
        args_LongbacTrackmate = {
            "huge_impurity_filter": para_dict["huge_impurity_filter"],
            "huge_impurity_time" : para_dict["huge_impurity_time"],
            "huge_impurity_intensity_add" : para_dict["huge_impurity_intensity_add"],
            "LD_target_channel" : para_dict["LD_target_channel"],
            "LD_simplify_contours" :para_dict["LD_simplify_contours"],
            "LD_intensity_threshold" : para_dict["LD_intensity_threshold"],
            "LDF_area" : para_dict["LDF_area"],
            "LT_max_frame_gap" : para_dict["LT_max_frame_gap"],
            "LT_gap_closing_max_distance" : para_dict["LT_gap_closing_max_distance"],
            "LT_linking_max_distance" : para_dict["LT_linking_max_distance"],
            "LTF_track_displacement" : para_dict["LTF_track_displacement"],
            "LTF_number_spots" : para_dict["LTF_number_spots"],
            "LTF_confinement_ratio" : para_dict["LTF_confinement_ratio"],
            "LTF_number_gaps" :para_dict["LTF_number_gaps"],
            "patient": path_dict["patient"],
            "group": path_dict["group"],
            "time": path_dict["time"],
            "path": path_dict["path"],
            "output": path_dict["output"],
        }
        output_LongbacTrackmate = standardScriptRuner(script_LongbacTrackmate, args_LongbacTrackmate)
        origin_imp = output_LongbacTrackmate.getOutput("origin_imp")
        trackSpot_imp = output_LongbacTrackmate.getOutput("trackSpot_imp")
        imp = output_LongbacTrackmate.getOutput("imp")
        Longbac_spots_num = output_LongbacTrackmate.getOutput("total_frame_spots_num")
        center_list = output_LongbacTrackmate.getOutput("center_list")
        args_subLongbac = {
            "original_binary_imp": trackSpot_imp,
            "total_frame_spots_num": Longbac_spots_num,
            "original_imp": origin_imp,
            "WL_close_iteration": para_dict["WL_close_iteration"],
            "WL_close_count": para_dict["WL_close_count"],
            "WL_dilate_iteration": para_dict["WL_dilate_iteration"],
            "WL_dilate_count": para_dict["WL_dilate_count"],
            "patient": path_dict["patient"],
            "group": path_dict["group"],
            "time": path_dict["time"],
            "path": path_dict["path"],
            "output": path_dict["output"],
        }
        output_subLongbac = standardScriptRuner(script_subLongbac, args_subLongbac)
        without_imp = output_subLongbac.getOutput("imp")
        args_NormalTrackmate = {
            "imp": without_imp,
            "overlay_imp": imp,
            "binary_imp": trackSpot_imp,
            "center_list": center_list,
            "huge_impurity_filter": para_dict["huge_impurity_filter"],
            "huge_impurity_time": para_dict["huge_impurity_time"],
            "ND_do_subpixel_localization": para_dict["ND_do_subpixel_localization"],
            "ND_radius": para_dict["ND_radius"],
            "ND_target_channel": para_dict["ND_target_channel"],
            "ND_threshold": para_dict["ND_threshold"],
            "ND_do_median_filtering": para_dict["ND_do_median_filtering"],
            "NDF_min_intensity": para_dict["NDF_min_intensity"],
            "NDF_snr": para_dict["NDF_snr"],
            "NT_max_frame_gap": para_dict["NT_max_frame_gap"],
            "NT_gap_closing_max_distance": para_dict["NT_gap_closing_max_distance"],
            "NT_linking_max_distance": para_dict["NT_linking_max_distance"],
            "NTF_track_displacement": para_dict["NTF_track_displacement"],
            "NTF_number_spots": para_dict["NTF_number_spots"],
            "NTF_confinement_ratio": para_dict["NTF_confinement_ratio"],
            "patient": path_dict["patient"],
            "group": path_dict["group"],
            "time": path_dict["time"],
            "path": path_dict["path"],
            "output": path_dict["output"],
            "contrast_max": para_dict["contrast_max"],
            "contrast_min": para_dict["contrast_min"],
        }
        output_NormalTrackmate = standardScriptRuner(script_NormalTrackmate, args_NormalTrackmate)
        Normal_spots_num = output_NormalTrackmate.getOutput("total_frame_spots_num")
        frame_num = output_NormalTrackmate.getOutput("frame_num")
        csv_manager(path_dict, Longbac_spots_num, Normal_spots_num, frame_num)
        self.progress['value'] = 75
        self.status_var.set("检测追踪完成")
        if program_end > 2:
            AST_features(self, path_dict, para_dict)
    except:
        self.status_var.set("检测追踪出错")
    return


def AST_features(self, path_dict, para_dict):
    if self.EndEvent.is_set():
        return
    self.status_var.set("开始特征提取")
    try:
        args_ReChooser = {
            "ROI_frame_start": para_dict["ROI_frame_start"],
            "ROI_frame_stop": para_dict["ROI_frame_stop"],
            "ROI_0_thres": para_dict["ROI_0_thres"],
            "ROI_1_thres": para_dict["ROI_1_thres"],
            "ROI_2_thres": para_dict["ROI_2_thres"],
            "ROI_h_thres": para_dict["ROI_h_thres"],
            "ROI_at_least": para_dict["ROI_at_least"],
            "patient": path_dict["patient"],
            "group": path_dict["group"],
            "time": path_dict["time"],
            "path": path_dict["path"],
            "output": path_dict["output"],
        }
        output_ReChooser = standardScriptRuner(script_ReChooser, args_ReChooser)
        ID_data_list = output_ReChooser.getOutput("ID_data_list")
        ID_csv_outputer(path_dict,  para_dict, ID_data_list)
        self.progress['value'] = 100
        self.status_var.set("特征提取完成")
    except:
        self.status_var.set("特征提取出错")
    return


def AST_impListener(self, mode):
    try:
        args_ImpListener = {
            "mode": mode,
        }
        standardScriptRuner(script_impListener, args_ImpListener)
    except:
        print("error in imp listener")
    return
