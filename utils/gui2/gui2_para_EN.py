# 修改 all_para_settings 中的变量类型时，需要在 _para.py 中同步修改 all_para_dict 中的变量类型

all_para_settings = {
    "camera": {
        "detail": [
            {"str": "— Multi-Sample Acquisition —", "name": "", "type": "label"},
            {"str": "Number of Samples", "name": "sample_num", "type": "int"},
            {"str": "Frame Rate (fps)", "name": "vimbaX_AcquisitionFrameRate", "type": "float"},
            # {"str": "", "name": "range=(1.0369e-05, 289.04776)", "type": "label"},
            {"str": "Per-Sample Capture Duration (s) ", "name": "video_period", "type": "float"},
            {"str": "Capture Interval (min)", "name": "video_interval", "type": "float"},
            {"str": "Capture End Time (min)", "name": "video_end_time", "type": "float"},

            {"str": "— Camera Parameters —", "name": "", "type": "label"},
            {"str": "Exposure", "name": "vimbaX_ExposureTime", "type": "float"},
            # {"str": "", "name": "range=(176.687, 10000009.253)", "type": "label"},
            {"str": "Gain", "name": "vimbaX_Gain", "type": "float"},
            # {"str": "", "name": "range=(0.0, 24.0000)", "type": "label"},
            {"str": "Sensor Bit Depth", "name": "vimbaX_SensorBitDepth", "type": {
                "Adaptive":0,
                "Bpp8":1,
                "Bpp10":2,
                "Bpp12":3,
            }},

            {"str": "— Contrast Processing —", "name": "", "type": "label"},
            {"str": "Upper Intensity", "name": "contrast_max", "type": "float"},
            {"str": "Lower Intensity", "name": "contrast_min", "type": "float"},
        ],
    },

    "preprocess": {
        "brief": [
            {"str": "— Noise Filtering —", "name": "", "type": "label"},
            {"str": "Frame Step", "name": "frame_step", "type": "int"},
            {"str": "Suspected Jitter Threshold", "name": "sus_threshold", "type": "float"},
            {"str": "Local-Min Window Length", "name": "local_min_len", "type": "int"},
            {"str": "Median Filter Radius", "name": "subtract_rolling", "type": "float"},
        ],
        "detail": [
            {"str": "— Video Stabilization —", "name": "", "type": "label"},
            {"str": "Frame Step", "name": "frame_step", "type": "int"},
            {"str": "Jitter Binarization Threshold", "name": "shake_binary_threshold", "type": "float"},
            {"str": "Jitter Smoothing Window Length", "name": "min_filter_len", "type": "int"},
            {"str": "Iteration Limit", "name": "iteration_limit", "type": "int"},
            {"str": "Iteration Step Size", "name": "iteration_step", "type": "float"},
            {"str": "Suspected Jitter Threshold", "name": "sus_threshold", "type": "float"},
            {"str": "Jitter Decision Threshold", "name": "shake_threshold", "type": "float"},

            {"str": "— Noise Filtering —", "name": "", "type": "label"},
            {"str": "Local-Min Window Length", "name": "local_min_len", "type": "int"},
            {"str": "Median Filter Radius", "name": "subtract_rolling", "type": "float"},
            {"str": "Outlier Radius (Class 1)", "name": "outliers_radius_1", "type": "int"},
            {"str": "Outlier Threshold (Class 1)", "name": "outliers_threshold_1", "type": "int"},
            {"str": "Outlier Radius (Class 2)", "name": "outliers_radius_2", "type": "int"},
            {"str": "Outlier Threshold (Class 2)", "name": "outliers_threshold_2", "type": "int"},

            {"str": "— Morphological Refinement —", "name": "", "type": "label"},
            {"str": "Black-Hole Binarization Threshold", "name": "zero_part_threshold", "type": "float"},
            {"str": "Closing Iterations", "name": "close_iteration", "type": "int"},
            {"str": "Closing Radius", "name": "close_count", "type": "int"},
            {"str": "Dilation Iterations", "name": "dilate_iteration", "type": "int"},
            {"str": "Dilation Radius", "name": "dilate_count", "type": "int"},
            {"str": "Brightness Boost Factor", "name": "enhance_brightness", "type": "float"},
        ],
    },

    "trackmate": {
        "brief": [
            {"str": "— Detection and Tracking —", "name": "", "type": "label"},
            {"str": "Enable Huge-Impurity Filter", "name": "huge_impurity_filter", "type": "bool"},
            {"str": "Filtering Time Limit", "name": "huge_impurity_time", "type": "int"},
            {"str": "Long-Bacteria Intensity Threshold", "name": "LD_intensity_threshold", "type": "float"},
            {"str": "Long-Bacteria Area Filter", "name": "LDF_area", "type": "float"},
            {"str": "Long-Bacteria Max Linking Distance", "name": "LT_linking_max_distance", "type": "float"},
            {"str": "Long-Bacteria Confinement Ratio", "name": "LTF_confinement_ratio", "type": "float"},
            {"str": "Short-Bacteria Detection Radius", "name": "ND_radius", "type": "float"},
            {"str": "Short-Bacteria Detection Threshold", "name": "ND_threshold", "type": "float"},
            {"str": "Short-Bacteria SNR Filter", "name": "NDF_snr", "type": "float"},
            {"str": "Short-Bacteria Max Linking Distance", "name": "NT_linking_max_distance", "type": "float"},
            {"str": "Short-Bacteria Confinement Ratio", "name": "NTF_confinement_ratio", "type": "float"},
        ],
        "detail": [
            {"str": "— Large-Impurity Filtering —", "name": "", "type": "label"},
            {"str": "Enable Huge-Impurity Filter", "name": "huge_impurity_filter", "type": "bool"},
            {"str": "Filtering Time Limit", "name": "huge_impurity_time", "type": "int"},
            {"str": "Filter Parameter Correction", "name": "huge_impurity_intensity_add", "type": "float"},

            {"str": "— Long-Bacteria Detection —", "name": "", "type": "label"},
            {"str": "Target Channel", "name": "LD_target_channel", "type": "int"},
            {"str": "Simplify Contours", "name": "LD_simplify_contours", "type": "bool"},
            {"str": "Intensity Threshold", "name": "LD_intensity_threshold", "type": "float"},

            {"str": "— Long-Bacteria Detection Filtering —", "name": "", "type": "label"},
            {"str": "Area Filter", "name": "LDF_area", "type": "float"},

            {"str": "— Long-Bacteria Tracking —", "name": "", "type": "label"},
            {"str": "Max Frame Gap", "name": "LT_max_frame_gap", "type": "int"},
            {"str": "Gap-Closing Max Distance", "name": "LT_gap_closing_max_distance", "type": "float"},
            {"str": "Max Linking Distance", "name": "LT_linking_max_distance", "type": "float"},

            {"str": "— Long-Bacteria Track Filtering —", "name": "", "type": "label"},
            {"str": "Track Displacement Filter", "name": "LTF_track_displacement", "type": "float"},
            {"str": "Track Duration Filter", "name": "LTF_number_spots", "type": "float"},
            {"str": "Track Confinement Ratio Filter", "name": "LTF_confinement_ratio", "type": "float"},
            {"str": "Track Gap Count Filter", "name": "LTF_number_gaps", "type": "float"},

            {"str": "— Long-Bacteria Removal —", "name": "", "type": "label"},
            {"str": "Closing Iterations", "name": "WL_close_iteration", "type": "int"},
            {"str": "Closing Radius", "name": "WL_close_count", "type": "int"},
            {"str": "Dilation Iterations", "name": "WL_dilate_iteration", "type": "int"},
            {"str": "Dilation Radius", "name": "WL_dilate_count", "type": "int"},

            {"str": "— Short-Bacteria Detection —", "name": "", "type": "label"},
            {"str": "Enable Subpixel Localization", "name": "ND_do_subpixel_localization", "type": "bool"},
            {"str": "Detection Radius", "name": "ND_radius", "type": "float"},
            {"str": "Target Channel", "name": "ND_target_channel", "type": "int"},
            {"str": "Detection Threshold", "name": "ND_threshold", "type": "float"},
            {"str": "Enable Median Filtering", "name": "ND_do_median_filtering", "type": "bool"},

            {"str": "— Short-Bacteria Detection Filtering —", "name": "", "type": "label"},
            {"str": "Min Intensity Filter", "name": "NDF_min_intensity", "type": "float"},
            {"str": "SNR Filter", "name": "NDF_snr", "type": "float"},

            {"str": "— Short-Bacteria Tracking —", "name": "", "type": "label"},
            {"str": "Max Frame Gap", "name": "NT_max_frame_gap", "type": "int"},
            {"str": "Gap-Closing Max Distance", "name": "NT_gap_closing_max_distance", "type": "float"},
            {"str": "Max Linking Distance", "name": "NT_linking_max_distance", "type": "float"},

            {"str": "— Short-Bacteria Track Filtering —", "name": "", "type": "label"},
            {"str": "Track Displacement Filter", "name": "NTF_track_displacement", "type": "float"},
            {"str": "Track Duration Filter", "name": "NTF_number_spots", "type": "float"},
            {"str": "Track Confinement Ratio Filter", "name": "NTF_confinement_ratio", "type": "float"},
        ],
    },

    "features": {
        "brief": [
            {"str": "— Feature Extraction —", "name": "", "type": "label"},
            {"str": "ROI Start Frame", "name": "ROI_frame_start", "type": "int"},
            {"str": "ROI End Frame", "name": "ROI_frame_stop", "type": "int"},
        ],
        "detail": [
            {"str": "— ROI Re-Selection —", "name": "", "type": "label"},
            {"str": "ROI Start Frame", "name": "ROI_frame_start", "type": "int"},
            {"str": "ROI End Frame", "name": "ROI_frame_stop", "type": "int"},
            {"str": "Background Decision Threshold", "name": "ROI_0_thres", "type": "float"},
            {"str": "Gradient Decision Threshold (Class 1)", "name": "ROI_1_thres", "type": "float"},
            {"str": "Gradient Decision Threshold (Class 2)", "name": "ROI_2_thres", "type": "float"},
            {"str": "Upper Decision Threshold", "name": "ROI_h_thres", "type": "float"},
            {"str": "Minimum Iterations", "name": "ROI_at_least", "type": "float"},

            {"str": "— Feature Computation —", "name": "", "type": "label"},
            {"str": "Heatflow Smoothing Window (Class 1)", "name": "smooth_window_len_1", "type": "int"},
            {"str": "Heatflow Smoothing Window (Class 2)", "name": "smooth_window_len_2", "type": "int"},
            {"str": "Heatflow Smoothing Window (Class 3)", "name": "smooth_window_len_3", "type": "int"},
            {"str": "Flicker Tolerance (Class 1)", "name": "shine_tolerance_1", "type": "float"},
            {"str": "Flicker Tolerance (Class 2)", "name": "shine_tolerance_2", "type": "float"},
            {"str": "Flicker Tolerance (Class 3)", "name": "shine_tolerance_3", "type": "float"},
        ],
    },
}
