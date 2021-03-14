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
from LogMaster import LogMaster


'''
前提条件
Strategyの売買判断に従って取引して、結果をBotAccountとSimAccountの両方に反映する。
NN / Strategyにおいては、SimAccountの情報を使って計算する。実際にorder出すときはその時点のbid/askに出す。
*Partial Execのときは、holding有りとしてNNに入力するが、orderは残っていても無しとしてNNに入力する。
->NNは全約定として反対売買を判断する ->order cancelしてholding sizeに対して反対売買すればいい
->NNは全約定として保有（buy）を継続し価格が上がり続ける、botは残りのorderをprice updateしながら全約定を目指す。結果として平均約定値が高くなりパフォーマンスが悪化する。 ->避けることができないが、simよりbotの方が約定能力高いので、この場合はsimでも1分毎にprice updateすると思われる。
'''
class Bot():
    def __init__(self, order_size):
        print('started bot')
        BotAccount.initialize()
        self.__nn = NN()
        self.__nn_input_data_generator = NNInputDataGenerator()
        self.__gene = Gene('./Model/best_weight.csv')
        self.__pred = -1
        self.__pred_log = []
        self.__bot_started_time = 0
        self.__bot_elapsed_time = 0
        self.__order_size = order_size
        th = threading.Thread(target=self.__bot_thread)
        th.start()
        


    def __bot_thread(self):
        while SystemFlg.get_system_flg():
            if MarketData.ohlc_bot_flg == True:
                ohlc = MarketData.get_latest_ohlc(1)
                BotAccount.ohlc_update(ohlc)
                self.__nn_process(ohlc)

                

        time.sleep(0.5)

    def __nn_process(self, ohlc):
        order_data = BotAccount.get_order_data_nn()
        holding_data = BotAccount.get_holding_data_nn()
        performance_data = BotAccount.get_performance_data_nn(ohlc)
        nn_input = self.nn_input_data_generator.generate_nn_input_data_limit_bot(ohlc['divergence_scaled'], order_data, holding_data, performance_data)
        nn_outputs = self.nn.calc_nn(nn_input, self.gene.num_units, self.gene.weight_gene1, self.gene.weight_gene2, self.gene.bias_gene1, self.gene.bias_gene2, 1)
        self.pred = self.nn.getActivatedUnit(nn_outputs)#{0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        self.pred_log.append(self.pred)
        #print('Bot: nn output=', self.pred, ':', {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[self.pred])



if __name__ == '__main__':
    while True:
        time.sleep(0.1)