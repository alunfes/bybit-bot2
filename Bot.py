from Strategy import Strategy
from datetime import datetime
import threading
import time
import glob
import os
import pandas as pd
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
要件：
・複数の戦略（NN）を同時に並列的に運用できる。
・それぞれの戦略とBot全体のパフォーマンス・ログを個別に計算・記録できる。
・約定は即座に察知してSimAccount / BotAccountに反映させる。
前提条件
・各戦略において毎分のohlcv更新後にnn計算を行いアクションを実施。
・各戦略の発注サイズは、Bot.__init__(order_size) / num strategies
・NN / Strategyにおいては、SimAccountの情報を使って計算する。実際にorder出すときはその時点のbid/askに出す。
*Partial Execのときは、holding有りとしてNNに入力するが、orderは残っていても無しとしてNNに入力する。
Memo
・BotAccountでそれぞれの戦略のorder / holding / performanceと約定を管理する。
個別のorder_idの約定をそれぞれ問い合わせるのが簡単だが、privateのアクセス数が多くなってしまう。
仮に10戦略でそれぞれオーダーがあれば1secに一回の問い合わせで1分間で600回のアクセスになってしまう。
よって、個別のorder id毎に問い合わせるのは無理。Trade.get_executionsで直近のトレードを取得して該当する
BotAccountは複数戦略分のオブジェクトが存在しているので、Bot側でいずれかのBotAccountにorderがある時はexec dataを取得してBotAccountに渡して約定確認・処理をする。


課題：
・複数の戦略が同じタイミングで同じ価格にorderを出した時に、それぞれのorderが別物ととして約定確認できるのか？


Strategyの売買判断に従って取引して、結果をBotAccountとSimAccountの両方に反映する。
->NNは全約定として反対売買を判断する ->order cancelしてholding sizeに対して反対売買すればいい
->NNは全約定として保有（buy）を継続し価格が上がり続ける、botは残りのorderをprice updateしながら全約定を目指す。結果として平均約定値が高くなりパフォーマンスが悪化する。 ->避けることができないが、simよりbotの方が約定能力高いので、この場合はsimでも1分毎にprice updateすると思われる。
'''
class Bot():
    def __init__(self, order_size):
        print('started bot')
        self.__nn_threshold = 0.7
        self.__nn = NN()
        self.__gene = []
        self.__nn_input_data_generator = NNInputDataGenerator()
        self.__read_genes()
        self.num_genes = len(self.__gene)
        self.bot_accounts = []
        for i in range(self.num_genes):
            self.bot_accounts.append(BotAccount(i))
        self.__pred = {}
        self.__pred_log = {}
        self.__bot_started_time = datetime.now()
        self.__bot_elapsed_time = 0
        self.__order_size = round(order_size  / self.num_genes)
        self.__full_order_size = order_size
        th = threading.Thread(target=self.__bot_thread)
        th.start()
        

    def __initialize_combined_order_data(self):
        self.order_side_com = ''
        self.order_price_com = 0
        self.order_qty_com = 0

    def __read_genes(self):
        for f in glob.glob('./Model/*_best_weight.csv'):
            self.__gene.append(Gene(f, None, None))
        print('Identified ', len(self.__gene), ' genes.')


    '''
    毎分MarketDataに最新のデータが準備されたことを確認して、各戦略のNN計算して必要なアクションを取る。
    いずれかのBotAccountでorderがある時は約定データを取得してそれらのBotAccountに渡して約定確認・処理を行う。
    '''
    def __bot_thread(self):
        loop_num = 0
        while SystemFlg.get_system_flg():
            #毎分のデータ更新時の処理
            if MarketData.get_ohlc_flg() == True:
                ohlc = MarketData.get_ohlc()
                index = MarketData.get_index()
                for i in range(self.num_genes): #各戦略毎に新しい行動を計算して、実際に発注等する。結果をBotAccountに入力
                    order_data = self.bot_accounts[i].get_last_order_data()
                    holding_data = self.bot_accounts[i].get_holding_data()
                    performance_data = self.bot_accounts[i].get_performance_data()
                    nn_output = self.__nn_process(ohlc, index, i, order_data, holding_data, performance_data)
                    actions = Strategy.ga_limit_market_strategy(nn_output, self.__order_size, self.__order_size, order_data, holding_data, i)
                    print('#',i,' - pred=',nn_output[0])
                    for j in range(len(actions.action)):
                        if actions.action[j] == 'entry':
                            res = Trade.order(actions.order_side[j], actions.order_price[j], actions.order_type[j], actions.order_size[j])
                            if res != None:
                                self.bot_accounts[i].entry_order(res['info']['order_id'], res['info']['side'], res['info']['price'], res['info']['qty'], res['info']['order_type'], actions.order_message[j])
                        elif actions.action[j] == 'cancel' and order_data['side'] != '':
                            res = Trade.cancel_order(order_data['id'])
                            if res != None:
                                self.bot_accounts[i].cancel_order(order_data['id'])
                        elif actions.action[j] == 'update amount':
                            res = Trade.update_order_amount(actions.order_serial_num[j], actions.order_size[j])
                            if res != None:
                                self.bot_accounts[i].update_order_amount(order_data['id'], actions.order_size[j])
                        elif actions.action[j] == 'update price':
                            res = Trade.update_order_price(actions.order_serial_num[j], actions.order_price[j])
                            if res != None:
                                self.bot_accounts[i].update_order_price(order_data['id'], actions.order_price[j])
                        else:
                            print('Unknown strategy action-', actions.action[j])
                    self.bot_accounts[i].move_to_next(ohlc['datetime'], loop_num, ohlc, self.__order_size)
                loop_num += 1
            #次のデータ更新まで未約定orderがある時に約定確認処理を継続する
            order_remaining_flg = True
            while MarketData.get_ohlc_flg() == False and order_remaining_flg:
                order_remaining_flg = False
                for i in range(self.num_genes):#未約定注文有無の確認
                    if len(self.bot_accounts[i].order_id) > 0:
                        order_remaining_flg = True
                if order_remaining_flg == False:#未約定注文がなければ確認処理を停止
                    break
                else:
                    exec_list = Trade.get_executions()
                    if exec_list != None: #datetime unmatched errorで取得できないことがある。
                        for i in range(self.num_genes):
                            if len(self.bot_accounts[i].order_id) > 0:
                                self.bot_accounts[i].check_execution(exec_list) #未約定注文があるBotAccountに約定データを渡す
                time.sleep(3)
            time.sleep(1)
        print('Exited Bot thread loop !')
        LineNotification.send_message('Exited Bot thread loop !')


    def __nn_process(self, ohlc, index, account_id, order_data, holding_data, performance_data):
        nn_input = self.__nn_input_data_generator.generate_nn_input_data_limit(self.__gene[account_id].num_index, ohlc, index, order_data, holding_data, performance_data)
        nn_outputs = self.__nn.calc_nn(nn_input, self.__gene[account_id], 0)
        self.__pred[account_id] = self.__nn.getActivatedUnitLimitMarket2(nn_outputs, self.__nn_threshold)#{0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        return self.__pred[account_id]

    def __calc_combined_orders(self):
        for i in range(self.num_genes):
            od = self.self.bot_accounts[i].get_last_order_data()



if __name__ == '__main__':
    while True:
        time.sleep(0.1)