import time
from SystemFlg import SystemFlg
from LineNotification import LineNotification
from Trade import Trade
from MarketData import MarketData
from Bot import Bot
from Sim import Sim
from LogMaster import LogMaster


class MasterThread:
    def __init__(self):
        SystemFlg.initialize()
        LineNotification.initialize()
        Trade.initialize()
        LogMaster.initialize()
        term_list = list(range(100, 1000, 100))
        MarketData.initialize_for_bot(term_list)
        #self.bot = Bot()
        self.sim = Sim()


if __name__ == '__main__':
    mt = MasterThread()
    while True:
        time.sleep(100)


        
