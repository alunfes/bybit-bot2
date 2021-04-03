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
            print('2: Mark3etData test')
            print('3: Bot test')
            print('4: Sim')
            print('5: WS Test')
            print('6: Trade Test')
            select = str(input())
            if select == '1':
                print('1: OHLCV data update')
                dmd = DownloadMarketData()
                dmd.download_all_targets_async(2017,1,2)
                dmd.update_ohlcv()
                RestAPI.update_onemin_data()
                break
            elif select == '2':
                print('2: MarketData test')
                term_list = list(range(10, 1000, 100))
                MarketData.initialize_for_bot(term_list, True)
                break
            elif select == '3':
                print('3: Bot test')
                term_list = list(range(10, 1000, 100))
                MarketData.initialize_for_bot(term_list, False)
                bot = Bot(100)
                break
            elif select == '4':
                print('4: Sim')
                pass
                break
            elif select == '5':
                print('5: WS Test')
                pass
                break
            elif select == '6':
                print('6: Trade Test')
                Trade.test_trade()
                break
            else:
                pass       


if __name__ == '__main__':
    mt = MasterThread()


        
