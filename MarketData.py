import datetime
import time
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from SystemFlg import SystemFlg
from RestAPI import RestAPI
from Sim import Sim
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


class MarketData:
    @classmethod
    def initialize_for_bot(cls, term_list):
        cls.__initialize_nn()
        cls.gene = Gene()
        cls.gene.readWeigth('./Model/best_weight.csv')
        cls.term_list = term_list
        cls.sim = Sim()
        t = datetime.datetime.now().timestamp()
        #最大のtermのindexの計算に必要なデータを確保するためのtarget from tを計算してデータを取得
        target_from_t = int(t - (t - (t // 60.0) * 60.0)) - int((60 * cls.term_list[-1] * 2.1))
        df = RestAPI.get_ohlc(1, target_from_t)
        cls.__initialize_ohlc(df)
        cls.initializa_nn()
        th = threading.Thread(target=cls.__ohlc_thread())
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
    
    @classmethod
    def __initialize_nn(cls):
        cls.nn = NN()
        cls.nn_input_data_generator = NNInputDataGenerator()
        cls.nn_pred = -1
        cls.nn_pred_log = []
        cls.nn_flg = False #nn predが更新されたらTrueにして、
        cls.lock_nn_data = threading.Lock()
    
    @classmethod
    def __calc_nn(cls):
        with cls.lock_nn_data:
            nn_input = cls.nn_input_data_generator.generate_nn_input_data_limit(cls.ohlc.divergence_scaled.iloc[-1])
            nn_outputs = cls.nn.calc_nn(nn_input, cls.gene.num_units, cls.gene.weight_gene1, cls.gene.weight_gene2, cls.gene.bias_gene1, cls.gene.bias_gene2, 1)
            cls.nn_pred = cls.nn.getActivatedUnit(nn_outputs)#{0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[nn_output]
            cls.nn_pred_log.append(cls.nn_pred)
            print('nn output=', cls.nn_pred, ':', {0:'no', 1: 'buy', 2:'sell', 3:'cancel'}[cls.nn_pred])


    @classmethod
    def get_latest_ohlc(cls):
        return {'dt':cls.ohlc.datetime[-1], 'open':cls.ohlc.open[-1], 'high':cls.ohlc.high[-1], 'low':cls.ohlc.low[-1], 'close':cls.ohlc.close[-1]}


    @classmethod
    def __ohlc_thread(cls):
        print('started MarketData.ohlc_thread')
        t = datetime.datetime.now().timestamp()
        kijun_timestamp = int(t - (t - (t // 60.0) * 60.0)) + 60  # timestampの秒を次の分の0に修正
        while SystemFlg.get_system_flg():
            if kijun_timestamp + 1 <= datetime.datetime.now().timestamp():
                downloaded_df = RestAPI.get_ohlc(1, cls.ohlc.timestamp[-1] - 60)
                cls.__add_ohlc_data(downloaded_df)
                print(cls.ohlc.get_df().iloc[-1:])
                cls.__calc_nn()
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
        df_divergence = pd.DataFrame(MarketData.ohlc.divergence)
        min_max_scaler = MinMaxScaler()
        x_scaled = min_max_scaler.fit_transform(df_divergence.T)
        cls.ohlc.divergence_scaled = pd.DataFrame(x_scaled).T

            
    @classmethod
    def generate_df_from_dict(cls):
        df = pd.DataFrame({'datetime':cls.ohlc.dt, 'open':cls.ohlc.open, 'high':cls.ohlc.high, 'low':cls.ohlc.low, 'close':cls.ohlc.close, 'size':cls.ohlc.size})
        print('completed generate df')
        return df



if __name__ == '__main__':
    SystemFlg.initialize()
    term_list = list(range(100, 1000, 100))
    MarketData.initialize_for_bot(term_list)
    while True:
        time.sleep(5)

    