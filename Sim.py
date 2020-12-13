from SimAccount import SimAccount
from Strategy import Strategy
from NNInputDataGenerator import NNInputDataGenerator
from SystemFlg import SystemFlg
from NN import NN


'''
毎分MarketDataでohlc / indexが更新されたことを確認して、SimAccountのpl / holding periodなどを更新する。
SimAccountを更新したらnnの計算を行い、strategyで必要なアクションを計算しSimAccountのorderを更新する。
'''
class Sim:
    def __init__(self):
        print('started Sim.')
        SimAccount.initialize()
        self.nn = NN()
        self.nn_input_data_generator = NNInputDataGenerator()
        self.gene = Gene()
        self.gene.readWeigth('./Model/best_weight.csv')
        self.pred = -1
        self.pred_log = []
        

    def __sim_thread(self):
        while SystemFlg.get_system_flg():
            #毎分00秒を過ぎた時点で0.1秒間隔でMarketDataの更新を確認する。
            while True:
                MarketData.
                
            time.sleep(1)


    def sim_ga_limit(self, from_ind, to_ind, max_amount, chromo, ac):
        nn = NN()
        strategy = Strategy()
        amount = 1
        nn_input_data_generator = NNInputDataGenerator()
        for i in range(from_ind, to_ind):
            nn_inputs = nn_input_data_generator.generate_nn_input_data_limit(ac, i)
            nn_outputs = nn.calc_nn(nn_inputs, chromo.num_units, chromo.weight_gene1, chromo.weight_gene2, chromo.bias_gene1, chromo.bias_gene2, 1)
            pred = nn.getActivatedUnit(nn_outputs)
            actions = strategy.ga_limit_strategy(i, pred, amount, max_amount, ac)

            for j in range(len(actions.action)):
                if actions.action[j] == 'entry':
                    ac.entry_order(actions.order_type[j], actions.order_side[j], actions.order_size[j], actions.order_price[j], i, OneMinMarketData.ohlc.dt[i], actions.order_message[j])
                elif actions.action[j] == 'cancel':
                    ac.cancel_all_order(i, OneMinMarketData.ohlc.dt[i])
                elif actions.action[j] == 'update amount':
                    ac.update_order_amount(actions.order_size[j], actions.order_serial_num[j], i, OneMinMarketData.ohlc.dt[i])
                elif actions.action[j] == 'update price':
                    ac.update_order_price(actions.order_price[j], actions.order_serial_num[j], i, OneMinMarketData.ohlc.dt[i])
            ac.move_to_next(i+1, OneMinMarketData.ohlc.dt[i+1], OneMinMarketData.ohlc.open[i+1], OneMinMarketData.ohlc.high[i+1], OneMinMarketData.ohlc.low[i+1], OneMinMarketData.ohlc.close[i+1])
        ac.calc_sharp_ratio()
        return ac
