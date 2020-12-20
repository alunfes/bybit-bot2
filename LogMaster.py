import csv
import os
import asyncio
from datetime import  datetime
import threading
import pandas as pd

'''
Sim / Botからlogデータの入力を受け付ける。
データが一定量溜まったらasyncでcsvに書き出す。
他クラスからの要請に応じてデータを渡す。
'''
class LogMaster:
    @classmethod
    def initialize(cls):
        #Sim Log
        cls.__lock_sim_log = threading.Lock()
        cls.__sim_performance_log = {} #{datetime, {performance data}}
        cls.__sim_holding_log = {} #{datetime, {holding data}}
        cls.__sim_order_log = {} #{datetime, [{order data}]}
        cls.__sim_trade_log = {} #{datetime, [{trade log}]}
        #Bot Log
        cls.__lock_bot_log = threading.Lock()
        cls.__bot_performance_log = {} #{datetime, {performance data}}
        cls.__bot_holding_log = {} #{datetime, {holding data}}
        cls.__bot_order_log = {} #{datetime, [{order data}]}
        cls.__bot_trade_log = {} #{datetime, [{trade log}]}
        #Error Log

    @classmethod
    def add_sim_performance_log(cls, dt, performance_data):
        with cls.__lock_sim_log:
            cls.__sim_performance_log[dt] = performance_data
        
    @classmethod
    def add_sim_holding_log(cls, dt, holding_data): #holding_data as dict
        with cls.__lock_sim_log:
            cls.__sim_holding_log[dt] = holding_data

    @classmethod
    def add_sim_order_log(cls, dt, order_data): #order_data as [{}]
        with cls.__lock_sim_log:
            cls.__sim_order_log[dt] = order_data

    @classmethod
    def add_sim_trade_log(cls, dt, trade_log): #trade_log as string
        with cls.__lock_sim_log:
            if dt not in list(cls.__sim_trade_log.keys()):
                cls.__sim_trade_log[dt] = []
                cls.__sim_trade_log[dt].append(trade_log)
            else:
                cls.__sim_trade_log[dt].append(trade_log)

    @classmethod
    def get_sim_performance_log(cls):
        with cls.__lock_sim_log:
            return cls.__sim_performance_log


    @classmethod
    def add_bot_performance_log(cls, dt, performance_data):
        with cls.__lock_bot_log:
            cls.__bot_performance_log[dt] = performance_data
        
    @classmethod
    def add_bot_holding_log(cls, dt, holding_data): #holding_data as dict
        with cls.__lock_bot_log:
            cls.__bot_holding_log[dt] = holding_data

    @classmethod
    def add_bot_order_log(cls, dt, order_data): #order_data as [{}]
        with cls.__lock_bot_log:
            cls.__bot_order_log[dt] = order_data

    @classmethod
    def add_bor_trade_log(cls, dt, trade_log): #trade_log as string
        with cls.__lock_bot_log:
            if dt not in list(cls.__bot_trade_log.keys()):
                cls.__bot_trade_log[dt] = []
                cls.__bot_trade_log[dt].append(trade_log)
            else:
                cls.__bot_trade_log[dt].append(trade_log)

    @classmethod
    def get_bot_performance_log(cls):
        with cls.__lock_bot_log:
            return cls.__bot_performance_log