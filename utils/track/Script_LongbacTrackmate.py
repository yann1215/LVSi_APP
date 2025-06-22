script_LongbacTrackmate = r'''
#@output origin_imp
#@output trackSpot_imp
#@output imp
#@output total_frame_spots_num
#@output center_list
#@ boolean huge_impurity_filter
#@ int huge_impurity_time
#@ float huge_impurity_intensity_add
#@ int LD_target_channel
#@ boolean LD_simplify_contours
#@ float LD_intensity_threshold
#@ float LDF_area
#@ int LT_max_frame_gap
#@ float LT_gap_closing_max_distance
#@ float LT_linking_max_distance
#@ float LTF_track_displacement
#@ float LTF_number_spots
#@ float LTF_confinement_ratio
#@ float LTF_number_gaps
#@ String patient
#@ String group
#@ String time
#@ String path
#@ String output
import sys
import os
import re
import math
import ij.plugin.FolderOpener as FolderOpener
from ij.plugin.frame import RoiManager
from ij.util import ArrayUtil
from ij.gui import Roi
from ij.gui import PolygonRoi
from ij.gui import Overlay
from ij import IJ
from ij import WindowManager
from ij import ImagePlus
from ij import ImageStack
from ij.plugin import ZProjector
from ij.plugin import ImageCalculator
from ij.measure import ResultsTable

from fiji.plugin.trackmate import Model
from fiji.plugin.trackmate import Settings
from fiji.plugin.trackmate import TrackMate
from fiji.plugin.trackmate import TrackModel
from fiji.plugin.trackmate import FeatureModel
from fiji.plugin.trackmate.features import FeatureAnalyzer
from fiji.plugin.trackmate import SelectionModel
from fiji.plugin.trackmate import Logger
from fiji.plugin.trackmate.detection import ThresholdDetectorFactory
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

origin_imp = IJ.openImage(path)
imp = origin_imp.duplicate()
# 交换T轴与Z轴，符合trackmate格式
dims = imp.getDimensions()
imp.setDimensions(dims[2], dims[4], dims[3])

# 展现图集
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
settings.detectorFactory = ThresholdDetectorFactory()


huge_impurity_flag = False
if huge_impurity_filter == True:
    time_num_list = re.findall('\d+', time)
    if len(time_num_list) > 0:
        time_num = int(time_num_list[0])
    else:
        time_num = 0
    if time_num <= huge_impurity_time:
        huge_impurity_flag = True

pre_time_para_fix = 0.0
if huge_impurity_flag == True:
    pre_time_para_fix = huge_impurity_intensity_add

# 设置寻找光点参数
settings.detectorSettings = {
    'TARGET_CHANNEL': LD_target_channel, # *********************
    'SIMPLIFY_CONTOURS': LD_simplify_contours,  # *********************
    'INTENSITY_THRESHOLD': LD_intensity_threshold + pre_time_para_fix,  # *********************
}
# 设置过滤阈值

filter1 = FeatureFilter('AREA', LDF_area + pre_time_para_fix, True)  # 最小光强过小的视为噪声（与黑洞配合）
                                              # *********************

settings.addSpotFilter(filter1)

##############################
#   P3Step3: 连轨参数设置       #*****************************************************
##############################
# # 选择手动追踪，即不追踪
# settings.trackerFactory = ManualTrackerFactory()
# # 设置轨迹参数
# settings.trackerSettings = ManualTrackerFactory().getDefaultSettings()

# 选择Simple LAP Tracker追踪模式
settings.trackerFactory = SimpleSparseLAPTrackerFactory()

# 设置轨迹参数
settings.trackerSettings = {
    'MAX_FRAME_GAP': LT_max_frame_gap,  # 使得细菌轨迹更连续***************
    'GAP_CLOSING_MAX_DISTANCE': LT_gap_closing_max_distance,  # **************
    'LINKING_MAX_DISTANCE': LT_linking_max_distance,  # ************
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
filter3 = FeatureFilter('TRACK_DISPLACEMENT', LTF_track_displacement, True)
settings.addTrackFilter(filter3)

filter4 = FeatureFilter('NUMBER_SPOTS', LTF_number_spots, True)
settings.addTrackFilter(filter4)

filter5 = FeatureFilter('CONFINEMENT_RATIO', LTF_confinement_ratio, True)
settings.addTrackFilter(filter5)

filter6 = FeatureFilter('NUMBER_GAPS', LTF_number_gaps, False)
settings.addTrackFilter(filter6)

#################################
#   P3Step4: trackmate启动       #*****************************************************
#################################

# 添加分析（运动速度，光强度，数量）
settings.addAllAnalyzers()
# 开始运行trackmate
trackmate = TrackMate(model, settings)
# 检查是否有错误

center_list = [[] for _ in range(imp.getNFrames())]

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
    selectionModel = SelectionModel(model)
    
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
            spot_id = str(track_id) + "_long"
            polygonX = map(float, spot.getRoi().toPolygonX(1.0, 0.0, spot_x, 1.0))
            polygonY = map(float, spot.getRoi().toPolygonY(1.0, 0.0, spot_y, 1.0))
            roi = PolygonRoi(polygonX, polygonY, Roi.POLYGON)
            roi.setPosition(spot_t + 1)
            rm.addRoi(roi)
            center_list[spot_t].append([spot_x, spot_y, spot_id])
        spots_num = featuremodel.getTrackFeature(track_id, "NUMBER_SPOTS")
        total_frame_spots_num += spots_num
    
    # 可视化存入overlay
    if huge_impurity_flag == True:
        center_list = [[] for _ in range(imp.getNFrames())]
        total_frame_spots_num = 0
    else:
        rm.moveRoisToOverlay(imp)
    
    
    rm.reset()
    rm.close()
    
    IJ.run(imp,"Overlay Options...", "stroke=magenta width=0 fill=none set apply")
    
    trackSpot_imp = LabelImgExporter.createLabelImagePlus(trackmate, False, True, LabelImgExporter.LabelIdPainting.LABEL_IS_TRACK_ID)
    IJ.run(trackSpot_imp, "8-bit", "")
    trackSpot_imp.show()
    
    # 关闭Log
    # window = WindowManager.getWindow("Log")
    # window.dispose()
    
    model.clearSpots(False)
    model.clearTracks(False)
else:
    trackSpot_imp = None
    total_frame_spots_num = 0

center_list = json.dumps(center_list)
'''