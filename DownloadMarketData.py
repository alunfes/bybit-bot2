import requests
import urllib.request
import pandas as pd
import shutil
import os
import gzip
import glob
import asyncio
import time
import datetime
from bs4 import BeautifulSoup



'''
timestamp  symbol  side   size    price  tickDirection                            trdMatchID  grossValue  homeNotional  foreignNotional
0       1.609632e+09  BTCUSD   Buy   6148  32214.5       PlusTick  e88eae17-ebd8-56f5-9e55-f1858e5cc34e  19084573.0          6148         0.190846
1       1.609632e+09  BTCUSD  Sell  13428  32214.0      MinusTick  e5130848-38eb-5792-b2ce-aad9e04646f6  41683739.0         13428         0.416837
2       1.609632e+09  BTCUSD   Buy      3  32214.5  ZeroMinusTick  27d2f04d-a7f7-5bce-b099-d9e76ded2855      9312.0             3         0.000093
3       1.609632e+09  BTCUSD   Buy      3  32214.5  ZeroMinusTick  ec2ead99-640a-58cc-a682-0c98c1193bdd      9312.0             3         0.000093
4       1.609632e+09  BTCUSD   Buy      3  32214.5       PlusTick  ecb9dd97-ffde-5949-9f84-4da07bb6183f      9312.0             3         0.000093
'''

class DownloadMarketData:
      def __init__(self):
            self.file_urls = []
            self.num_files = 0
            self.downloaded_file = []
            self.target_file = []


      def __check_downloaded_file(self):
            self.downloaded_file = []
            files = glob.glob('./Data/*')
            for file in files:
                  #./Data/BTCUSD2020-05-11.csv.gz
                  if 'BTCUSD' in file:
                        self.downloaded_file.append(file.split('/')[2])
                        #print(file)
            print('checked ', len(self.downloaded_file), ' files are in the Data directory.')

      def __check_download_target_file(self):
            self.target_file = list(set(self.file_urls) - set(self.downloaded_file))
            print('target files=',len(self.target_file))
            #[print(f) for f in self.target_file]


      def get_file_list(self, from_year, from_month, from_day):
            target_url = 'https://public.bybit.com/trading/BTCUSD/'
            r = requests.get(target_url)         #requestsを使って、webから取得
            soup = BeautifulSoup(r.text, 'lxml') #要素を抽出
            for a in soup.find_all('a'):
                  #print(a.get('href'))
                  urlstr = a.get('href').split('-')
                  dt = datetime.datetime(int(urlstr[0].split('BTCUSD')[1]), int(urlstr[1]), int(urlstr[2].split('.')[0]))
                  dt_from = datetime.datetime(from_year, from_month, from_day)
                  if dt >= dt_from:
                        self.file_urls.append(a.get('href'))
                        self.num_files += 1
            return self.file_urls


      def download_file(self, file_url):
            file_name = os.path.basename(file_url)
            res = requests.get(file_url, stream=True)
            if res.status_code == 200:
                  urllib.request.urlretrieve(file_url,"{0}".format(file_name))
                  print('url=', file_url)
                  print('file name=', file_name)
                  shutil.move('./'+file_name, './Data/'+file_name, copy_function = shutil.copy2)
                  '''
                  with open(os.path.basename(file_url), 'wb') as file:
                        #res.raw.decode_content = True
                        #shutil.copyfileobj(res.raw, file)
                        shutil.move(file, './Data')
                        print('downloaded ' + file_name)
                  '''
                  

      def download_all_targets(self):
            for f in self.target_file:
                  self.download_file('https://public.bybit.com/trading/BTCUSD/' + str(f))
                  time.sleep(1)

      def download_all_targets_async(self, from_year, from_month, from_day):
            self.get_file_list(from_year, from_month, from_day)
            self.__check_downloaded_file()
            self.__check_download_target_file()
            loop = asyncio.get_event_loop()
            data = loop.run_until_complete(self.handler(loop))
            print('completed download files !')

      def convert_all_tick_to_ohlcv(self):
            print('Converting tick files to ohlcv data...')
            self.__check_downloaded_file()
            ts, dt, size, price = [], [], [], []
            ohlcv_df = pd.DataFrame()
            i = 0
            for d in self.downloaded_file:
                  df = pd.read_csv('./Data/'+d, compression='gzip')
                  ts.extend(df['timestamp'])
                  for timestamp_data in df['timestamp']:
                        dt.append(datetime.datetime.fromtimestamp(timestamp_data))
                  size.extend(df['size'])
                  price.extend(df['price'])
                  print('Converted file No.', i, ':', d)
                  i += 1
            ohlcv_df = pd.DataFrame({'price':price, 'size':size}, index=dt)
            con_df = ohlcv_df['price'].resample('1T').ohlc()
            con_df = con_df.assign(size=ohlcv_df['size'].resample('1T').sum())
            con_df = con_df.reset_index().rename(columns={'index':'datetime'})
            con_df = self.__check_ohlc_data(con_df)
            con_df.to_csv('./Data/onemin_bybit.csv', index=False)
            print('Generated ohlcv data, ./Data/onemin_bybit.csv')
            print(con_df)


      '''
      all data、buyとsellの3つに分けてohlcを計算して、そこからall data closeと同じclose値がbuy or sellかによってbid / askを特定する。
      （buyのときは、ask=buy close, bid=buy close-0.5）
      '''
      def convert_all_tick_to_ohlcv2(self):
            print('Converting tick files to ohlcv data...')
            self.__check_downloaded_file()
            ohlcv_df = pd.DataFrame()

            for d in self.downloaded_file:
                  all_df = pd.DataFrame()
                  buy_df= pd.DataFrame()
                  sell_df = pd.DataFrame()
                  buy_tmp_df = pd.DataFrame()
                  sell_tmp_df = pd.DataFrame()
                  tick_df = pd.read_csv('./Data/'+d, compression='gzip', index_col='timestamp')
                  tick_df.index = [datetime.datetime.fromtimestamp(x) for x in tick_df.index]
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
                  #use same ohlc, bid, ask as previous(1min before) data for size=0 data
                  '''
                  size_zero_target = all_df[all_df['size'] == 0]
                  if size_zero_target.empty == False:
                        index = all_df.index.get_loc(pd.Timestamp(int(size_zero_target.index[0].timestamp()), unit='s', freq='T'))
                        all_df.iloc[index] = all_df.iloc[index-1]
                        all_df['size'].iloc[index] = 0
                        all_df['buy_vol'].iloc[index] = 0
                        all_df['sell_vol'].iloc[index] = 0
                        print(all_df.iloc[index-3: index+3])
                  '''
                  if len(ohlcv_df) == 0:
                        ohlcv_df = all_df
                  else:
                        ohlcv_df = pd.concat([ohlcv_df, all_df], axis=0)
            ohlcv_df = self.__check_ohlc_data2(ohlcv_df)
            ohlcv_df.index.name = 'dt'
            ohlcv_df.to_csv('./Data/onemin_bybit.csv', index=True)
            print(ohlcv_df.iloc[3485:3490])
            pass


      def __check_ohlc_data(self, df):
            num_correction = 0
            for i in range(len(df)):
                  if df['size'].iloc[i] == 0:
                        df['open'].iloc[i], df['high'].iloc[i], df['low'].iloc[i], df['close'].iloc[i], df['size'].iloc[i]  = df['open'].iloc[i-1], df['high'].iloc[i-1], df['low'].iloc[i-1], df['close'].iloc[i-1], 0
                        num_correction += 1
            print('corrected ', num_correction, ' data.')
            return df

      def __check_ohlc_data2(self, df):
            num_correction = 0
            for i in range(len(df)):
                  if df['size'].iloc[i] == 0:
                        df['open'].iloc[i], df['high'].iloc[i], df['low'].iloc[i], df['close'].iloc[i], df['size'].iloc[i], df['bid'].iloc[i], df['ask'].iloc[i], df['buy_vol'].iloc[i], df['sell_vol'].iloc[i]  = df['open'].iloc[i-1], df['high'].iloc[i-1], df['low'].iloc[i-1], df['close'].iloc[i-1], 0, df['bid'].iloc[i-1], df['ask'].iloc[i-1], 0, 0
                        num_correction += 1
            print('corrected ', num_correction, ' data.')
            return df


      async def handler(self, loop):
            async def async_download_file(f):
                  async with asyncio.Semaphore(1000):
                        return await loop.run_in_executor(None, self.download_file, 'https://public.bybit.com/trading/BTCUSD/' + str(f))
            tasks = [async_download_file(f) for f in self.target_file]
            return await asyncio.gather(*tasks)


if __name__ == '__main__':
      dmd = DownloadMarketData()
      dmd.download_all_targets_async(2017,1,2)
      dmd.convert_all_tick_to_ohlcv2()