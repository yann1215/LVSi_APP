script_subLongbac = r'''
#@output imp
#@ ij.ImagePlus (required=false) original_binary_imp
#@ int total_frame_spots_num
#@ ij.ImagePlus original_imp
#@ int WL_close_iteration
#@ int WL_close_count
#@ int WL_dilate_iteration
#@ int WL_dilate_count
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

if original_binary_imp == None and total_frame_spots_num == 0:
    imp = original_imp
else:
    binary_imp = original_binary_imp.duplicate()
    
    # 将二值化图像除椒盐噪声，除黑点，除白点
    IJ.run(binary_imp, "Options...", "iterations=" + str(WL_close_iteration) + " count=" + str(
        WL_close_count) + " black do=Close stack")
    
    IJ.run(binary_imp, "Options...", "iterations=" + str(WL_dilate_iteration) + " count=" + str(
        WL_dilate_count) + " black do=Dilate stack")
    
    # 获取所认为长细菌的其余区域，用于在trackmate检测（因为不排除长短细菌混合的情况）
    imp_without = ImageCalculator.run(original_imp, binary_imp, "Substract create stack")
    
    imp_without.show()
    
    original_imp.changes = False
    original_imp.close()
    
    binary_imp.changes = False
    binary_imp.close()
    
    imp = imp_without
'''