import threading
import time

from SimAccount import SimAccount
from Strategy import Strategy, ActionData
from NNInputDataGenerator import NNInputDataGenerator
from MarketData import MarketData
from Gene import Gene
from SystemFlg import SystemFlg
from NN import NN


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
    def __init__(self):
        print('started Sim.')
        SimAccount.initialize()
        self.loop_i = 0
        self.max_amount = 1
        self.nn = NN()
        self.nn_input_data_generator = NNInputDataGenerator()
        self.gene = Gene('./Model/best_weight.csv')
        self.pred = -1
        self.pred_log = []
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
                self.loop_i += 1
            time.sleep(1)


    def __nn_process(self, divergence_scaled):
        nn_input = self.nn_input_data_generator.generate_nn_input_data_limit(divergence_scaled)
        nn_outputs = self.nn.calc_nn(nn_input, self.gene.num_units, self.gene.weight_gene1, self.gene.weight_gene2, self.gene.bias_gene1, self.gene.bias_gene2, 1)
        self.pred = self.nn.getActivatedUnit(nn_outputs)#{0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        self.pred_log.append(self.pred)
        print('Sim: nn output=', self.pred, ':', {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[self.pred])


    def __sim_action_process(self, i, actions:ActionData, ohlc):
        for j in range(len(actions.action)):
            if actions.action[j] == 'entry':
                SimAccount.entry_order(i, actions.order_side[j], actions.order_price[j], actions.order_size[j], ohlc['dt'], actions.order_type[j], actions.order_message[j])
            elif actions.action[j] == 'cancel':
                SimAccount.cancel_all_order()
            elif actions.action[j] == 'update amount':
                print('update amount is not programmed !')
                pass
            elif actions.action[j] == 'update price':
                SimAccount.update_order_price(actions.order_price[j])