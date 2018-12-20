import pdf_tabular
import pdfminer
"""pip3 install pdfminer-3k"""
import matplotlib.pyplot as plt
from matplotlib import patches 
import os
path = '/home/pengfei/TransDataBase/PDF试验/Schedule.pdf'

for page_number in range(202,203):
    out_Path = '/home/pengfei/TransDataBase/PDF试验/输出/11号/'+str(page_number)+'/'  # 生成输出文件夹 

    current_page = pdf_tabular.extract_layout_by_page(path, page_number)
    dfs = pdf_tabular.page_to_tables(current_page)
    pdf_tabular.dfs_to_excels(dfs,out_Path, page_number)
"""
page_number = 578
LTTexts = []
LTRects = []
LTLines = []
LTCurves = []
current_page = pdf_tabular.extract_layout_by_page(path, page_number)
# 将文本和rectangle元素分开
for e in current_page:
    if isinstance(e, pdfminer.layout.LTTextBoxHorizontal):
        LTTexts.append(e)
    elif isinstance(e, pdfminer.layout.LTRect):
        LTRects.append(e)
    elif isinstance(e, pdfminer.layout.LTLine):
        LTLines.append(e)
    elif isinstance(e, pdfminer.layout.LTCurve):
        LTCurves.append(e)
        
lines = [pdf_tabular.cast_as_line(r) for r in LTRects 
         if (pdf_tabular.width(r) < 2 and pdf_tabular.area(r) > 1) or pdf_tabular.length(r)> 100]
Textlines = []
for i in LTTexts:
    for e in i:
        if isinstance(e, pdfminer.layout.LTTextLine):
            Textlines.append(e)
contents = []
for text in Textlines:
    contents.append(text.get_text())
    
dic_groups = pdf_tabular.page_to_groups(Textlines,lines)

k = sorted(list(dic_groups.keys()),reverse = True)[-2]
columns, start_poses,signs = pdf_tabular.group_to_columns(dic_groups[k], k)
# 尝试构造一个表格
if len(start_poses)>=2:   # 至少被标识了一个起始位置和一个结束位置
    for i in range(0,1):#(len(start_poses)-1):
        df = pdf_tabular.columns_to_table(columns,start_poses[i],start_poses[i+1],sign=0)

# 画图
new_columns = []
for pdfcolumn in columns:
    new_columns.append(pdfcolumn.cells)
columns = new_columns

xmin, ymin, xmax, ymax = current_page.bbox
size = 10

fig, ax = plt.subplots(figsize = (size, size * (ymax/xmax)))

for l in lines:
    x0,y0,x1,y1,_ = l
    plt.plot([x0, x1], [y0, y1], 'k-')
'''
for l in LTRects:
    pdf_tabular.draw_rect(l, ax)
'''  
for key_group in dic_groups:
    for c in dic_groups[key_group]:
        pdf_tabular.draw_rect(c, ax, "red")

for r in dic_groups[k]: 
    pdf_tabular.draw_rect(r, ax, "green")

for r in columns[0]:
    pdf_tabular.draw_rect(r, ax, "blue")

plt.xlim(xmin, xmax)
plt.ylim(ymin, ymax)
plt.show()
"""