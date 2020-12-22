from Trade import Trade
from SimAccount import SimAccount

'''
FullyExecuted / Cancelledの時だけholding dataをsize=1としてnn入力する。
よって以下のようなsimとのgapがあり、NNの出力を本当の現状を考慮して適切なactionを判断しないといけない。


1.cancel判断だが、実は既にpartially executedでholdingがある。
->cancelしてpartially executedのholdingを0にする反対売買注文を出す。 -> 
2.cancel & opposite entry判断だが、実は既にpartially executedでholdingがある。
3.現在のbid-askでentryするが、ohlc['close']の方が有利な場合はohlc['close']でのentryとする。
4.判断した直後に既存のorderが全約定した。
5.

結局、partial executedが発生した時に、①holding無しとしてNNに入力する、②holding有りとしてNNに入力する、の2パターンになる。
①holding無しとしてNNに入力する
->NNはholding無しの前提でcancelや反対売買の判断を下す可能性があり、マーケットの値動きによっては（partial executed holding=buyなのにNNがsell判断で価格が下がり続ける）
パフォーマンスが大幅に劣化する原因になる。また潜在的に常に実際と異なる情報でNN判断を下すことになる。
②holding有りとしてNNに入力する
->holding = buyでorder=buyというsimでは有りえない入力データを使ってNN判断下すことになり、パフォーマンスが検証に裏打ちされたものでなくなる。
③holding有りとしてNNに入力するが、orderは残っていても無しとしてNNに入力する。
->NNは全約定として反対売買を判断する ->order cancelしてholding sizeに対して反対売買すればいい
->NNは全約定として保有（buy）を継続し価格が上がり続ける、botは残りのorderをprice updateしながら全約定を目指す。結果として平均約定値が高くなりパフォーマンスが悪化する。 ->避けることができないが、simよりbotの方が約定能力高いので、この場合はsimでも1分毎にprice updateすると思われる。
'''


class Strategy:
    '''
    Botのおいてpartial executedとなった場合は、holding size=1、order=なしとしてNN入力データを作成する。
    Cancel判断されてもholding side=order sideの場合はcancelを実施しない。
    '''
    @classmethod
    def bot_ga_limit_strategy(self, nn_output, amount, max_amount):
        ad = ActionData()
        pred_side = {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        holding_data = BotAccount.get_holding_data()
        order_data = BotAccount.get_order_data(BotAccount.get_order_ids()[-1])
        performance_data = BotAccount.get_performance_data()
        partial_exe_flg = True if (holding_data['side'] == order_data['side'] and holding_data['side'] != '') else False
        if pred_side == 'no':
            pass
        elif pred_side == 'cancel':
            if order_data['side']!='' and partial_exe_flg== False:
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