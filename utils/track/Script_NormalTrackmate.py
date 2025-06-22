script_NormalTrackmate = r'''
#@output total_frame_spots_num
#@output frame_num
#@ ij.ImagePlus imp
#@ ij.ImagePlus overlay_imp
#@ ij.ImagePlus (required=false) binary_imp
#@ String center_list
#@ boolean huge_impurity_filter
#@ int huge_impurity_time
#@ boolean ND_do_subpixel_localization
#@ float ND_radius
#@ int ND_target_channel
#@ float ND_threshold
#@ boolean ND_do_median_filtering
#@ float NDF_min_intensity
#@ float NDF_snr
#@ int NT_max_frame_gap
#@ float NT_gap_closing_max_distance
#@ float NT_linking_max_distance
#@ float NTF_track_displacement
#@ float NTF_number_spots
#@ float NTF_confinement_ratio
#@ String patient
#@ String group
#@ String time
#@ String path
#@ String output
#@ float contrast_max
#@ float contrast_min

import sys
import os
import re
import math
import ij.plugin.FolderOpener as FolderOpener
from ij.plugin.frame import RoiManager
from ij.util import ArrayUtil
from ij.gui import Roi
from ij.gui import Overlay
from ij import IJ
from ij import WindowManager
from ij import ImagePlus
from ij import ImageStack
from ij.plugin import ZProjector
from ij.plugin import ImageCalculator
from ij.measure import ResultsTable

import fiji.plugin.trackmate.FeatureModel as FeatureModel
from fiji.plugin.trackmate import Model
from fiji.plugin.trackmate import Settings
from fiji.plugin.trackmate import TrackMate
from fiji.plugin.trackmate import TrackModel
from fiji.plugin.trackmate.features import FeatureAnalyzer
from fiji.plugin.trackmate import SelectionModel
from fiji.plugin.trackmate import Logger
from fiji.plugin.trackmate.detection import LogDetectorFactory
from fiji.plugin.trackmate.tracking.jaqaman import SparseLAPTrackerFactory
from fiji.plugin.trackmate.tracking.jaqaman import SimpleSparseLAPTrackerFactory
from fiji.plugin.trackmate.tracking.jaqaman import SparseLAPTracker
from fiji.plugin.trackmate.tracking.jaqaman.costmatrix import JaqamanSegmentCostMatrixCreator
from fiji.plugin.trackmate.tracking import TrackerKeys

from fiji.plugin.trackmate.gui.displaysettings import DisplaySettingsIO
from fiji.plugin.trackmate.gui.displaysettings import DisplaySettings
from fiji.plugin.trackmate.gui.displaysettings import Colormap
import fiji.plugin.trackmate.visualization.hyperstack.HyperStackDisplayer as HyperStackDisplayer
import fiji.plugin.trackmate.features.FeatureFilter as FeatureFilter
import fiji.plugin.trackmate.action.ExportTracksToXML as ExportTracksToXML
import fiji.plugin.trackmate.action.ExportAllSpotsStatsAction as ExportAllSpotsStatsAction
import fiji.plugin.trackmate.action.LabelImgExporter as LabelImgExporter
import fiji.plugin.trackmate.visualization.table as table

from fiji.plugin.trackmate.action import CaptureOverlayAction

from fiji.plugin.trackmate.tracking.manual import ManualTrackerFactory
from fiji.plugin.trackmate.tracking.jaqaman import SparseLAPTrackerFactory
from fiji.plugin.trackmate.tracking.jaqaman import SimpleSparseLAPTrackerFactory

import json

center_list = json.loads(center_list)

frame_num = imp.getNSlices()
dims = imp.getDimensions()
imp.setDimensions(dims[2], dims[4], dims[3])

imp.show()

# 建立空model，用于储存点、轨迹、边界信息
model = Model()
# 创建log用以记录进程
# model.setLogger(Logger.IJ_LOGGER)
# 设定trackmate参数对应在图片上
settings = Settings(imp)

##############################
#   P3Step2: 寻点参数设置       #*****************************************************
##############################

# 选择LoG Detector寻找模式
settings.detectorFactory = LogDetectorFactory()
# 设置寻找光点参数
settings.detectorSettings = {
    'DO_SUBPIXEL_LOCALIZATION': ND_do_subpixel_localization,
    'RADIUS': ND_radius,
    'TARGET_CHANNEL': ND_target_channel,
    'THRESHOLD': ND_threshold,  # 使得细菌轨迹更连续
    'DO_MEDIAN_FILTERING': ND_do_median_filtering,
}
# 设置过滤阈值
filter1 = FeatureFilter('MIN_INTENSITY_CH1', NDF_min_intensity, True)  # 最小光强过小的视为噪声（与黑洞配合）
settings.addSpotFilter(filter1)

filter2 = FeatureFilter('SNR_CH1', NDF_snr, True)
settings.addSpotFilter(filter2)

##############################
#   P3Step3: 连轨参数设置       #*****************************************************
##############################
# # 选择手动追踪，即不追踪
# settings.trackerFactory = ManualTrackerFactory()
#
# # 设置轨迹参数
# settings.trackerSettings = ManualTrackerFactory().getDefaultSettings()

# 选择Simple LAP Tracker追踪模式
settings.trackerFactory = SimpleSparseLAPTrackerFactory()

# 设置轨迹参数
settings.trackerSettings = {
    'MAX_FRAME_GAP': NT_max_frame_gap,  # 使得细菌轨迹更连续
    'GAP_CLOSING_MAX_DISTANCE': NT_gap_closing_max_distance,
    'LINKING_MAX_DISTANCE': NT_linking_max_distance,
    'ALTERNATIVE_LINKING_COST_FACTOR': TrackerKeys.DEFAULT_ALTERNATIVE_LINKING_COST_FACTOR,
    'SPLITTING_MAX_DISTANCE': 10.0,  # 没用
    'ALLOW_GAP_CLOSING': True,
    'ALLOW_TRACK_SPLITTING': False,  # 基本不考虑细菌分裂（算两条线
    'ALLOW_TRACK_MERGING': False,  # 不考虑细菌合并
    'MERGING_MAX_DISTANCE': 10.0,  # 没用
    'CUTOFF_PERCENTILE': 0.9,
    'BLOCKING_VALUE': float('inf')  # python的无穷大的表达
}
# 设置过滤阈值
filter3 = FeatureFilter('TRACK_DISPLACEMENT', NTF_track_displacement, True)
settings.addTrackFilter(filter3)

filter4 = FeatureFilter('NUMBER_SPOTS', NTF_number_spots, True)
settings.addTrackFilter(filter4)

filter5 = FeatureFilter('CONFINEMENT_RATIO', NTF_confinement_ratio, True)
settings.addTrackFilter(filter5)

#################################
#   P3Step4: trackmate启动       #*****************************************************
#################################

# 添加分析（运动速度，光强度，数量）
settings.addAllAnalyzers()
# 开始运行trackmate
trackmate = TrackMate(model, settings)
# 检查是否有错误

NoneSpotFound = False
# 寻点
if not NoneSpotFound == True:
    trackmate.execDetection()
    if model.getSpots().getNSpots(False) == 0:
        NoneSpotFound = True

# 筛点
if not NoneSpotFound == True:
    model.getSpots().setVisible(True)
    trackmate.computeSpotFeatures(False)
    trackmate.execSpotFiltering(False)
    if model.getSpots().getNSpots(True) == 0:
        NoneSpotFound = True

# 追迹
if not NoneSpotFound == True:
    trackmate.execTracking()
    if model.getTrackModel().nTracks(False) == 0:
        NoneSpotFound = True

# 筛迹
if not NoneSpotFound == True:
    trackmate.computeTrackFeatures(False)
    trackmate.execTrackFiltering(False)
    if model.getTrackModel().nTracks(True) == 0:
        NoneSpotFound = True

if not NoneSpotFound == True:
    # 展示结果参数
    selectionModel = SelectionModel(model)
    
    # 将trackmate的spot数据转入imagej的roi体系
    trackmodel = model.getTrackModel()
    featuremodel = model.getFeatureModel()
    
    rm = RoiManager(False)
    rm.reset()
    
    total_frame_spots_num = 0
    
    track_id_list = trackmodel.unsortedTrackIDs(True)
    for track_id in track_id_list:
        spot_list = trackmodel.trackSpots(track_id)
        for spot in spot_list:
            spot_t = int(spot.getFeature("POSITION_T"))
            model.spots.add(spot, spot_t)
            spot_x = int(spot.getFeature("POSITION_X"))
            spot_y = int(spot.getFeature("POSITION_Y"))
            spot_id = str(track_id) + "_normal"
            roi = Roi(spot_x - 5, spot_y - 5, 10, 10, 10)
            roi.setPosition(spot_t + 1)
            rm.addRoi(roi)
            center_list[spot_t].append([spot_x, spot_y, spot_id])
        spots_num = featuremodel.getTrackFeature(track_id, "TRACK_DURATION")
        total_frame_spots_num += spots_num
    
    # 可视化存入overlay
    rm.moveRoisToOverlay(overlay_imp)
    
    rm.reset()
    IJ.run(overlay_imp, "Overlay Options...", "stroke=magenta width=0 fill=none set apply")
    
    trackSpot_imp = LabelImgExporter.createLabelImagePlus(trackmate, False, True, LabelImgExporter.LabelIdPainting.LABEL_IS_TRACK_ID)
    IJ.run(trackSpot_imp, "8-bit", "")
    trackSpot_imp.show()
    
    huge_impurity_flag = False
    if huge_impurity_filter == True:
        time_num_list = re.findall('\d+', time)
        if len(time_num_list) > 0:
            time_num = int(time_num_list[0])
        else:
            time_num = 0
        if time_num <= huge_impurity_time:
            huge_impurity_flag = True
            
    if binary_imp == None or huge_impurity_flag == True:
        new_binary_imp = trackSpot_imp
    else:
        new_binary_imp = ImageCalculator.run(trackSpot_imp, binary_imp, "Add create stack")
        new_binary_imp.show()
    
        trackSpot_imp.changes = False
        trackSpot_imp.close()
    
        binary_imp.changes = False
        binary_imp.close()
    # 关闭Log
    # window = WindowManager.getWindow("Log")
    # window.dispose()
    
    # release the memory
    model.clearSpots(False)
    model.clearTracks(False)
    
    imp.changes = False
    imp.close()
else:
    new_binary_imp = binary_imp
    overlay_imp = overlay_imp
    total_frame_spots_num = 0

center_list = json.dumps(center_list)

spotJSON_path = output + "\\" + patient + "-SPOT_JSON"
if os.path.exists(spotJSON_path) == False:
    os.mkdir(spotJSON_path)

spotJSON_name = patient + group + time

spot_json_path = spotJSON_path + "\\" + spotJSON_name + ".json"

with open(spot_json_path, 'w') as f:
    f.write(center_list)

spotAVI_path = output + "\\" + patient + "-SPOT_AVI"
if os.path.exists(spotAVI_path) == False:
    os.mkdir(spotAVI_path)

spotAVI_name = patient + group + time

spot_imp_path = spotAVI_path + "\\" + spotAVI_name + '.tif' 

overlay_imp.setDisplayRange(contrast_min, contrast_max)
overlay_imp.updateAndDraw()
overlay_imp.flattenStack()
IJ.saveAs(overlay_imp, "Tiff", spot_imp_path)

# overlay_imp.changes = False
# overlay_imp.close()

binaryAVI_path = output + "\\" + patient + "-ONLY_SPOT_AVI"
if os.path.exists(binaryAVI_path) == False:
    os.mkdir(binaryAVI_path)

binaryAVI_name = patient + group + time

binary_imp_path = binaryAVI_path + "\\" + binaryAVI_name + '.tif' 

new_binary_imp.setDisplayRange(contrast_min, contrast_max)
new_binary_imp.updateAndDraw()
IJ.run(new_binary_imp, "Grays", "")
IJ.saveAs(new_binary_imp, "Tiff", binary_imp_path)

new_binary_imp.changes = False
new_binary_imp.close()
'''