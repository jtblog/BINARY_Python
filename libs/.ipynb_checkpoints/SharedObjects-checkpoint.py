import websocket
import json
import pandas
import datetime
import pairs
import numpy
import matplotlib.pyplot
import time
from scipy import stats
import threading
from ipywidgets import interact, interactive, fixed, interact_manual
import ipywidgets as widgets
import re
import os
from IPython.display import clear_output, Audio
import random
import warnings
warnings.filterwarnings("error")
import calendar

class SharedObjects:
    
    contract_type = ['UPORDOWN', 'EXPIRYRANGE', 'ONETOUCH', 
                     'DIGITDIFF', 'DIGITMATCH', 'DIGITOVER', 'DIGITUNDER', 
                     'NOTOUCH', 'CALL', 'RANGE', 'DIGITODD', 'PUT', 'EXPIRYMISS', 
                     'DIGITEVEN', 'TICKHIGH', 'TICKLOW', 'RESETCALL', 'RESETPUT']
    forex_major = ['frxAUDJPY', 'frxAUDUSD', 'frxEURAUD', 'frxEURCAD', 
                  'frxEURCHF', 'frxEURGBP', 'frxEURJPY', 'frxEURUSD', 
                  'frxGBPAUD', 'frxGBPJPY', 'frxGBPUSD', 'frxUSDCAD', 'frxUSDCHF', 'frxUSDJPY']
    volatility_indices = ['R_10', 'R_25', 'R_50', 'R_75', 'R_100', 'RDBEAR', 'RDBULL']
    account = pandas.DataFrame()
    size = 720
    prs = dict()
    error = pandas.DataFrame(columns=['code','message'])
    standardized_prices = pandas.DataFrame()
    corr_mat = pandas.DataFrame()
    coint_mat = pandas.DataFrame()
    params = {
      "proposal": 1,
      "amount": 0.5,
      "basis": "stake",
      "contract_type": "ONETOUCH",
      "currency": "USD",
      "duration": 5,
      "duration_unit": "m",
      "barrier": "",
      "barrier2": "",
      "symbol": ''
    }
    
    exitcode = 0
    automate = False
    alert = False
    
    proposals = pandas.DataFrame(columns=['amount', 'barrier', 'barrier2','basis', 'contract_type', 'currency', 
                                      'duration', 'duration_unit', 'payout', 'proposal', 'spot', 'symbol'])
    def ping(self, dummy=None):
        try:
            self.ws.send(json.dumps({"ping": 1}))
            self.ws.send(json.dumps({"transaction": 1, "subscribe": 1}))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
            clear_output()
        time.sleep(60)
        #tr = threading.Timer(1, self.ping).start()
        threading.Thread(target=self.ping).start()
        return
    
    def analysis(self, dummy=None):
        try:
            self.corr_mat = self.standardized_prices.corr(method='kendall').replace(1, 0).fillna(0).round(5)
            for sym in self.prs:
                if(len(self.standardized_prices[sym].dropna()) > 1):
                    self.prs.get(sym).analysis(self.params)
                self.coint_mat = self.prs.get(sym).co(self.coint_mat, self.standardized_prices).replace(0, 1).fillna(1).round(5)
                    
        except:
            pass
        time.sleep(10)
        threading.Thread(target=self.analysis).start()
        return
    
    def login(self):
        self.ws.run_forever()
        return
        
    def __init__(self, ws):
        self.ws = ws
        threading.Thread(target=self.login).start()
        return
    
    def update(self, message):
        if ('authorize' in message):
            self.process_account(message)
        if ('tick' in message):
            self.process_tick(message['tick'])
        if ('candles' in message):
            self.process_history(message['echo_req']['ticks_history'], message['candles'])
        if ('error' in message):
            self.process_error(message, message['error'])
        if ('transaction' in message):
            self.process_transaction(message['transaction'])
        if ('buy' in message):
            self.process_buy(message['echo_req']['buy'], message)
        if ('proposal' in message):
            self.process_proposal(message)
        return
        
    def process_buy(self, prp_id, message):
        shortcode = message['buy']['shortcode']
        contract_id = message['buy']['contract_id']
        transaction_id = message['buy']['transaction_id']
        for key in self.prs:
            if(key in shortcode):
                self.prs.get(key).transactions.loc[prp_id] = [contract_id, transaction_id]
        return
    
    def process_error(self, message, err_message):
        if('ticks' in message['echo_req']):
            self.error.loc[message['echo_req']['ticks'], 'code'] = err_message['code']
            self.error.loc[message['echo_req']['ticks'], 'message'] = err_message['message']
        elif('symbol' in message['echo_req']):
            self.error.loc[message['echo_req']['symbol'], 'code'] = err_message['code']
            self.error.loc[message['echo_req']['symbol'], 'message'] = err_message['message']
        return
    
    def subscribe(self, sym):
        try:
            self.ws.send(json.dumps({"ticks": sym, "subscribe": 1}))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
        return
    
    def transaction_stream(self):
        try:
            self.ws.send(json.dumps({"transaction": 1, "subscribe": 1}))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
        return
    
    def unsubscribe(self, pid):
        try:
            self.ws.send(json.dumps({"forget": pid}))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
        return
    
    def logout(self, dummy = None):
        clear_output()
        try:
            self.ws.send(json.dumps({'forget_all': 'ticks'}))
            self.ws.send(json.dumps({'logout': 1}))
            self.ws.close()
            self.exitcode = 1
            del self.prs
            del self.ws
            self = None
        except:
            pass
        
        return
    
    def process_account(self, message):
        try:
            sl = message['authorize']
            if('account_list' in sl): sl.pop('account_list')
            if('scopes' in sl): sl.pop('scopes')
            if('upgradeable_landing_companies' in sl): sl.pop('upgradeable_landing_companies')
            self.account = pandas.DataFrame(columns = [0])
            self.transaction_stream()
            for key in sl:
                self.account.loc[key] = {0: str(sl[key])}
            #for sym in self.forex_major:
                #self.subscribe(sym)
            for sym in self.volatility_indices:
                self.subscribe(sym)
            #tr = threading.Timer(1, self.ping).start()
            threading.Thread(target=self.analysis).start()
            threading.Thread(target=self.ping).start()
            display(Audio(numpy.sin(numpy.linspace(0, 4 * 2 * numpy.pi, 25)), rate=20000, autoplay=True))
        except:
            pass
        return
    
    def process_tick(self, message):
        quote = float(message['quote'])
        pid = message['id']
        symbol = message['symbol']
        time = datetime.datetime.fromtimestamp(int(message['epoch']))
        d = {'Open': [quote], 'High': [quote], 'Low': [quote], 'Close': [quote]}
        dtf = pandas.DataFrame(data = d, index = [time])
        
        if(symbol in self.prs):
            minimum = min([len(x.prices.index) for x in self.prs.values()])
            try: 
                self.standardized_prices = self.standardized_prices.reindex(range(minimum))
            except:
                pass
            self.standardized_prices = self.prs.get(symbol).update(dtf, minimum, self.standardized_prices).fillna(0)
        else:
            self.prs[symbol] = pairs.Pair(symbol, dtf, pid, self.ws, self.size)
            try:
                if(os.path.isfile('data/onetouch_bar_5m.csv') ):
                    self.prs.get(symbol).barrier_nt = list(pandas.read_csv('data/onetouch_bar_5m.csv')[symbol])[0]
                if(os.path.isfile('data/higherlower_bar_5t.csv') ):
                    self.prs.get(symbol).barrier_hl = list(pandas.read_csv('data/higherlower_bar_5t.csv')[symbol])[0]   
            except:
                pass
            return
        del dtf
        
        return
    
    def process_history(self, sym, message):
        Open = []
        High = []
        Low = []
        Close = []
        Epoch = []
        for candle in message:
            Open.append(float(candle['open']))
            Low.append(float(candle['low']))
            High.append(float(candle['high']))
            Close.append(float(candle['close']))
            Epoch.append(datetime.datetime.fromtimestamp(int(candle['epoch'])))
        dt = pandas.DataFrame({'Open': Open, 'High': High, 'Low': Low, 'Close': Close}, index = Epoch)
        self.prs.get(sym).process_history(dt)
        del dt
        return
    
    def process_proposal(self, message):
        pid = message['proposal']['id']
        payout = ((float(message['proposal']['payout']) - float(message['echo_req']['amount']) ) / float(message['echo_req']['amount']) ) * 100
        spot = float(message['proposal']['spot'])
        
        self.params['amount'] = message['echo_req']['amount']
        self.params['basis'] = message['echo_req']['basis']
        self.params['contract_type'] = message['echo_req']['contract_type']
        self.params['duration'] = message['echo_req']['duration']
        self.params['duration_unit'] = message['echo_req']['duration_unit']
        if ('barrier' in message['echo_req']):
            self.params['barrier'] = message['echo_req']['barrier']
        else:
            if('barrier' in self.params): del self.params['barrier'] 
        if ('barrier2' in message['echo_req']):
            self.params['barrier2'] = message['echo_req']['barrier2']
        else:
            if('barrier2' in self.params): del self.params['barrier2'] 
        self.params['symbol'] = message['echo_req']['symbol']
        
        df0 = pandas.DataFrame(self.params, index = [pid])
        df0['payout'] = payout
        df0['spot'] = spot
        if( pid in self.prs.get(message['echo_req']['symbol']).proposals.index):
            self.prs.get(message['echo_req']['symbol']).proposals.loc[pid] = df0.loc[pid]
        else:
            self.prs.get(message['echo_req']['symbol']).proposals = pandas.concat([self.prs.get(message['echo_req']['symbol']).proposals, df0], sort = True)
        return
    
    def process_transaction(self, message):
        if('action' in message):
            action = message['action']
            symbol = message['symbol']
            contract_id = message['contract_id']
            amount = float(message['amount'])
            if(action == 'sell'):
                self.prs.get(symbol).transact(contract_id = contract_id, amount = amount)
                pass
        return
    
    def pairwise_plot(self, y, x):
        dff = self.prs.get(y).spreads.get(x)
        pplt = matplotlib.pyplot.figure(figsize = (17,10))
        plt1 = pplt.add_subplot(211)
        plt2 = pplt.add_subplot(212)
        plt1.plot(self.standardized_prices[[y, x]])
        plt1.set_title('Standardized Prices')
        plt2.plot(dff['spread'], 'g', dff['mean'], '--r', dff['upper'], '--b', dff['lower'], '--b', dff['buy'], 'm^', dff['sell'], 'cv')
        plt2.set_title('Spreads')
        del dff
        return
    
    def pairwise_forex_major(self):
        try:
            clear_output()
            def view():
                display(interactive(self.pairwise_plot, y = self.forex_major, x = self.forex_major))
            threading.Thread(target=view).start()
        except:
            pass
        return
    
    def pairwise_volatility_indices(self):
        try:
            clear_output()
            def view():
                display(interactive(self.pairwise_plot, y = self.volatility_indices, x = self.volatility_indices))
            threading.Thread(target=view).start()
        except:
            pass
        return
    
    def tables_forex_major(self):
        try:
            clear_output()
            interactive(display(self.coint_mat.loc[self.forex_major, self.forex_major]))
            interactive(display(self.corr_mat.loc[self.forex_major, self.forex_major]))
        except:
            pass
        return
    
    def tables_volatility_indices(self):
        try:
            clear_output()
            interactive(display(self.coint_mat.loc[self.volatility_indices, self.volatility_indices]))
            interactive(display(self.corr_mat.loc[self.volatility_indices, self.volatility_indices]))
        except:
            pass
        return
    
    def ta_plot(self):
        try:
            clear_output()
            def ta(y):
                return(self.prs.get(y).TA_plot())
            def view():
                display(interactive(ta, y = list(self.prs.keys())))
            threading.Thread(target=view).start()
        except:
            pass
        return
    
    def set_automate(self, change): 
        clear_output()
        self.automate = bool(change['new'])
        return
    
    def set_alarm(self, change): 
        self.alert = bool(change['new'])
        return
    
    def set_alarm(self): 
        clear_output()
        if (self.alert == True):
            self.alert = False
        elif(self.alert == False):
            self.alert = True
        for key in self.prs:
            self.prs.get(key).alert = self.alert
        print(self.alert)
        return
    
    def set_automate(self): 
        clear_output()
        if (self.automate == True):
            self.automate = False
        elif(self.automate == False):
            self.automate = True
        for key in self.prs:
            self.prs.get(key).automate = self.automate
        print(self.automate)
        return
    
    def reload_pairs(self):
        def reload():
            for sym in self.prs:
                try:
                    #self.prs.get(sym).get_historical_data()
                    self.prs.get(sym).analysis(self.params)
                except:
                    pass
        threading.Thread(target=reload).start()
        return
    
    def get_proposals(self):
        def p_dat():
            def merge(pid, df): self.proposals.loc[pid] = df.loc[pid]
            self.proposals = pandas.DataFrame(columns=['amount', 'barrier', 'barrier2','basis', 'contract_type', 'currency', 
                                                  'duration', 'duration_unit', 'payout', 'proposal', 'spot', 'symbol'])
            for key in self.prs:
                [merge(pid, self.prs.get(key).proposals) for pid in self.prs.get(key).proposals.index]
        threading.Thread(target=p_dat).start()
        return self.proposals