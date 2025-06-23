import json
import os
import re
import csv
import math


def csv_manager(path_dict, num_1, num_2, frame_num):
    """
    (Function)

    Args:
        path_dict:
        num_1:
        num_2:
        frame_num:

    """

    patient = path_dict["patient"]
    name = path_dict["group"]
    time = path_dict["time"]
    output = path_dict["output"]

    num = int((num_1 + num_2) / frame_num)
    num_1 = int(num_1 / frame_num)
    num_2 = int(num_2 / frame_num)

    print("long_bac:" + str(num_1) + "  normal_bac:" + str(num_2) + "  total_bac:" + str(num))

    # 建立空数据链表
    data_list = []
    data_head = []

    # 建立路径
    csv_path = output + "\\" + patient + "-CSV"
    if not os.path.exists(csv_path):
        os.mkdir(csv_path)
    csv_file = csv_path + "\\" + patient + ".csv"

    # 若已有文件，读原数据
    if os.path.exists(csv_file):
        with open(csv_file, "rt") as f:
            # 建立原数据列表
            data_lib = csv.DictReader(f)
            for row in data_lib:
                data_list.append(row)
        if len(data_list) != 0:
            data_head.extend(data_list[0])
    # 若没有文件，设立初值
    else:
        data_head.append("Group")

    # 若为新时间点，先添加列
    if time not in data_head:
        data_head.append(time)
        for row in data_list:
            row[time] = ""

    # 匹配组别
    find_row = False
    for i in range(len(data_list)):
        if name == data_list[i]["Group"]:
            data_list[i][time] = num
            find_row = True

    # 若为新组，增加该组
    if not find_row:
        new_row = {}
        for col in data_head:
            new_row[col] = ""
        new_row["Group"] = name
        new_row[time] = num
        data_list.append(new_row)

    # 为表头排序
    data_head.remove("Group")
    def time_str2num(str_num):
        time_num = float("inf")
        time_num_list = re.findall(r'\d+', str_num)
        if len(time_num_list) > 0:
            time_num = int(time_num_list[0])
        return time_num
    data_head.sort(key=lambda str_num: time_str2num(str_num))
    data_head.insert(0, "Group")

    # 写入csv
    with open(csv_file, "wt") as f:
        writer = csv.DictWriter(f, fieldnames=data_head, lineterminator='\n')
        writer.writeheader()
        writer.writerows(data_list)
    return


def id_csv_output(path_dict, data_dict, ID_data_list):

    ID_data_list = json.loads(str(ID_data_list))

    if ID_data_list == False:
        print("csv outputer: no rechoose done")
        return

    if len(ID_data_list) == 0:
        print("csv outputer: no spot found")
        return

    # 路径
    time = path_dict["time"]
    name = path_dict["group"]
    patient = path_dict["patient"]
    output = path_dict["output"]

    # 建立路径
    csv_path = output + "\\" + patient + "-ID_SPOT_CSV"
    if not os.path.exists(csv_path):
        os.mkdir(csv_path)
    csv_file = csv_path + "\\" + name + "-" + time +  "_id_spot.csv"

    writeheader = list(ID_data_list[0].keys())
    writeheader.remove("TRACK_ID")
    writeheader.remove("FRAME")
    writeheader = ["TRACK_ID", "FRAME"] + writeheader

    with open(csv_file, "wt") as f:
        writer = csv.DictWriter(f, fieldnames=writeheader, lineterminator='\n')
        writer.writeheader()
        for line in ID_data_list:
            writer.writerow(line)

    track_dict = {}
    for spot in ID_data_list:
        track_id = spot["TRACK_ID"]
        if not track_id in track_dict.keys():
            track_dict[track_id] = []
        track_dict[track_id].append(spot)

    window_len_1 = int(data_dict["smooth_window_len_1"])
    window_len_2 = int(data_dict["smooth_window_len_2"])
    window_len_3 = int(data_dict["smooth_window_len_3"])
    all_window_1 = window_len_1 * 2 + 1
    all_window_2 = window_len_2 * 2 + 1
    all_window_3 = window_len_3 * 2 + 1

    tolerance_1 = float(data_dict["shine_tolerance_1"])
    tolerance_2 = float(data_dict["shine_tolerance_2"])
    tolerance_3 = float(data_dict["shine_tolerance_3"])

    track_data_list = []
    for track_id, spot_list in track_dict.items():

        spot_num = len(spot_list)

        MEAN_mean_I = 0
        MEAN_max_I = 0
        MEAN_sum_I = 0
        MEAN_perim = 0

        STD_mean_I = 0
        STD_max_I = 0
        STD_sum_I = 0
        STD_perim = 0

        spot_mean_location_1 = []
        spot_mean_location_2 = []
        spot_mean_location_3 = []

        index = 0
        for spot in spot_list:
            single_mean_I = spot["MEAN"]
            single_max_I = spot["MAX"]
            single_sum_I = spot["SUM"]
            single_perim = spot["PERIM"]

            MEAN_mean_I += single_mean_I
            MEAN_max_I += single_max_I
            MEAN_sum_I += single_sum_I
            MEAN_perim += single_perim

            if index >= window_len_1 and index < spot_num - window_len_1:
                mean_x_1 = 0
                mean_y_1 = 0
                for i in range(-window_len_1 + index, window_len_1 + 1 + index):
                    mean_x_1 += spot_list[i]["X"]
                    mean_y_1 += spot_list[i]["Y"]
                mean_x_1 = mean_x_1 / all_window_1
                mean_y_1 = mean_y_1 / all_window_1
                spot_mean_location_1.append([mean_x_1, mean_y_1])

            if index >= window_len_2 and index < spot_num - window_len_2:
                mean_x_2 = 0
                mean_y_2 = 0
                for i in range(-window_len_2 + index, window_len_2 + 1 + index):
                    mean_x_2 += spot_list[i]["X"]
                    mean_y_2 += spot_list[i]["Y"]
                mean_x_2 = mean_x_2 / all_window_2
                mean_y_2 = mean_y_2 / all_window_2
                spot_mean_location_2.append([mean_x_2, mean_y_2])

            if index >= window_len_3 and index < spot_num - window_len_3:
                mean_x_3 = 0
                mean_y_3 = 0
                for i in range(-window_len_3 + index, window_len_3 + 1 + index):
                    mean_x_3 += spot_list[i]["X"]
                    mean_y_3 += spot_list[i]["Y"]
                mean_x_3 = mean_x_3 / all_window_3
                mean_y_3 = mean_y_3 / all_window_3
                spot_mean_location_3.append([mean_x_3, mean_y_3])

            index += 1

        MEAN_mean_I = MEAN_mean_I / spot_num
        MEAN_max_I = MEAN_max_I / spot_num
        MEAN_sum_I = MEAN_sum_I / spot_num
        MEAN_perim = MEAN_perim / spot_num

        activity_1 = 0
        activity_2 = 0
        activity_3 = 0

        shine_sum_frequency_1 = 0
        shine_sum_frequency_2 = 0
        shine_sum_frequency_3 = 0

        change_sum_direction_1 = None
        change_sum_direction_2 = None
        change_sum_direction_3 = None

        last_sum_I_1 = 0
        last_sum_I_2 = 0
        last_sum_I_3 = 0

        degree_1 = 0
        degree_2 = 0
        degree_3 = 0

        index = 0
        for spot in spot_list:
            single_mean_I = spot["MEAN"]
            single_max_I = spot["MAX"]
            single_sum_I = spot["SUM"]
            single_perim = spot["PERIM"]

            STD_mean_I += (single_mean_I - MEAN_mean_I) ** 2
            STD_max_I += (single_max_I - MEAN_max_I) ** 2
            STD_sum_I += (single_sum_I - MEAN_sum_I) ** 2
            STD_perim += (single_perim - MEAN_perim) ** 2

            if index >= window_len_1 and index < spot_num - window_len_1:
                delta_x_1 = spot["X"] - spot_mean_location_1[index - window_len_1][0]
                delta_y_1 = spot["Y"] - spot_mean_location_1[index - window_len_1][1]
                delta_location_1 = math.sqrt(delta_x_1 ** 2 + delta_y_1 ** 2)
                activity_1 += delta_location_1

            if index >= window_len_1 + 2 and index < spot_num - window_len_1:
                xA_1 = spot_mean_location_1[index - window_len_1 - 1][0] - spot_mean_location_1[index - window_len_1 - 2][0]
                yA_1 = spot_mean_location_1[index - window_len_1 - 1][1] - spot_mean_location_1[index - window_len_1 - 2][1]
                xB_1 = spot_mean_location_1[index - window_len_1][0] - spot_mean_location_1[index - window_len_1 - 1][0]
                yB_1 = spot_mean_location_1[index - window_len_1][1] - spot_mean_location_1[index - window_len_1 - 1][1]
                AB_1 = xA_1 * xB_1 + yA_1 * yB_1
                A_1 = math.sqrt(xA_1 ** 2 + yA_1 ** 2)
                B_1 = math.sqrt(xB_1 ** 2 + yB_1 ** 2)
                if (A_1 * B_1) == 0:
                    local_degree_1 = 0
                else:
                    cosAB_1 = AB_1 / (A_1 * B_1)
                    cosAB_1 = max(min(cosAB_1, 1.0), -1.0)
                    local_degree_1 = math.acos(cosAB_1) * 180 / math.pi
                degree_1 += local_degree_1

            if index >= window_len_2 and index < spot_num - window_len_2:
                delta_x_2 = spot["X"] - spot_mean_location_2[index - window_len_2][0]
                delta_y_2 = spot["Y"] - spot_mean_location_2[index - window_len_2][1]
                delta_location_2 = math.sqrt(delta_x_2 ** 2 + delta_y_2 ** 2)
                activity_2 += delta_location_2

            if index >= window_len_2 + 2 and index < spot_num - window_len_2:
                xA_2 = spot_mean_location_2[index - window_len_2 - 1][0] - spot_mean_location_2[index - window_len_2 - 2][0]
                yA_2 = spot_mean_location_2[index - window_len_2 - 1][1] - spot_mean_location_2[index - window_len_2 - 2][1]
                xB_2 = spot_mean_location_2[index - window_len_2][0] - spot_mean_location_2[index - window_len_2 - 1][0]
                yB_2 = spot_mean_location_2[index - window_len_2][1] - spot_mean_location_2[index - window_len_2 - 1][1]
                AB_2 = xA_2 * xB_2 + yA_2 * yB_2
                A_2 = math.sqrt(xA_2 ** 2 + yA_2 ** 2)
                B_2 = math.sqrt(xB_2 ** 2 + yB_2 ** 2)
                if (A_2 * B_2) == 0:
                    local_degree_2 = 0
                else:
                    cosAB_2 = AB_2 / (A_2 * B_2)
                    cosAB_2 = max(min(cosAB_2, 1.0), -1.0)
                    local_degree_2 = math.acos(cosAB_2) * 180 / math.pi
                degree_2 += local_degree_2

            if index >= window_len_3 and index < spot_num - window_len_3:
                delta_x_3 = spot["X"] - spot_mean_location_3[index - window_len_3][0]
                delta_y_3 = spot["Y"] - spot_mean_location_3[index - window_len_3][1]
                delta_location_3 = math.sqrt(delta_x_3 ** 2 + delta_y_3 ** 2)
                activity_3 += delta_location_3

            if index >= window_len_3 + 2 and index < spot_num - window_len_3:
                xA_3 = spot_mean_location_3[index - window_len_3 - 1][0] - spot_mean_location_3[index - window_len_3 - 2][0]
                yA_3 = spot_mean_location_3[index - window_len_3 - 1][1] - spot_mean_location_3[index - window_len_3 - 2][1]
                xB_3 = spot_mean_location_3[index - window_len_3][0] - spot_mean_location_3[index - window_len_3 - 1][0]
                yB_3 = spot_mean_location_3[index - window_len_3][1] - spot_mean_location_3[index - window_len_3 - 1][1]
                AB_3 = xA_3 * xB_3 + yA_3 * yB_3
                A_3 = math.sqrt(xA_3 ** 2 + yA_3 ** 2)
                B_3 = math.sqrt(xB_3 ** 2 + yB_3 ** 2)
                if (A_3 * B_3) == 0:
                    local_degree_3 = 0
                else:
                    cosAB_3 = AB_3 / (A_3 * B_3)
                    cosAB_3 = max(min(cosAB_3, 1.0), -1.0)
                    local_degree_3 = math.acos(cosAB_3) * 180 / math.pi
                degree_3 += local_degree_3

            if index > 0:
                if abs(single_sum_I - last_sum_I_1) > tolerance_1:
                    if single_sum_I > last_sum_I_1 and (change_sum_direction_1 == False or change_sum_direction_1 == None):
                        change_sum_direction_1 = True
                        shine_sum_frequency_1 += 1
                    elif single_sum_I > last_sum_I_1 and (change_sum_direction_1 == True or change_sum_direction_1 == None):
                        change_sum_direction_1 = False
                        shine_sum_frequency_1 += 1
                    last_sum_I_1 = single_sum_I
                if abs(single_sum_I - last_sum_I_2) > tolerance_2:
                    if single_sum_I > last_sum_I_2 and (change_sum_direction_2 == False or change_sum_direction_2 == None):
                        change_sum_direction_2 = True
                        shine_sum_frequency_2 += 1
                    elif single_sum_I > last_sum_I_2 and (change_sum_direction_2 == True or change_sum_direction_2 == None):
                        change_sum_direction_2 = False
                        shine_sum_frequency_2 += 1
                    last_sum_I_2 = single_sum_I
                if abs(single_sum_I - last_sum_I_3) > tolerance_3:
                    if single_sum_I > last_sum_I_3 and (change_sum_direction_3 == False or change_sum_direction_3 == None):
                        change_sum_direction_3 = True
                        shine_sum_frequency_3 += 1
                    elif single_sum_I > last_sum_I_3 and (change_sum_direction_3 == True or change_sum_direction_2 == None):
                        change_sum_direction_3 = False
                        shine_sum_frequency_3 += 1
                    last_sum_I_3 = single_sum_I

            else:
                last_sum_I_1 = single_sum_I
                last_sum_I_2 = single_sum_I
                last_sum_I_3 = single_sum_I

            index += 1

        STD_mean_I = math.sqrt(STD_mean_I / spot_num)
        STD_max_I = math.sqrt(STD_max_I / spot_num)
        STD_sum_I = math.sqrt(STD_sum_I / spot_num)
        STD_perim = math.sqrt(STD_perim / spot_num)

        shine_sum_frequency_1 = float(shine_sum_frequency_1) / spot_num
        shine_sum_frequency_2 = float(shine_sum_frequency_2) / spot_num
        shine_sum_frequency_3 = float(shine_sum_frequency_3) / spot_num

        if spot_num >= all_window_1 + 2:
            activity_1 = activity_1 / (spot_num - window_len_1 * 2)
            degree_1 = degree_1 / (spot_num - window_len_1 * 2 - 2)
        else:
            activity_1 = 0
            degree_1 = 0
        if spot_num >= all_window_2 + 2:
            activity_2 = activity_2 / (spot_num - window_len_2 * 2)
            degree_2 = degree_2 / (spot_num - window_len_2 * 2 - 2)
        else:
            activity_2 = 0
            degree_2 = 0
        if spot_num >= all_window_3 + 2:
            activity_3 = activity_3 / (spot_num - window_len_3 * 2)
            degree_3 = degree_3 / (spot_num - window_len_3 * 2 - 2)
        else:
            activity_3 = 0
            degree_3 = 0

        track_data_dict = {
            "TRACK_ID": track_id,
            "SPOT_NUM": spot_num,

            "MEAN_MEAN_INTENSITY": MEAN_mean_I,
            "MEAN_MAX_INTENSITY": MEAN_max_I,
            "MEAN_SUM_INTENSITY": MEAN_sum_I,
            "MEAN_PERIM": MEAN_perim,

            "STD_MEAN_INTENSITY": STD_mean_I,
            "STD_MAX_INTENSITY": STD_max_I,
            "STD_SUM_INTENSITY": STD_sum_I,
            "STD_PERIM": STD_perim,

            "ACTIVITY_1": activity_1,
            "ACTIVITY_2": activity_2,
            "ACTIVITY_3": activity_3,

            "DEGREE_1": degree_1,
            "DEGREE_2": degree_2,
            "DEGREE_3": degree_3,

            "SHINE_SUM_FREQUENCY_1": shine_sum_frequency_1,
            "SHINE_SUM_FREQUENCY_2": shine_sum_frequency_2,
            "SHINE_SUM_FREQUENCY_3": shine_sum_frequency_3,
        }

        track_data_list.append(track_data_dict)

    # 建立路径
    csv_path = output + "\\" + patient + "-ID_TRACK_CSV"
    if os.path.exists(csv_path) == False:
        os.mkdir(csv_path)
    csv_file = csv_path + "\\" + name + "-" + time + "_id_track.csv"

    writeheader = ["TRACK_ID",
                   "SPOT_NUM",

                   "MEAN_MEAN_INTENSITY",
                   "MEAN_MAX_INTENSITY",
                   "MEAN_SUM_INTENSITY",
                   "MEAN_PERIM",

                   "STD_MEAN_INTENSITY",
                   "STD_MAX_INTENSITY",
                   "STD_SUM_INTENSITY",
                   "STD_PERIM",

                   "ACTIVITY_1",
                   "ACTIVITY_2",
                   "ACTIVITY_3",

                   "DEGREE_1",
                   "DEGREE_2",
                   "DEGREE_3",

                   "SHINE_SUM_FREQUENCY_1",
                   "SHINE_SUM_FREQUENCY_2",
                   "SHINE_SUM_FREQUENCY_3",
                   ]

    with open(csv_file, "wt") as f:
        writer = csv.DictWriter(f, fieldnames=writeheader, lineterminator='\n')
        writer.writeheader()
        for line in track_data_list:
            writer.writerow(line)

    return
