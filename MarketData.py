import datetime
import time
import pandas as pd
import numpy as np
import threading
import warnings
from sklearn.preprocessing import MinMaxScaler
from SystemFlg import SystemFlg
from RestAPI import RestAPI
from Gene import Gene
from NN import NN
from DownloadMarketData import DownloadMarketData


class OneMinData:
    def initialize(self):
        self.__lock_data = threading.Lock()
        self.datetime = []
        self.open = []
        self.high = []
        self.low = []
        self.close = []
        self.size = []
        self.buy_vol = []
        self.sell_vol = []
        self.sma = {}
        self.divergence = {}
        self.divergence_scaled = pd.DataFrame()
        self.vola_kyori = {}
        self.vola_kyori_scaled = pd.DataFrame()
        self.vol_ma_divergence = {}
        self.vol_ma_divergence_scaled = pd.DataFrame()
        self.buysell_vol_ratio = {}
        self.buysell_vol_ratio_scaled = pd.DataFrame()
        self.buysellvol_price_ratio= {}
        self.rsi = {}
        self.rsi_scaled = pd.DataFrame()
        self.uwahige = {}
        self.shitahige = {}
        self.uwahige_scaled = pd.DataFrame()
        self.shitahige_scaled = pd.DataFrame()


    def cut_data(self, cut_size):
        with self.__lock_data:
            self.datetime = self.datetime[-cut_size:]
            self.open = self.open[-cut_size:]
            self.high = self.high[-cut_size:]
            self.low = self.low[-cut_size:]
            self.close = self.close[-cut_size:]
            self.size = self.size[-cut_size:]
            self.buy_vol = self.buy_vol[-cut_size:]
            self.sell_vol = self.sell_vol[-cut_size:]

    def get_ohlc(self):
        with self.__lock_data:
            return pd.DataFrame({'datetime':self.datetime, 'open':self.open, 'high':self.high, 'low':self.low, 'close':self.close, 'size':self.size, 'buy_vol':self.buy_vol, 'sell_vol':self.sell_vol})

    def get_index(self):
        with self.__lock_data:
            return {'divergence_scaled':self.divergence_scaled, 'vola_kyori_scaled':self.vola_kyori_scaled, 'vol_ma_divergence_scaled':self.vol_ma_divergence_scaled, 'buysell_vol_ratio_scaled':self.buysell_vol_ratio_scaled,
            'rsi_scaled':self.rsi_scaled, 'uwahige_scaled':self.uwahige_scaled, 'shitahige_scaled':self.shitahige_scaled}

'''
最初にonemin_bybit.csvを最新のデータに更新する。
onemin_bybitから必要な量のデータを読み込んで、OneMinMarketData = ohlcを更新する。
indexを計算する。
その後は、毎分ohlcを取得してindexを計算する。
'''
class MarketData:
    @classmethod
    def initialize_for_bot(cls, term_list, test_flg):
        print('started MarketData')
        cls.term_list = term_list
        cls.test_flg = test_flg #True:test mode, False:production bot mode
        #update onemin_bybit.csv
        dmd = DownloadMarketData()
        dmd.download_all_targets_async(2017,1,2)
        dmd.update_ohlcv()
        RestAPI.update_onemin_data()
        #最大のtermのindexの計算に必要なデータを確保するためのtarget from tを計算してデータを取得
        cls.md = cls.__read_from_csv('./Data/onemin_bybit.csv') #term_listから必要最小限のデータのみを読み込む機能付き
        cls.__lock_ohlc_flg = threading.Lock()
        cls.__ohlc_flg = False #Trueの時にBotが最新のohlc / indexデータの取得する。
        th = threading.Thread(target=cls.__ohlc_thread)
        th.start()


    @classmethod
    def get_ohlc_flg(cls):
        with cls.__lock_ohlc_flg:
            return cls.__ohlc_flg

    @classmethod
    def get_ohlc(cls):
        with cls.__lock_ohlc_flg:
            cls.__ohlc_flg = False
            return cls.md.get_ohlc()
    
    @classmethod
    def get_index(cls):
        with cls.__lock_ohlc_flg:
            cls.__ohlc_flg = False
            return cls.md.get_index()

    '''
    Botが動いている間、毎分ごとにohlcを更新してindexを計算する。
    '''
    @classmethod
    def __ohlc_thread(cls):
        print('started MarketData.ohlc_thread')
        t = datetime.datetime.now().timestamp()
        kijun_timestamp = int(t - (t - (t // 60.0) * 60.0)) + 60  # timestampの秒を次の分の0に修正
        while SystemFlg.get_system_flg():
            if kijun_timestamp + 1 <= datetime.datetime.now().timestamp():
                downloaded_df = RestAPI.get_ohlcv_update(cls.md.datetime[-1])
                #downloaded_df = RestAPI.get_ohlc(1, cls.md.timestamp[-1] - 60)
                cls.__add_ohlc_data(downloaded_df)
                print(cls.md.get_ohlc().iloc[-1:])
                kijun_timestamp += 60
                if cls.test_flg:
                    print('*******************MarketData OHLCV*******************')
                    print(cls.md.get_ohlc())
                    print('*******************MarketData index*******************')
                    print(cls.md.get_index())
            else:
                time.sleep(1)
        print('stopped MarketData.ohlc_thread!')


    @classmethod
    def __add_ohlc_data(cls, df_ohlc):
        #dt[-1]と同じdf_ohlc['datetime']を見つけてその次からextendする
        matched_index = -1
        for i in range(len(df_ohlc)):
            if cls.md.datetime[-1] == df_ohlc.index[i]:
                matched_index = i
                break
        if matched_index >= 0:
            cut_size = len(cls.md.datetime)
            cls.md.datetime.extend(list(df_ohlc.index[matched_index+1:]))
            cls.md.open.extend(list(df_ohlc['open'].iloc[matched_index+1:]))
            cls.md.high.extend(list(df_ohlc['high'].iloc[matched_index+1:]))
            cls.md.low.extend(list(df_ohlc['low'].iloc[matched_index+1:]))
            cls.md.close.extend(list(df_ohlc['close'].iloc[matched_index+1:]))
            cls.md.size.extend(list(df_ohlc['size'].iloc[matched_index+1:]))
            cls.md.buy_vol.extend(list(df_ohlc['buy_vol'].iloc[matched_index+1:]))
            cls.md.sell_vol.extend(list(df_ohlc['sell_vol'].iloc[matched_index+1:]))
            cls.md.cut_data(cut_size)
            cls.df = cls.md.get_ohlc()
            cls.calc_sma()
            cls.calc_divergence()
            cls.calc_divergence_scaled()
            cls.calc_vola_kyori()
            cls.calc_vola_kyori_scaled()
            cls.calc_vol_ma_divergence()
            cls.calc_vol_ma_divergence_scaled()
            cls.calc_rsi()
            cls.calc_rsi_scaled()
            cls.calc_uwahige()
            cls.calc_shitahige()
            cls.calc_uwahige_scaled()
            cls.calc_shitahige_scaled()
            with cls.__lock_ohlc_flg:
                cls.__ohlc_flg = True
        else:
            print('No matched datetime found in downloaded ohlc data!')
            print(df_ohlc)



    @classmethod
    def __sim_process(cls):
        pass


    @classmethod
    def initialize_for_sim(cls, term_list):
        cls.term_list = term_list
        cls.md = cls.__read_from_csv('./Data/onemin_bybit.csv')
        cls.calc_sma()
        cls.calc_divergence()
        cls.calc_divergence_scaled()


    @classmethod
    def __read_from_csv(cls, file_name):
        ohlc = OneMinData()
        ohlc.initialize()
        line_count = 0
        with open(file_name) as f:
            line_count = sum([1 for line in f])
        #print('line count=', line_count)
        cls.df = pd.read_csv(file_name, skiprows=range(1,line_count - cls.term_list[-1] - 5))
        ohlc.datetime = list(map(lambda x: datetime.datetime.strptime(str(x), '%Y-%m-%d %H:%M:%S'), list(cls.df['dt'])))
        ohlc.open = list(cls.df['open'])
        ohlc.high = list(cls.df['high'])
        ohlc.low = list(cls.df['low'])
        ohlc.close = list(cls.df['close'])
        ohlc.size = list(cls.df['size'])
        ohlc.buy_vol = list(cls.df['buy_vol'])
        ohlc.sell_vol = list(cls.df['sell_vol'])
        return ohlc

    @classmethod
    def calc_sma(cls):
        cls.md.sma = {}
        for t in cls.term_list:  
            cls.md.sma[t] = cls.df['close'].rolling(window=t).mean()


    @classmethod
    def calc_divergence(cls):
        cls.md.divergence = {}
        for t in cls.term_list:
            cls.md.divergence[t] = (cls.df['close'] - cls.md.sma[t]) / cls.md.sma[t]

    @classmethod
    def calc_divergence_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_divergence = pd.DataFrame(cls.md.divergence)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_divergence.T)
            cls.md.divergence_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.md.divergence_scaled, 'divergence_scaled')

    @classmethod
    def calc_vola_kyori(cls):
        cls.md.vola_kyori = {}
        for t in cls.term_list: 
            change_df = cls.df['close'].pct_change()
            change_df = change_df.pow(2.0)
            cls.md.vola_kyori[t] = change_df.rolling(window=t).mean()

    @classmethod
    def calc_vola_kyori_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_vola_kyori = pd.DataFrame(cls.md.vola_kyori)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_vola_kyori.T)
            cls.md.vola_kyori_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.md.vola_kyori_scaled, 'vola_kyori_scaled')
            

    @classmethod
    def calc_vol_ma_divergence(cls):
        cls.md.vol_ma_divergence = {}
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            for t in cls.term_list:
                vol_ma = []
                vol_ma = cls.df['size'].rolling(window=t).mean()
                cls.md.vol_ma_divergence[t] = list((np.array(cls.md.size) - np.array(vol_ma)) / np.array(vol_ma))

    @classmethod
    def calc_vol_ma_divergence_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_vol_ma_div = pd.DataFrame(cls.md.vol_ma_divergence)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_vol_ma_div.T)
            cls.md.vol_ma_divergence_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.md.vol_ma_divergence_scaled, 'vol_ma_divergence_scaled')
    
    @classmethod
    def calc_buysell_vol_ratio(cls):
        cls.md.buysell_vol_ratio = {}
        for t in cls.term_list:
            buy_ma = []
            sell_ma = []
            buy_ma = cls.df['buy_vol'].rolling(window=t).mean()
            sell_ma = cls.df['sell_vol'].rolling(window=t).mean()
            ratio = []
            for i in range(len(buy_ma)):
                if sell_ma[i] > 0:
                    ratio.append(buy_ma[i] / sell_ma[i])
                else:
                    ratio.append(buy_ma[i])
            cls.md.buysell_vol_ratio[t] = ratio


    @classmethod
    def calc_buysell_vol_ratio_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_buysell_vol = pd.DataFrame(cls.md.buysell_vol_ratio)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_buysell_vol.T)
            cls.md.buysell_vol_ratio_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.md.buysell_vol_ratio_scaled, 'buysell_vol_ratio_scaled')

    @classmethod
    def calc_buysell_vol_price_ratio(cls):
        for t in cls.term_list:
            diff_array = [np.nan] * t
            for i in range(t, len(cls.md.close)):
                diff_array.append( (cls.md.close[i]) / cls.md.close[i-t])
            cls.md.buysellvol_price_ratio[t] = list(np.array(diff_array) / np.array(cls.md.buysell_vol_ratio[t]))


    @classmethod
    def calc_rsi(cls):
        cls.md.rsi = {}
        for t in cls.term_list:
            up_list = []
            down_list = []
            cls.md.rsi[t] = []
            r = 0
            for i in range(0, t-1): 
                if cls.md.close[i+1] - cls.md.close[i] > 0:
                    up_list.append(cls.md.close[i+1] - cls.md.close[i])
                    down_list.append(0)
                else:
                    down_list.append(cls.md.close[i+1] - cls.md.close[i])
                    up_list.append(0)
                cls.md.rsi[t].append(np.nan)
            up = sum(up_list) / t
            down = -sum(down_list) / t
            r = up / (up + down)
            cls.md.rsi[t].append(r)
            for i in range(t-1, len(cls.md.close)-1):
                if cls.md.close[i+1] - cls.md.close[i] > 0:
                    up_list.append(cls.md.close[i+1] - cls.md.close[i])
                    down_list.append(0)
                else:
                    down_list.append(cls.md.close[i+1] - cls.md.close[i])
                    up_list.append(0)
                del up_list[0]
                del down_list[0]
                up = sum(up_list) / t
                down = -sum(down_list) / t
                if up == 0 and down == 0:
                    r = 0
                else:
                    r = up / (up + down)
                cls.md.rsi[t].append(r)


    @classmethod
    def calc_rsi_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_rsi = pd.DataFrame(cls.md.rsi)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_rsi.T)
            cls.md.rsi_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.md.rsi_scaled, 'rsi_scaled')


    @classmethod
    def calc_uwahige(cls):
        cls.md.uwahige = {}
        for t in cls.term_list:
            cls.md.uwahige[t] = []
            for i in range(t):
                cls.md.uwahige[t].append(np.nan)
            for i in range(t, len(cls.md.close)):
                close_list = cls.md.close[i-t:i]
                if close_list[0] > close_list[-1]: #insen
                    cls.md.uwahige[t].append(1000.0 * (max(close_list) - close_list[0]) / close_list[-1] / t)
                else: #yosen
                    cls.md.uwahige[t].append( 1000.0 * (max(close_list) - close_list[-1]) / close_list[-1]/ t)

    @classmethod
    def calc_shitahige(cls):
        cls.md.shitahige = {}
        for t in cls.term_list:
            cls.md.shitahige[t] = []
            for i in range(t):
                cls.md.shitahige[t].append(np.nan)
            for i in range(t, len(cls.md.close)):
                close_list = cls.md.close[i-t:i]
                if close_list[0] > close_list[-1]: #insen
                    cls.md.shitahige[t].append(1000.0 * (close_list[-1] - min(close_list)) / close_list[-1] / t)
                else: #yosen
                    cls.md.shitahige[t].append( 1000.0 * (close_list[0] - min(close_list)) / close_list[-1]/ t)


    @classmethod
    def calc_uwahige_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_uwahige = pd.DataFrame(cls.md.uwahige)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_uwahige.T)
            cls.md.uwahige_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.md.uwahige_scaled, 'uwahige_scaled')

    
    @classmethod
    def calc_shitahige_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_shitahige = pd.DataFrame(cls.md.shitahige)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_shitahige.T)
            cls.md.shitahige_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.md.shitahige_scaled, 'shitahige_scaled')

    @classmethod
    def convert_col_for_scaled_data(cls, data, var_name):
        cols = []
        for c in data:
            cols.append(var_name+'-'+str(c))
        data.columns = cols


    @classmethod
    def test(cls):
        term_list = list(range(10, 1000, 100))
        cls.term_list = term_list
        start = time.time()
        cls.md = cls.__read_from_csv('./Data/onemin_bybit.csv')
        elapsed_time = time.time() - start
        print ("read_data_time:{0}".format(elapsed_time) + "[sec]")
        start = time.time()
        cls.calc_sma()
        cls.calc_divergence()
        cls.calc_divergence_scaled()
        cls.calc_vola_kyori()
        cls.calc_vola_kyori_scaled()
        cls.calc_vol_ma_divergence()
        cls.calc_vol_ma_divergence_scaled()
        cls.calc_rsi()
        cls.calc_rsi_scaled()
        cls.calc_uwahige()
        cls.calc_shitahige()
        cls.calc_uwahige_scaled()
        cls.calc_shitahige_scaled()
        elapsed_time = time.time() - start
        print ("calc_data_time:{0}".format(elapsed_time) + "[sec]")

if __name__ == '__main__':
    SystemFlg.initialize()
    MarketData.test()

    