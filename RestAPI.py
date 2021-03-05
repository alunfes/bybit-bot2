import requests
import json
import time
import datetime
import pandas as pd
import threading
from SystemFlg import SystemFlg


'''
GETmethod:
    70 requests per second
    50 requests per second continuously for 2 minutes
POSTmethod:
    50 requests per second
    20 requests per second continuously for 2 minutes
'''



class RestAPI:

    '''
    多くても数日分のohlc取得に使う。
    分の途中でもohlc返すので、最後のデータは使わない。
    interval:ohlcのminutes
    from_utを含んだデータを返す

     Bybit has different IP frequency limits for GET and POST method：

    GETmethod:
        70 requests per second
        50 requests per second continuously for 2 minutes
    POSTmethod:
        50 requests per second
        20 requests per second continuously for 2 minutes
    '''
    @classmethod
    def get_ohlc(cls, interval, from_ut):
        #https://api.bybit.com/v2/public/kline/list?symbol=BTCUSD&interval=1&limit=10&from=1590956090
        '''
        [{'symbol': 'BTCUSD', 'interval': '1', 'open_time': 1590956100, 'open': '9497.5', 'high': '9497.5', 'low': '9497', 'close': '9497', 'volume': '119952', 'turnover': '12.630514759999999'}, {'symbol': 'BTCUSD', 'interval': '1', 'open_time': 1590956160, 'open': '9497', 'high': '9497.5', 'low': '9497', 'close': '9497', 'volume': '71382', 'turnover': '7.516256749999998'}, {'symbol': 'BTCUSD', 'interval': '1', 'open_time': 1590956220, 'open': '9497', 'high': '9497.5', 'low': '9497', 'close': '9497', 'volume': '15624', 'turnover': '1.6451110899999999'}, {'symbol': 'BTCUSD', 'interval': '1', 'open_time': 1590956280, 'open': '9497', 'high': '9501', 'low': '9497', 'close': '9501', 'volume': '204107', 'turnover': '21.486218679999986'}, {'symbol': 'BTCUSD', 'interval': '1', 'open_time': 1590956340, 'open': '9501', 'high': '9505', 'low': '9501', 'close': '9505', 'volume': '92542', 'turnover': '9.736941810000001'}, {'symbol': 'BTCUSD', 'interval': '1', 'open_time': 1590956400, 'open': '9505', 'high': '9505', 'low': '9504.5', 'close': '9505', 'volume': '47031', 'turnover': '4.94804154'}, {'symbol': 'BTCUSD', 'interval': '1', 'open_time': 1590956460, 'open': '9505', 'high': '9505', 'low': '9501.5', 'close': '9501.5', 'volume': '67640', 'turnover': '7.116735020000003'}, {'symbol': 'BTCUSD', 'interval': '1', 'open_time': 1590956520, 'open': '9501.5', 'high': '9502', 'low': '9501.5', 'close': '9502', 'volume': '31054', 'turnover': '3.26817925'}, {'symbol': 'BTCUSD', 'interval': '1', 'open_time': 1590956580, 'open': '9502', 'high': '9502', 'low': '9501.5', 'close': '9501.5', 'volume': '15395', 'turnover': '1.6202682699999995'}, {'symbol': 'BTCUSD', 'interval': '1', 'open_time': 1590956640, 'open': '9501.5', 'high': '9502', 'low': '9497', 'close': '9497', 'volume': '213264', 'turnover': '22.44883971999999'}]
        '''
        url = 'https://api.bybit.com/v2/public/kline/list'
        current_ts = from_ut
        reminaing_limit = 200 #一度に取得できるデータ数で200以下
        timestamp = []
        dt = []
        open = []
        high = []
        low = []
        close = []
        volume = []
        flg = True
        while flg:
            params = {
                'symbol':'BTCUSD',
                'interval':interval,
                'limit':reminaing_limit,
                'from':current_ts
            }
            res = requests.get(url, params=params)
            jdata = res.json()
            if jdata['result'] != None:
                if len(jdata['result']) > 0:
                    timestamp.extend([d.get('open_time') for d in jdata['result']])
                    li = list(map(lambda x: datetime.datetime.strptime(str(datetime.datetime.fromtimestamp(int(x))), '%Y-%m-%d %H:%M:%S'), [d.get('open_time') for d in jdata['result']]))
                    dt.extend(li)
                    open.extend([d.get('open') for d in jdata['result']])
                    high.extend([d.get('high') for d in jdata['result']])
                    low.extend([d.get('low') for d in jdata['result']])
                    close.extend([d.get('close') for d in jdata['result']])
                    volume.extend([d.get('volume') for d in jdata['result']])
                    current_ts = timestamp[-1] + 60
                else:
                    flg = False
                    break
            else:
                flg=False
                break
            time.sleep(0.02)
        df = pd.DataFrame({'timestamp':timestamp, 'datetime':dt, 'open':open, 'high':high, 'low':low, 'close':close, 'size':volume})
        df = df.astype({'timestamp': 'int64', 'datetime':'object', 'open': 'float64', 'high': 'float64', 'low': 'float64', 'close': 'float64', 'size': 'int64'})
        if time.time() - df.iloc[-1]['timestamp'] <= 59: #分の途中でもohlcを返すので、60秒経過しているかチェックして、経過していなければ削除
            df = df.iloc[0:-1]
        return df

    @classmethod
    def get_order_status(cls, order_id):
        #url = 'https://api.bybit.com/v2/private/order'
        url = 'https://api.bybit.com/v2/private/execution/list'
        #url = 'https://api.bybit.com/v2/open-api/order/list'
        params = {
            'order_id': order_id,
            'symbol': 'BTCUSD',
        }
        res = requests.get(url, params=params)
        jdata = res.json()
        #if jdata['result'] != None:

    '''
    target_dt:取得する対象時間
    1000データを取得するが、もし1分のデータが1000以上ある場合はtarget_dt以前の分のデータが出現するまでデータ取得を行う。
    {'ret_code': 0, 'ret_msg': 'OK', 'ext_code': '', 'ext_info': '', 'result': 
    [{'id': 202924334, 'symbol': 'BTCUSD', 'price': 35144.5, 'qty': 97, 'side': 'Buy', 'time': '2021-01-18T04:59:04.396Z'}, 
    {'id': 202924333, 'symbol': 'BTCUSD', 'price': 35144.5, 'qty': 500, 'side': 'Buy', 'time': '2021-01-18T04:59:01.72Z'}, 
    {'id': 202924332, 'symbol': 'BTCUSD', 'price': 35144.5, 'qty': 94, 'side': 'Buy', 'time': '2021-01-18T04:59:00.718Z'}, 
    {'id': 202924331, 'symbol': 'BTCUSD', 'price': 35144, 'qty': 500, 'side': 'Sell', 'time': '2021-01-18T04:58:59.835Z'}, 
    {'id': 202924330, 'symbol': 'BTCUSD', 'price': 35144.5, 'qty': 2989, 'side': 'Buy', 'time': '2021-01-18T04:58:57.727Z'}, 
    {'id': 202924329, 'symbol': 'BTCUSD', 'price': 35144, 'qty': 8, 'side': 'Sell', 'time': '2021-01-18T04:58:56.966Z'}, 
    {'id': 202924328, 'symbol': 'BTCUSD', 'price': 35144, 'qty': 8, 'side': 'Sell', 'time': '2021-01-18T04:58:56.966Z'}, 
    '''
    @classmethod
    def get_public_trading_recoreds(cls, target_dt:datetime):
        print('downloading trading data from API...')
        url = 'https://api.bybit.com/v2/public/trading-records'
        params = {
            'symbol': 'BTCUSD',
            #'from': 1000,From ID. Default: return latest data 
            'limit':1000
        }
        df_list = []
        res = requests.get(url, params=params)
        jdata = res.json()
        df = pd.DataFrame(jdata['result'])
        df['time'] = pd.to_datetime(df['time'])
        #check over 1000data in a minute
        target_dt_con = str(target_dt.year) + '-' + str(target_dt.month).zfill(2)+ '-' + str(target_dt.day).zfill(2)+ 'T' + str(target_dt.hour).zfill(2)+ ':' + str(target_dt.minute).zfill(2) + 'Z'
        target_dt_con = pd.to_datetime(target_dt_con)
        i=0
        df = df.sort_values('id',ascending=True)
        df_list.append(df)
        while True:
            if df_list[-1]['time'].iloc[0] > target_dt_con:
                params = {
                    'symbol': 'BTCUSD',
                    'from': int(df_list[-1]['id'].iloc[0]) - 1000,
                    'limit':1000
                }
                res = requests.get(url, params=params)
                jdata = res.json()
                df2 = pd.DataFrame(jdata['result'])
                df2['time'] = pd.to_datetime(df2['time'])
                #df2 = df2.sort_values('id',ascending=True)
                #df = pd.concat([df2, df], ignore_index=True)
                #df = df.sort_values('id',ascending=True)
                #df = df.reset_index(drop=True)
                #print(i)
                #print(df.iloc[0:])
                df_list.append(df2)
                i+=1
                print(i, df_list[-1].iloc[-1]['time'])
            else:
                break
        df = pd.concat(df_list)
        df = df.sort_values('id',ascending=True)
        df = df.reset_index(drop=True)
        target_dt_str = str(target_dt.year) + '-' + str(target_dt.month).zfill(2)+ '-' + str(target_dt.day).zfill(2)+ 'T' + str(target_dt.hour).zfill(2)+ ':' + str(target_dt.minute).zfill(2) + 'Z'
        before_target_dt = target_dt + datetime.timedelta(minutes=-1)
        before_dt_str = str(before_target_dt.year) + '-' + str(before_target_dt.month).zfill(2)+ '-' + str(before_target_dt.day).zfill(2)+ 'T' + str(before_target_dt.hour).zfill(2)+ ':' + str(before_target_dt.minute).zfill(2) + 'Z'
        #df = df[ (df['time'] > pd.to_datetime(before_dt_str)) & (df['time'] <= pd.to_datetime(target_dt_str))]
        #print('---------------Duplicated List---------------')
        #print(df.duplicated(subset='id'))
        print('---------------Trading Data DF---------------')
        print(df.iloc[0:])
        return df


    @classmethod
    def update_onemin_data(cls):
        #check last datetime in OneMinData.csv
        df = pd.read_csv('./Data/onemin_bybit.csv')
        latest_dt = datetime.datetime.strptime(str(df['dt'].iloc[-1]), '%Y-%m-%d %H:%M:%S') #2019-10-01 00:00:00,8298.5
        print(latest_dt)
        #get trading data from the latest datetime using API
        df_trading = cls.get_public_trading_recoreds(latest_dt)
        df_trading = df_trading.rename(columns={'qty': 'size'})
        print(df_trading.iloc[0:])
        #convert trading data to ohlcv + buy / sell vol
        con_df = df_trading['price'].resample('1T').ohlc()
        con_df = con_df.assign(size=df_trading['size'].resample('1T').sum())
        con_df = con_df.reset_index().rename(columns={'index':'datetime'})
        #add to OneMinData.csv
        


    @classmethod
    def get_rate_limit_status(cls):
        url = 'https://api.bybit.com/v2/private/rate_limit_status'
        res = requests.get(url, params=None)
        return res


    @classmethod
    def update_onemin_data_csv(cls):
        print('updating onemine_data.csv...')
        df_original = pd.read_csv('./Data/onemin_bybit.csv')
        last_dt = datetime.datetime.strptime(df_original.iloc[-1]['datetime'], '%Y-%m-%d %H:%M:%S')
        df_updates = cls.get_ohlc(1, int(last_dt.timestamp())).drop('timestamp', axis=1)
        df_merged = pd.concat([df_original, df_updates.iloc[1:]])
        df_merged = df_merged.reset_index()
        df_merged = df_merged.drop('index', axis=1)
        df_merged.to_csv('./Data/onemin_bybit.csv', index=False)
        print('updated onemine_data.csv with ', len(df_updates), ' data.')
        return df_merged


    @classmethod
    def __ohlc_thread(cls):
        t = datetime.datetime.now().timestamp()
        cls.kijun_timestamp = int(t - (t - (t // 60.0) * 60.0))+ 60 #timestampの秒を次の分の0に修正
        while SystemFlg.get_system_flg():
            if cls.kijun_timestamp <= datetime.datetime.now().timestamp():
                #download last 1m ohlc

                df = cls.get_ohlc(1, cls.kijun_timestamp - 60)
                print(datetime.datetime.now())
                print(df)
                cls.kijun_timestamp += 60
            else:
                time.sleep(1)




if __name__ == '__main__':
    RestAPI.update_onemin_data()
    #ut = datetime.datetime.now().timestamp()
    #print(RestAPI.get_buysell_vol(datetime.datetime.fromtimestamp(ut)+ datetime.timedelta(hours=-500)))
    #print(RestAPI.get_public_trading_recoreds(datetime.datetime.now()+ datetime.timedelta(hours=-1)))
    #print(RestAPI.get_ohlc(1, 1607457000))
    #RestAPI.update_onemin_data_csv()