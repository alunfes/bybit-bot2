import time
import threading

from SystemFlg import SystemFlg
from PrivateWS import PrivateWS, PrivateWSData
from MarketData import MarketData



'''
・Botからのorder idを受けて、それをprivate wsとTradeのデータで確認し、約定処理等行う。
'''
class BotAccount:
    @classmethod
    def initialize(cls):
        pws = PrivateWS()
        cls.__initialize_order_data()
        cls.__initialize_holding_data()
        th = threading.Thread(target=cls.__account_thread())
        th.start()


    @classmethod
    def __initialize_order_data(cls):
        cls.lock_order = threading.Lock()
        cls.order_id = ''
        cls.order_side = ''
        cls.order_price = 0
        cls.order_size = 0
        cls.order_leaves_qty = 0
        cls.order_cum_exec_fee = 0
        cls.order_type = ''
        cls.order_dt = ''
        cls.order_status = '' #

    @classmethod
    def __initialize_holding_data(cls):
        cls.lock_holding = threading.Lock()
        cls.holding_side = ''
        cls.holding_size = 0
        cls.holding_price = 0
        cls.holding_dt = ''
        cls.holding_period = 0

    @classmethod
    def get_holding_data(cls):
        with cls.lock_holding:
            return {'side':cls.holding_side, 'size':cls.holding_size, 'price':cls.holding_price, 'dt':cls.holding_dt, 'period':cls.holding_period}

    @classmethod
    def update_holding_data(cls, side, size, price, dt, period):
        with cls.lock_holding:
            cls.holding_side = side
            cls.holding_size = size
            cls.holding_price = price
            cls.holding_dt = dt
            cls.holding_period = period


    @classmethod
    def __initialize_performance_data(cls):
        cls.lock_performance = threading.Lock()
        cls.total_pl = 0
        cls.total_pl_list = []
        cls.realized_pl = 0
        cls.unrealized_pl = 0
        cls.total_fee = 0
        cls.num_trade = 0
        cls.num_sell = 0
        cls.num_buy = 0
        cls.num_win = 0
        cls.win_rate = 0
        cls.num_market_order = 0
        cls.sharp_ratio = 0

    @classmethod
    def get_performance_data(cls):
        with cls.lock_performance:
            return {'total_pl':cls.total_pl, 'realized_pl':cls.realized_pl, 'unrealized_pl':cls.unrealized_pl, 'total_pl_list':cls.total_pl_list,
            'num_trade':cls.num_trade, 'win_rate':cls.win_rate}



    @classmethod
    def __account_thread(cls):
        while SystemFlg.get_system_flg():
            #orderがある時に約定、変更確認
            if cls.order_id != '':
                th = threading.Thread(target=cls.__order_exec_check_thread())
                th.start()
            #holdingがある時に、pl等確認
            
            time.sleep(1)


    @classmethod
    def __calc_holding_pl(cls):
        with cls.lock_performance:
            if cls.holding_side != '':
                close = MarketData.get_latest_ohlc()['close']
                cls.unrealized_pl = (close - self.holding_price) * self.holding_size if self.holding_side == 'buy' else (self.holding_price - close) * self.holding_size
                self.unrealized_pl_list.append(self.unrealized_pl)
        else:
            self.unrealized_pl = 0
            self.unrealized_pl_list = []

    @classmethod
    def __order_exec_check_thread(cls):
        while cls.order_id != '':
            order_data = PrivateWSData.get_order_data()
            if order_data != None:
                for d in order_data:

            times.sleep(0.5)

    @classmethod
    def add_order(cls, order_id):
        with cls.lock_order:
            if cls.id != '':
                print('Order is alredy exist !')
            cls.order_id = order_id

