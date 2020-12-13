from MarketData import MarketData
from LineNotification import LineNotification
from Trade import Trade
from BotAccount import BotAccount
from SystemFlg import SystemFlg
import threading
import time

'''
x`
'''
class Bot():
    def __init__(self):
        print('started bot')
        LineNotification.initialize()
        Trade.initialize()
        term_list = list(range(100, 1000, 100))
        MarketData.initialize_for_bot(term_list)
        BotAccount.initialize()
        th = threading.Thread(target=self.__bot_thread)
        th.start()
        


    def __bot_thread(self):
        #
        time.sleep(1)


if __name__ == '__main__':
    while True:
        time.sleep(0.1)