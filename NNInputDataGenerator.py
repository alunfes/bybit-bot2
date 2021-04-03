from LineNotification import LineNotification
import numpy as np
from MarketData import MarketData

'''
can be used only by bot
考え方：
GA for NNに合わせるために以下の変換を行う。
・Partial executionでも全約定としてNN入力値を計算。（holdingあり、orderなしとする）
->order status==partilly filledでかつholding side != order sideの時は全約定後のholdingを計算してnn入力データとして使う。

'''
class NNInputDataGenerator:
    def generate_nn_input_data_limit(self, gene_index, ohlc_data, index_data, order_data, holding_data, performance_data):
        #ma divergence
        input_data = []
        if gene_index[0] == 1:
            for key in index_data['divergence_scaled'].keys():
                input_data.append(index_data['divergence_scaled'][key].iloc[-1])
        if gene_index[1] == 1:
            for key in index_data['vola_kyori_scaled'].keys():
                input_data.append(index_data['vola_kyori_scaled'][key].iloc[-1])
        if gene_index[2] == 1:
            for key in index_data['vol_ma_divergence_scaled'].keys():
                input_data.append(index_data['vol_ma_divergence_scaled'][key].iloc[-1])
        if gene_index[3] == 1:
            for key in index_data['buysell_vol_ratio_scaled'].keys():
                input_data.append(index_data['buysell_vol_ratio_scaled'][key].iloc[-1])
        if gene_index[4] == 1:
            for key in index_data['rsi_scaled'].keys():
                input_data.append(index_data['rsi_scaled'][key].iloc[-1])
        if gene_index[5] == 1:
            for key in index_data['uwahige_scaled'].keys():
                input_data.append(index_data['uwahige_scaled'][key].iloc[-1])
        if gene_index[6] == 1:
            for key in index_data['shitahige_scaled'].keys():
                input_data.append(index_data['shitahige_scaled'][key].iloc[-1])

        #order side
        if order_data['side'] == '':
            input_data.append(0)
            input_data.append(0)
        else:
            if order_data['status'] == 'Partially Filled': #全約定として取り扱う
                input_data.append(0)
                input_data.append(0)
            else:
                if order_data['side'] == 'buy':
                    input_data.append(1)
                    input_data.append(0)
                elif order_data['side'] == 'sell':
                    input_data.append(0)
                    input_data.append(1)
                else:
                    print("Unknown order side! " + order_data['side'])
                    input_data.append(0)
                    input_data.append(0)
        
        #holding side
        if order_data['status'] == 'Partially Filled': #partially filledなので全約定したと仮定して処理する。
            if holding_data['side'] != '' and order_data['side'] != holding_data['side']:
                if holding_data['size'] == order_data['leaves_qty']: #Exit order
                    holding_data['side'] = ''
                    holding_data['size'] = 0
                    holding_data['price'] = 0
                elif holding_data['size'] < order_data['leaves_qty']: #Exit and opposite entry
                    if order_data['side'] == 'buy':
                        holding_data['side'] = 'buy'
                        holding_data['size'] = order_data['leaves_qty'] - holding_data['size']
                        holding_data['price'] = order_data['price']
                    else:
                        holding_data['side'] = 'sell'
                        holding_data['size'] = order_data['leaves_qty'] - holding_data['size']
                        holding_data['price'] = order_data['price']
                else: #Partial Exit which should not be occurred in the current 
                    print('NNInputDataGenerator: ')
        if holding_data['side'] == 'buy':
            input_data.append(1)
            input_data.append(0)
        elif holding_data['side'] == 'sell':
            input_data.append(0)
            input_data.append(1)
        else:
            input_data.append(0)
            input_data.append(0)

        #ac pl, 損益率を表現する。GA for NNに合わせてsize = 1に変換して計算する。
        pl_ratio = 0
        if holding_data['side'] != '':
            pl_ratio = 100.0 * (ohlc_data['close'].iloc[-1] - holding_data['price']) / holding_data['price']  if holding_data['side'] == 'buy' else 100.0 * (holding_data['price'] - ohlc_data['close'].iloc[-1]) / holding_data['price']
        for j in range(1, 21):
            if pl_ratio >= -20 + (j * 2.0):
                input_data.append(1)
            else:
                input_data.append(0)

        if np.nan in input_data:
                print("NNInputDataGenerator: Nan is included !")
                LineNotification.send_message("NNInputDataGenerator: Nan is included !")
        return input_data
