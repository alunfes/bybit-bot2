import numpy as np

class NN:
    def __tanh(self, input_val):
        return np.tanh(input_val)
    
    def __sigmoid(self, input_val):
        return 1.0 / (1.0 + np.exp(-input_val))


    def calc_weights(self, input_vals, chromo, layer_key, activation):
        res = []
        for i in range(len(chromo.weight_gene[layer_key])): # for units
            sum_v = 0
            for j in range(len(input_vals)): #for weight
                sum_v += input_vals[j] * chromo.weight_gene[layer_key][i][j] #weight_gene[layer][input unit][output unit]
            sum_v += chromo.bias_gene[layer_key][i]
            res.append(self.__sigmoid(sum_v) if activation == 0 else self.__tanh(sum_v))
        return res


    def calc_nn(self, input_vals, chromo, activation):
        if np.nan in input_vals:
            print("NN-calcNN: nan in included in input_vals !")
        #input layer
        inputs = self.calc_weights(input_vals, chromo, 0, activation)
        #middle layers
        for i in range(1, len(chromo.weight_gene)-1):#do calc for each layers
            outputs = self.calc_weights(inputs, chromo, i, activation)
            inputs = outputs
        return self.calc_weights(inputs, chromo, len(chromo.weight_gene) - 1, 0)


    def getActivatedUnit(self, output_vals):
        return np.argmax(output_vals)

    '''
    nn_output = "no", "buy", "sell", "cancel", "Market / Limit"
    int[action, order_type]
    order_type: 0-> Market, 1->Limit
    最大出力outputがthreshold以下の場合はnoとして取り扱う
    '''
    def getActivatedUnitLimitMarket(self, output_vals, threshold):
        res = []
        maxv = 0.0
        max_ind = -1
        for i in range(len(output_vals)-1):
            if maxv < output_vals[i]:
                maxv = output_vals[i]
                max_ind = i
        if max_ind < 0:
            print("NN-getActivatedUnit: Invalid output val !")
        if output_vals[max_ind] < threshold:
            max_ind = 0
        res.append(max_ind)
        #order type
        otype = 0 if output_vals[-1] >= 0.5 else 1
        res.append(otype)
        return res

    def getActivatedUnitLimitMarket2(self, output_vals, threshold):
        res = []
        fired_units = []
        for i in range(len(output_vals)-1):
            if output_vals[i] >= threshold:
                fired_units.append(i)
        if len(fired_units) == 2 and 0 in fired_units and 3 in fired_units: #no / cancelが同時に発火した場合はcancelとして取り扱う
            res.append(3)
        elif len(fired_units) > 1 or len(fired_units) == 0:
            res.append(0)
        elif len(fired_units) == 1:
            res.append(fired_units[0])
        else:
            print('Unknown fired units !')
            res.append(0)
        #order type
        otype = 0 if output_vals[-1] >= 0.5 else 1
        res.append(otype)
        return res