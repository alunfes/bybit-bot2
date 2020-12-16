import time
import threading
import copy

from SystemFlg import SystemFlg
from Trade import Trade

'''
Botとは完全に分離したAccount。
'''
class SimAccount:
    @classmethod
    def initialize(cls):
        cls.taker_fee_ratio = 0.00075
        cls.maker_fee_ratio = -0.00025
        cls.__initialize_order_data()
        cls.__initialize_holding_data()
        cls.__initialize_performance_data()


    @classmethod
    def __initialize_order_data(cls):
        cls.lock_order = threading.Lock()
        cls.order_serial_num = 0
        cls.order_serial_list = []
        cls.order_side = {}
        cls.order_price = {}
        cls.order_size = {}
        cls.order_type = {}
        cls.order_dt = {}
        cls.order_i= {}
        cls.order_message = {}
        cls.order_cancel = {}

    @classmethod
    def __initialize_holding_data(cls):
        cls.lock_holding = threading.Lock()
        cls.holding_side = ''
        cls.holding_size = 0
        cls.holding_price = 0
        cls.holding_i = 0
        cls.holding_period = 0

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

    '''
    should be called only by Sim when ohlc is updated
    '''
    @classmethod
    def ohlc_update(cls, i, ohlc): #ohlc = {'dt', 'open', 'high', 'low', 'close', 'divergence_scaled'}
        #check & process execution
        cls.__check_cancel()
        cls.__check_execution(i, ohlc['open'], ohlc['high'], ohlc['low'])
        #update pl / holding period
        holding_data = cls.get_holding_data()
        if holding_data['side'] != '':
            with cls.lock_performance:
                cls.unrealized_pl = (ohlc['close'] - holding_data['price']) * holding_data['size'] if holding_data['side'] == 'buy' else (holding_data['price'] - ohlc['close']) * holding_data['size']
            with cls.lock_holding:
                cls.holding_period = i - cls.holding_i #int( (datetime.datetime.now().timestamp - cls.holding_timestamp) / 60.0)
        else:
            with cls.lock_performance:
                cls.unrealized_pl = 0
        with cls.lock_performance:
            cls.total_pl= cls.unrealized_pl + cls.realized_pl - cls.total_fee
            cls.total_pl_list.append(cls.total_pl)
            if cls.num_trade > 0:
                cls.win_rate = round(float(cls.num_win) / float(cls.num_trade), 4)
        print('SimAccount: ', 'total_pl=', cls.total_pl, ', num trade=', cls.num_trade, ', win rate=', cls.win_rate)
        print('Sim Holding Data: ', cls.get_holding_data())
        print('Sim Order Data: ', cls.get_order_data())

    
    @classmethod
    def entry_order(cls, i, side, price, size, dt, otype, message):
        with cls.lock_order:
            if otype == 'market' or otype=='limit':
                cls.order_side[cls.order_serial_num] = side
                cls.order_price[cls.order_serial_num] = price
                cls.order_size[cls.order_serial_num] = size
                cls.order_type[cls.order_serial_num] = otype
                cls.order_dt[cls.order_serial_num] = dt
                cls.order_i[cls.order_serial_num] = i
                cls.order_message[cls.order_serial_num] = message
                cls.order_cancel[cls.order_serial_num] = False
                cls.order_serial_list.append(cls.order_serial_num)
                cls.order_serial_num += 1
            else:
                print('SimAccount-entry_order: Invalid order type !', otype)
                

    @classmethod
    def get_order_data(cls):
        with cls.lock_order:
            orders = []
            for oid in cls.order_serial_list:
                orders.append({'id':oid, 'side':cls.order_side[oid], 'price':cls.order_price[oid], 'size':cls.order_size[oid],
            'type':cls.order_type[oid], 'dt':cls.order_dt[oid], 'message':cls.order_message[oid], 'cancel':cls.order_cancel[oid]})
            return orders


    @classmethod
    def getLastOrderSide(cls):
        with cls.lock_order:
            if (len(cls.order_serial_list) > 0):
                return cls.order_side[cls.order_serial_list[-1]]
            else:
                return ''


    @classmethod
    def getLastOrderSize(cls):
        with cls.lock_order:
            if (len(cls.order_serial_list) > 0):
                return cls.order_size[cls.order_serial_list[-1]]
            else:
                return ''


    @classmethod
    def getLastOrderPrice(cls):
        with cls.lock_order:
            if (len(cls.order_serial_list) > 0):
                return cls.order_price[cls.order_serial_list[-1]]
            else:
                return ''

    @classmethod
    def getLastSerialNum(cls):
        with cls.lock_order:
            if (len(cls.order_serial_list) > 0):
                return cls.order_serial_list[-1]
            else:
                return -1


    @classmethod
    def update_order_price(cls, oid, update_price):
        with cls.lock_order:
            if cls.order_side[oid] == 'buy' and cls.order_price[oid] > update_price:
                print('buy price update issue: ', cls.order_price[oid], ' -> ', update_price)
            if cls.order_side[oid] == 'sell' and cls.order_price[oid] < update_price:
                print('sell price update issue: ', cls.order_price[oid], ' -> ', update_price)
            if update_price > 0 and cls.order_side[oid] != '':
                cls.order_price[oid] = update_price

    @classmethod
    def cancel_order(cls, oid):
        if cls.order_side[oid] != '':
            cls.order_cancel[oid] = True
        else:
            print('SimAccount-cancel_order: order is not exist !')

    @classmethod
    def cancel_all_order(cls):
        for oid in cls.order_serial_list:
            cls.cancel_order(oid)

    @classmethod
    def get_holding_data(cls):
        with cls.lock_holding:
            return {'side':cls.holding_side, 'size':cls.holding_size, 'price':cls.holding_price, 'i':cls.holding_i, 'period':cls.holding_period}

    @classmethod
    def __update_holding(cls, side, price, size, i, period):
        with cls.lock_holding:
            cls.holding_side = side
            cls.holding_size = size
            cls.holding_price = price
            cls.holding_i = i
            cls.holding_period = period


    @classmethod
    def get_performance_data(cls):
        with cls.lock_performance:
            return {'total_pl':cls.total_pl, 'realized_pl':cls.realized_pl, 'unrealized_pl':cls.unrealized_pl, 'total_pl_list':cls.total_pl_list,
            'num_trade':cls.num_trade, 'win_rate':cls.win_rate}


    @classmethod
    def __calc_fee(cls, size, price, maker_taker):
        if maker_taker == 'maker':
            cls.total_fee += size * price * cls.maker_fee_ratio
        elif maker_taker == 'taker':
            cls.total_fee += size * price * cls.taker_fee_ratio
        else:
            print('unknown maker_taker type!', maker_taker)
            pass
        
    @classmethod
    def __check_cancel(cls):
        ks = copy.copy(cls.order_serial_list)
        for k in ks:
            if cls.order_cancel[k]==True:
                cls.__del_order(k)


    @classmethod
    def __del_order(cls, oid):
        with cls.lock_order:
            if oid in cls.order_serial_list:
                cls.order_serial_list.remove(oid)
            del cls.order_side[oid]
            del cls.order_price[oid]
            del cls.order_size[oid]
            del cls.order_i[oid]
            del cls.order_dt[oid]
            del cls.order_type[oid]  # market / limit
            del cls.order_cancel[oid] #True / False
            del cls.order_message[oid]


    @classmethod
    def __check_execution(cls, i, openp, high, low):
        ks = copy.copy(cls.order_serial_list)
        for k in ks:
            if cls.order_type[k] == "market":
                cls.num_market_order +=1
                cls.__process_execution(openp, i, k)
                cls.__del_order(k)
            elif cls.order_i[k] < i:
                if cls.order_type[k] == 'limit' and (cls.order_side[k] =='buy' and cls.order_price[k] > low) or (cls.order_side[k] =='sell' and cls.order_price[k] < high):
                    cls.__process_execution(cls.order_price[k], i, k)
                    cls.__del_order(k)
            else:
                pass

    @classmethod
    def __process_execution(cls, exec_price, i, k):
        cls.__calc_fee(cls.order_size[k], exec_price, 'maker' if cls.order_type[k] == 'limit' else 'taker')
        if cls.holding_side == '':
            cls.__update_holding(cls.order_side[k], exec_price, cls.order_size[k], i, 0) #side, price, size, i, period
        elif cls.holding_side == cls.order_side[k]:
            ave_price = round(((cls.holding_price * cls.holding_size) + (exec_price * cls.order_size[k])) / (cls.order_size[k] + cls.holding_size))  # averaged holding price
            cls.__update_holding(cls.holding_side, ave_price, cls.order_size[k] + cls.holding_size, i)
        elif cls.holding_size > cls.order_size[k]:
            cls.__calc_executed_pl(exec_price, cls.order_size[k], i)
            cls.__update_holding(cls.holding_side, cls.holding_price, cls.holding_size - cls.order_size[k], i)
        elif cls.holding_size == cls.order_size[k]:
            cls.__calc_executed_pl(exec_price, cls.order_size[k], i)
            cls.__initialize_holding_data()
        elif cls.holding_size < cls.order_size[k]:
            cls.__calc_executed_pl(exec_price, cls.holding_size, i)
            cls.__update_holding(cls.order_side[k], exec_price, cls.order_size[k] - cls.holding_size, i)


    @classmethod
    def __calc_executed_pl(cls, exec_price, size, i):  # assume all order size was executed
        pl = (exec_price - cls.holding_price) * size if cls.holding_side == 'buy' else (cls.holding_price - exec_price) * size
        cls.realized_pl += round(pl,6)
        cls.num_trade += 1
        if pl > 0:
            cls.num_win += 1


if __name__ == '__main__':
    print('As')