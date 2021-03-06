from threading import current_thread
from numpy import conjugate
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


      '''
      trading dataをohlcv, bid ask, buy sell volに変換する。
      ＊trading dfは、dt, price, size, sideからなるdataframeとする。
      ＊trading dfのindexはdt
      '''
      def convert_tick_to_ohlcv(self, trading_df):
            all_df = pd.DataFrame()
            buy_df= pd.DataFrame()
            sell_df = pd.DataFrame()
            buy_tmp_df = pd.DataFrame()
            sell_tmp_df = pd.DataFrame()
            all_df = trading_df['price'].resample('1T').ohlc()
            all_df = all_df.assign(size=trading_df['size'].resample('1T').sum())
            buy_tmp_df = trading_df[trading_df['side'] == 'Buy']
            buy_df = buy_tmp_df['price'].resample('1T').ohlc()
            buy_df = buy_df.assign(size=buy_tmp_df['size'].resample('1T').sum())
            sell_tmp_df = trading_df[trading_df['side'] == 'Sell']
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
            ohlcv_df = self.__check_size_replace(all_df)
            ohlcv_df.index.name = 'dt'
            return ohlcv_df


      '''
      直近までのtrading data fileをダウンロードして、全てのファイルデータを読み取りohlcvを計算する。
      all data、buyとsellの3つに分けてohlcを計算して、そこからall data closeと同じclose値がbuy or sellかによってbid / askを特定する。
      （buyのときは、ask=buy close, bid=buy close-0.5）
      '''
      def convert_all_tick_to_ohlcv(self):
            print('Converting tick files to ohlcv data...')
            self.__check_downloaded_file()
            ohlcv_df = pd.DataFrame()
            for d in self.downloaded_file:
                  all_df = pd.DataFrame()
                  tick_df = pd.read_csv('./Data/'+d, compression='gzip', index_col='timestamp')
                  tick_df.index = [datetime.datetime.fromtimestamp(x) for x in tick_df.index]
                  all_df = self.convert_tick_to_ohlcv(tick_df)
                  if len(ohlcv_df) == 0:
                        ohlcv_df = all_df
                  else:
                        ohlcv_df = pd.concat([ohlcv_df, all_df], axis=0)
            ohlcv_df = self.__check_size_replace(ohlcv_df)
            ohlcv_df.index.name = 'dt'
            ohlcv_df.to_csv('./Data/onemin_bybit.csv', index=True)
            pass


      '''
      onemin_bybit.csvの最後の日付の翌日からのデータファイルを取得してohlcvとして追記する。
      (最新データの時刻が59分以外の場合は、latest_dtをその日とする。)

      ・fileの最後の日時を確認＝latest_dt & current_dt
      ・latest_dt.minutes!=59の時はflg_ontheday=falseにする
      ・current_dt +1day
      ・current_dtのファイルからデータを読み込んでohlcに変換
      ・
      '''
      def update_ohlcv(self):
            line_count = 0
            with open('./Data/onemin_bybit.csv') as f:
                  line_count = sum([1 for line in f])
            df = pd.read_csv('./Data/onemin_bybit.csv', skiprows=range(1,line_count - 10))
            print('DownloadMarketData: update_ohlc')
            latest_dt = datetime.datetime.strptime(df.iloc[-1]['dt'], '%Y-%m-%d %H:%M:%S')
            current_dt = latest_dt
            print('latest_dt=', latest_dt)
            self.__check_downloaded_file()
            ohlcv_df = pd.DataFrame()
            flg_ontheday = False #True:last_dt.minute != 59
            num = 0
            if latest_dt.minute != 59:
                  flg_ontheday = True      # 2021-03-10 06:46:00,5
            else:
                  current_dt = current_dt +datetime.timedelta(days=1)
            while True:
                  target_file_name = 'BTCUSD' + str(current_dt.year) + '-' + str(str(current_dt.month).zfill(2)) + '-' + str(str(current_dt.day).zfill(2)) + '.csv.gz' #BTCUSD2021-03-02.csv.gz
                  if target_file_name in self.downloaded_file:
                        tick_df = pd.read_csv('./Data/'+target_file_name, compression='gzip', index_col='timestamp')
                        tick_df.index = [datetime.datetime.fromtimestamp(x) for x in tick_df.index]
                        all_df = self.convert_tick_to_ohlcv(tick_df)
                        print('OHLC update progress: Converted #', num, ' dt=', all_df.index[-1])
                        num += 1
                        if len(ohlcv_df) == 0:
                              ohlcv_df = all_df
                        else:
                              ohlcv_df = pd.concat([ohlcv_df, all_df], axis=0)
                        current_dt = current_dt +datetime.timedelta(days=1)
                  else:
                        break
            ohlcv_df = self.__check_size_replace(ohlcv_df)
            ohlcv_df.index.name = 'dt'
            #最新データの時刻が59分以外の場合に、重複したデータを削除する
            if flg_ontheday:
                  ohlcv_df = ohlcv_df[ohlcv_df.index > latest_dt]
            print('DownloadMarketData: ohlcv_df')
            ohlcv_df.to_csv('./Data/onemin_bybit.csv', mode='a', header=False, index=True)
            print('DonwloadMarketData: Completed update_ohlcv.')
      
      '''
      size==0のものが合った時にohlcを１分前の値と同じにする。
      '''
      def __check_size_replace(self, df):
            num_correction = 0
            for i in range(len(df)):
                  if df['size'].iloc[i] == 0:
                        df['open'].iloc[i], df['high'].iloc[i], df['low'].iloc[i], df['close'].iloc[i], df['size'].iloc[i], df['bid'].iloc[i], df['ask'].iloc[i], df['buy_vol'].iloc[i], df['sell_vol'].iloc[i]  = df['open'].iloc[i-1], df['high'].iloc[i-1], df['low'].iloc[i-1], df['close'].iloc[i-1], 0, df['bid'].iloc[i-1], df['ask'].iloc[i-1], 0, 0
                        num_correction += 1
            if num_correction > 0:
                  print('corrected ', num_correction, ' data.')
                  print(df.iloc[0:])
            return df

      
      '''
      onemin_bybit.csvを読み込んで、データ抜けや不正値が含まれていないかを確認する。
      '''
      def check_all_data(self):
            print('DownloadMarketData: Checking all data...')
            df = pd.read_csv('./Data/onemin_bybit.csv')
            dt = list(map(lambda x: datetime.datetime.strptime(str(x), '%Y-%m-%d %H:%M:%S'), list(cls.df['dt'])))
            df['dt'] = dt
            current_dt = dt[-1]
            for i in range(len(df)):
                  if current_dt != df['dt'].iloc[i]:
                        print('dt=', current_dt, ' is missed !')
                  current_dt = current_dt + +datetime.timedelta(minutes=1)




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