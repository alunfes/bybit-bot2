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
from NNInputDataGenerator import NNInputDataGenerator
from NN import NN


class OneMinData:
    def initialize(self):
        self.datetime = []
        self.timestamp = []
        self.open = []
        self.high = []
        self.low = []
        self.close = []
        self.size = []
        self.sma = {}
        self.divergence = {}
        self.divergence_scaled = pd.DataFrame()
        self.vola_kyori = {}
        self.vola_kyori_scaled = pd.DataFrame()
        self.vol_ma_divergence = {}
        self.vol_ma_divergence_scaled = pd.DataFrame()
        self.rsi = {}
        self.rsi_scaled = pd.DataFrame()
        self.uwahige = {}
        self.shitahige = {}
        self.uwahige_scaled = pd.DataFrame()
        self.shitahige_scaled = pd.DataFrame()


    def cut_data(self, cut_size):
        self.datetime = self.datetime[-cut_size:]
        self.timestamp = self.timestamp[-cut_size:]
        self.open = self.open[-cut_size:]
        self.high = self.high[-cut_size:]
        self.low = self.low[-cut_size:]
        self.close = self.close[-cut_size:]
        self.size = self.size[-cut_size:]

    def get_df(self):
        return pd.DataFrame({'datetime':self.datetime, 'open':self.open, 'high':self.high, 'low':self.low, 'close':self.close, 'size':self.size})


'''
毎分ohlcを取得してindexを計算する。
'''
class MarketData:
    @classmethod
    def initialize_for_bot(cls, term_list):
        print('started MarketData')
        cls.term_list = term_list
        t = datetime.datetime.now().timestamp()
        #最大のtermのindexの計算に必要なデータを確保するためのtarget from tを計算してデータを取得
        target_from_t = int(t - (t - (t // 60.0) * 60.0)) - int((60 * cls.term_list[-1] * 2.1))
        df = RestAPI.get_ohlc(1, target_from_t)
        cls.__initialize_ohlc(df)
        cls.ohlc_sim_flg = False #Trueの時にSimが最新のohlc / indexデータの取得する。
        cls.ohlc_bot_flg = False #Trueの時にBotが最新のohlc / indexデータの取得する。
        th = threading.Thread(target=cls.__ohlc_thread)
        th.start()


    @classmethod
    def __initialize_ohlc(cls, df):
        cls.ohlc = OneMinData()
        cls.ohlc.initialize()
        cls.ohlc.datetime = list(df['datetime'])
        cls.ohlc.timestamp = list(df['timestamp'])
        cls.ohlc.open = list(df['open'])
        cls.ohlc.high = list(df['high'])
        cls.ohlc.low = list(df['low'])
        cls.ohlc.close = list(df['close'])
        cls.ohlc.size = list(df['size'])
        cls.df = cls.ohlc.get_df()
        cls.calc_sma()
        cls.calc_divergence()
        cls.calc_divergence_scaled()



    '''
    SimとBotから毎分1回ずつアクセスがある。
    sim_bot_flg = 0 or 1 (0:sim, 1:bot)
    '''
    @classmethod
    def get_latest_ohlc(cls, sim_bot_flg):
        if sim_bot_flg==0:
            cls.ohlc_sim_flg = False
        elif sim_bot_flg==1:
            cls.ohlc_bot_flg = False
        else:
            print('MarketData-get_latest_ohlc: Invalid sim_bot_flg !', sim_bot_flg)
        return {'dt':cls.ohlc.datetime[-1], 'open':cls.ohlc.open[-1], 'high':cls.ohlc.high[-1], 'low':cls.ohlc.low[-1], 'close':cls.ohlc.close[-1], 
        'divergence_scaled':cls.ohlc.divergence_scaled.iloc[-1], 'vola_kyori_scaled':cls.ohlc.vola_kyori_scaled.iloc[-1]}


    @classmethod
    def __ohlc_thread(cls):
        print('started MarketData.ohlc_thread')
        t = datetime.datetime.now().timestamp()
        kijun_timestamp = int(t - (t - (t // 60.0) * 60.0)) + 60  # timestampの秒を次の分の0に修正
        while SystemFlg.get_system_flg():
            if kijun_timestamp + 1 <= datetime.datetime.now().timestamp():
                downloaded_df = RestAPI.get_ohlc(1, cls.ohlc.timestamp[-1] - 60)
                buy_vol, sell_vol = RestAPI.get_buysell_vol()
                cls.__add_ohlc_data(downloaded_df)
                print(cls.ohlc.get_df().iloc[-1:])
                print('divergence_scaled')
                print(cls.ohlc.divergence_scaled.iloc[-1:])
                print('vola_kyori_scaled')
                print(cls.ohlc.vola_kyori_scaled.iloc[-1:])
                print('vol_ma_divergence_scaled')
                print(cls.ohlc.vol_ma_divergence_scaled.iloc[-1:])
                print('rsi_scaled')
                print(cls.ohlc.rsi_scaled.iloc[-1:])
                print('uwahige_scaled')
                print(cls.ohlc.uwahige_scaled.iloc[-1:])
                print('shitahige_scaled')
                print(cls.ohlc.shitahige_scaled.iloc[-1:])
                kijun_timestamp += 60
            else:
                time.sleep(1)
        print('stopped MarketData.ohlc_thread!')


    @classmethod
    def __add_ohlc_data(cls, df_ohlc):
        #dt[-1]と同じdf_ohlc['datetime']を見つけてその次からextendする
        matched_index = -1
        for i in range(len(df_ohlc)):
            if cls.ohlc.datetime[-1] == df_ohlc['datetime'].iloc[i]:
                matched_index = i
                break
        if matched_index >= 0:
            cut_size = len(cls.ohlc.datetime)
            cls.ohlc.datetime.extend(list(df_ohlc['datetime'].iloc[matched_index+1:]))
            cls.ohlc.timestamp.extend(list(df_ohlc['timestamp'].iloc[matched_index+1:]))
            cls.ohlc.open.extend(list(df_ohlc['open'].iloc[matched_index+1:]))
            cls.ohlc.high.extend(list(df_ohlc['high'].iloc[matched_index+1:]))
            cls.ohlc.low.extend(list(df_ohlc['low'].iloc[matched_index+1:]))
            cls.ohlc.close.extend(list(df_ohlc['close'].iloc[matched_index+1:]))
            cls.ohlc.size.extend(list(df_ohlc['size'].iloc[matched_index+1:]))
            cls.ohlc.cut_data(cut_size)
            cls.df = cls.ohlc.get_df()
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
            cls.ohlc_sim_flg = True
            cls.ohlc_bot_flg = True
        else:
            print('No matched datetime found in downloaded ohlc data!')
            print(df_ohlc)



    @classmethod
    def __sim_process(cls):
        pass


    @classmethod
    def initialize_for_sim(cls, term_list):
        cls.term_list = term_list
        cls.ohlc = cls.__read_from_csv('./Data/onemin_bybit_opt.csv')
        cls.calc_sma()
        cls.calc_divergence()
        cls.calc_divergence_scaled()


    @classmethod
    def __read_from_csv(cls, file_name):
        ohlc = OneMinData()
        ohlc.initialize()
        cls.df = pd.read_csv(file_name)
        ohlc.dt = list(map(lambda x: datetime.strptime(str(x), '%Y/%m/%d %H:%M:%S'), list(cls.df['datetime'])))
        ohlc.open = list(cls.df['open'])
        ohlc.high = list(cls.df['high'])
        ohlc.low = list(cls.df['low'])
        ohlc.close = list(cls.df['close'])
        ohlc.size = list(cls.df['size'])
        return ohlc

    @classmethod
    def calc_sma(cls):
        for t in cls.term_list:  
            cls.ohlc.sma[t] = cls.df['close'].rolling(window=t).mean()


    @classmethod
    def calc_divergence(cls):
        for t in cls.term_list:
            cls.ohlc.divergence[t] = (cls.df['close'] - cls.ohlc.sma[t]) / cls.ohlc.sma[t]

    @classmethod
    def calc_divergence_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_divergence = pd.DataFrame(MarketData.ohlc.divergence)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_divergence.T)
            cls.ohlc.divergence_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.ohlc.divergence_scaled, 'divergence_scaled')

    @classmethod
    def calc_vola_kyori(cls):
        for t in cls.term_list: 
            change_df = cls.df['close'].pct_change()
            change_df = change_df.pow(2.0)
            cls.ohlc.vola_kyori[t] = change_df.rolling(window=t).mean()

    @classmethod
    def calc_vola_kyori_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_vola_kyori = pd.DataFrame(cls.ohlc.vola_kyori)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_vola_kyori.T)
            cls.ohlc.vola_kyori_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.ohlc.vola_kyori_scaled, 'vola_kyori_scaled')
            

    @classmethod
    def calc_vol_ma_divergence(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            for t in cls.term_list:
                vol_ma = []
                vol_ma = cls.df['size'].rolling(window=t).mean()
                cls.ohlc.vol_ma_divergence[t] = list((np.array(cls.ohlc.size) - np.array(vol_ma)) / np.array(vol_ma))

    @classmethod
    def calc_vol_ma_divergence_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_vol_ma_div = pd.DataFrame(cls.ohlc.vol_ma_divergence)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_vol_ma_div.T)
            cls.ohlc.vol_ma_divergence_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.ohlc.vol_ma_divergence_scaled, 'vol_ma_divergence_scaled')
    

    @classmethod
    def calc_rsi(cls):
        for t in cls.term_list:
            up_list = []
            down_list = []
            cls.ohlc.rsi[t] = []
            r = 0
            for i in range(1, t-1): 
                if cls.ohlc.close[i+1] - cls.ohlc.close[i] > 0:
                    up_list.append(cls.ohlc.close[i+1] - cls.ohlc.close[i])
                    down_list.append(0)
                else:
                    down_list.append(cls.ohlc.close[i+1] - cls.ohlc.close[i])
                    up_list.append(0)
                cls.ohlc.rsi[t].append(np.nan)
            up = sum(up_list) / t
            down = -sum(down_list) / t
            r = up / (up + down)
            cls.ohlc.rsi[t].append(r)
            for i in range(t-1, len(cls.ohlc.close)-1):
                if cls.ohlc.close[i+1] - cls.ohlc.close[i] > 0:
                    up_list.append(cls.ohlc.close[i+1] - cls.ohlc.close[i])
                    down_list.append(0)
                else:
                    down_list.append(cls.ohlc.close[i+1] - cls.ohlc.close[i])
                    up_list.append(0)
                del up_list[0]
                del down_list[0]
                up = sum(up_list) / t
                down = -sum(down_list) / t
                if up == 0 and down == 0:
                    r = 0
                else:
                    r = up / (up + down)
                cls.ohlc.rsi[t].append(r)


    @classmethod
    def calc_rsi_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_rsi = pd.DataFrame(cls.ohlc.rsi)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_rsi.T)
            cls.ohlc.rsi_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.ohlc.rsi_scaled, 'rsi_scaled')


    @classmethod
    def calc_uwahige(cls):
        for t in cls.term_list:
            cls.ohlc.uwahige[t] = []
            for i in range(t):
                cls.ohlc.uwahige[t].append(np.nan)
            for i in range(t, len(cls.ohlc.close)):
                close_list = cls.ohlc.close[i-t:i]
                if close_list[0] > close_list[-1]: #insen
                    cls.ohlc.uwahige[t].append(1000.0 * (max(close_list) - close_list[0]) / close_list[-1] / t)
                else: #yosen
                    cls.ohlc.uwahige[t].append( 1000.0 * (max(close_list) - close_list[-1]) / close_list[-1]/ t)

    @classmethod
    def calc_shitahige(cls):
        for t in cls.term_list:
            cls.ohlc.shitahige[t] = []
            for i in range(t):
                cls.ohlc.shitahige[t].append(np.nan)
            for i in range(t, len(cls.ohlc.close)):
                close_list = cls.ohlc.close[i-t:i]
                if close_list[0] > close_list[-1]: #insen
                    cls.ohlc.shitahige[t].append(1000.0 * (close_list[-1] - min(close_list)) / close_list[-1] / t)
                else: #yosen
                    cls.ohlc.shitahige[t].append( 1000.0 * (close_list[0] - min(close_list)) / close_list[-1]/ t)


    @classmethod
    def calc_uwahige_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_uwahige = pd.DataFrame(cls.ohlc.uwahige)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_uwahige.T)
            cls.ohlc.uwahige_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.ohlc.uwahige_scaled, 'uwahige_scaled')

    
    @classmethod
    def calc_shitahige_scaled(cls):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
            df_shitahige = pd.DataFrame(cls.ohlc.shitahige)
            min_max_scaler = MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(df_shitahige.T)
            cls.ohlc.shitahige_scaled = pd.DataFrame(x_scaled).T
            cls.convert_col_for_scaled_data(cls.ohlc.shitahige_scaled, 'shitahige_scaled')

    @classmethod
    def convert_col_for_scaled_data(cls, data, var_name):
        cols = []
        for c in data:
            cols.append(var_name+'-'+str(c))
        data.columns = cols


    @classmethod
    def generate_df_from_dict(cls):
        df = pd.DataFrame({'dt':cls.ohlc.dt, 'open':cls.ohlc.open, 'high':cls.ohlc.high, 'low':cls.ohlc.low, 'close':cls.ohlc.close, 'size':cls.ohlc.size})
        print('completed generate df')
        return df



if __name__ == '__main__':
    SystemFlg.initialize()
    term_list = list(range(10, 1000, 100))
    MarketData.initialize_for_bot(term_list)
    while True:
        time.sleep(5)

    