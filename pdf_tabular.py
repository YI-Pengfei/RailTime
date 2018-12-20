from __future__ import division

import math
from bisect import bisect_left # 排序/查找用到的
import pdfminer
import os
import re
"""
line_overlap=0.3, char_margin=3, line_margin=0.01, word_margin=0.3
这时候没有被误分开的单元格，但有被误合并的单元格，无需合并单元格，只需考虑合并列
*****************以没有单元格被错误拆分为前提***************************
"""
from collections import defaultdict

import matplotlib.pyplot as plt
from matplotlib import patches 
import pandas as pd

from pdfminer.pdfparser import PDFParser,PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTTextBoxHorizontal, LAParams,LTTextBox, LTTextLine, LTRect, LTFigure, LTImage
from pdfminer.pdfinterp import PDFTextExtractionNotAllowed

from special_chars import SPECIAL_CHARS

TEXT_ELEMENTS = [
    pdfminer.layout.LTTextBox,
    pdfminer.layout.LTTextBoxHorizontal,
    pdfminer.layout.LTTextLine,
    pdfminer.layout.LTTextLineHorizontal
]


class PDFCell:
    """
    一个单元格
    """
    def __init__(self, lt_Object):
        self.text = lt_Object.get_text().strip('\n').strip(' ')
        self.lt_obj = lt_Object  # 保留LTTextLine对象，用于后续可能的用途
        self.bbox = lt_Object.bbox
        if self.text.endswith('a.') or self.text.endswith('d.'):
            self.role = 's_name'
        else:
            self.role = 'other'
        self.center = ((self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2)  # 中心
    
    def get_text(self):
        return self.text
    
    def overlap_with(self, other_cell, line_overlap = 0.5):
        #  是否与另一个单元格重叠
        # obj0 and obj1 is horizontally aligned:
        #
        #   +------+ - -
        #   |cell0 | - +------+   -
        #   |      |   | ell1 |   | (line_overlap)
        #   +------+ - |      |   -
        #          - - +------+
        #    
        y_top = min(self.bbox[3], other_cell.bbox[3])
        y_bottom = max(self.bbox[1], other_cell.bbox[1])
        if y_top - y_bottom >= line_overlap * (self.bbox[3] - self.bbox[1]) or \
                y_top - y_bottom >= line_overlap * (other_cell.bbox[3] - other_cell.bbox[1]):
            return True
        else:
            return False        
    # 没加入单元格间合并的函数
    #


class PDFColumn:
    """
    一列，包括一组pdfcell对象，列的bbox，以及角色
    """
    def __init__(self):
        self.cells = []
        self.bbox = (1000, 1000, 0, 0)
        
    def add_cell(self, pdfcell):
        # 添加单元格
        self.bbox = (min(self.bbox[0], pdfcell.bbox[0]),
                     min(self.bbox[1], pdfcell.bbox[1]),
                     max(self.bbox[2], pdfcell.bbox[2]),
                     max(self.bbox[3], pdfcell.bbox[3]),
                     )  
        self.cells.append(pdfcell)
        # 加入排序功能，使之变得有序
        # 

    def does_it_is_names(self):
        count = 0
        for c in self.cells:
            if c.role == 's_name':
                count += 1
        if count >= 2:
            return True
        else:
            return False  
    
    def does_it_is_DisInfos(self):
        if self.cells[0].get_text() == 'km':
            return True
        else:
            return False
        
    def column_overlap_with(self, pdfcolumn, line_overlap=0.8):
        """if it is overlap with another column"""
        #
        #   +-------+
        #   |column0|
        #   |       |
        #   +-------+
        #     |     |
        #     +-------+
        #     |column1|
        #     |       |
        #     +-------+
        #     |<--->|
        #   (line_overlap)        
        x_left = max(self.bbox[0], pdfcolumn.bbox[0])
        x_right = min(self.bbox[2], pdfcolumn.bbox[2])
        if x_right - x_left >= line_overlap * (self.bbox[2] - self.bbox[0]) or \
                x_right - x_left >= line_overlap * (pdfcolumn.bbox[2] - pdfcolumn.bbox[0]):
            return True
        else:
            return False
        
    def column_merge_with(self, pdfcolumn):
        # 更新边界框
        self.bbox = (min(self.bbox[0], pdfcolumn.bbox[0]),
                     min(self.bbox[1], pdfcolumn.bbox[1]),
                     max(self.bbox[2], pdfcolumn.bbox[2]),
                     max(self.bbox[3], pdfcolumn.bbox[3]),
                     )
        # 更新内容，排序
        self.cells += pdfcolumn.cells
        self.cells.sort(key=lambda cell: cell.center[1], reverse=True)        


def extract_layout_by_page(pdf_path, page_number):
    """
    :param pdf_path:  pdf file path
    :param page_number:      the specific page that you want to parse(start from 1)
    :return: a list of pdfminer layout object
    """
    fp = open(pdf_path, 'rb') # 以二进制读模式打开
    # 用文件对象来创建一个pdf文档分析器
    praser = PDFParser(fp)  # 创建一个PDF文档
    doc = PDFDocument()  # 连接分析器 与文档对象
    praser.set_document(doc)
    doc.set_parser(praser)

    doc.initialize()
    # 检测文档是否提供txt转换，不提供就忽略
    if not doc.is_extractable:
        raise PDFTextExtractionNotAllowed
    # 创建PDf 资源管理器 来管理共享资源
    rsrcmgr = PDFResourceManager()  # 创建一个PDF设备对象
    laparams = LAParams()
    laparams.line_overlap = 0.3
    laparams.char_margin = 3
    laparams.word_margin = 0.3
    laparams.line_margin=0.01
    
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)  # 创建一个PDF解释器对象
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    
    layouts = []
    # 循环遍历列表，每次处理一个page的内容
    pages = list(doc.get_pages())

    interpreter.process_page(pages[page_number-1])
    # 接受该页面的LTPage对象
    return device.get_result()


def page_to_tables(page_layout):
    """
    extract the tables from a pdf page
    """
    lt_TextBoxes = []
    lt_Rects = []
    
    for e in page_layout:
        if isinstance(e, pdfminer.layout.LTTextBoxHorizontal):
            lt_TextBoxes.append(e)
        elif isinstance(e, pdfminer.layout.LTRect):
            lt_Rects.append(e) 
    # get all the LTTextLines         
    lt_TextLines = []
    for textbox in lt_TextBoxes:
        for e in textbox:
            if isinstance(e, pdfminer.layout.LTTextLine):
                lt_TextLines.append(e)
    # transform rectangles into lines
    lines = [cast_as_line(r) for r in lt_Rects 
             if (width(r) < 2 and area(r) > 1) or length(r) > 100]
    h_lines = [(l[0], l[1], l[2], l[3]) for l in lines if l[4] == 'H']  # Horizontal line
    # split one page into several groups
    dic_groups = page_to_groups(lt_TextLines, h_lines)
    # sort dictionaries
    sorted_keys = sorted(list(dic_groups.keys()), reverse=True) # 对字典由上到下排序
    # process each group
    dfs = []
    for k in sorted_keys:
        if len(dic_groups[k]) < 4:
            continue
        else:
            columns, start_indexes, signs = group_to_columns(dic_groups[k], k)
        # try to construct tabular structure.
        if len(start_indexes)>=2: # At least one start point and one end point
            for i in range(len(start_indexes)-1):
                if start_indexes[i+1] - start_indexes[i] >=2: # At least two columns
                    df = columns_to_table(columns,start_indexes[i],start_indexes[i+1],signs[i])
                    if not df.empty:
                        dfs.append(df)       
    
    return dfs
 
    
def page_to_groups(lt_TextLines, h_lines):    
    """
    :param lt_TextLines: a list of LTTextLine Objects
    :param h_lines: a list of horizontal line
    :return: a dictionary of "y_bottom:group", LTTextLine Objects are transformed to "Cell" Object
    """
    dic_groups = {}
    old_baseline = (0, 0, 600, 0) # the bottom of the page
    
    for textline in lt_TextLines:
        cur_cell = PDFCell(textline) # convert LTTextLine object to the PDFCell object
        
        new_baseline, temp_dis = find_baseline(textline, h_lines)
        new_y_bottom = new_baseline[1]
        old_y_bottom = old_baseline[1]
        if abs(new_y_bottom - old_y_bottom) < 4: # 4 as a buffer margin
            dic_groups.setdefault(old_y_bottom,[]).append(cur_cell)
        else:
            dic_groups.setdefault(new_y_bottom, []).append(cur_cell)
            old_baseline = new_baseline
    
    return dic_groups


def group_to_columns(group, y_bottom):
    """
    :param group: a list of cells
    :param y_bottom: baseline y coordinate
    :return: columns,
             start-end indexes,
             signs to identify if this table include distance information
    """
    old_center = 1000
    pdfcolumn = PDFColumn()
    out_columns = []
    
    # split the group into several columns
    for cell in group:
        # 简化分列逻辑，比较单元格的中心位置，
        if cell.center[1] - old_center < - 2:  # 2 as a buffer margin
            pdfcolumn.add_cell(cell)
            old_center = cell.center[1]
        else:
            out_columns.append(pdfcolumn)
            pdfcolumn = PDFColumn()
            pdfcolumn.add_cell(cell)
            old_center = cell.center[1]
            
    out_columns.append(pdfcolumn) # the last column
    #return out_columns, [], 0  #########################      
    # sort, merge columns
    # 减掉表头的那部分
    first_pos = -1
    for i in range(len(out_columns)):
        if out_columns[i].does_it_is_DisInfos() and out_columns[i+1].does_it_is_names():
            first_pos = i
            break
        elif out_columns[i].does_it_is_names():
            first_pos = i
            break
    if first_pos != -1:
            cutted_columns = out_columns[first_pos:]
    else:
        return [], [], [] 
    
    # sort
    cutted_columns.sort(key=lambda pdfcolumn: pdfcolumn.bbox[0]+pdfcolumn.bbox[2])
    
    # merge
    final_columns = []
    for pdfcolumn in cutted_columns:
        if final_columns and final_columns[-1].column_overlap_with(pdfcolumn):
            final_columns[-1].column_merge_with(pdfcolumn)
        else:
            final_columns.append(pdfcolumn)
    
    start_indexes = []
    signs = []
    for i in range(len(final_columns)):
        if final_columns[i].does_it_is_names():
            if i == 0: # this table has no distance information
                start_indexes.append(i)
                signs.append(0)
            elif final_columns[i-1].cells[0].get_text() == 'km':  # this table has distance information
                start_indexes.append(i-1)
                signs.append(1)
            else:
                start_indexes.append(i)
                signs.append(0)
                
    start_indexes.append(len(final_columns))
    
    return final_columns, start_indexes, signs


def columns_to_table(columns, start, end, sign):
    """
    :param columns: a list of pdfcolumn
    :param start: one table start index,
    :param end:   one table end index
    :param sign:  0- without distance, 1- with distance
    :return: DataFrame object
    """
    new_columns = []
    for pdfcolumn in columns:
        new_columns.append(pdfcolumn.cells)
    columns = new_columns
    # judge whether it has a distance information
    if sign == 1:
        offset = 1
        schedules = [['km', 'd./a.']]
    else:
        offset = 0
        schedules = [['d./a.']]
    stations = []
    for e in columns[start+offset]:
        if e.role == 's_name':
            stations.append(e)   
    y_top = stations[0].bbox[3]
    y_bottom = stations[-1].bbox[1]  # unused,
    
    # whether it is a meaningless table (take comments as a table by mistake)
    if not stations[0].get_text().endswith('d.'):
        return pd.DataFrame() # return an empty DataFrame
    
    # judge whether it has train type, train number, notes, if so, create header list
    begin = columns[start+offset].index(stations[0])
    if begin == 0:
        schedules[0].append('train info')  # set header aas 'train info' by default
    else:
        header = ''
        for k in columns[start+offset][:begin]:
            header += k.get_text().replace('.', '') + '\n'
        schedules[0].append(header.strip('\n'))
    
    # construct table
    for i in range(len(stations)):
        s = stations[i]
        # clean the city/station name first
        station_name, d_or_a = fix_name(s.get_text())
        # get distance information (if has)
        if offset == 1:
            value, index, dis = find_closest(s, columns[start])
            if s.overlap_with(value):
                dis_info = value.get_text()
            else:
                dis_info = ' '
            schedules.append([dis_info, d_or_a, station_name])
        else:
            schedules.append([d_or_a, station_name])
        # reconstruct rows
        for column in columns[start+offset+1:end]:
            # 若该列只有一个元素，跳过
            if column[-1].bbox[1] > y_top or (len(column) <= 2 and len(column) < len(stations)):
                continue
            # 若全是“...”，跳过
            count = 0
            for c in column:
                if c.get_text() != '...':
                    count += 1
                    break
            if count == 0:
                continue
            
            # reconstruct table body
            value, index, dis = find_closest(s, column)
            if s.overlap_with(value, line_overlap=0.3):
                schedules[-1].append(clean_cell(value.get_text()))   # 单元格的时刻是经过清理的
            # the closest object is not the same row with s, full the cell with ' '
            else: 
                schedules[-1].append(' ')
            
            # reconstruct header
            if i == 0:
                info = ''
                for k in column[:index]:
                    info += k.get_text()+'\n'

                schedules[0].append(info.strip('\n'))
    
    df = pd.DataFrame(schedules)

    return df


def dfs_to_excels(dfs, out_path, page_number):
    for df in dfs:
        if not os.path.exists(out_path):
            os.makedirs(out_path)
        # 存入excel文件中
        for j in range(len(dfs)):
            file_name = str(page_number)+'-'+ str(j) + '.xls'   ###CHANGE OUT FILE PATH HERE
            dfs[j].to_excel(out_path+file_name)    


#  基础的子函数
def find_closest(cell, column):
    """从一个列表中找与给定元素最接近的元素值\位置\及距离"""
    dis = 1000
    for i in range(len(column)):
        k = column[i]
        new_dis = abs(k.center[1]-cell.center[1])
        if new_dis <= dis:
            temp = k
            index = i
            dis = new_dis
        else:
            break
    return temp, index, dis
            
            
def find_baseline(lt_textline, h_lines):
    """
    :param lt_textline: a LTTextLine object
    :param h_lines: a set of horizontal lines
    :return: the nearest line of the LTTextLine object, and the distance
    """
    y_bottom = lt_textline.bbox[1]
    baseline = (0, 0, 600, 0) # the bottom of the page
    min_dis = 1000
    
    for l in h_lines:
        if 0 < y_bottom - l[1] < min_dis:
            x_left = max(l[0],lt_textline.bbox[0])
            x_right = min(l[2],lt_textline.bbox[2])
            if x_right - x_left > 0:
                min_dis = y_bottom - l[1]
                baseline = l
    
    return baseline, min_dis


def draw_rect(rect, ax, color='black'):
    x0 = rect.bbox[0]
    y0 = rect.bbox[1]
    x1 = rect.bbox[2]
    y1 = rect.bbox[3]
    ax.add_patch(patches.Rectangle(
        (x0, y0), x1 - x0, y1 - y0, fill=False, color=color
    ))

        
def width(rect):
    x0, y0, x1, y1 = rect.bbox
    return min(x1 - x0, y1 - y0)


def length(rect):
    x0, y0, x1, y1 = rect.bbox
    return max(x1 - x0, y1 - y0)


def area(rect):
    x0, y0, x1, y1 = rect.bbox
    return (x1 - x0) * (y1 - y0)


def cast_as_line(rect):
    """基于矩形的面积，将某些矩形替换为线段"""
    x0, y0, x1, y1 = rect.bbox

    if x1 - x0 > y1 - y0:
        return (x0, y0, x1, y0, "H")
    else:
        return (x0, y0, x0, y1, "V")


def fix_name(str_name):
    """
    process the city/station name, fix special characters,
    and determine whether it's a departure or arrival station
    :param str_name:
    :return:
    """
    str_name = re.sub(r'([\d]+)', '', str_name)  # remove digit 0~9
    for k in SPECIAL_CHARS:
        if k in str_name:
            str_name = str_name.replace(k, SPECIAL_CHARS[k])

    if str_name.endswith('a.'):
        d_or_a = 'a.'
        name = str_name[:len(str_name)-2].replace('.', '')  # remove 'a.' and then '....'
    elif str_name.endswith('d.'):
        d_or_a = 'd.'
        name = str_name[:len(str_name)-2].replace('.', '')
    else:
        print("Warning! It is not a station..")

    # remove some symbols in the name
    clean_name = ''
    for k in name.split():
        if len(k) > 1 or k.isupper():  # 是我们需要的
            if k.isupper():  # 全是大写，可能是缩写
                clean_name += k + ' '
            else:
                clean_name += re.sub("[A-Z]", lambda x: " " + x.group(0), k) + ' ' # 按大写字母分开
    # remove redundant space

    return ' '.join(clean_name.split()), d_or_a


def clean_cell(cell_str):
    out_str = cell_str
    for s in re.findall(r'[0-9]+', cell_str):  # 处理stop time
        if len(s)==4:
            out_str = s
    return out_str