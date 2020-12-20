import threading
import time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import asyncio
import os

from SimAccount import SimAccount
from Strategy import Strategy, ActionData
from NNInputDataGenerator import NNInputDataGenerator
from MarketData import MarketData
from Gene import Gene
from SystemFlg import SystemFlg
from NN import NN
from LogMaster import LogMaster
from LineNotification import LineNotification



'''
loop_i = 0
detected the ohlc is updated in MarketData
check & process execution using MarketData[i]
update order/holding/performance with MarketData[i]
calc nn using MarketData[i] and Account
calc actions using the Account / MarketData[i]
place orders(order_i=loop_i)
loop_i += 1


毎分MarketDataでohlc / indexが更新されたことを確認して、check & process executionをしてorder / holding更新
SimAccountのpl / holding periodなどを更新する。
SimAccountを更新したらnnの計算を行い、strategyで必要なアクションを計算しSimAccountのorderを更新する。
'''
class Sim:
    def __init__(self, bool_display):
        print('started Sim.')
        SimAccount.initialize()
        self.loop_i = 0
        self.max_amount = 1
        self.nn = NN()
        self.nn_input_data_generator = NNInputDataGenerator()
        self.gene = Gene('./Model/best_weight.csv')
        self.pred = -1
        self.pred_log = []
        self.__bool_display = bool_display #True=display log
        th = threading.Thread(target=self.__sim_thread)
        th.start()

        

    def __sim_thread(self):
        while SystemFlg.get_system_flg():
            if MarketData.ohlc_sim_flg == True:
                #毎分MarketDataでohlc / indexが更新されたことを確認
                ohlc = MarketData.get_latest_ohlc(0) #{'dt', 'open', 'high', 'low', 'close', 'divergence_scaled'}
                #SimAccountのpl / holding periodなどを更新
                SimAccount.ohlc_update(self.loop_i, ohlc)
                #nnの計算を行い、strategyで必要なアクションを計算
                self.__nn_process(ohlc['divergence_scaled'])
                #SimAccountのorderを更新する。
                actions = Strategy.sim_ga_limit_strategy(self.pred, 1, self.max_amount, ohlc)
                self.__sim_action_process(self.loop_i, actions, ohlc)
                #Log
                LogMaster.add_sim_holding_log(ohlc['dt'], SimAccount.get_holding_data())
                LogMaster.add_sim_order_log(ohlc['dt'], SimAccount.get_order_data())
                LogMaster.add_sim_performance_log(ohlc['dt'], SimAccount.get_performance_data())
                LogMaster.add_sim_trade_log(ohlc['dt'], SimAccount.get_latest_trade_log())
                #Display
                if self.__bool_display:
                    print('')
                    print('**************************************************************************************************')
                    print('i=',self.loop_i)
                    del ohlc['divergence_scaled']
                    print(ohlc)
                    print('nn ouput=', {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[self.pred_log[-1]])
                    performance_log = SimAccount.get_performance_data()
                    print('----------------------------------------Performance Data--------------------------------------------')
                    print(performance_log)
                    print('-------------------------------------------Holding Data---------------------------------------------')
                    print(SimAccount.get_holding_data())
                    print('--------------------------------------------Order Data----------------------------------------------')
                    print(SimAccount.get_order_data())
                    print('--------------------------------------------Trade Log-----------------------------------------------')
                    print(SimAccount.get_latest_trade_log())
                    print('**************************************************************************************************')
                    #create pl chart
                    plog = LogMaster.get_sim_performance_log()
                    self.__generate_pl_chart(plog)
                    #send message
                    LineNotification.send_performance(performance_log)
                    LineNotification.send_holding(SimAccount.get_holding_data())
                    if os.path.isfile('./Image/sim_pl.jpg'):
                        LineNotification.send_image(open('./Image/sim_pl.jpg', 'rb'))
                self.loop_i += 1
            time.sleep(1)


    def __nn_process(self, divergence_scaled):
        nn_input = self.nn_input_data_generator.generate_nn_input_data_limit_sim(divergence_scaled)
        nn_outputs = self.nn.calc_nn(nn_input, self.gene.num_units, self.gene.weight_gene1, self.gene.weight_gene2, self.gene.bias_gene1, self.gene.bias_gene2, 1)
        self.pred = self.nn.getActivatedUnit(nn_outputs)#{0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        self.pred_log.append(self.pred)
        #print('Sim: nn output=', self.pred, ':', {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[self.pred])


    def __generate_pl_chart(self, plog):
        if len(plog) > 2:
            df = pd.concat([pd.DataFrame(plog.values()), pd.DataFrame({'dt':plog.keys()})], axis=1)
            df = df.set_index('dt')
            fig, ax = plt.subplots()
            plt.plot(df.index, df['total_pl'])
            #plt.xticks(rotation=70)
            xfmt = mdates.DateFormatter("%d - %H:%M")
            ax.xaxis.set_major_formatter(xfmt)
            labels = ax.get_xticklabels()
            plt.setp(labels, rotation=45, fontsize=10)
            plt.show()
            plt.savefig('./Image/sim_pl.jpg')
            plt.close()


    def __sim_action_process(self, i, actions:ActionData, ohlc):
        for j in range(len(actions.action)):
            if actions.action[j] == 'entry':
                SimAccount.entry_order(i, actions.order_side[j], actions.order_price[j], actions.order_size[j], ohlc['dt'], actions.order_type[j], actions.order_message[j])
            elif actions.action[j] == 'cancel':
                SimAccount.cancel_all_order(i)
            elif actions.action[j] == 'update amount':
                print('update amount is not programmed !')
                pass
            elif actions.action[j] == 'update price':
                SimAccount.update_order_price(i, actions.order_serial_num[j], actions.order_price[j])