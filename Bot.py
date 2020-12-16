import threading
import time
from MarketData import MarketData
from LineNotification import LineNotification
from Trade import Trade
from BotAccount import BotAccount
from SystemFlg import SystemFlg
from NN import NN
from NNInputDataGenerator import NNInputDataGenerator
from Gene import Gene


'''
check and get latest ohlc from MarketData
calc nn
calc strategy
place orders
'''
class Bot():
    def __init__(self):
        print('started bot')
        BotAccount.initialize()
        self.nn = NN()
        self.nn_input_data_generator = NNInputDataGenerator()
        self.gene = Gene('./Model/best_weight.csv')
        self.pred = -1
        self.pred_log = []
        th = threading.Thread(target=self.__bot_thread)
        th.start()
        


    def __bot_thread(self):
        while SystemFlg.get_system_flg():
            if MarketData.ohlc_bot_flg == True:
                ohlc = MarketData.get_latest_ohlc()
                self.__nn_process(ohlc['divergence_scaled'])
                

        time.sleep(0.5)

    def __nn_process(self, divergence_scaled):
        nn_input = self.nn_input_data_generator.generate_nn_input_data_limit(divergence_scaled)
        nn_outputs = self.nn.calc_nn(nn_input, self.gene.num_units, self.gene.weight_gene1, self.gene.weight_gene2, self.gene.bias_gene1, self.gene.bias_gene2, 1)
        self.pred = self.nn.getActivatedUnit(nn_outputs)#{0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        self.pred_log.append(self.pred)
        print('Bot: nn output=', self.pred, ':', {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[self.pred])



if __name__ == '__main__':
    while True:
        time.sleep(0.1)