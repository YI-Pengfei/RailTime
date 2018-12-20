import osmium as o
import matplotlib.pyplot as plt
from sklearn import neighbors
import numpy as np

class NodeProcessor(o.SimpleHandler):
    """
    提取所有符合标签要求的nodes，以及用于way的成员的nodes
    进数据库
    """

    def __init__(self):
        super(NodeProcessor, self).__init__()
        self.total_n = 0  # 节点计数器
        self.names = []
        self.lons= []
        self.lats = []

    def end(self):
        print("Nodes: ", self.total_n)

    def node(self, n):
        if 'name' or 'name:zh' in n.tags:
            self.total_n += 1
            if 'name:zh' in n.tags:
                self.names.append(n.tags.get('name:zh'))
            else:
                self.names.append(n.tags.get('name'))
            self.lons.append(n.location.lon)
            self.lats.append(n.location.lat)
            
if __name__ == '__main__':
    SourceFile = 'cleased-railway-china.osm.pbf'
    node_handler = NodeProcessor()
    node_handler.apply_file(SourceFile)
    node_handler.end()
    names = node_handler.names
    lons = node_handler.lons
    lats = node_handler.lats
    plt.scatter(lons, lats,s=0.5)  # 绘制散点图
    
    xy=[]
    for i in range(len(lons)):
        xy.append([lons[i],lats[i]])
    xy = np.array(xy) # 7668 points in 2 dimensions
    
    tree = neighbors.KDTree(xy)   
    dist, ind = tree.query(xy[:1], k=3)   
    print(ind)  # 输出三个最近邻的索引
    