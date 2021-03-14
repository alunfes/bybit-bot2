import time
import threading
import copy

from SystemFlg import SystemFlg
from Trade import Trade
import pandas as pd

'''
Botとは完全に分離したAccount。

'''
class SimAccount:
    def __init__(self):
        self.__initialize_order()
        self.__initialize_holding()

        self.log_data_list = []
        self.log_data_df = pd.DataFrame()
        self.taker_fee = 0.00075
        self.maker_fee = -0.00025

        #performance data
        self.total_pl = 0
        self.total_pl_ratio = 0
        self.realized_pl = 0
        self.unrealized_pl = 0
        self.unrealized_pl_list = []
        self.total_fee = 0
        self.num_trade = 0
        self.num_sell = 0
        self.num_buy = 0
        self.num_win = 0
        self.win_rate = 0
        self.num_market_order = 0
        self.sharp_ratio = 0
        self.total_pl_list = []
        self.total_pl_ratio_list = []
        self.buy_pl_list = []
        self.sell_pl_list = []
        self.buy_pl_ratio_list = []
        self.sell_pl_ratio_list = []

        #log data
        self.dt_log = []
        self.i_log = []
        self.order_log = []
        self.holding_log = []
        self.total_pl_log = []
        self.action_log = []
        self.price_log = []
        self.performance_total_pl_log = []
        self.performance_dt_log = []
        self.pl_stability = 0
        self.close_log = []

        self.start_dt = ''
        self.end_dt = ''
        self.start_ind = 0
        self.end_ind = 0

        #order data
    def __initialize_order(self):
        self.order_serial_num = -1
        self.order_serial_list = []
        self.order_side ={}
        self.order_price = {}
        self.order_size = {}
        self.order_i = {}
        self.order_dt = {}
        self.order_ut = {}
        self.order_type = {}  # market / limit / limit-market (limit orderとしてentryして最初の1分で約定しなかったらmarket orderにする）
        self.order_cancel = {} #True / False
        self.order_message = {} #//entry, pt, exit&entry, update


    def getLastOrderSide(self):
        if (len(self.order_serial_list) > 0):
            return self.order_side[self.order_serial_list[-1]]
        else:
            return ''

    def getLastOrderSize(self):
        if (len(self.order_serial_list) > 0):
            return self.order_size[self.order_serial_list[-1]]
        else:
            return ''


    def getLastOrderPrice(self):
        if (len(self.order_serial_list) > 0):
            return self.order_price[self.order_serial_list[-1]]
        else:
            return ''

    def getLastSerialNum(self):
        if (len(self.order_serial_list) > 0):
            return self.order_serial_list[-1]
        else:
            return -1


        #holding data
    def __initialize_holding(self):
        self.holding_side = ''
        self.holding_price = 0
        self.holding_size = 0
        self.holding_i = 0
        self.holding_period = 0
        self.holding_dt = ''
        self.holding_ut = 0


    def __update_holding(self, side, price, size, i, dt):
        self.holding_side = side
        self.holding_price = price
        self.holding_size = size
        self.holding_i = i
        self.holding_dt = dt
        self.holding_period = 0

    def calc_sharp_ratio(self):
        change = np.diff(np.array(self.performance_total_pl_log))
        self.sharp_ratio = self.total_pl / np.std(change)

    
    def move_to_next(self, i, dt, openp, high, low, close):
        if len(str(self.start_dt)) < 3:
            self.start_dt = dt
        if self.start_ind == 0:
            self.start_ind = i
        self.end_ind = i
        self.__check_cancel(i, dt)
        self.__check_execution(i, dt, openp, high, low)
        self.holding_period = i - self.holding_i if self.holding_i > 0 else 0

        if self.holding_side != '':
            self.unrealized_pl = (close - self.holding_price) * self.holding_size if self.holding_side == 'buy' else (self.holding_price - close) * self.holding_size
            self.unrealized_pl_list.append(self.unrealized_pl)
        else:
            self.unrealized_pl = 0
            self.unrealized_pl_list = []

        self.total_pl = self.realized_pl + self.unrealized_pl - self.total_fee
        self.total_pl_ratio = self.total_pl / close
        if self.num_trade > 0:
            self.win_rate = round(float(self.num_win) / float(self.num_trade), 4)
        self.performance_total_pl_log.append(self.total_pl)
        self.performance_dt_log.append(dt)
        self.price_log.append(close)
        self.__add_log('i:'+str(i)+' Move to next', i, dt)
        self.close_log.append(close)
        self.total_pl_list.append(self.total_pl)
        self.total_pl_ratio_list.append(self.total_pl_ratio)


    def entry_order(self, order_type, side, size, price, i, dt, message):
        if size > 0 and (side == 'buy' or side == 'sell'):
            self.order_serial_num += 1
            self.order_serial_list.append(self.order_serial_num)
            self.order_type[self.order_serial_num] = order_type  # limit, market
            self.order_side[self.order_serial_num] =side
            self.order_price[self.order_serial_num] = price
            self.order_size[self.order_serial_num] = size
            self.order_i[self.order_serial_num] = i
            self.order_dt[self.order_serial_num] = dt
            self.order_ut[self.order_serial_num] = 0
            self.order_cancel[self.order_serial_num] = False
            self.order_message[self.order_serial_num] = message
            self.__add_log('entry order' + side + ' type=' + order_type, i, dt)
        else:
            print('entry order failed due to max order error !s', i, dt)
            self.__add_log('entry order failed due to max order error !s', i, dt)


    def update_order_price(self, update_price, order_serial_num, i, dt):
        if self.getLastOrderSide() == 'buy' and self.getLastOrderPrice() > update_price:
            print(i, ': buy price update issue: ', self.getLastOrderPrice(), ' -> ', update_price)
        if self.getLastOrderSide() == 'sell' and self.getLastOrderPrice() < update_price:
            print(i, ': sell price update issue: ', self.getLastOrderPrice(), ' -> ', update_price)

        if update_price > 0 and order_serial_num in self.order_serial_list:
            self.order_price[order_serial_num] = update_price
            self.__add_log('updated order price', i, dt)
        else:
            print('invalid update price or order_serial_num in update_order_price !')

    
    def update_order_amount(self, update_amount, order_serial_num, message, i, dt):
        if update_amount > 0 and order_serial_num in self.order_serial_list:
            self.order_size[order_serial_num] = update_amount
            self.order_message[order_serial_num] = message #partially_executed
            self.__add_log('updated order amount', i, dt)
        else:
            print('invalid update amount or order_serial_num in update_order_amount !')


    def __del_order(self, target_serial, i):
        if target_serial in self.order_serial_list:
            self.order_serial_list.remove(target_serial)
            del self.order_side[target_serial]
            del self.order_price[target_serial]
            del self.order_size[target_serial]
            del self.order_i[target_serial]
            del self.order_dt[target_serial]
            del self.order_ut[target_serial]
            del self.order_type[target_serial]  # market / limit
            del self.order_cancel[target_serial] #True / False
            del self.order_message[target_serial]


    #always cancel latest order
    def cancel_order(self, order_serial_num, i, dt):
        if len(self.order_serial_list) > 0:
            if order_serial_num in self.order_serial_list:
                if self.order_cancel[order_serial_num] == False:
                    self.order_cancel[order_serial_num] = True
                else:
                    print('cancel failed!')


    def cancel_all_order(self, i, dt):
        for n in self.order_serial_list:
            self.cancel_order(n, i, dt)


    def exit_all(self, i, dt):
        if self.holding_side != '':
            self.entry_order('market', 'buy' if self.holding_side == 'sell' else 'sell', self.holding_size, 0, i, dt, 'exit all')



    def __calc_fee(self, size, price, maker_taker):
        if maker_taker == 'maker':
            self.total_fee += size * price * self.maker_fee
        elif maker_taker == 'taker':
            self.total_fee += size * price * self.taker_fee
        else:
            print('unknown maker_taker type!', maker_taker)
            pass



    def __check_cancel(self, i, dt):
        #ks = copy.copy(list(self.order_cancel.keys()))
        ks = copy.copy(self.order_serial_list)
        for k in ks:
            if self.order_cancel[k]:
                self.__del_order(k, i)
                self.__add_log('order cancelled.', i, dt)


    def __check_execution(self, i, dt, openp, high, low):
        ks = copy.copy(self.order_serial_list)
        for k in ks:
            if self.order_type[k] == 'market':
                self.num_market_order +=1
                self.__process_execution(openp, k, i, dt)
                self.__del_order(k, i)
            elif self.order_i[k] < i:
                if self.order_type[k] == 'limit' and (self.order_side[k]=='buy' and self.order_price[k] >= low+0.5) or (self.order_side[k]=='sell' and self.order_price[k] <= high-0.5):
                    self.__process_execution(self.order_price[k], k, i, dt)
                    self.__del_order(k, i)
            else:
                pass


    def __process_execution(self, exec_price, k ,i, dt):
        self.__calc_fee(self.order_size[k], exec_price, 'maker' if self.order_type[k] == 'limit' else 'taker')
        if self.holding_side == "":
            if self.order_side[k] == 'buy':
                self.num_buy += 1
            else:
                self.num_sell += 1
            self.__update_holding(self.order_side[k], exec_price, self.order_size[k], i, dt)
            self.__add_log('New Entry:' + self.order_type[k], i, dt)
        elif self.holding_side == self.order_side[k]:
            ave_price = round(((self.holding_price * self.holding_size) + (exec_price * self.order_size[k])) / (self.order_size[k] + self.holding_size), 1)  # averaged holding price
            self.__update_holding(self.holding_side, ave_price, self.order_size[k] + self.holding_size, i, dt)
            self.__add_log('Additional Entry:' + self.order_type[k], i, dt)
        elif self.holding_size > self.order_size[k]:
            self.__calc_executed_pl(exec_price, self.order_size[k], i)
            self.__update_holding(self.holding_side, self.holding_price, self.holding_size - self.order_size[k], i, dt)
            self.__add_log('Exit Order (h>o):' + self.order_type[k], i, dt)
        elif self.holding_size == self.order_size[k]:
            self.__calc_executed_pl(exec_price, self.order_size[k], i)
            self.__initialize_holding()
            self.__add_log('Exit Order (h=o):' + self.order_type[k], i, dt)
        elif self.holding_size < self.order_size[k]:
            if self.order_side[k] == 'buy':
                self.num_buy += 1
            else:
                self.num_sell += 1
            self.__calc_executed_pl(exec_price, self.holding_size, i)
            self.__update_holding(self.order_side[k], exec_price, self.order_size[k] - self.holding_size, i, dt)
            self.__add_log('Exit and Entry Order (h<o):' + self.order_type[k], i, dt)


    def __calc_executed_pl(self, exec_price, size, i):  # assume all order size was executed
        pl = (exec_price - self.holding_price) * size if self.holding_side == 'buy' else (self.holding_price - exec_price) * size
        self.realized_pl += round(pl,6)
        self.unrealized_pl_list.append(round(pl,6))
        self.num_trade += 1
        if pl > 0:
            self.num_win += 1
        if self.holding_side == 'buy':
            self.buy_pl_list.append(round(pl,6))
        else:
            self.sell_pl_list.append(round(pl,6))


    def __add_log(self, log, i, dt):
        self.total_pl_log.append(self.total_pl)
        self.action_log.append(log)
        self.holding_log.append(self.holding_side + ' @' + str(self.holding_price) + ' x' + str(self.holding_size))
        if len(self.order_i) > 0:
            k = self.order_serial_list[-1]
            self.order_log.append(self.order_side[k] + ' @' + str(self.order_price[k]) + ' x' + str(self.order_size[k]) + ' cancel=' + str(self.order_cancel[k]) + ' type=' + self.order_type[k])
        else:
            self.order_log.append('' + ' @' + '0' + ' x' + '0' + ' cancel=' + 'False' + ' type=' + '')
        self.i_log.append(i)
        self.dt_log.append(dt)
        if len(self.order_serial_list) > 0: 
            k=self.order_serial_list[-1]
            #print('i={}, dt={}, action={}, holding side={}, holding price={}, holding size={}, order side={}, order price={}, order size={}, pl={}, num_trade={}'
            #.format(i, dt, log, self.holding_side, self.holding_price, self.holding_size, self.order_side[k], self.order_price[k], self.order_size[k], self.total_pl, self.num_trade))
            self.log_data_list.append({'i':i, 'dt':dt, 'action':log, 'holding_side':self.holding_side,'holding_price':self.holding_price, 'holding_size':self.holding_size, 'order_side':self.order_side[k], 'order_price':self.order_price[k],
                                       'order_size':self.order_size[k], 'total_pl':self.total_pl, 'total_fee':self.total_fee, 'num_trade':self.num_trade})
        else:
            #print(';i={}, dt={}, action={}, holding side={}, holding price={}, holding size={}, order side={}, order price={}, order size={}, pl={}, num_trade={}'.format(i, dt, log, self.holding_side, self.holding_price, self.holding_size, '', '0', '0', self.total_pl, self.num_trade))
            self.log_data_list.append({'i':i, 'dt':dt, 'action':log, 'holding_side':self.holding_side, 'holding_price':self.holding_price, 'holding_size':self.holding_size, 'order_side':0, 'order_price':0, 
                                       'order_size':0, 'total_pl':self.total_pl, 'total_fee':self.total_fee, 'num_trade':self.num_trade})


if __name__ == '__main__':
    print('As')