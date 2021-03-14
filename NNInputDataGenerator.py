import numpy as np
from MarketData import MarketData



class NNInputDataGenerator:
    def generate_nn_input_data_limit(self, ac, i, index):
        #ma divergence
        input_data = []
        if index[0] == 1:
            for key in MarketData.ohlc.divergence_scaled.keys():
                input_data.append(MarketData.ohlc.divergence_scaled[key].iloc[i])
        if index[1] == 1:
            for key in MarketData.ohlc.vola_kyori_scaled.keys():
                input_data.append(MarketData.ohlc.vola_kyori_scaled[key].iloc[i])
        if index[2] == 1:
            for key in MarketData.ohlc.vol_ma_divergence_scaled.keys():
                input_data.append(MarketData.ohlc.vol_ma_divergence_scaled[key].iloc[i])
        if index[3] == 1:
            for key in MarketData.ohlc.buysell_vol_ratio_scaled.keys():
                input_data.append(MarketData.ohlc.buysell_vol_ratio_scaled[key].iloc[i])
        if index[4] == 1:
            for key in MarketData.ohlc.rsi_scaled.keys():
                input_data.append(MarketData.ohlc.rsi_scaled[key].iloc[i])
        if index[5] == 1:
            for key in MarketData.ohlc.uwahige_scaled.keys():
                input_data.append(MarketData.ohlc.uwahige_scaled[key].iloc[i])
        if index[6] == 1:
            for key in MarketData.ohlc.shitahige_scaled.keys():
                input_data.append(MarketData.ohlc.shitahige_scaled[key].iloc[i])
        if np.nan in input_data:
                print("NNInputDataGenerator: Nan is included !")

        #order side
        if len(ac.order_side) > 0:
            if ac.getLastOrderSide()=="buy":
                input_data.append(1)
                input_data.append(0)
            elif ac.getLastOrderSide() == "sell":
                input_data.append(0)
                input_data.append(1)
            else:
                print("Unknown order side! " + ac.order_side[ac.order_serial_list[0]])
                input_data.append(0)
                input_data.append(0)
        else:
            input_data.append(0)
            input_data.append(0)
        
        #holding side
        if ac.holding_side == "buy":
            input_data.append(1)
            input_data.append(0)
        elif ac.holding_side == "sell":
            input_data.append(0)
            input_data.append(1)
        else:
            input_data.append(0)
            input_data.append(0)

        #holding size
        max_amount = 3
        for j in range(max_amount):
            if ac.holding_size > j:
                input_data.append(1)
            else:
                input_data.append(0)

        #ac pl, 損益率を表現する
        pl_ratio = 100.0 * (ac.unrealized_pl / ac.holding_size) / (ac.holding_price) if ac.holding_size > 0 else 0
        for j in range(1, 21):
            if pl_ratio >= -20 + (j * 2.0):
                input_data.append(1)
            else:
                input_data.append(0)

        #holding period
        for j in range(1, 21):
            if ac.holding_period >= j*10:
                input_data.append(1)
            else:
                input_data.append(0)
        print(input_data)
        return input_data
