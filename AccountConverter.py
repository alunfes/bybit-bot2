
from Bot import Bot
from SimAccount import SimAccount
from BotAccount import BotAccount

class AccountConverter:
    '''
    '''
    @classmethod
    def convert_bot_account(cls):
        sim_ac = SimAccount()
        hd = BotAccount.get_holding_data()
        if hd['side'] != '':
            sim_ac.holding_side = hd['side']
            sim_ac.holding_price = hd['price']
            sim_ac.holding_size = hd['size']
            sim_ac.holding_dt = hd['dt']
            sim_ac.holding_period = hd['period']
            sim_ac.holding_ut = hd['dt'].timestamp()
        oids = BotAccount.get_order_ids()
        if len(oids) > 0:
            
        od = BotAccount.get_order_data()
        if od['side']
        sim_ac.order_side
        pd = BotAccount.get_performance_data()
        return sim_ac
