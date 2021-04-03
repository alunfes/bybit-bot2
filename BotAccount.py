import time
import threading
import datetime

from numpy import place

from SystemFlg import SystemFlg
from PrivateWS import PrivateWS, PrivateWSData
from MarketData import MarketData
from Trade import Trade
from LineNotification import LineNotification

'''
Order削除のタイミング：
・leaves_qty=0となった時、order_status = Cancelledとなった時。get_orderで取得した情報を確認しないといけない？
理屈上は、cancelはBotの指示により行われるので正常にキャンセル完了した段階でcancelled_orderを呼び出せばBotAccountで処理できる。


Fee計算：
・約定更新の度にexec_feeを取得してorder_cum_exec_feeに記録。order削除するタイミングで反映。
Pl計算：
・holdingがありholding side != exec_dataのsideの時、exec priceを使って都度plを計算する。
'''
class BotAccount:
    def __init__(self, account_id) -> None:
        self.account_id = account_id
        self.__initialize_order()
        self.__initialize_holding()
        self.__initialize_performance()
        self.__initialize_log()

    def __initialize_order(self):
        self.__lock_order_data = threading.Lock()
        self.order_id = []
        self.order_side = {}
        self.order_price = {}
        self.order_qty = {}
        self.order_leaves_qty = {}
        self.order_type = {}
        self.order_dt= {}
        self.order_status = {} #New, Partially Filled
        self.order_cum_exec_fee = {}
        self.order_checked_exec_id = {} #{order_id:[checked_exec_ids]}

    def __initialize_holding(self):
        self.__lock_holding_data = threading.Lock()
        self.holding_side = ''
        self.holding_price = 0
        self.holding_size = 0
        self.holding_dt = ''
        self.holding_period = 0

    def __initialize_performance(self):
        self.__lock_performance_data = threading.Lock()
        self.total_pl = 0
        self.total_pl_ratio = 0
        self.unrealized_pl = 0
        self.realized_pl = 0
        self.total_fee = 0
        self.num_trade = 0 #holding positionが変わったタイミングをカウント
        self.num_win = 0
        self.num_buy = 0
        self.num_sell = 0
        self.win_rate = 0
        self.num_maker_order = 0 #現状正確な把握が難しい

    def __initialize_log(self):
        self.__lock_log_data = threading.Lock()
        self.__tmp_trade_log = []
        self.trade_log = {}
        self.total_pl_log = []
        self.total_pl_ratio_log = []
        self.unrealized_pl_log = []
        self.realized_pl_log = []
        self.total_fee_log = []

    def __remove_order_data(self, oid):
        with self.__lock_order_data:
            self.order_id.remove(oid)
            del self.order_checked_exec_id[oid]
            del self.order_cum_exec_fee[oid]
            del self.order_dt[oid]
            del self.order_leaves_qty[oid]
            del self.order_price[oid]
            del self.order_qty[oid]
            del self.order_status[oid]
            del self.order_type[oid]
            del self.order_side[oid]

    def get_order_data(self, oid):
        with self.__lock_order_data:
            if oid in self.order_id:
                return {'id':oid, 'dt':self.order_dt[oid] ,'side':self.order_side[oid], 'price':self.order_price[oid], 'qty':self.order_qty[oid]
                ,'leaves_qty':self.order_leaves_qty[oid], 'type':self.order_type[oid], 'status':self.order_status[oid], 'fee':self.order_cum_exec_fee[oid]}
            else:
                print('BotAccount.get_order_data: Unknown order id !', oid)
                LineNotification.send_message('BotAccount.get_order_data: Unknown order id ! - ' +oid)
                return {'id':'', 'dt':'' ,'side':'', 'price':0, 'qty':0,'leaves_qty':0, 'type':'', 'status':'', 'fee':0}

    def get_last_order_data(self):
        with self.__lock_order_data:
            if len(self.order_id) > 0:
                oid = self.order_id[-1]
                return {'id':oid, 'dt':self.order_dt[oid] ,'side':self.order_side[oid], 'price':self.order_price[oid], 'qty':self.order_qty[oid]
                ,'leaves_qty':self.order_leaves_qty[oid], 'type':self.order_type[oid], 'status':self.order_status[oid], 'fee':self.order_cum_exec_fee[oid]}
            else:
                return {'id':'', 'dt':'' ,'side':'', 'price':0, 'qty':0,'leaves_qty':0, 'type':'', 'status':'', 'fee':0}
                
    def get_holding_data(self):
        with self.__lock_holding_data:
            return {'dt':self.holding_dt, 'side':self.holding_side, 'size':self.holding_size, 'price':self.holding_price, 'period':self.holding_period}

    def get_performance_data(self):
        with self.__lock_performance_data:
            return {'total_pl':self.total_pl, 'total_pl_ratio':self.total_pl_ratio, 'unrealized_pl':self.unrealized_pl, 'total_fee':self.total_fee, 'num_trade':self.num_trade,
            'num_win':self.num_win, 'num_buy':self.num_buy, 'num_sell':self.num_sell, 'win_rate':self.win_rate, 'num_maker_order':self.num_maker_order}


    def entry_order(self, id, side, price, qty, type, message):
        with self.__lock_order_data:
            self.order_id.append(id)
            self.order_side[id] = str(side).lower()
            self.order_price[id] = round(float(price),1) if str(type).lower() == 'limit' else 0 #market orderのAPI response priceは板の上下限値になる
            self.order_qty[id] = int(qty)
            self.order_checked_exec_id[id] = []
            self.order_cum_exec_fee[id] = 0
            self.order_type[id] = str(type).lower()
            self.order_dt[id] = datetime.datetime.now()
            self.order_leaves_qty[id] = int(qty)
            self.order_status[id] = 'New'
            print('#', self.account_id, ' - ', message, type, side, ' @', price, ' x', qty)
            LineNotification.send_message('#' + str(self.account_id) + ' - ' + message+ type + ' ' + side+' @'+ str(price)+ ' x' + str(qty))
            self.__tmp_trade_log.append('#' + str(self.account_id) + ' - ' + message+ side+' @'+ str(price)+ ' x' + str(qty))

    def cancel_order(self, oid):
        self.__remove_order_data(oid)
        self.__tmp_trade_log.append('#'+ str(self.account_id) + ' - cancelled order.')
        print('#',self.account_id, ' - cancelled order.')
        LineNotification.send_message('#'+ str(self.account_id) + ' - cancelled order.')

    def update_order_price(self, oid, new_price):
        with self.__lock_order_data:
            if oid in self.order_id:
                self.__tmp_trade_log.append('#' + str(self.account_id) + ' - updated order price from ' + str(self.order_price[oid]) + ' to ' + str(new_price))
                print('#',self.account_id, ' - updated order price from', self.order_price[oid], ' to ', new_price)
                LineNotification.send_message('#' + str(self.account_id) + ' - updated order price from ' + str(self.order_price[oid]) + ' to ' + str(new_price))
                self.order_price[oid] = round(float(new_price),1)
            else:
                self.__tmp_trade_log.append('#' + str(self.account_id) + ' - updated order price but order_id is not existed in BotAccount !')
                print('#',self.account_id, ' - updated order price but order_id is not existed in BotAccount !')
                LineNotification.send_message('#' + str(self.account_id) + ' - updated order price but order_id is not existed in BotAccount !')

    def update_order_amount(self, oid, new_amount):
        with self.__lock_order_data:
            if oid in self.order_id:
                self.__tmp_trade_log.append('#' + str(self.account_id) + ' - updated order amount from ' + str(self.order_qty[oid]) + ' to ' + str(new_amount))
                print('#',self.account_id, ' - updated order amount from', self.order_qty[oid], ' to ', new_amount)
                LineNotification.send_message('#' + str(self.account_id) + ' - updated order amount from ' + str(self.order_qty[oid]) + ' to ' + str(new_amount))
                self.order_leaves_qty[oid] += int(new_amount) - int(self.order_qty[oid])
                self.order_qty[oid] = int(new_amount)
            else:
                self.__tmp_trade_log.append('#' + str(self.account_id) + ' - updated order price but order_id is not existed in BotAccount !')
                print('#',self.account_id, ' - updated order price but order_id is not existed in BotAccount !')
                LineNotification.send_message('#' + str(self.account_id) + ' - updated order price but order_id is not existed in BotAccount !')

    '''
    new entry, additional entry, opposite entryを識別して適切にholding dataを更新
    '''
    def __update_holding_data_execution(self, side, executed_price, executed_qty, pl):
        with self.__lock_holding_data:
            if self.holding_side == '': #new entry
                self.holding_side = str(side).lower()
                self.holding_price = executed_price
                self.holding_period = 0
                self.holding_size = int(executed_qty)
                self.__num_trade_counter(side, pl)
            elif self.holding_side == side: #additional entry
                self.holding_price = (self.holding_price * self.holding_size + executed_price * executed_qty) / (self.holding_size + executed_qty)
                self.holding_size += int(executed_qty)
            else: #exit execution
                if self.holding_size == executed_qty: #exited all position
                    self.__num_trade_counter(side, pl)
                    self.__initialize_holding()
                else: #exit and opposite entry
                    self.holding_side = str(side).lower()
                    self.holding_size = int(executed_qty) - self.holding_size
                    self.holding_price = executed_price
                    self.holding_dt = datetime.datetime.now()
                    self.holding_period =0
                    self.__num_trade_counter(side, pl)

    def __num_trade_counter(self, side, pl):
        self.num_trade += 1
        self.num_win += 1 if pl >0 else 0
        if side == 'buy':
            self.num_buy += 1
        else:
            self.num_sell += 1

    '''

    '''
    def __update_order_data_execution(self, oid, executed_qty, leaves_qty, executed_fee, execution_id):
        if self.order_leaves_qty[oid] < executed_qty: #Partially Executed
            with self.__lock_order_data:
                self.order_leaves_qty[oid] = int(leaves_qty)
                self.order_cum_exec_fee[oid] += executed_fee
                self.order_checked_exec_id[oid].append(execution_id)
                self.order_status[oid] = 'Partially Filled'
        elif self.order_leaves_qty[oid] == executed_qty: #Fully executed
            self.__remove_order_data(oid)
        else:
            print('BotAccount-', self.account_id, ': Larger qty was executed !')
            LineNotification.send_message('BotAccount-'+ str(self.account_id) +  ': Larger qty was executed !')
            self.__remove_order_data(oid)
                
    
    def __add_log(self, i):
        with self.__lock_log_data:
            self.trade_log[i] = self.__tmp_trade_log
            self.total_pl_log.append(self.total_pl)
            self.total_pl_ratio_log.append(self.total_pl_ratio)
            self.unrealized_pl_log.append(self.unrealized_pl)
            self.realized_pl_log.append(self.realized_pl)
            self.total_fee_log.append(self.total_fee)
            self.__tmp_trade_log = []

    def move_to_next(self, dt, i, ohlc_df, order_size):
        if self.holding_side != '':
            self.unrealized_pl = self.holding_size * (self.holding_price - ohlc_df['close'].iloc[-1]) / self.holding_price if self.holding_side == 'buy' else self.holding_size * (self.holding_price - ohlc_df['close'].iloc[-1]) / self.holding_price
        else:
            self.unrealized_pl = 0
        self.total_pl = self.unrealized_pl + self.realized_pl - self.total_fee
        self.total_pl_ratio = round(self.total_pl / order_size, 6)
        if self.num_trade > 0:
            self.win_rate = round(self.num_win / self.num_trade, 4)
        else:
            self.win_rate = 0
        self.num_maker_order = 0
        self.holding_period += 1
        self.__add_log(i)

    '''
    botから与えられるTrade.get_executions()で取得できる直近の約定データにorder idが含まれており、未処理のexec_idか否かを確認する。
    '''
    def check_execution(self, exec_list):
        for d in exec_list:
            if len(self.order_id) == 0:
                break
            if d['info']['order_id'] in self.order_id: #該当するorder idを保有中
                if d['info']['exec_id'] not in self.order_checked_exec_id[d['info']['order_id']]: #約定idを未確認の時
                    self.__process_execution(d)


    '''
    約定の度に都度fee, pl, order, holdingを更新。

    前提条件：
    ・未確認のexec_idが確認済でorder_idを保有中
    '''
    def __process_execution(self, exec_dict):
        oid = exec_dict['info']['order_id']
        if int(exec_dict['info']['leaves_qty']) != self.order_leaves_qty[oid]:
            od = self.get_order_data(oid)
            executed_qty = int(od['leaves_qty']) - int(exec_dict['info']['leaves_qty'])
            executed_fee = float(exec_dict['info']['exec_fee']) * float(exec_dict['info']['exec_price'])
            fee = self.__calc_fee(float(exec_dict['info']['exec_fee']), float(exec_dict['info']['exec_price']))
            pl = self.__calc_realized_pl(exec_dict['info']['side'], float(exec_dict['info']['exec_price']), int(exec_dict['info']['exec_qty']))
            self.__update_order_data_execution(oid, int(exec_dict['info']['exec_qty']), int(exec_dict['info']['leaves_qty']), fee, exec_dict['info']['exec_id'])
            self.__update_holding_data_execution(exec_dict['info']['side'], float(exec_dict['info']['exec_price']), int(exec_dict['info']['exec_qty']), pl)
            print('BotAccount-', self.account_id, ': Executed ', exec_dict['type'], '-', exec_dict['info']['side'], ' order ', '@', float(exec_dict['info']['exec_price']), ' x', int(exec_dict['info']['exec_qty']), ' pl=', pl)
            LineNotification.send_message('BotAccount-' + str(self.account_id) + ': Executed ' + exec_dict['type']+ '-'+ exec_dict['info']['side']+ ' order '+ '@'+ str(float(exec_dict['info']['exec_price']))+ ' x'+ str(int(exec_dict['info']['exec_qty']))+ ' pl='+ str(pl))
        else:
            print('BotAccount-',self.account_id, ':leaves_qty is not matched !')
            print('execution data:')
            print(exec_dict)
            print('order data:')
            print(self.get_order_data(oid))
            LineNotification.send_message('BotAccount-' + str(self.account_id) + ':leaves_qty is not matched !')

    def __calc_fee(self, exec_fee, exec_price):
        fee = exec_fee * exec_price
        with self.__lock_performance_data:
            self.total_fee += fee
        return fee

    def __calc_realized_pl(self, exec_side, exec_price, exec_qty):
        if self.holding_side != '' and self.holding_side != exec_side:
            pl = exec_qty *  (exec_price - self.holding.price if self.holding_side == 'buy' else self.holding.price - exec_price)
            with self.__lock_performance_data:
                self.realized_pl += pl
            return pl
        else:
            return 0