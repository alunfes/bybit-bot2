from MarketData import MarketData, OneMinData

class NNInputDataGenerator:
    def generate_nn_input_data_limit(self, ac, i):
        #ma divergence
        input_data = np.array(MarketData.ohlc.divergence_scaled.iloc[i]).T.tolist()

        if len(ac.order_serial_list) > 0:
            if ac.getLastOrderSide() == 'buy':
                input_data.append(0)
                input_data.append(1)
                input_data.append(0)
            elif ac.getLastOrderSide() == 'sell':
                input_data.append(0)
                input_data.append(0)
                input_data.append(1)
            else:
                print('Unknown order side! ', ac.order_side[ac.order_serial_list[-1]])
                input_data.append(0)
                input_data.append(0)
                input_data.append(0)
        else:
            input_data.append(0)
            input_data.append(0)
            input_data.append(0)

        if ac.holding_side =='buy':
            input_data.append(0)
            input_data.append(1)
            input_data.append(0)
        elif ac.holding_side =='sell':
            input_data.append(0)
            input_data.append(0)
            input_data.append(1)
        else:
            input_data.append(1)
            input_data.append(0)
            input_data.append(0)

        #//ac pl, 損益率を2unitにわけて表現する
        if ac.unrealized_pl == 0:
            input_data.append(0)
            input_data.append(0)
        elif ac.unrealized_pl > 0:
            input_data.append( (ac.unrealized_pl / ac.holding_size) / ac.holding_price)
            input_data.append(0)
        else:
            input_data.append(0)
            input_data.append(-1.0 * (ac.unrealized_pl / ac.holding_size) / ac.holding_price)
        
        #holding period
        if ac.holding_period == 0:
            input_data.append(-1)
        else:
            input_data.append(1.0 / ac.holding_period)
        
        #unrealized pl / holding period
        if ac.holding_period ==0:
            input_data.append(0)
        else:
            input_data.append(ac.unrealized_pl / ac.holding_period)
        
        #holding size
        if ac.holding_size == 0:
            input_data.append(0)
        else:
            input_data.append(ac.holding_size / 10.0)

        return input_data