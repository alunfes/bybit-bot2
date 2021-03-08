import time
from SystemFlg import SystemFlg
from LineNotification import LineNotification
from Trade import Trade
from MarketData import MarketData
from Bot import Bot
from Sim import Sim
from LogMaster import LogMaster
from DownloadMarketData import DownloadMarketData
from RestAPI import RestAPI


class MasterThread:
    def __init__(self):
        SystemFlg.initialize()
        LineNotification.initialize()
        Trade.initialize()
        LogMaster.initialize()
        while True:
            print('Please select program mode.')
            print('1: OHLCV data update')
            print('2: MarketData test')
            print('3: Bot test')
            print('4: Sim')
            select = str(input())
            if select == '1':
                dmd = DownloadMarketData()
                dmd.download_all_targets_async(2017,1,2)
                dmd.update_ohlcv()
                RestAPI.update_onemin_data()
                break
            elif select == '2':
                term_list = list(range(10, 1000, 100))
                MarketData.initialize_for_bot(term_list)
                break
            elif select == '3':
                pass
                break
            elif select == '4':
                pass
                break
            else:
                pass       


if __name__ == '__main__':
    mt = MasterThread()


        
