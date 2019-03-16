import websocket
import numpy
import json
import pandas
from sklearn import *
import statsmodels.tsa.stattools as ts
from scipy import stats
import statsmodels.api as sm
import warnings
warnings.filterwarnings("error")
import ta
from IPython.display import clear_output, Audio
from IPython.display import Audio
from ipywidgets import interact, interactive, fixed, interact_manual
import matplotlib.pyplot
import random
import re
import os
import multiprocessing
from itertools import chain

class Pair:
    
    sym = ''
    ws = None
    pid = ''
    prices = pandas.DataFrame()
    
    period = 1
    size = 130
    digit_percent = dict();
    autotrade = False
    alert = False
    g2 = 0
    l7 = 0
    not45 = 0
    cids0 = dict()
    fail_trade = 0
    
    def __init__(self, symbol, dataframe, pid, ws, size, sh_obj):
        numpy.seterr(divide='ignore', invalid='ignore')
        self.sh_obj = sh_obj
        self.size = size
        self.sym = symbol
        self.ws = ws
        self.pid = pid
        self.get_historical_data("ticks")
        return
    
    def update(self, df, sh_obj):
        self.sh_obj = sh_obj
        if(len(self.prices.index) > 0):
            quote = str(df.loc[df.index[0]]['prices'])
            before, after = quote.split('.')
            self.lastdigit0 = int(before)%10
            self.lastdigit1 = int(after)%10
            self.prices = pandas.concat([self.prices, df])
            self._cursec = self.prices.index[len(self.prices.index)-1].second
            
            if(self.prices.index[len(self.prices.index)-1].hour == self.prices.index[0].hour):
                while(abs(self.prices.index[len(self.prices.index)-1].minute - self.prices.index[0].minute) > 1):
                    self.prices = self.prices.drop(self.prices.index[0])
                    pass
                pass
            else:
                while(abs(abs(self.prices.index[len(self.prices.index)-1].minute - self.prices.index[0].minute) - 60) > 1):
                    self.prices = self.prices.drop(self.prices.index[0])
                    pass
                pass
                    
            for x in range(0, 10):
                self.digit_percent[x] = (len([y for y in self.prices['prices'] if self.getlastdigit(y, x) == True]) * 100) / len(self.prices.index)
                pass
            
            self.g2 = sum([v for k, v in self.digit_percent.items() if k > 2])
            self.l7 = sum([v for k, v in self.digit_percent.items() if k < 7])
            self.not45 = sum([v for k, v in self.digit_percent.items() if not(k == 4 or k == 5)])
            pass
        else:
            self.prices = df
            pass
        self.logic()
        return
    
    def getlastdigit(self, y, x):
        quote = str(y)
        before, after = quote.split('.')
        y = int(after)%10
        if(x == y):
            return True
        else:
            return False
        return
    
    def logic(self):
        limit = 85
        if(self.sh_obj.autotrade == True and self.sh_obj.api_limit > 1 and self._cursec >= 25):
            if(self.sh_obj.isTraded == False and (self.lastdigit1 == 4 or self.lastdigit1 == 5) and self.sh_obj.trade_ou45 == True):
                if (self.sh_obj.balance - ( 2 * self.sh_obj.ou_stake0) > 0) :
                    if (self.fail_trade < 1 and self.not45 > limit and len(self.cids0) == 0) :
                        self.sh_obj.isTraded = True
                        self.cids0 = {}
                        self.sh_obj.api_limit -= 2
                        self.TRADE_ONE_BARRIER(str(self.sh_obj.ou_stake0), "DIGITOVER", 1, "t", 5)
                        self.TRADE_ONE_BARRIER(str(self.sh_obj.ou_stake0), "DIGITUNDER", 1, "t", 4)
                        pass
                    pass
                else:
                    display(Audio(numpy.sin(numpy.linspace(0, 4 * 4 * numpy.pi, 25)), rate=25000, autoplay=True))
                    pass
                pass
            pass
        
        limit = 80
        if(self.sh_obj.autotrade == True and self.sh_obj.api_limit > 1 and self._cursec >= 25):
            if(self.sh_obj.isTraded == False and (self.lastdigit1 <= 2 or self.lastdigit1 >= 7) and self.sh_obj.trade_ou27 == True):
                if (self.sh_obj.balance - ( 2 * self.sh_obj.ou_stake1) > 0) :
                    if (self.fail_trade < 1 and self.g2 >= limit ) :
                        self.sh_obj.isTraded = True
                        self.sh_obj.api_limit -= 1
                        self.TRADE_ONE_BARRIER(str(self.sh_obj.ou_stake1), "DIGITOVER", 1, "t", 2)
                    elif (self.fail_trade < 1 and self.l7 >= limit ) :
                        self.sh_obj.isTraded = True
                        self.sh_obj.api_limit -= 1
                        self.TRADE_ONE_BARRIER(str(self.sh_obj.ou_stake1), "DIGITUNDER", 1, "t", 7)
                        pass
                else:
                    display(Audio(numpy.sin(numpy.linspace(0, 4 * 4 * numpy.pi, 25)), rate=25000, autoplay=True))
                    pass
                pass
            pass
        
        if(self.sh_obj.autotrade == True and self.sh_obj.api_limit > 0 and self._cursec >= 25):
            if(self.sh_obj.isTraded == False and self.sh_obj.trade_diff == True):
                if (self.sh_obj.balance - self.sh_obj.diff_stake > 0):
                    if (self.fail_trade < 1 and (self.lastdigit0 == self.lastdigit1) and self.digit_percent[self.lastdigit1] <= 3):
                        self.sh_obj.isTraded = True
                        self.sh_obj.api_limit-=1
                        self.TRADE_ONE_BARRIER(str(self.sh_obj.diff_stake), "DIGITDIFF", 1, "t", self.lastdigit1)
                    elif(self.fail_trade < 1):
                        i = [k for k, v in self.digit_percent.items() if v == min(self.digit_percent.values())][0]
                        self.sh_obj.isTraded = True
                        self.sh_obj.api_limit-=1
                        self.TRADE_ONE_BARRIER(str(self.sh_obj.diff_stake), "DIGITDIFF", 1, "t", i)
                        pass  
                else:
                    display(Audio(numpy.sin(numpy.linspace(0, 4 * 4 * numpy.pi, 25)), rate=25000, autoplay=True))
                    pass
                pass
            pass
                 
            #try:
            #    if(self.alert == True): display(Audio(numpy.sin(numpy.linspace(0, 3000, 10000)), rate=200000, autoplay=True));
            #    if (self.automate == True): self.higher_lower();
            #    pass
            #except:
            #    pass
        return
    
    def TRADE_ONE_BARRIER(self, stake, contract_type, duration, duration_unit, digit):
        self.ws.send(json.dumps({
            "buy": 1,
            "price": stake,
            "parameters" : {
              "amount": stake,
              "basis": "stake",
              "contract_type": contract_type,
              "currency": "USD",
              "duration": duration,
              "duration_unit": duration_unit,
              "barrier": digit,
              "symbol": self.sym
            },
            "subscribe": 1}))
        return
    
    def TRADE_NO_BARRIER(self, stake, contract_type, duration, duration_unit):
        self.ws.send(json.dumps({
            "buy": 1,
            "price": stake,
            "parameters" : {
              "amount": stake,
              "basis": "stake",
              "contract_type": contract_type,
              "currency": "USD",
              "duration": duration,
              "duration_unit": duration_unit,
              "symbol": self.sym
            },
            "subscribe": 1}))
        return
    
    def get_historical_data(self, _type):
        try:
            self.ws.send(json.dumps({"ticks_history": self.sym,
              "end": "latest",
              "start": 1,
              "style": _type,
              "adjust_start_time": 1,
              "count": self.size}))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
        return
    
    def process_transaction(self, contract_id, contract_type, profit, status):
        self.sh_obj.balance += profit;
        self.sh_obj.balance = round(self.sh_obj.balance, 2)
        if(status == "buy"):
            self.sh_obj.isTraded = True
            pass
        elif(status == "won"):
            if(contract_type == "CALLE" or contract_type == "PUTE"):
                self.sh_obj.stake = 0.35;
                pass
            elif(contract_type == "DIGITOVER" or contract_type == "DIGITUNDER"):
                if(self.sh_obj.trade_ou45 == True):
                    self.sh_obj.ou_count+=1;
                    self.cids0[contract_id] = profit;
                    if(self.sh_obj.ou_count == 2):
                        if(sum(self.cids0.values()) <= 0):
                            self.fail_trade+=1;
                            self.sh_obj.ou_stake0 *= 5.92;
                            pass
                        else:
                            self.sh_obj.ou_stake0 = 0.35;
                            pass
                        self.sh_obj.ou_count = 0;
                        self.cids0.clear();
                        pass
                    pass
                elif(self.sh_obj.trade_ou27 == True):
                    self.sh_obj.ou_stake1 = 0.35;
                    pass
                pass
            elif(contract_type == "DIGITDIFF"):
                self.sh_obj.diff_stake = 1;
                pass
            for sym in self.sh_obj.prs.keys():
                self.sh_obj.prs[sym].fail_trade = 0;
            self.reset();
            pass
        elif(status == "lost"):
            if(contract_type == "CALLE" or contract_type == "PUTE"):
                self.fail_trade+=1
                self.sh_obj.stake *= 2.2
                pass
            elif(contract_type == "DIGITOVER" or contract_type == "DIGITUNDER"):
                if(self.sh_obj.trade_ou45 == True):
                    self.sh_obj.ou_count+=1
                    self.cids0[contract_id] = profit;
                    if(self.sh_obj.ou_count == 2):
                        if(sum(self.cids0.values()) <= 0):
                            self.fail_trade+=1
                            self.sh_obj.ou_stake0 *= 5.92
                            pass
                        else:
                            self.sh_obj.ou_stake0 = 0.35
                            pass
                        self.sh_obj.ou_count = 0;
                        self.cids0 = {}
                        pass
                    pass
                elif(self.sh_obj.trade_ou27 == True):
                    self.fail_trade+=1
                    self.sh_obj.ou_stake1 *= 4.3
                    pass
                pass
            elif(contract_type == "DIGITDIFF"):
                self.sh_obj.diff_stake *= 12
                pass
            self.reset();
            pass
        
        return
    
    def reset(self):
        self.sh_obj.isTraded = False;
        self.sh_obj.stake = round(self.sh_obj.stake, 2);
        self.sh_obj.ou_stake0 = round(self.sh_obj.ou_stake0, 2);
        self.sh_obj.ou_stake1 = round(self.sh_obj.ou_stake1, 2);
        self.sh_obj.diff_stake = round(self.sh_obj.diff_stake, 2)
        self.sh_obj.stake_max = max(self.sh_obj.stake, self.sh_obj.stake_max);
        return
    '''
    def update(self, df, minimum, standardized_df):
        
        if(self.prices.index[-1:][0].minute == df.index[0].minute):
            self.prices.loc[self.prices.index[-1:][0]]['Close'] = df.loc[df.index[0]]['Close']
            self.prices.loc[self.prices.index[-1:][0]]['High'] = max(self.prices.loc[self.prices.index[-1:][0]]['High'], self.prices.loc[self.prices.index[-1:][0]]['Close'])
            self.prices.loc[self.prices.index[-1:][0]]['Low'] = max(self.prices.loc[self.prices.index[-1:][0]]['Low'], self.prices.loc[self.prices.index[-1:][0]]['Close'])
            if(len(self.prices.index)>=2):
                self.prices.loc[self.prices.index[-1:][0]]['Open'] = self.prices.loc[self.prices.index[-2:-1][0]]['Close']
        elif(df.index[0].minute > self.prices.index[-1:][0].minute):
            
            self.prices = pandas.merge(self.prices.T, df.T, left_index=True, right_index=True, how='outer').T
            
            if(len(self.prices.index)>=2):
                self.prices.loc[self.prices.index[-1:][0]]['Open'] = self.prices.loc[self.prices.index[-2:-1][0]]['Close']
            while(len(self.prices.index) > self.size):
                self.prices = self.prices.drop(self.prices.index[0])
        try:
            if(self.sym not in standardized_df.columns):
                standardized_df = pandas.concat([standardized_df, pandas.Series(stats.zscore(self.prices['Close'][-minimum:].dropna())).rename(self.sym)], axis=1, sort=True)
            else:
                standardized_df[self.sym] = pandas.Series(stats.zscore(self.prices['Close'][-minimum:].dropna())).rename(self.sym)
        except:
            pass
        self.prices = self.prices.round(5)
        
        try:
            self.logic()
            if(self.prices.index <= 1):
                self.get_historical_data()
        except:
            pass
        
        return(standardized_df)
    '''
    
    