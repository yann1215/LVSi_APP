script_preProcess = r'''
#@output imp_path
#@ int toStart
#@ int toEnd
#@ int frame_step
#@ int local_min_len
#@ float subtract_rolling
#@ int outliers_radius_1
#@ int outliers_threshold_1
#@ int outliers_radius_2
#@ int outliers_threshold_2
#@ float zero_part_threshold
#@ int close_iteration
#@ int close_count
#@ int dilate_iteration
#@ int dilate_count
#@ float enhance_brightness
#@ String patient
#@ String group
#@ String time
#@ String path
#@ String output
#@ float contrast_max
#@ float contrast_min

import sys
import os
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

imp = FolderOpener.open(path, "filter=tif" + " start="+str(toStart)
                        +" count="+str(toEnd - toStart + 1) + " step=" + str(frame_step))
# 只留像素信息
imp.removeScale()
imp.show()

slice_ = imp.getNSlices()
new_stack = ImageStack(imp.getWidth(), imp.getHeight())
n = local_min_len
for i in range(1, slice_-n+1):
    imp_min = ZProjector.run(imp, "min",i,i+n) #获取局部最小值
    ip = imp_min.getProcessor()
    new_stack.addSlice(ip) #将最小值加入新序列
new_imp = ImagePlus(imp.getTitle(),new_stack)
new_imp.show()
imp_2 = imp.crop("1-"+str(slice_-n)) #取原数据
imp_sub = ImageCalculator.run(imp_2, new_imp, "Subtract create stack") #原数据减去局部最小值序列
imp_sub.show()

# 关闭无关窗口
imp_2.changes = False
imp_2.close()
new_imp.changes = False
new_imp.close()

# 关闭无关窗口
imp.changes = False
imp.close()
imp_min.changes = False
imp_min.close()

imp_sub_2 = imp_sub.duplicate() #复制Step1数据以备用

# 除背景，平基线
IJ.run(imp_sub, "Subtract Background...", "rolling=" + str(subtract_rolling) + " stack")

# 除异常数据值（部分椒盐噪声）
IJ.run(imp_sub, "Remove Outliers...", "radius="+str(outliers_radius_1)+" threshold="+str(outliers_threshold_1)+" which=Bright stack")

IJ.run(imp_sub, "Remove Outliers...", "radius="+str(outliers_radius_2)+" threshold="+str(outliers_threshold_2)+" which=Bright stack")

# 设阈值二值化，取0以上部分
IJ.setRawThreshold(imp_sub_2, zero_part_threshold, 255.0)

IJ.run(imp_sub_2, "Convert to Mask", "background=Dark black create")
imp_binary_1 = IJ.getImage()
imp_binary_1.show()

# 关闭无关窗口
imp_sub_2.changes = False
imp_sub_2.close()

# 闭运算除椒盐噪声，只保留大黑洞
IJ.run(imp_binary_1, "Options...", "iterations="+str(close_iteration)+" count="+str(close_count)+" black do=Close stack")
# IJ.run(imp_binary_2, "Options...", "iterations=1 count=1 black do=Open stack")

# 复制
imp_binary_2 = imp_binary_1.duplicate()
IJ.run(imp_binary_2, "Invert", "stack")

# 膨胀
IJ.run(imp_binary_2, "Options...", "iterations="+str(dilate_iteration)+" count="+str(dilate_count)+" black do=Dilate stack")

# 降低亮度（使得黑洞周围部分亮度提高，但又不至于影响过重）
IJ.run(imp_binary_1, "Divide...", "value=" + str(255.0 / enhance_brightness) + " stack")

# 做相加（亮度提升1，使得椒盐噪声不影响spot筛选）
imp_add = ImageCalculator.run(imp_sub, imp_binary_1, "Add create stack")
imp_add.show()

# 关闭无关窗口
imp_binary_1.changes = False
imp_binary_1.close()
imp_sub.changes = False
imp_sub.close()

# 做相减（使得黑洞范围扩大，有利于筛选spot）
imp_add_sub = ImageCalculator.run(imp_add, imp_binary_2, "Substract create stack")
imp_add_sub.show()

# 关闭无关窗口
imp_binary_2.changes = False
imp_binary_2.close()
imp_add.changes = False
imp_add.close()

preAVI_path = output + "\\" + patient + "-PRE_AVI"
if os.path.exists(preAVI_path) == False:
    os.mkdir(preAVI_path)

preAVI_name = patient + group + time

imp_path = preAVI_path + "\\" + preAVI_name + '.tif' 

imp_add_sub.setDisplayRange(contrast_min, contrast_max)
imp_add_sub.updateAndDraw()
IJ.saveAs(imp_add_sub, "Tiff", imp_path)

# imp_add_sub.changes = False
# imp_add_sub.close()
'''