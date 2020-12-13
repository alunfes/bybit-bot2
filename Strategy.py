

class Strategy:
    @classmethod
    def ga_limit_strategy(cls, i, nn_output, amount, max_amount, ac:SimAccount):
        ad = ActionData()
        pred_side = {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        if pred_side == 'no':
            pass
        elif pred_side == 'cancel':
            if ac.getLastSerialNum() > 0:
                ad.add_action('cancel', '', '', 0, 0, ac.order_serial_list[-1], 'cancel all orders')
        else:
            if pred_side == ac.getLastOrderSide():
                if ac.holding_size + ac.getLastOrderSize() < max_amount:
                    ad.add_action('update amount', pred_side, 'limit', 0, ac.getLastOrderSize() + amount, ac.order_serial_list[-1], 'update order amount')
                #if (ac.getLastOrderSide() == 'buy' and OneMinMarketData.ohlc.close[i] > ac.getLastOrderPrice()) or ac.getLastOrderSide() == 'sell' and OneMinMarketData.ohlc.close[i] < ac.getLastOrderPrice():
                if (ac.getLastOrderPrice() != OneMinMarketData.ohlc.close[i]):
                    ad.add_action('update price', pred_side, 'limit', OneMinMarketData.ohlc.close[i], ac.getLastOrderSize(), ac.order_serial_list[-1], 'update order price')
            elif pred_side != ac.getLastOrderSide():
                if ac.getLastOrderSide() != '':
                    ad.add_action('cancel', '', '', 0, 0, ac.order_serial_list[-1], 'cancel all orders')
                if (pred_side == ac.holding_side and ac.holding_size + amount > max_amount) == False:
                    ad.add_action('entry', pred_side, 'limit', OneMinMarketData.ohlc.close[i], amount, -1, 'entry order')
            elif pred_side == ac.holding_side and ac.holding_size + ac.getLastOrderSize() < max_amount:
                ad.add_action('entry', pred_side, 'limit', OneMinMarketData.ohlc.close[i], amount, -1, 'entry order')
            elif pred_side != ac.holding_side and ac.getLastOrderSide() != pred_side:
                ad.add_action('entry', pred_side, 'limit', OneMinMarketData.ohlc.close[i], min([ac.holding_size + amount, ac.holding_size + max_amount]), -1, 'entry order')
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