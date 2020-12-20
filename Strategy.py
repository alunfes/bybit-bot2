from Trade import Trade
from SimAccount import SimAccount

'''
FullyExecuted / Cancelledの時だけholding dataをsize=1としてnn入力する。
よって以下のようなsimとのgapがあり、NNの出力を本当の現状を考慮して適切なactionを判断しないといけない。

・cancel判断だが、実は既にpartially executedでholdingがある。
・cancel & opposite entry判断だが、実は既にpartially executedでholdingがある。
・現在のbid-askでentryするが、ohlc['close']の方が有利な場合はohlc['close']でのentryとする。
・

・Partially executedで実は一部約定済みの時に
'''
class Strategy:
    @classmethod
    def bot_ga_limit_strategy(self, nn_output, amount, max_amount):
        ad = ActionData()
        pred_side = {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        holding_data = SimAccount.get_holding_data()
        if pred_side == 'no':
            pass
        elif pred_side == 'cancel':
            if SimAccount.getLastOrderSide() != '':
                ad.add_action('cancel', '', '', 0, 0, SimAccount.getLastSerialNum(), 'cancel all orders')
        else:
            if pred_side == SimAccount.getLastOrderSide():
                if holding_data['size'] + SimAccount.getLastOrderSize() < max_amount:
                    ad.add_action('update amount', pred_side, 'limit', 0, SimAccount.getLastOrderSize() + amount, SimAccount.getLastSerialNum(), 'update order amount')
                    print('Strategy: hit at update amount!')
                if (SimAccount.getLastOrderPrice() != ohlc['close']):
                    ad.add_action('update price', pred_side, 'limit', ohlc['close'], SimAccount.getLastOrderSize(), SimAccount.getLastSerialNum(), 'update order price')
            elif pred_side != SimAccount.getLastOrderSide():
                if SimAccount.getLastOrderSide() != '':
                    ad.add_action('cancel', '', '', 0, 0, SimAccount.getLastSerialNum(), 'cancel all orders')
                if (pred_side == holding_data['side'] and holding_data['size'] + amount > max_amount) == False:
                    ad.add_action('entry', pred_side, 'limit', ohlc['close'], amount, SimAccount.getLastSerialNum(), 'entry order')
            elif pred_side == holding_data['side'] and holding_data['size'] + SimAccount.getLastOrderSize() < max_amount: #
                ad.add_action('entry', pred_side, 'limit', ohlc['close'], amount, SimAccount.getLastSerialNum(), 'entry order')
            elif pred_side != holding_data['side'] and order_data['side'] != pred_side: #opposite side entry
                ad.add_action('entry', pred_side, 'limit', ohlc['close'], min([holding_data['size'] + amount, holding_data['side'] + max_amount]), SimAccount.getLastSerialNum(), 'entry order')
        return ad



    @classmethod
    def sim_ga_limit_strategy(cls, nn_output, amount, max_amount, ohlc):
        ad = ActionData()
        pred_side = {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        holding_data = SimAccount.get_holding_data()
        if pred_side == 'no':
            pass
        elif pred_side == 'cancel':
            if SimAccount.getLastOrderSide() != '':
                ad.add_action('cancel', '', '', 0, 0, SimAccount.getLastSerialNum(), 'cancel all orders')
        else:
            if pred_side == SimAccount.getLastOrderSide():
                if holding_data['size'] + SimAccount.getLastOrderSize() < max_amount:
                    ad.add_action('update amount', pred_side, 'limit', 0, SimAccount.getLastOrderSize() + amount, SimAccount.getLastSerialNum(), 'update order amount')
                    print('Strategy: hit at update amount!')
                if (SimAccount.getLastOrderPrice() != ohlc['close']):
                    ad.add_action('update price', pred_side, 'limit', ohlc['close'], SimAccount.getLastOrderSize(), SimAccount.getLastSerialNum(), 'update order price')
            elif pred_side != SimAccount.getLastOrderSide():
                if SimAccount.getLastOrderSide() != '':
                    ad.add_action('cancel', '', '', 0, 0, SimAccount.getLastSerialNum(), 'cancel all orders')
                if (pred_side == holding_data['side'] and holding_data['size'] + amount > max_amount) == False:
                    ad.add_action('entry', pred_side, 'limit', ohlc['close'], amount, SimAccount.getLastSerialNum(), 'entry order')
            elif pred_side == holding_data['side'] and holding_data['size'] + SimAccount.getLastOrderSize() < max_amount: #
                ad.add_action('entry', pred_side, 'limit', ohlc['close'], amount, SimAccount.getLastSerialNum(), 'entry order')
            elif pred_side != holding_data['side'] and order_data['side'] != pred_side: #opposite side entry
                ad.add_action('entry', pred_side, 'limit', ohlc['close'], min([holding_data['size'] + amount, holding_data['side'] + max_amount]), SimAccount.getLastSerialNum(), 'entry order')
        return ad


class ActionData:
    def __init__(self):
        self.action = []
        self.order_side = []
        self.order_price = []
        self.order_size = []
        self.order_type = []
        self.order_serial_num = []
        self.order_message = []
    
    def add_action(self, action ,order_side, order_type, order_price, order_size, serial_num, message):
        self.action.append(action)
        self.order_side.append(order_side)
        self.order_price.append(order_price)
        self.order_size.append(order_size)
        self.order_type.append(order_type)
        self.order_serial_num.append(serial_num)
        self.order_message.append(message)