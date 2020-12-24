import time
import threading

from SystemFlg import SystemFlg
from PrivateWS import PrivateWS, PrivateWSData
from MarketData import MarketData
from Trade import Trade
from LineNotification import LineNotification

'''
約定処理について：
Partial Executedでもholdingは即時に反映させる。
realized pl / 
'''

'''
・Botからのorder idを受けて、Tradeのget order info by idで確認し、約定処理等行う。
・約定処理はpartial executedでもholding / orderを即時更新するが、最終的にorder_status=Filled / Cancelledになった時点で
・全てLimit orderを想定（板にぶつけてしまい結果としてmarket orderとなった場合も適切に対処）
'''
class BotAccount:
    @classmethod
    def initialize(cls):
        #pws = PrivateWS()
        cls.__initialize_order_data()
        cls.__initialize_holding_data()
        cls.__initialize_performance_data()
        cls.__initialize_trade_data()
        #th = threading.Thread(target=cls.__account_thread)
        #th.start()


    @classmethod
    def __initialize_order_data(cls):
        cls.__lock_order = threading.Lock()
        cls.order_id = []
        cls.order_side = {}
        cls.order_price = {}
        cls.order_size = {}
        cls.order_leaves_qty = {}
        cls.order_type = {} #Limit, Market
        cls.order_dt = {}
        cls.order_status = {} #Filled, Cancelled, New, Created, PartiallyFilled

    @classmethod
    def __initialize_holding_data(cls):
        cls.__lock_holding = threading.Lock()
        cls.holding_side = ''
        cls.holding_size = 0
        cls.holding_price = 0
        cls.holding_dt = ''
        cls.holding_period = 0


    @classmethod
    def __initialize_performance_data(cls):
        cls.__lock_performance = threading.Lock()
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
    def __initialize_trade_data(cls):
        cls.__lock_trade = threading.Lock()
        cls.trade_log = {} #{i, [trade_log]}


    @classmethod
    def get_holding_data(cls):
        with cls.__lock_holding:
            return {'side':cls.holding_side, 'size':cls.holding_size, 'price':cls.holding_price, 'dt':cls.holding_dt, 'period':cls.holding_period}

    
    @classmethod
    def get_holding_data_nn(cls):
        with cls.lock_holding:
            return {'side':cls.holding_side, 'size':1 if cls.holding_size > 0 else 0, 'price':cls.holding_price, 'period':cls.holding_period}


    @classmethod
    def __update_holding_data(cls, side, size, price, dt, period):
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
    def get_performance_data_nn(cls, ohlc):
        with cls.lock_performance:
            if cls.holding_side != '':
                pl =  ohlc['close'] - cls.holding_price if cls.holding_side == 'buy' else cls.holding_price - ohlc['close'] 
                return {'unrealized_pl':pl}
            else:
                return {'unrealized_pl':0}

    @classmethod
    def add_order(cls, order_id, side, price, size, leaves_qty, otype):
        with cls.__lock_order:
            cls.order_id.append(order_id)
            cls.order_side[order_id] = side
            cls.order_price[order_id] = price
            cls.order_size[order_id] = size
            cls.order_leaves_qty[order_id] = leaves_qty
            cls.order_type[order_id] = otype
            cls.order_dt[order_id] = datetime.datetime.now()
            cls.order_status[order_id] = 'New'
            if leaves_qty != size:
                print('Bot.add_order: New entry order is already partially executed!')
            if len(cls.order_id) > 1:
                print('Bot.add_order: Multi order exists !', cls.order_side, ' ; ', cls.order_price, ' ; ', cls.order_leaves_qty)
            th = threading.Thread(target=cls.__order_exec_check_thread)
            th.start()


    @classmethod
    def __update_order(cls, order_id, price, leaves_qty, status):
        with cls.__lock_order:
            cls.order_price[order_id] = price
            cls.order_leaves_qty[order_id] = leaves_qty
            cls.order_status[order_id] = status


    @classmethod
    def get_order_ids(cls):
        with cls.__lock_order:
            return cls.order_id


    @classmethod
    def get_order_data(cls, oid):
        with cls.__lock_order:
            if oid in cls.order_id:
                return {'id':oid, 'side':cls.order_side[oid], 'price':cls.order_price[oid], 'size':cls.order_size[oid], 'leaves_qty':cls.order_leaves_qty[oid],
                'type':cls.order_type[oid], 'dt':cls.order_dt[oid], 'status':cls.order_status[oid]}
            else:
                print('BotAccount.get_order_data: Unknown order id !', oid)

    '''
    partial execでholding side == order sideの場合は、order無しとしてNNに入力する。
    '''
    @classmethod
    def get_order_data_nn(cls):
        with cls.__lock_order:
            if cls.holding_side == cls.order_side[cls.order_id[-1]]:
                return {'side':''}
            else:
                return {'side':cls.order_side[cls.order_id[-1]]}


    @classmethod
    def cancel_order(cls, order_id, leaves_qty):
        with cls.__lock_order:
            if cls.order_leaves_qty != leaves_qty:
                pass
            
    
    @classmethod
    def __del_order(cls, order_id):
        with cls.__lock_order:
            if order_in in cls.order_id:
                cls.order_id.remove(oreder_id)
                del cls.order_side[order_id]
                del cls.order_price[order_id]
                del cls.order_size[order_id]
                del cls.order_leaves_qty[order_id]
                del cls.order_type[order_id]
                del cls.order_dt[order_id]
                del cls.order_status[order_id]
            else:
                print('BotAccount-del_order: Invalid order id !', order_id)


    '''
    @classmethod
    def __account_thread(cls):
        while SystemFlg.get_system_flg():
            #holdingがある時に、pl等確認
            cls.__calc_realized_pl()
            time.sleep(1)
    '''

    '''
    Should called only by Bot when ohlc was updated
    holding_periodは60sec未満だと0となるがsimではNNにholding side !=''のときはholding period=0とはならない？
    '''
    @classmethod
    def ohlc_update(cls, ohlc): #ohlc{'dt', 'open', 'high', 'low', 'close', 'divergence_scaled'}
        period = int((datetime.datetime.now().timestamp() - cls.hodlding_dt.timestamp()) / 60.0)
        cls.__update_holding_data(cls.holding_side, cls.holding_size, cls.holding_price, cls.holding_dt, period)
        cls.__calc_total_pl(ohlc)


    @classmethod
    def __calc_total_pl(cls, ohlc):
        with cls.lock_performance:
            if cls.holding_side != '':
                cls.unrealized_pl = (ohlc['close'] - self.holding_price) * self.holding_size if self.holding_side == 'buy' else (self.holding_price - ohlc['close']) * self.holding_size
            else:
                self.unrealized_pl = 0
            cls.total_pl = cls.unrealized_pl + cls.realized_pl - cls.total_fee
            if cls.num_trade > 0:
                cls.win_rate = round(float(cls.num_win) / float(cls.num_trade), 4)


    '''
    order entryが確認されたらthreadとして呼び出される。
    orderがfully exexuted or cancelledされるまで約定状況を確認し続ける。
    '''
    @classmethod
    def __order_exec_check_thread(cls):
        while len(cls.order_id) > 0:
            for oid in cls.order_id:
                order = Trade.get_order_byid(oid)
                if 'order_id' in order:
                    if order['leaves_qty'] < cls.order_leaves_qty[oid]:
                        exec_price = order['price'] if order['order_type'] == 'Limit' else order['average']
                        cls.__process_execution(oid, order['qty'], order['side'], order['leaves_qty'], order['cum_exec_qty'], order['order_type'], exec_price, order['cum_exec_fee'], order['order_status'])
                else:
                    print('BotAccount-__order_exec_check_thread: Invalid order data!', order)
                    LineNotification.send_message('BotAccount-__order_exec_check_thread: Invalid order data!')
            times.sleep(0.5)


    '''
    Partiall
    '''
    @classmethod
    def __process_execution(cls, oid, side, qty, leaves_qty, cum_exec_qty, otype, exec_price, cum_exec_fee, order_status):
        cls.__calc_fee(otype, cum_exec_fee, exec_price, average_price)
        cls.__calc_realized_pl(cum_exec_qty, exec_price)
        if otype == 'Market':
            cls.num_market_order += 1
            print('Bot.__process_execution: Order was executed as a market order !')
            LineNotification.send_message('Bot.__process_execution: Order was executed as a market order !')
        #update holding data
        if cls.holding_side == '':
            cls.__update_holding_data(side, cum_exec_qty, exec_price, datetime.datetime.now(), 0)    
            print('Bot: New Entry: ', side + ' @', exec_price, ' x ', cls.order_size[k])
        elif cls.holding_side == cls.order_side[oid]: #Additional Entry (Remaining parts of partial execution)
            ave_price = round(((cls.holding_price * cls.holding_size) + (exec_price * cum_exec_qty)) / (cum_exec_qty + cls.holding_size))  # averaged holding price
            cls.__update_holding_data(side, cls.holding_size + cum_exec_qty, ave_price, cls.holding_dt, cls.holding_period)
            print('Bot: Additional Entry: ', side + ' @', exec_price, ' x ', cls.order_size[k])
        elif cls.holding_size > cum_exec_qty: #Opposite Entry (h>o)
            cls.__update_holding_data(cls.holding_side, cls.holding_size - cum_exec_qty, cls.holding_price, cls.holding_dt, cls.holding_period)
            print('Bot: Opposite Entry: ', side + ' @', exec_price, ' x ', cls.order_size[k])
        elif cls.holding_size == cls.order_size[k]: #All Exit
            cls.__initialize_holding_data()
            print('Bot: All Exit: ', side + ' @', exec_price, ' x ', cls.order_size[k])
        elif cls.holding_size < cls.order_size[k]: #Opposite Entry (h<o)
            cls.__update_holding_data(side, cum_exec_qty - cls.holding_size, exec_price, datetime.datetime.now(), 0)
            print('Bot: Opposite Entry: ', side + ' @', exec_price, ' x ', cls.order_size[k])
        else:
            print('BotAccount.__process_execution: Undefined Situation !')
            LineNotification.send_message('BotAccount.__process_execution: Undefined Situation !')
        
        #update order data
        if order_status == 'Filled' or order_status == 'Cancelled':
            cls.__del_order(oid)
            print('Bot: Order ', order_status, ' - ', side, ' @ ', exec_price, ' x ', qty)
        else: #New, Created, PartiallyFilled
            print('BotAccount.__process_execution: Partially Filled. Order ID=', oid, ', side=', side, 'exec qty=', cls.order_size[oid] - leaves_qty, ' @ ', exec_price)
            cls.__update_order(oid, cls.order_price[oid], leaves_qty, 'PartiallyFilled']) #order_id, price, leaves_qty, status




    '''
    feeはorderがFully executedもしくはcancelledとなった時のみ計算し反映される。
    '''
    @classmethod
    def __calc_fee(cls, cum_exec_fee, exec_price):
        cls.total_fee -= round(cum_exec_fee * exec_price, 6)


    @classmethod
    def __calc_realized_pl(cls, exec_qty, exec_price):
        pl = (exec_price - cls.holding_price) * exec_qty if cls.holding_side == 'buy' else (cls.holding_price - exec_price) * exec_qty
        cls.realized_pl += round(pl,6)
        cls.num_trade += 1
        if pl > 0:
            cls.num_win += 1

