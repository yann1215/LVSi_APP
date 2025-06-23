script_correct_shake = r'''
#@output toStart
#@output toEnd
#@output update_dict
#@ int frame_step
#@ float shake_binary_threshold
#@ int min_filter_len
#@ int iteration_limit
#@ float iteration_step
#@ float sus_threshold
#@ float shake_threshold
#@ int local_min_len
#@ int LTF_number_spots
#@ int NTF_number_spots
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

IJ.run("Collect Garbage")
IJ.run("Fresh Start")

update_dict = {}
imp = FolderOpener.open(path,  "filter=tif" + " step=" + str(frame_step))
# 只留像素信息 （意义不大）
imp.removeScale()
imp.show()
slice_ = imp.getNSlices()
atLeastLen = (local_min_len + max(LTF_number_spots, NTF_number_spots)) * 2
if slice_ < atLeastLen and slice_ > local_min_len:
    atLeastLen_final = local_min_len + max(LTF_number_spots, NTF_number_spots) + 5
    final_flag = False
    while atLeastLen > atLeastLen_final:
        atLeastLen -= 1
        if atLeastLen < slice_:
            final_flag = True
            break
    if final_flag == False:
        atLeastLen = slice_
        new_num_filter = int((slice_ - local_min_len) / 2)
        update_dict = {
            "LTF_number_spots": str(new_num_filter),
            "NTF_number_spots": str(new_num_filter)
        }
        print("WARNING! too less frame! new num filter is " + str(new_num_filter))
elif slice_ < local_min_len:
    print("ERROR! too less frame! less than " + str(local_min_len))
# imp_min = ZProjector.run(imp, "min")
# 
# imp_sub = ImageCalculator.run(imp, imp_min, "Subtract create stack")
# imp_sub.show()
# 
# imp.changes = False
# imp.close()
# imp_min.changes = False
# imp_min.close()
imp_sub = imp

slice_ = imp_sub.getNSlices()
new_stack = ImageStack(imp_sub.getWidth(), imp_sub.getHeight())
old_stack = imp_sub.getStack()
for i in range(1, slice_):
    ip_1 = old_stack.getProcessor(i)
    imp_1 = ImagePlus('',ip_1)
    ip_2 = old_stack.getProcessor(i+1)
    imp_2 = ImagePlus('',ip_2)
    imp_d = ImageCalculator.run(imp_1, imp_2,
                                #"Subtract create"
                                "Difference create"
                                )
    ip = imp_d.getProcessor()
    new_stack.addSlice(ip)
    imp_d.changes = False
    imp_d.close()
new_imp = ImagePlus(imp.getTitle(), new_stack)
new_imp.show()

IJ.setRawThreshold(new_imp, shake_binary_threshold, 255.0)

IJ.run(new_imp, "Convert to Mask", "background=Dark black create")
imp_binary = IJ.getImage()
imp_binary.show()

new_imp.changes = False
new_imp.close()

rt = ResultsTable.getResultsTable()
rt.reset()
IJ.run(imp_binary, "Measure Stack...", "")
IJ.selectWindow("Results")
rt = ResultsTable.getResultsTable()
meanRT = rt.getColumn("Mean")
rt.reset()

window = WindowManager.getWindow("Results")
window.dispose()

diffMRT = []

# 滤波窗口参数
full_len = min_filter_len
half_len = (full_len-1)/2
for i in range(0,len(meanRT)):
    # 将原数据每一点按前后共5帧进行最小值滤波
    mFlist = []
    start = i - half_len
    end = i + half_len
    if start<0:
        start = 0
        end = full_len - 1
    elif end>len(meanRT)-1:
        start = len(meanRT)-full_len
        end = len(meanRT)-1
    for j in range(start,end+1):
        mFlist.append(meanRT[j])
    arrMFL = ArrayUtil(mFlist)
    diffArr = arrMFL.getMinimum()

    diffMRT.append(meanRT[i]-diffArr)

shakeList = [[1,slice_]]
susList = []

limitLoose = 0 #该参数用于增加鲁棒性。

while limitLoose < iteration_limit: 
    for i in range(0,len(diffMRT)):
        if diffMRT[i] > sus_threshold:
            susList.append(str(i+1)+'-'+str(i+2)) #导数大于0.5处仅【怀疑】存在突变，即抖动处，反应在txt上，不影响图像集切割
        if diffMRT[i] > shake_threshold+limitLoose:
            shakeList[-1][1] = i + 1  #导数大于1+limitLoose处，【认定】该处为突变，即抖动处，将该点作为图像集切割点
            if shakeList[-1][0] == i + 1:
                shakeList[-1] = [i + 2,slice_]
            else:
                shakeList.append([i + 2,slice_])

    lenList = []

    for pieceList in shakeList:  #获取每个突变点之间所占帧数
        lenS = pieceList[1] - pieceList[0] + 1
        lenList.append(lenS)

    arrLL = ArrayUtil(lenList)
    maxArr = arrLL.getMaximum() #取最长者

    if maxArr < atLeastLen:  # 若长度小于后续局部最小值长度，以及trackmate的帧数筛选，则必定无法获得一个spot（图像集长度小于筛选长度，所有spot被筛选完），所以需要放宽标准。
        limitLoose = limitLoose + iteration_step
    else:
        break


chooseToDo = shakeList[lenList.index(maxArr)]
chooseToDo[1] = max(chooseToDo[1], chooseToDo[0] + atLeastLen - 1)

if chooseToDo[0] + atLeastLen - 1 > slice_:
    chooseToDo[1] = slice_
    chooseToDo[0] = slice_ - atLeastLen + 1

print("frame chosen: " + str(chooseToDo))

#路径
txt_path = output + "\\" + patient + "-TXT"
if os.path.exists(txt_path) == False:
    os.mkdir(txt_path)

txt_name = patient + group + time

full_path = txt_path + "\\" + txt_name + '.txt'  # 也可以创建一个.doc的word文档

file = open(full_path, 'w')
file.writelines('limit loose times: '+str(int(limitLoose/0.25))+'\n')

file.writelines(str(susList)+'\n')
file.writelines(str(shakeList)+'\n')
file.writelines(str(chooseToDo)+'\n')

for i in range(0,len(diffMRT)):
    file.writelines(str(meanRT[i])+'   '+str(diffMRT[i])+'   '+str(i+1)+'-'+str(i+2)+'\n') #帧间变化值
file.close()

imp_binary.changes = False
imp_binary.close()

imp_sub.changes = False
imp_sub.close()

IJ.run("Collect Garbage")
IJ.run("Fresh Start")

frame_num = int(chooseToDo[1] - chooseToDo[0] + 1 - local_min_len)
toStart = chooseToDo[0]
toEnd = chooseToDo[1]
'''