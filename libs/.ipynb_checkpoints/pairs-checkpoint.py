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
    
    period = 5
    spreads = dict()
    size = 720
    params = {
      "proposal": 1,
      "amount": 0.35,
      "basis": "stake",
      "contract_type": "ONETOUCH",
      "currency": "USD",
      "duration": 5,
      "duration_unit": "m",
      "barrier": "",
      "barrier2": "",
      "symbol": ''
    }
    transactions = pandas.DataFrame(columns=['contract_id', 'transaction_id'])
    automate = False
    alert = False
    proposals = pandas.DataFrame(columns=['amount', 'barrier', 'barrier2','basis', 'contract_type', 'currency', 
                                      'duration', 'duration_unit', 'payout', 'proposal', 'spot', 'symbol'])
    
    stakelist = [0.35, 0.36, 0.37, 0.38, 0.39, 0.4, 0.6, 0.8, 0.9, 1, 1]
    #stakelist = [0.35, 0.36, 0.37, 0.38, 0.39, 0.4, 0.6, 0.8, 0.9, 1, 1, 1.2, 1.5, 1.7, 2, 2.3, 2.6, 3, 4, 4.5, 5, 5.1]
    barrier_nt = 0.0
    barrier_hl = 0.0
    ih = 0
    il = 0
    
    def __init__(self, symbol, dataframe, pid, ws, size):
        numpy.seterr(divide='ignore', invalid='ignore')
        self.size = size
        self.sym = symbol
        self.ws = ws
        self.pid = pid
        self.prices = dataframe
        self.get_historical_data()
        if(self.sym[0:3] == 'frx'):
            self.params['amount'] = 0.5
        return
    
    def update(self, df, minimum, standardized_df):
        
        if(self.prices.index[-1:][0].minute == df.index[0].minute):
            self.prices.loc[self.prices.index[-1:][0]]['Close'] = df.loc[df.index[0]]['Close']
            self.prices.loc[self.prices.index[-1:][0]]['High'] = max(self.prices.loc[self.prices.index[-1:][0]]['High'], self.prices.loc[self.prices.index[-1:][0]]['Close'])
            self.prices.loc[self.prices.index[-1:][0]]['Low'] = max(self.prices.loc[self.prices.index[-1:][0]]['Low'], self.prices.loc[self.prices.index[-1:][0]]['Close'])
            if(len(self.prices.index)>=2):
                self.prices.loc[self.prices.index[-1:][0]]['Open'] = self.prices.loc[self.prices.index[-2:-1][0]]['Close']
        elif(df.index[0].minute > self.prices.index[-1:][0].minute):
            
            #_axes = self.prices.index.tolist()
            #[_axes.append(indx) for indx in df.index.tolist()]
            #dicts = [d.T.to_dict().values() for d in [self.prices, df] ]    
            #self.prices = pandas.DataFrame(list(chain(*dicts)), index = _axes)
            #del _axes, dicts
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
    
    def analysis(self, params):
        #numpy.seterr(divide='ignore', invalid='ignore')
        self.prices['V-'] = ta.trend.vortex_indicator_neg(self.prices['High'], self.prices['Low'], self.prices['Close'], n=self.period, fillna=False)
        self.prices['V+'] = ta.trend.vortex_indicator_pos(self.prices['High'], self.prices['Low'], self.prices['Close'], n=self.period, fillna=False)
        self.prices['RSI'] = ta.momentum.rsi(self.prices['Close'], n=self.period, fillna=False)
        self.prices['RSI'][self.period:] = stats.zscore(self.prices['RSI'].dropna())
        self.prices['RSI_mean'] = self.prices['RSI'].mean()
        self.prices['RSI_UB'] = max(self.prices['RSI'].dropna()) - 0.2
        self.prices['RSI_LB'] = min(self.prices['RSI'].dropna()) + 0.2
        
        self.prices['RSI_buy'] = self.prices['RSI'][((self.prices['RSI'] < self.prices['RSI_LB']) & (self.prices['RSI'].shift(1) > self.prices['RSI_LB'])) | ((self.prices['RSI'] <  self.prices['RSI_mean']) & (self.prices['RSI'].shift(1) >  self.prices['RSI_mean']))]
        self.prices['RSI_sell'] = self.prices['RSI'][((self.prices['RSI'] > self.prices['RSI_UB']) & (self.prices['RSI'].shift(1) < self.prices['RSI_UB'])) | ((self.prices['RSI'] >  self.prices['RSI_mean']) & (self.prices['RSI'].shift(1) <  self.prices['RSI_mean']))]
        
        self.prices['MACD_Hist'] = ta.trend.macd_diff(self.prices['Close'], n_fast=12, n_slow=26, n_sign=9, fillna=False)
        self.prices['MACD_Signal'] = ta.trend.macd_signal(self.prices['Close'], n_fast=12, n_slow=26, n_sign=9, fillna=False)
        self.prices['MACD'] = ta.trend.macd(self.prices['Close'], n_fast=12, n_slow=26, fillna=False)
        
        try:
            self.logic()
            if(self.prices.index <= 1):
                self.get_historical_data()
        except:
            pass
        return
    
    def higher_lower(self):
        self.params['duration'] = '5'
        self.params['duration_unit'] = 't'
        self.params['symbol'] = self.sym
        if('barrier2' in self.params): del self.params['barrier2'];
                
        trade_h = True
        trade_l = True
        for indx in self.proposals.index:
            if( float(self.proposals.loc[indx]['barrier']) > 0 and self.proposals.loc[indx]['contract_type'] == 'CALL'):
                trade_h = False
            elif( float(self.proposals.loc[indx]['barrier']) < 0 and self.proposals.loc[indx]['contract_type'] == 'PUT' ):
                trade_l = False
       
        if(trade_h == True and self.barrier_hl != 0):
            self.params['contract_type'] = 'CALL'
            self.params['amount'] = self.stakelist[self.ih]
            self.params['barrier'] = '+' + str(self.barrier_hl)
            self.ws.send(json.dumps(self.params))
                
        if(trade_l == True and self.barrier_hl != 0):
            self.params['contract_type'] = 'PUT'
            self.params['amount'] = self.stakelist[self.il]
            self.params['barrier'] = '-' + str(self.barrier_hl)
            self.ws.send(json.dumps(self.params))
        return
    
    def logic(self):
        if( (numpy.isnan(float(self.prices['RSI_buy'][-1:])) == False or numpy.isnan(float(self.prices['RSI_sell'][-1:])) == False) and self.sym[0] == 'R'):
            try:
                if(self.alert == True): display(Audio(numpy.sin(numpy.linspace(0, 3000, 10000)), rate=200000, autoplay=True));
                if (self.automate == True): self.higher_lower();
                pass
            except:
                pass
            
            try:
                self.automate_trade()
                pass
            except:
                pass
            
        return
    
    def automate_trade(self):
        if (self.automate == True):
            for indx in self.proposals.index :
                if(indx not in self.transactions.index):
                    if(self.alert == True): display(Audio(numpy.sin(numpy.linspace(0, 9000, 10000)), rate=200000, autoplay=True));
                    self.ws.send(json.dumps({"buy": indx, "price": self.proposals.loc[indx]['amount']}))
        return
    
    def process_history(self, df):
        self.prices = df
        return
    
    def co(self, df0, df1):
        df0 = df0.T
        if(self.sym not in df0.columns):
            df0 = pandas.concat([df0, pandas.Series(dict([(key, self.co_integration(key, df1[self.sym], df1[key])) for key in df1.columns if len(df1[key].dropna()) > 1])).rename(self.sym)], axis=1, sort=True)
        else:
            df0[self.sym] = pandas.Series(dict([(key, self.co_integration(key, df1[self.sym], df1[key])) for key in df1.columns if len(df1[key].dropna()) > 1])).rename(self.sym) 
        df0 = df0.T
        return df0
    
    def transact(self, contract_id = None, amount = float('NaN')):
        if(contract_id is not None):
            for idx in self.transactions.index:
                if(self.transactions.loc[idx]['contract_id'] == contract_id):
                    if (float(amount) == 0 and self.proposals.loc[idx]['contract_type'] == 'CALL'):
                        if(self.ih < len(self.stakelist)-1): self.ih = self.ih + 1;
                    elif (float(amount) == 0 and self.proposals.loc[idx]['contract_type'] == 'PUT'):
                        if(self.il < len(self.stakelist)-1): self.il = self.il + 1;
                    elif(float(amount) > 0 and self.proposals.loc[idx]['contract_type'] == 'CALL'): self.ih = 0;
                    elif(float(amount) > 0 and self.proposals.loc[idx]['contract_type'] == 'PUT'): self.il = 0;
                    if(idx in self.proposals.index): self.proposals = self.proposals.drop([idx], axis = 0)
                    if(idx in self.transactions.index): self.transactions = self.transactions.drop([idx], axis = 0)
        return
    
    def co_integration(self, key, y, x):
        spd = pandas.DataFrame()
        adf = 1
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                adf = ts.coint(y, x, method='adfuller', autolag='aic', maxlag = 1)[1]
                
            spd['spread'] = stats.zscore(sm.OLS(y, x).fit().resid)
            spd['upper'] = max(spd['spread'].dropna()) - 0.2
            spd['lower'] = min(spd['spread'].dropna()) + 0.2
            spd['mean'] = spd['spread'].mean()

            spd = spd.round(5)
            spd['buy'] = spd['spread'][(spd['spread'] < spd['lower']) & (spd['spread'].shift(1) > spd['lower'])]
            spd['sell'] = spd['spread'][(spd['spread'] > spd['upper']) & (spd['spread'].shift(1) < spd['upper'])]
        except:
            pass
        self.spreads[key] = spd
        del spd
        return adf
    
    def get_historical_data(self):
        try:
            self.ws.send(json.dumps({"ticks_history": self.sym,
              "end": "latest",
              "start": 1,
              "style": "candles",
              "adjust_start_time": 1,
              "count": self.size}))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
        return
    
    def TA_plot(self):
        
        pplt = matplotlib.pyplot.figure(figsize = (17,15))
        plt1 = pplt.add_subplot(311)
        plt2 = pplt.add_subplot(312)
        plt3 = pplt.add_subplot(313)
        plt1.plot(self.prices['V+'].tolist(),'b', self.prices['V-'].tolist(), 'r')
        plt1.set_title('Vortex Indicator')

        bins = numpy.linspace(-10, 10, 100)
        plt2.plot(self.prices['MACD_Signal'].tolist(), 'r', self.prices['MACD'].tolist(), 'b')
        plt2.bar(range(self.size), self.prices['MACD_Hist'].tolist(), alpha=0.5)
        plt2.set_title('Moving Average Convergence Divergence')

        plt3.plot(self.prices['RSI'].tolist(), 'k')
        plt3.plot(self.prices['RSI_LB'].tolist(), 'r', self.prices['RSI_UB'].tolist(), 'r', self.prices['RSI_mean'].tolist(), 'b')
        plt3.plot(self.prices['RSI_buy'].tolist(), 'm^', self.prices['RSI_sell'].tolist(), 'cv')
        plt3.set_title('Relative Strength Index')
        return