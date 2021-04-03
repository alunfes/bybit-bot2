import requests
import json
import time
import datetime
import pandas as pd
import threading
import bybit
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
        #sprint('---------------Trading Data DF---------------')        
        con1 =  [str(x).split('+')[0] for x in df['time']]
        df['time'] =  [datetime.datetime.strptime(str(x).split('.')[0], '%Y-%m-%d %H:%M:%S') for x in con1]
        #print(df.iloc[0:])
        return df


    @classmethod
    def get_privatge_trading_recoreds(cls):
        url = 'https://api.bybit.com/v2/private/execution/list'
        params = {
            'symbol': 'BTCUSD',
            'order':'desc'
        }
        df_list = []
        res = requests.get(url, params=params)
        jdata = res.json()
        df = pd.DataFrame(jdata['result'])
        return df

    '''
    onemin_bybit.csvの最新の日付以降のデータをtrading dataをAPI経由で取得してohlcv + buy/sell volに変換して、onemin_bybit.csvに追記する。
    *この関数を実行する前に最新の日付までのtrading data（csv）をDownloadMarketDataでダウンロードしてonemin_bybit.csvに記録する。
    '''
    @classmethod
    def update_onemin_data(cls):
        #check last datetime in OneMinData.csv
        line_count = 0
        with open('./Data/onemin_bybit.csv') as f:
            line_count = sum([1 for line in f])
        df = pd.read_csv('./Data/onemin_bybit.csv', skiprows=range(1,line_count - 10))
        latest_dt = datetime.datetime.strptime(str(df['dt'].iloc[-1]), '%Y-%m-%d %H:%M:%S') #2019-10-01 00:00:00,8298.5
        #print(latest_dt)
        #get trading data from the latest datetime using API
        current_dt = datetime.datetime.now()
        current_dt = current_dt + datetime.timedelta(seconds=-current_dt.second)
        current_dt = current_dt + datetime.timedelta(microseconds=-current_dt.microsecond)
        df_trading = cls.get_public_trading_recoreds(latest_dt)
        tick_df = df_trading.rename(columns={'qty': 'size', 'time': 'dt'})
        tick_df.index = tick_df['dt']
        #print(tick_df.iloc[0:])
        tick_df = tick_df.drop(columns=['symbol', 'id', 'dt'])
        #convert trading data to ohlcv + buy / sell vol
        ohlcv_df = cls.__convert_trading_data(tick_df)
        #latest_dt以降のデータのみを抽出する（trading dataを1000ずつ取得するとlatest_dt以前のohlcvが含まれることがあるため）
        ohlcv_df = ohlcv_df[ohlcv_df.index > latest_dt ]
        #ohlcv_df = ohlcv_df.iloc[0:-1] 
        ohlcv_df = ohlcv_df[ohlcv_df.index < current_dt] #現在時刻と同じ分のデータはまだohlcv確定していないので削除
        #add to OneMinData.csv
        #print('RestAPI: ohlcv_df')
        #print(ohlcv_df.iloc[0:])
        if len(ohlcv_df) > 0:
            ohlcv_df.to_csv('./Data/onemin_bybit.csv',  mode='a', header=False) #dt,open,high,low,close,size,bid,ask,buy_vol,sell_vol   2021-01-30 23:59:00
            print('RestAPI: Added ', len(ohlcv_df), ' data to onemin_bybit.csv')

    
    '''
    Botが動いている間にMarketDataから毎分ごと(00秒以降）に呼び出されることを想定。
    MarketDataで保持しているohlcvの最新のdatetimeを引数に取る。
    '''
    @classmethod
    def get_ohlcv_update(cls, lastest_dt_onemin:datetime.datetime):
        current_dt = datetime.datetime.now()
        current_dt = current_dt + datetime.timedelta(seconds=-current_dt.second)
        current_dt = current_dt + datetime.timedelta(microseconds=-current_dt.microsecond)
        df_trading = cls.get_public_trading_recoreds(lastest_dt_onemin)
        tick_df = df_trading.rename(columns={'qty': 'size', 'time': 'dt'})
        tick_df.index = tick_df['dt']
        tick_df = tick_df.drop(columns=['symbol', 'id', 'dt'])
        ohlcv_df = cls.__convert_trading_data(tick_df)
        #print('current_dt=',current_dt)
        ohlcv_df = ohlcv_df[ohlcv_df.index < current_dt]
        return ohlcv_df


        
    @classmethod
    def __convert_trading_data(cls, tick_df):
        all_df = tick_df['price'].resample('1T').ohlc()
        all_df = all_df.assign(size=tick_df['size'].resample('1T').sum())
        buy_tmp_df = tick_df[tick_df['side'] == 'Buy']
        buy_df = buy_tmp_df['price'].resample('1T').ohlc()
        buy_df = buy_df.assign(size=buy_tmp_df['size'].resample('1T').sum())
        sell_tmp_df = tick_df[tick_df['side'] == 'Sell']
        sell_df = sell_tmp_df['price'].resample('1T').ohlc()
        sell_df = sell_df.assign(size=sell_tmp_df['size'].resample('1T').sum())
        bid = []
        ask = []
        #1分の間に1回もbuy/sellが無い場合があるので、数が一致しているか確認して、不一致がある場合には同じ時間のohlcvをsize=0として追加する。
        if (len(all_df) == len(buy_df) == len(sell_df)) == False:
            if len(all_df) != len(buy_df):
                    #欠けているindexを特定して、size=0として追加する
                    target_index = list( set(all_df.index) - set(buy_df.index))
                    cop_df = all_df.loc[target_index]
                    cop_df['size']=0
                    con_df = pd.concat([buy_df, cop_df])
                    con_df.sort_index()
                    buy_df = con_df
            if len(all_df) != len(sell_df):
                    #欠けているindexを特定して、size=0として追加する
                    target_index = list( set(all_df.index) - set(sell_df.index))
                    cop_df = all_df.loc[target_index]
                    cop_df['size']=0
                    con_df = pd.concat([sell_df, cop_df])
                    con_df.sort_index()
                    sell_df = con_df
        for i in range(len(all_df)): #calc bid ask
            if all_df['close'].iloc[i] == buy_df['close'].iloc[i]:
                    ask.append(all_df['close'].iloc[i])
                    bid.append(all_df['close'].iloc[i] - 0.5)
            else:
                    bid.append(all_df['close'].iloc[i])
                    ask.append(all_df['close'].iloc[i] + 0.5)
        all_df['bid'] = bid
        all_df['ask'] = ask
        all_df['buy_vol'] = buy_df['size']
        all_df['sell_vol'] = sell_df['size']
        ohlcv_df = cls.__check_ohlc_data2(all_df)
        ohlcv_df.index.name = 'dt'
        return ohlcv_df


    @classmethod
    def __check_ohlc_data2(cls, df):
            num_correction = 0
            for i in range(len(df)):
                  if df['size'].iloc[i] == 0:
                        df['open'].iloc[i], df['high'].iloc[i], df['low'].iloc[i], df['close'].iloc[i], df['size'].iloc[i], df['bid'].iloc[i], df['ask'].iloc[i], df['buy_vol'].iloc[i], df['sell_vol'].iloc[i]  = df['open'].iloc[i-1], df['high'].iloc[i-1], df['low'].iloc[i-1], df['close'].iloc[i-1], 0, df['bid'].iloc[i-1], df['ask'].iloc[i-1], 0, 0
                        num_correction += 1
            if num_correction > 0:
                print('corrected ', num_correction, ' data.')
            return df

    @classmethod
    def get_rate_limit_status(cls):
        url = 'https://api.bybit.com/v2/private/rate_limit_status'
        res = requests.get(url, params=None)
        return res

    '''
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
    '''

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


    @classmethod
    def test(cls):
        df = cls.get_privatge_trading_recoreds()
        print(df)

if __name__ == '__main__':
    RestAPI.test()
    #ut = datetime.datetime.now().timestamp()
    #print(RestAPI.get_buysell_vol(datetime.datetime.fromtimestamp(ut)+ datetime.timedelta(hours=-500)))
    #print(RestAPI.get_public_trading_recoreds(datetime.datetime.now()+ datetime.timedelta(hours=-1)))
    #print(RestAPI.get_ohlc(1, 1607457000))
    #RestAPI.update_onemin_data_csv()