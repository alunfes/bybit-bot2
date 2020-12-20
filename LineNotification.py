from functools import partial
import requests
import asyncio
import numpy as np
import matplotlib.pyplot as plt
import json
import os


class LineNotification:
    @classmethod
    def initialize(cls):
        json_dict = json.load(open('./ignore/line.json', 'r'))
        cls.token = json_dict['api_token']
        cls.api_url = json_dict['api_url']
        cls.headers = {"Authorization": "Bearer " + cls.token}
        print('initialized LineNotification')

    @classmethod
    def send_message(cls, message):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(cls.__send_message(message))

    @classmethod
    def send_performance(cls, performance_data): #performance_data{'total_pl':cls.total_pl, 'realized_pl':cls.realized_pl, 'unrealized_pl':cls.unrealized_pl, 'total_fee':cls.total_fee, 'num_trade':cls.num_trade, 'win_rate':cls.win_rate}
        loop = asyncio.new_event_loop()
        loop.run_until_complete(cls.__send_message('\rtotal pl='+str(round(performance_data['total_pl'],4))+'\rrealized pl='+str(performance_data['realized_pl'])+
        '\runrealized pl='+str(performance_data['unrealized_pl'])+'\rtotal fee='+str(round(performance_data['total_fee'],4))+'\rnum trade='+str(performance_data['num_trade'])+
        '\rwin rate='+str(performance_data['win_rate'])))

    @classmethod
    def send_holding(cls, holding_data): #{'side':cls.holding_side, 'size':cls.holding_size, 'price':cls.holding_price, 'i':cls.holding_i, 'period':cls.holding_period}
        loop = asyncio.new_event_loop()
        loop.run_until_complete(cls.__send_message('\r---Holding Data---\rSide: '+holding_data['side'] + '\rPrice: '+str(holding_data['price'])+'\rperiod: '+str(holding_data['period'])))

    @classmethod
    async def __send_message(cls, message):
        payload = {"message": str(message)}
        try:
            res = requests.post(cls.api_url, headers=cls.headers, data=payload, timeout=(6.0))
        except Exception as e:
            print('Line notify error!={}'.format(e))

    @classmethod
    def send_image(cls, image):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(cls.__send_image(image))

    @classmethod
    async def __send_image(cls, image):
        payload = {"imageFile": image}
        try:
            res = requests.post(cls.api_url, headers=cls.headers, params={"message" :  '\rPL Chart'}, files=payload, timeout=(6.0))
        except Exception as e:
            print('Line notify error!={}'.format(e))


if __name__ == '__main__':
    LineNotification.initialize()
    li = [1,2,3,4,3,4,5,6,5,4,3,4,5,6,7]
    plt.plot(li)
    plt.savefig('./ignore/test.jpeg')
    print('kita1')
    LineNotification.send_image(open('./ignore/test.jpeg', 'rb'))
    print('kita')