import numpy as np

class NN:
    def __tanh(self, input_val):
        return np.tanh(input_val)
    
    def __sigmoid(self, input_val):
        return 1.0 / (1.0 + np.exp(-input_val))

    def calc_nn(self, input_vals, num_units, weight1, weight2, bias1, bias2, activation):
        if (len(input_vals) * num_units[1]) == len(weight1):
            #first weight
            sum_first_outputs = []
            for i in range(num_units[1]):
                sum_v = 0
                for j in range(len(input_vals)):
                    sum_v += input_vals[j] * weight1[i]
                sum_v += bias1[i]
                sum_first_outputs.append(self.__sigmoid(sum_v) if activation == 0 else self.__tanh(sum_v))

            #second weight
            sum_second_outputs = []
            for i in range(num_units[2]):
                sum_v = 0
                for j in range(len(sum_first_outputs)):
                    sum_v += sum_first_outputs[j] * weight2[i]
                sum_v += bias2[i]
                sum_second_outputs.append(self.__sigmoid(sum_v))
            return sum_second_outputs
        else:
            print('# of input vals and units in first layer is not matched!')
            return []

    def getActivatedUnit(self, output_vals):
        return np.argmax(output_vals)