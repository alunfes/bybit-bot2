from Trade import Trade
from SimAccount import SimAccount
from LineNotification import LineNotification
from BotAccount import BotAccount

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

    1. No / Cancel (NNはorderない前提でNo / Cancelを判断しているので、Cancel判断されてもholding side=order sideの場合はcancelを実施せずupdate priceする。)
    2. New Entry
    3. Update Price
    4. Additional Entry 
    5. Exit (もし既存のadditional orderがあったらまずはそれをキャンセル）
    6. Opposite Order Cancel (orderと逆の判定なので)
    7. Others1 (既にmax amountのholdingがあり、pred side=holding sideで何もしなくて良い場合）
    8. Others2 (holding side== pred sideで既にpred sideのorderが存在しており、update priceも不要な場合）
    9. Others3 (holding side != predで既にexit orderが存在しており、update priceも不要な場合)
    '''
    @classmethod
    def bot_ga_limit_strategy(self, nn_output, amount, max_amount, ohlc):
        ad = ActionData()
        pred_side = {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        holding_data = BotAccount.get_holding_data()
        order_data = BotAccount.get_order_data(order_id)
        performance_data = BotAccount.get_performance_data()
        partial_exe_flg = True if (holding_data['side'] == order_data['side'] and holding_data['side'] != '') else False
        bid_ask = Trade.get_bid_ask()
        #sim performanceに劣後しないためにclose priceよりも不利な価格ではエントリーしない
        buy_entry_price = bid_ask[0] if ohlc['close'] > bid_ask[0] else ohlc['close']
        sell_entry_price = bid_ask[1] if ohlc['close'] < bid_ask[1] else ohlc['close']
        #1. No / Cancel
        if pred_side == 'no':
            #pred_side=Noでも実際にはholding & orderあればupdate priceを実施。
            if holding_data['side'] != '' and order_data['side'] != '' and ((order_data['price'] != bid_ask[0] and order_data['side']=='buy') or (order_data['price'] != bid_ask[1] and order_data['side']=='sell')) :
                ad.add_action('update price', '', '', buy_entry_price if order_data['side']=='buy' else sell_entry_price, order_data['size'], order_data['id'], '1. No: update order price')
        elif pred_side == 'cancel':
            #partial exec == Falseの時だけcancel
            if order_data['side']!='' and partial_exe_flg== False:
                ad.add_action('cancel', '', '', 0, 0, order_data['id'], 'cancel all orders')
            #partial executedのときは必要に応じてupdate price
            elif partial_exe_flg == True and ((order_data['price']!=bid_ask[0] and order_data['side']=='buy') or (order_data['price']!=bid_ask[1] and order_data['side']=='sell')):
                ad.add_action('update price', '', '', buy_entry_price if order_data['side']=='buy' else sell_entry_price, order_data['size'], order_data['id'], '1. Cancel: update order price')
        else:
            #2. New Entry
            if holding_data['side'] == '' and pred_side != order_data['side'] and order_data['side'] == '':
                ad.add_action('entry', pred_side, 'limit', ohlc['close'], amount, -1, '2. New Entry')
            #3.Update Price
            elif order_data['side'] == pred_side and ((order_data['price'] != bid_ask[0] and order_data['side'] == ' buy') or (order_data['price'] != bid_ask[1] and order_data['side'] == ' sell')):
                ad.add_action('update price', '', '', bid_ask[0] if order_data['side']=='buy' else bid_ask[1], -1, order_data[id], '3. update order price')
            #4. Additional Entry (pred = holding sideで現在orderなく、holding sizeにamount加えてもmax_amount以下の時に追加注文）
            elif holding_data['side'] == pred_side and holding_data['size'] + amount <= max_amount and order_data['side'] == '':
                ad.add_action('entry', pred_side, 'limit', bid_ask[0] if order_data['side']=='buy' else bid_ask[1], amount, -1, '4. Additional Entry')
            #5. Exit (holding side != predでかつpred sideのorderがない時にexit orderを出す）
            elif holding_data['side'] != pred_side and holding_data['side'] !='' and pred_side != order_data['side']:
                #もし既存のadditional orderがあったらまずはそれをキャンセル）
                if order_data['side'] !='':
                    ad.add_action('cancel', '', '', 0, 0, order_data['id'], '5. cancel all orders')
                ad.add_action('entry', pred_side, 'limit', bid_ask[0] if order_data['side']=='buy' else bid_ask[1], holding_data['size'], -1, '5. Exit Entry')
            #6. Opposite Order Cancel
            elif pred_side != order_data['side'] and order_data['side'] !='':
                ad.add_action('cancel', '', '', 0, 0, order_data['id'], '6. cancel all orders')
                if holding_data['size'] <= max_amount:
                    ad.add_action('entry', pred_side, 'limit', bid_ask[0] if order_data['side']=='buy' else bid_ask[1], amount, -1, '6. Opposite Entry')
                if holding_data['side'] != '' and holding_data['side'] != pred_side:
                    print('Bot Strategy: Opposite holding exist while cancelling opposite order !')
            else:
                #7. Others1 (既にmax amountのholdingがあり、pred side=holding sideで何もしなくて良い場合）
                if holding_data['size'] >= max_amount and holding_data['side'] == pred_side:
                    pass
                #8.Others2(holding side == pred sideで既にpred sideのorderが存在しており、その価格の更新が不要な場合）
                elif holding_data['side'] == pred_side and order_data['side'] == pred_side and ((order_data['price'] == buy_entry_price and order_data['side']=='buy') or  (order_data['price'] == sell_entry_price and order_data['side']=='sell')):
                    pass
                #9. Others3 (holding side != predで既にexit orderが存在しており、update priceも不要な場合)
                elif holding_data['side'] != pred_side and order_data['side'] == pred_side and ((order_data['price'] == buy_entry_price and order_data['side']=='buy') or  (order_data['price'] == sell_entry_price and order_data['side']=='sell')):
                    pass
                else:
                    print('Bot Strategy - Unknown Situation !')
        return ad





    '''
    1. No / Cancel (Noでorderある場合はupdate price）
    2. New Entry
    3. Update Price
    4. Additional Entry
    5. Exit (もし既存のadditional orderがあったらまずはそれをキャンセル）
    6. Opposite Order Cancel （cancelした上でholding sizeがmax amount以下だったらpred sideのorderを出す）
    7. Others1 (既にmax amountのholdingがあり、pred side=holding sideで何もしなくて良い場合）
    8. Others2 (holding side== pred sideで既にpred sideのorderが存在しており、update priceも不要な場合）
    9. Others3 (holding side != predで既にexit orderが存在しており、update priceも不要な場合)
    '''
    '''
    ・simだと本来約定できない状況でもlimit order executedとして処理されることがある。
    例えば、priceは10000.5/10000で動かない場合でもclose priceは10000.5 / 10000で変動する、sell@10000.5のorderが約定しないのでclose priceにupdateするとsell@10000となる。
    すると次のohlcは価格が動かなくてもhigh=10000.5となるのでlimit sell orderが10000で約定したことになり、0.00025%のmaker fee分の利益が出たようになってしまう。 
    ->entry / price updateはcloseよりも0.5だけ有利な方向にする（i.e. buy orderのときclose=10000でも10000.5にentryするので最低でもbuy/sellに合ったbid_ask値でのentryとなる）
    ->realtime simではその時点のbid_ask値を取って
    '''

    @classmethod
    def sim_ga_limit_strategy(cls, nn_output, amount, max_amount, ohlc):
        ad = ActionData()
        pred_side = {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
        holding_data = SimAccount.get_holding_data()
        update_price_kijun = 3
        bid_ask = Trade.get_bid_ask()
        buy_entry_price = bid_ask[0] - 0.5
        sell_entry_price = bid_ask[1] + 0.5
        #1. No / Cancel
        if pred_side == 'no':
            if SimAccount.getLastOrderSide() != '' and abs(SimAccount.getLastOrderPrice() - (buy_entry_price if SimAccount.getLastOrderSide() == 'buy' else sell_entry_price)) > update_price_kijun:
                ad.add_action('update price', '', '', buy_entry_price if SimAccount.getLastOrderSide() == 'buy' else sell_entry_price, -1, SimAccount.getLastSerialNum(), '1. No: update order price')
        elif pred_side == 'cancel':
            if SimAccount.getLastOrderSide() != '':
                ad.add_action('cancel', '', '', 0, 0, SimAccount.getLastSerialNum(), 'cancel all orders')
        else:
            #2. New Entry
            if holding_data['side'] == '' and pred_side != SimAccount.getLastOrderSide() and SimAccount.getLastOrderSide() == '':
                ad.add_action('entry', pred_side, 'limit', buy_entry_price if SimAccount.getLastOrderSide() == 'buy' else sell_entry_price, amount, -1, '2. New Entry')
            #3.Update Price
            elif SimAccount.getLastOrderSide() == pred_side and abs(SimAccount.getLastOrderPrice() - (buy_entry_price if SimAccount.getLastOrderSide() == 'buy' else sell_entry_price)) > update_price_kijun:
                ad.add_action('update price', '', '', buy_entry_price if SimAccount.getLastOrderSide() == 'buy' else sell_entry_price, -1, SimAccount.getLastSerialNum(), '3. update order price')
            #4. Additional Entry (pred = holding sideで現在orderなく、holding sizeにamount加えてもmax_amount以下の時に追加注文）
            elif holding_data['side'] == pred_side and holding_data['size'] + amount <= max_amount and SimAccount.getLastOrderSide() == '':
                ad.add_action('entry', pred_side, 'limit', buy_entry_price if SimAccount.getLastOrderSide() == 'buy' else sell_entry_price, amount, -1, '4. Additional Entry')
            #5. Exit (holding side != predでかつpred sideのorderがない時にexit orderを出す）
            elif holding_data['side'] != pred_side and holding_data['side'] !='' and pred_side != SimAccount.getLastOrderSide():
                #もし既存のadditional orderがあったらまずはそれをキャンセル）
                if SimAccount.getLastOrderSide() !='':
                    ad.add_action('cancel', '', '', 0, 0, SimAccount.getLastSerialNum(), '5. cancel all orders')
                ad.add_action('entry', pred_side, 'limit', buy_entry_price if SimAccount.getLastOrderSide() == 'buy' else sell_entry_price, holding_data['size'], -1, '5. Exit Entry')
            #6. Opposite Order Cancel
            elif pred_side != SimAccount.getLastOrderSide() and SimAccount.getLastOrderSide() !='':
                ad.add_action('cancel', '', '', 0, 0, SimAccount.getLastSerialNum(), '6. cancel all orders')
                if holding_data['size'] + amount <= max_amount:
                    ad.add_action('entry', pred_side, 'limit', buy_entry_price if SimAccount.getLastOrderSide() == 'buy' else sell_entry_price, amount, -1, '6. Opposite Entry')
                if holding_data['side'] != '' and holding_data['side'] != pred_side:
                    print('Sim Strategy: Opposite holding exist while cancelling opposite order !')
                    LineNotification.send_message('Sim Strategy: Opposite holding exist while cancelling opposite order !')
            else:
                #7. Others1 (既にmax amountのholdingがあり、pred side=holding sideで何もしなくて良い場合）
                if holding_data['size'] >= max_amount and holding_data['side'] == pred_side:
                    pass
                #8.Others2(holding side == pred sideで既にpred sideのorderが存在しており、その価格の更新が不要な場合）
                elif holding_data['side'] == pred_side and SimAccount.getLastOrderSide() == pred_side and abs(SimAccount.getLastOrderPrice() - (buy_entry_price if SimAccount.getLastOrderSide() == 'buy' else sell_entry_price)) <= update_price_kijun:
                    pass
                #9. Others3 (holding side != predで既にexit orderが存在しており、update priceも不要な場合)
                elif holding_data['side'] != pred_side and SimAccount.getLastOrderSide() == abs(SimAccount.getLastOrderPrice() - (buy_entry_price if SimAccount.getLastOrderSide() == 'buy' else sell_entry_price)) <= update_price_kijun:
                    pass
                #10.Others4(holding side == pred sideでorderもない場合）
                elif holding_data['side'] == pred_side and SimAccount.getLastOrderSide() == '':
                    pass
                else:
                    print('Sim Strategy - Unknown Situation !')
                    LineNotification.send_message('Sim Strategy - Unknown Situation !')
        return ad


    @classmethod
    def ga_limit_market_strategy(cls, nn_output, amount, max_amount, order_data, holding_data, account_id):
        ad = ActionData()
        output_action_list = ['no', 'buy', 'sell', 'cancel']
        pred_side = output_action_list[nn_output[0]]
        otype = 'market' if nn_output[1] == 0 else 'limit'
        update_price_kijun = 50
        bid_ask = Trade.get_bid_ask()
        buy_entry_price = bid_ask[0]
        sell_entry_price = bid_ask[1]
        
        if holding_data['size'] > max_amount:
            print('Strategy: ' 'Holding size is larger than max_amount !')
        if pred_side == 'no':
            if order_data['side'] != '' and abs(order_data['price'] - (buy_entry_price if order_data['side'] == 'buy' else sell_entry_price)) > update_price_kijun:
                    ad.add_action('update price', pred_side, otype, buy_entry_price if pred_side == 'buy' else sell_entry_price, -1, order_data['id'], "Update order price")
        elif pred_side == 'cancel':
            if order_data['side'] != '':
                ad.add_action('cancel', '', '', 0, 0, order_data['id'], "1. Cancel: cancel all order")
        else:
            #2. new entry
            if holding_data['side'] == '' and pred_side != order_data['side'] and order_data['side'] == '':
                ad.add_action('entry', pred_side, otype, buy_entry_price if pred_side == 'buy' else sell_entry_price, amount, -1, "New Entry")
            #3.Update Price
            elif order_data['side'] == pred_side and abs(order_data['price'] - (buy_entry_price if order_data['side'] == 'buy' else sell_entry_price)) > update_price_kijun:
                ad.add_action('update price', '', otype, buy_entry_price if pred_side == 'buy' else sell_entry_price, -1, order_data['id'], "Update order price")
            #4. Additional Entry (pred = holding sideで現在orderなく、holding sizeにamount加えてもmax_amount以下の時に追加注文）
            elif holding_data['side'] == pred_side and holding_data['size'] + amount <= max_amount and order_data['side'] == '':
                ad.add_action('entry', pred_side, otype, buy_entry_price if pred_side == 'buy' else sell_entry_price, amount, -1, "Additional Entry")
            #5. Exit (holding side != predでかつpred sideのorderがない時にexit orderを出す）
            elif (holding_data['side'] != pred_side and holding_data['side'] != '') and (pred_side != order_data['side']):
                #もし既存のadditional orderがあったらまずはそれをキャンセル）
                if order_data['side'] != '':
                    ad.add_action('cancel', '', '', 0, 0, order_data['id'], "Cancel order")
                ad.add_action("entry", pred_side, otype, buy_entry_price if pred_side == 'buy' else sell_entry_price, holding_data['size'], -1, "Exit Entry")
            #6. Opposite Order Cancel
            elif pred_side != order_data['side'] and order_data['side'] != '':
                ad.add_action('cancel', '', '', 0, 0, order_data['id'], "6. cancel all order")
                if holding_data['size'] + amount <= max_amount:
                    ad.add_action('entry', pred_side, otype, buy_entry_price if pred_side == 'buy' else sell_entry_price, amount, -1, "Opposite Entry")
                if holding_data['side'] != '' and holding_data['side'] != pred_side:
                    print("Strategy: Opposite holding exist while cancelling opposite order !")
            else:
                #7. Others1 (既にmax amountのholdingがあり、pred side=holding sideで何もしなくて良い場合）
                if holding_data['size'] >= max_amount and holding_data['side'] == pred_side:
                    pass
                #8.Others2(holding side == pred sideで既にpred sideのorderが存在しており、その価格の更新が不要な場合）
                elif holding_data['side'] == pred_side and order_data['side'] == pred_side and abs(order_data['price'] - (buy_entry_price if order_data['side'] == "buy" else sell_entry_price)) <= update_price_kijun:
                    pass
                #9. Others3 (holding side != predで既にexit orderが存在しており、update priceも不要な場合)
                elif holding_data['side'] != pred_side and order_data['side'] == pred_side and abs(order_data['price'] - (buy_entry_price if order_data['side'] == "buy" else sell_entry_price)) <= update_price_kijun:
                    pass
                #10.Others4(holding side == pred sideでorderもない場合）
                elif holding_data['side'] == pred_side and order_data['side'] =='':
                    pass
                else:
                    print("Strategy - Unknown Situation !")
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