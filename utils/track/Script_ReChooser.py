script_ReChooser = r'''
#@output ID_data_list
#@ int ROI_frame_start
#@ int ROI_frame_stop
#@ float ROI_0_thres
#@ float ROI_1_thres
#@ float ROI_2_thres
#@ float ROI_h_thres
#@ int ROI_at_least
#@ String patient
#@ String group
#@ String time
#@ String path
#@ String output
import sys
import os
import math
import ij.plugin.FolderOpener as FolderOpener
from ij.plugin.frame import RoiManager
from ij.process import ByteProcessor, ImageProcessor, ImageStatistics
from ij.util import ArrayUtil
from ij.gui import Roi
from ij.gui import Overlay
from ij import IJ
from ij import WindowManager
from ij import ImagePlus
from ij import ImageStack
from ij.plugin import ZProjector
from ij.plugin import ImageCalculator
from ij.measure import ResultsTable, Measurements
from java.util import LinkedList, ArrayList
from java.util.concurrent import Executors, TimeUnit
from java.lang import Runtime, Runnable
import threading
import csv
import json
import traceback

lock = threading.Lock()
json_path = path.split("-PRE_AVI")[0] + "-SPOT_JSON"
json_name = patient + group + time + ".json"
center_list = "[]"
with open(json_path + "\\" + json_name, 'r') as f:
    center_list = f.read()

pre_imp = IJ.openImage(path)
spot_list = json.loads(center_list)

def spotReChooser(pre_imp, spot_list):

    frame_start = ROI_frame_start
    frame_stop = ROI_frame_stop

    spot_list = spot_list[frame_start - 1: frame_stop]
    imp = pre_imp.crop(str(frame_start) + "-" + str(frame_stop))
    frame_num = len(spot_list)

    dims = imp.getDimensions()
    imp.setDimensions(dims[2], dims[4], dims[3])
    width = imp.getWidth()
    height = imp.getHeight()
    binary_stack = ImageStack(width, height)

    rm = RoiManager(False)
    rm.reset()
    
    num_cores = Runtime.getRuntime().availableProcessors()
    executor = Executors.newFixedThreadPool(num_cores) 
    
    min_thread_step = int(math.ceil(float(frame_num) / float(num_cores)))
    
    result_all = []
    ID_data_list = []
    binary_list = []
    roi_list = []
    
    local_index = 0
    for local_frame_index in range(1, frame_num, min_thread_step):
        local_start = local_frame_index - 1
        local_stop = local_start + min_thread_step
        local_imp = imp.crop(str(local_frame_index) + "-" + str(local_stop))
        local_spot_list = spot_list[local_start: local_stop]
        task = ComputeTask(local_imp, local_spot_list, result_all, local_index, local_frame_index, lock)
        executor.submit(task)
        local_index += 1
    
    executor.shutdown()
    executor.awaitTermination(1, TimeUnit.HOURS)
    
    result_all.sort(key=lambda item: item["index"])
    for result in result_all:
        ID_data_list += result["local_ID_data_list"]
        binary_list += result["local_binary_list"]
        roi_list += result["local_roi_list"]

    for bp in binary_list:
        binary_stack.addSlice(bp)
        
    for roi in roi_list:
        rm.addRoi(roi)
        
    roi_path = output + "\\" + patient + "-ROI"
    if os.path.exists(roi_path) == False:
        os.mkdir(roi_path)

    roi_name = patient + group + time

    this_roi_path = roi_path + "\\" + roi_name + ".zip"
    rm.save(this_roi_path)

    imp.changes = False
    imp.close()

    rm.reset()

    onlyroi_imp = ImagePlus("", binary_stack)
    onlyroi_imp_path = output + "\\" + patient + "-ROI_SPOT_TIFF"
    if os.path.exists(onlyroi_imp_path) == False:
        os.mkdir(onlyroi_imp_path)

    onlyroi_imp_name = patient + group + time

    IJ.saveAs(onlyroi_imp, "Tiff", onlyroi_imp_path + "\\" + onlyroi_imp_name + ".tif")
    onlyroi_imp.changes = False
    onlyroi_imp.close()
        
    return ID_data_list

class ComputeTask(Runnable):
    def __init__(self, imp, spot_list, result_dict, index, frame_index, lock):
            self.imp = imp  # 要处理的帧索引列表
            self.spot_list = spot_list  # 对应帧的点坐标子集
            self.result_dict = result_dict  # 线程安全的集合存放结果
            self.index = index
            self.frame_index = frame_index
            self.lock = lock
            
    def run(self):
        local_binary_list = []
        local_roi_list = []
        local_ID_data_list = []
        imp = self.imp
        width = imp.getWidth()
        height = imp.getHeight()
        frame_index = self.frame_index
        index = self.index
        spot_list = self.spot_list
        local_frame_index = 1
        for frame in spot_list:
            bp = ByteProcessor(width, height)
            bp.setColor(0)
            frame_roi_list = []
            for spot in frame:
                spot_x = int(spot[0])
                spot_y = int(spot[1])
                spot_id = spot[2]
                roi, bp, local_ID_data_list = self.downhillRegionGrowing(imp, local_frame_index, spot_x, spot_y, spot_id, bp, local_ID_data_list)
                roi.setPosition(frame_index)
                frame_roi_list.append(roi)
            local_frame_index += 1
            frame_index += 1
            local_binary_list.append(bp)
            local_roi_list += frame_roi_list
        # 将局部结果添加到线程安全容器
        lock = self.lock
        lock.acquire()
        try:
            self.result_dict.append({
                "index": index,
                "local_ID_data_list": local_ID_data_list,
                "local_roi_list": local_roi_list,
                "local_binary_list": local_binary_list,
            })
        finally:
            lock.release()


    
    def downhillRegionGrowing(self, imp, frame_index, spot_x, spot_y, spot_id, all_bp, ID_data_list):
        width = imp.getWidth()
        height = imp.getHeight()
    
        imp.setT(frame_index)
        ip = imp.getProcessor()
    
        bp = ByteProcessor(width, height)
        bp.setColor(0)
    
        queue = [(spot_x, spot_y)]
    
        bp.set(spot_x, spot_y, 255)
    
        # 定义4邻域坐标偏移量
        neighbors = [(0, -1), (-1, 0), (1, 0), (0, 1)]
        quit_flag = False
    
        iteration_times = 0
    
        while not quit_flag:
            
            spot_list = queue
            neighbors_list = []
    
            all_neighbors_num = 0
            chosen_neighbors_num = 0
    
            for spot in spot_list:
                x, y = spot
                spot_value = ip.getPixel(x, y)
    
                # 检查所有邻域像素
                for dx, dy in neighbors:
                    nx = x + dx
                    ny = y + dy
    
                    # 检查是否在图像范围内且未被访问
                    if 0 <= nx < width and 0 <= ny < height and not bp.get(nx, ny) == 255:
    
                        if bp.get(nx, ny) == 0:
                            all_neighbors_num += 1
                            bp.set(nx, ny, 127)
    
                        append_flag = True
                        neighbor_value = ip.getPixel(nx, ny)
    
                        if iteration_times <= ROI_at_least:
                            bp.set(nx, ny, 255)
                        elif spot_value >= ROI_h_thres:
                            bp.set(nx, ny, 255)
                        elif neighbor_value >= ROI_2_thres and neighbor_value - spot_value < 2:
                            bp.set(nx, ny, 255)
                        elif neighbor_value >= ROI_1_thres and neighbor_value - spot_value < 1:
                            bp.set(nx, ny, 255)
                        elif neighbor_value >= ROI_0_thres and neighbor_value - spot_value < 0:
                            bp.set(nx, ny, 255)
                        else:
                            append_flag = False
                        if append_flag:
                            neighbors_list.append((nx, ny))
                            all_bp.set(nx, ny, 255)
                            chosen_neighbors_num += 1
            if all_neighbors_num == 0:
                quit_flag = True
            elif (chosen_neighbors_num / all_neighbors_num) < (1 / 2):
                quit_flag = True
    
            queue = neighbors_list
            iteration_times += 1
    
    
        bp.setThreshold(255, 255, ImageProcessor.NO_LUT_UPDATE)
        bmp = ImagePlus("", bp)
        IJ.doWand(bmp, spot_x, spot_y, 0.0, "4-connected")
        roi = bmp.getRoi()
        roi.setName(str(spot_x) + ", " + str(spot_y) + ", " + str(iteration_times))
        bmp.close()
    
        imp.resetRoi()
        imp.setRoi(roi)
        ip = imp.getProcessor()
        options = (Measurements.AREA | Measurements.MEAN | Measurements.STD_DEV | Measurements.MIN_MAX)
        stats = ImageStatistics().getStatistics(ip, options, imp.getCalibration())
        spot_area = stats.area
        spot_mean = stats.mean
        spot_stdDev = stats.stdDev
        spot_max = stats.max
        spot_perimeter = roi.getLength()
        spot_sum = spot_area * spot_mean

        ID_data_dict = {}
        ID_data_dict["TRACK_ID"] = spot_id
        ID_data_dict["FRAME"] = frame_index
        ID_data_dict["X"] = spot_x
        ID_data_dict["Y"] = spot_y
        ID_data_dict["AREA"] = spot_area
        ID_data_dict["MEAN"] = spot_mean
        ID_data_dict["STD"] = spot_stdDev
        ID_data_dict["MAX"] = spot_max
        ID_data_dict["PERIM"] = spot_perimeter
        ID_data_dict["SUM"] = spot_sum
    
        ID_data_list.append(ID_data_dict)
        
        return roi, all_bp, ID_data_list
    
ID_data_list = spotReChooser(pre_imp, spot_list)
ID_data_list = json.dumps(ID_data_list)

'''