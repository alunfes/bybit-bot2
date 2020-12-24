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
    Botのおいてpartial executedとなった場合は、holding size=1、order=なしとしてNN入力データを作成する。（simではholdingとorderが存在していて同じsideとなることがないから）
    Cancel判断されてもholding side=order sideの場合はcancelを実施しない。
    pred_side=Noでも実際にはholding & orderあればupdate priceを実施。（orderだけの場合はsimでもupdate priceとならない）
    pred_side != order_sideの場合に、partial executedの状態となっているときは、orderをキャンセルしてholding_size+amountのpred_side orderを出す。
    '''
    @classmethod
    def bot_ga_limit_strategy(self, nn_output, amount, max_amount):
        ad = ActionData()
        pred_side = {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        order_id = BotAccount.get_order_ids()[-1]
        holding_data = BotAccount.get_holding_data()
        order_data = BotAccount.get_order_data(order_id)
        performance_data = BotAccount.get_performance_data()
        partial_exe_flg = True if (holding_data['side'] == order_data['side'] and holding_data['side'] != '') else False
        bid_ask = Trade.get_bid_ask()
        if pred_side == 'no':
            if holding_data['side'] != '' and order_data['side'] != '':　#pred_side=Noでも実際にはholding & orderあればupdate priceを実施。
                ad.add_action('update price', order_data['side'], 'limit', bid_ask[0] if order_data['side']=='buy' else bid_ask[1], order_data['size'], order_id, 'update order price')
        elif pred_side == 'cancel':
            if order_data['side']!='' and partial_exe_flg== False: #Cancel判断されてもholding side=order sideの場合はcancelを実施しない。
                ad.add_action('cancel', '', '', 0, 0, order_id, 'cancel all orders')
        else:
            if pred_side == order_data['side']:
                if holding_data['size'] + order_data['leaves_qty'] < max_amount: #
                    ad.add_action('update amount', pred_side, 'limit', 0, max_amount - holding_data['size'], order_id, 'update order amount')
                    print('Bot Strategy: hit at update amount!')
                if ((order_data['side'] == 'buy' and order_data['price'] != bid_ask[0]) or (order_data['side'] == 'sell' and order_data['price'] != bid_ask[1])):
                    ad.add_action('update price', pred_side, 'limit', bid_ask[0] if pred_side == 'buy' else bid_ask[1], order_data['size'], order_id, 'update order price')
            elif pred_side != order_data['side']:
                if order_data['side'] != '':
                    ad.add_action('cancel', '', '', 0, 0, order_id, 'cancel all orders')
                    if partial_exe_flg: #pred_side != order_sideの場合に、partial executedの状態となっているときは、orderをキャンセルしてholding_size+amountのpred_side orderを出す。
                        ad.add_action('entry', pred_side, 'limit', bid_ask[0] if pred_side == 'buy' else bid_ask[1], holding_data['size'] + amount, '', 'opposite side entry order')    
                if (pred_side == holding_data['side'] and holding_data['size'] < max_amount) == False: #pred = buy, order=sell, holding=buy -> holding sizeが足りなければ追加する
                    ad.add_action('entry', pred_side, 'limit', ohlc['close'], amount, SimAccount.getLastSerialNum(), 'entry order')
            elif pred_side == holding_data['side'] and holding_data['size'] + SimAccount.getLastOrderSize() < max_amount: #
                ad.add_action('entry', pred_side, 'limit', ohlc['close'], amount, SimAccount.getLastSerialNum(), 'entry order')
            elif pred_side != holding_data['side'] and order_data['side'] != pred_side: #opposite side entry
                ad.add_action('entry', pred_side, 'limit', ohlc['close'], min([holding_data['size'] + amount, holding_data['side'] + max_amount]), SimAccount.getLastSerialNum(), 'entry order')
        return ad



    '''
    1. No / Cancel
    2. New Entry
    3. Update Price
    4. Additional Entry
    5. Exit (もし既存のadditional orderがあったらまずはそれをキャンセル）
    6. Opposite Order Cancel
    7. Others1 (既にmax amountのholdingがあり、pred side=holding sideで何もしなくて良い場合）
    8. Others2 (holding side== pred sideで既にpred sideのorderが存在しており、update priceも不要な場合）
    9. Others3 (holding side != predで既にexit orderが存在しており、update priceも不要な場合)
    '''
    @classmethod
    def sim_ga_limit_strategy(cls, nn_output, amount, max_amount, ohlc):
        ad = ActionData()
        pred_side = {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        holding_data = SimAccount.get_holding_data()

        #1. No / Cancel
        if pred_side == 'no':
            pass
        elif pred_side == 'cancel':
            if SimAccount.getLastOrderSide() != '':
                ad.add_action('cancel', '', '', 0, 0, SimAccount.getLastSerialNum(), 'cancel all orders')
        else:
            #2. New Entry
            if holding_data['side'] == '' and pred_side != SimAccount.getLastOrderSide():
                ad.add_action('entry', pred_side, 'limit', ohlc['close'], amount, -1, 'New Entry')
            #3.Update Price
            elif SimAccount.getLastOrderSide() == pred_side and SimAccount.getLastOrderPrice() != ohlc['close']:
                ad.add_action('update price', '', 'limit', ohlc['close'], -1, SimAccount.getLastSerialNum(), 'update order price')
            #4. Additional Entry (pred = holding sideで現在orderなく、holding sizeにamount加えてもmax_amount以下の時に追加注文）
            elif holding_data['side'] == pred_side and holding_data['size'] + amount <= max_amount and SimAccount.getLastOrderSide() == '':
                ad.add_action('entry', pred_side, 'limit', ohlc['close'], amount, -1, 'Additional Entry')
            #5. Exit (holding side != predでかつpred sideのorderがない時にexit orderを出す）
            elif holding_data['side'] != pred_side and holding_data['side'] !='' and pred_side != SimAccount.getLastOrderSide():
                #もし既存のadditional orderがあったらまずはそれをキャンセル）
                if SimAccount.getLastOrderSide() !='':
                    ad.add_action('cancel', '', '', 0, 0, SimAccount.getLastSerialNum(), 'cancel all orders')
                ad.add_action('entry', pred_side, 'limit', ohlc['close'], holding_data['size'], -1, 'Exit Entry')
            #6. Opposite Order Cancel
            elif pred_side != SimAccount.getLastOrderSide() and SimAccount.getLastOrderSide() !='':
                ad.add_action('cancel', '', '', 0, 0, SimAccount.getLastSerialNum(), 'cancel all orders')
            else:
                #7. Others1 (既にmax amountのholdingがあり、pred side=holding sideで何もしなくて良い場合）
                if holding_data['size'] >= max_amount and holding_data['side'] == pred_side:
                    pass
                #8.Others2(holding side == pred sideで既にpred sideのorderが存在しており、その価格の更新が不要な場合）
                elif holding_data['side'] == pred_side and SimAccount.getLastOrderSide() == pred_side and SimAccount.getLastOrderPrice() == ohlc['close']:
                    pass
                #9. Others3 (holding side != predで既にexit orderが存在しており、update priceも不要な場合)
                elif holding_data['side'] != pred_side and SimAccount.getLastOrderSide() == pred_side and SimAccount.getLastOrderPrice() == ohlc['close']:
                    pass
                else:
                    print('Sim Strategy - Unknown Situation !')
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