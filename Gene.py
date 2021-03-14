import pandas as pd
import numpy as np
import csv
from RandomGenerator import RandomGenerator


class Gene:
    def __init__(self, units, index):
        self.weight_gene = [] #weight_gene[layer][output unit][input unit] -> [<inputs units id as key, double[num middle units-1]>, <middle units id as key, double[num middle units-2>, ..]
        self.bias_gene = [] #bias_gene[layer][output unit]  ->  [num_unit[1], num_unit[2], .. num_unit[num_layers - 1]]
        self.num_units = units
        self.num_index = index
        for i in range(1,len(units)): #for layers
            weight = {}
            for j in range(units[i]): #for units in a layer
                weight[j] = RandomGenerator.getRandomArray(units[i - 1])
            self.weight_gene.append(weight)
            gene = RandomGenerator.getRandomArray(units[i])
            self.bias_gene.append(gene)

    
    def readWeigth(self, file_name):
        f = open(file_name)
        reader = csv.reader(f)
        units = []
        index = []
        bias = []
        layer_id_list = []
        weights = []
        for row in reader:
            if 'units' in ','.join(row):
                units = list(map(int, row[1:]))
            elif 'index' in ','.join(row):
                index = list(map(int, row[1:]))
            elif 'bias' in ','.join(row):
                bias.append(list(map(float, row[1:])))
            elif 'weight' in ','.join(row): #weight:0:0,-0.369,0.9373   -> weight:layer:unit
                weight = list(map(float, row[1:]))
                layer_id = int(row[0].split(':')[1])
                unit_id = int(row[0].split(':')[2])
                dic = {unit_id:weight}
                if layer_id in layer_id_list:
                    weights[layer_id][unit_id] = weight
                else:
                    weights.append(dic)
                layer_id_list.append(layer_id)
        self.bias_gene = bias
        self.weight_gene = weights
        self.num_units = units
        self.num_index = index
        
