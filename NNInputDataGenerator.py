import numpy as np
from SimAccount import SimAccount


class NNInputDataGenerator:
    def generate_nn_input_data_limit_bot(self, divergence_scaled, order_data, holding_data, performance_data):
        #ma divergence
        input_data = np.array(divergence_scaled).T.tolist()

        if order_data['side'] != '':
            if order_data['side'] == 'buy':
                input_data.append(0)
                input_data.append(1)
                input_data.append(0)
            elif order_data['side'] == 'sell':
                input_data.append(0)
                input_data.append(0)
                input_data.append(1)
            else:
                print('Unknown order side! ', order_data['side'])
                input_data.append(0)
                input_data.append(0)
                input_data.append(0)
        else:
            input_data.append(0)
            input_data.append(0)
            input_data.append(0)

        if holding_data['side'] =='buy':
            input_data.append(0)
            input_data.append(1)
            input_data.append(0)
        elif holding_data['side'] =='sell':
            input_data.append(0)
            input_data.append(0)
            input_data.append(1)
        else:
            input_data.append(1)
            input_data.append(0)
            input_data.append(0)

        #//ac pl, 損益率を2unitにわけて表現する
        if performance_data['unrealized_pl'] == 0:
            input_data.append(0)
            input_data.append(0)
        elif performance_data['unrealized_pl'] > 0:
            input_data.append( (performance_data['unrealized_pl'] / holding_data['size']) / holding_data['price'])
            input_data.append(0)
        else:
            input_data.append(0)
            input_data.append(-1.0 * (performance_data['unrealized_pl'] / holding_data['size']) / holding_data['price'])
        
        #holding period
        if holding_data['period'] == 0:
            input_data.append(-1)
        else:
            input_data.append(1.0 / holding_data['period'])
        
        #unrealized pl / holding period
        if holding_data['period'] ==0:
            input_data.append(0)
        else:
            input_data.append(performance_data['unrealized_pl'] / holding_data['period'])
        return input_data
    
    
    def generate_nn_input_data_limit_sim(self, divergence_scaled, vola_kyori_scaled):
        holding_data = SimAccount.get_holding_data()
        performance_data = SimAccount.get_performance_data()

        #ma divergence
        input_data = np.array(divergence_scaled).T.tolist()

        #vola kyori
        input_data.extend(np.array(vola_kyori_scaled).T.tolist())

        #order side
        if SimAccount.getNumOrders() > 0:
            if SimAccount.getLastOrderSide() == 'buy':
                input_data.append(1)
                input_data.append(0)
            elif SimAccount.getLastOrderSide() == 'sell':
                input_data.append(0)
                input_data.append(1)
            else:
                print('Unknown order side! ', SimAccount.getLastOrderSide())
                input_data.append(0)
                input_data.append(0)
        else:
            input_data.append(0)
            input_data.append(0)

        #holding side
        if holding_data['side'] =='buy':
            input_data.append(1)
            input_data.append(0)
        elif holding_data['side'] =='sell':
            input_data.append(0)
            input_data.append(1)
        else:
            input_data.append(0)
            input_data.append(0)

        #//ac pl, 損益率を2unitにわけて表現する
        if performance_data['unrealized_pl'] == 0:
            input_data.append(0)
        else:
            input_data.append((performance_data['unrealized_pl'] / holding_data['size']) / holding_data['price'])
        
        #holding period
        if holding_data['period'] == 0:
            input_data.append(1.0)
        else:
            input_data.append(1.0 / holding_data['period'])
        
        #unrealized pl / holding period
        if holding_data['period'] ==0:
            input_data.append(0)
        else:
            input_data.append(performance_data['unrealized_pl'] / holding_data['period'])
        return input_data