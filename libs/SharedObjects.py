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
    
    volatility_indices = ['R_10', 'R_25', 'R_50', 'R_75', 'R_100', 'RDBEAR', 'RDBULL']
    #symbols = widgets.Select(options = volatility_indices)
    
    account = pandas.DataFrame()
    size = 130
    prs = dict()
    error = pandas.DataFrame(columns=['code','message'])
    standardized_prices = pandas.DataFrame()
    
    exitcode = 0
    autotrade = False
    alert = False
    balance = 50
    stake_max = 0.0
    
    api_limit = 40
    stake = 0.35
    diff_stake = 1
    ou_stake0 = 0.35
    ou_stake1 = 0.35
    isTraded = False
    ou_count = 0
    
    trade_ou27 = False
    trade_ou45 = False
    trade_diff = False
    
    def ping(self, dummy=None):
        try:
            self.ws.send(json.dumps({"ping": 1}))
            self.ws.send(json.dumps({"transaction": 1, "subscribe": 1}))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
            #clear_output()
        time.sleep(60)
        threading.Thread(target=self.ping).start()
        return
    
    def login(self):
        self.ws.run_forever()
        return
        
    def getInstance(self):
        return self
    
    def __init__(self, ws):
        self.ws = ws
        threading.Thread(target=self.login).start()
        return
    
    def update(self, message):
        if ('authorize' in message):
            self.process_account(message)
        if ('tick' in message):
            self.process_tick(message['tick'])
        if ('error' in message):
            self.process_error(message, message['error'])
        if ('buy' in message):
            self.process_buy(message['echo_req']['parameters'], message)
        if ('proposal_open_contract' in message):
            self.process_proposal_open_contract(message['proposal_open_contract'])
        if ('history' in message):
            self.process_history(message['echo_req']['ticks_history'], message['history'])
        #if ('transaction' in message):
        #    self.process_transaction(message['transaction'])
        #if ('candles' in message):
        #    self.process_history(message['echo_req']['ticks_history'], message['candles'])
        return
    
    def process_proposal_open_contract(self, proposal_open_contract):
        symbol = proposal_open_contract['underlying']
        contract_id = proposal_open_contract['contract_id']
        contract_type = proposal_open_contract['contract_type']
        status = proposal_open_contract['status']
        if(status == "won" or status == "lost"):
            profit = float(proposal_open_contract['sell_price'])
            self.prs.get(symbol).process_transaction(contract_id, contract_type, profit, status);
        return
    
    def process_buy(self, parameters, message):
        #shortcode = message['buy']['shortcode']
        symbol = parameters['symbol']
        contract_id = message['buy']['contract_id']
        contract_type = parameters['contract_type']
        self.stake = float(parameters['amount'])
        #_balance = message['buy']['balance_after']
        self.prs.get(symbol).process_transaction(contract_id, contract_type, -self.stake, "buy");
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
            for sym in self.volatility_indices:
                self.subscribe(sym)
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
        d = {'prices': [quote]}
        dtf = pandas.DataFrame(data = d, index = [time])
        
        if(symbol in self.prs):
            self.prs.get(symbol).update(dtf, self.getInstance())
        else:
            self.prs[symbol] = pairs.Pair(symbol, dtf, pid, self.ws, self.size, self.getInstance())
            return
        del dtf
        return
    
    def process_history(self, sym, message):
        prices = message['prices']
        times = message['times']
        for t, p in zip(times, prices):
            quote = float(p)
            time = datetime.datetime.fromtimestamp(int(t))
            d = {'prices': [quote]}
            dtf = pandas.DataFrame(data = d, index = [time])
            self.prs.get(sym).update(dtf, self.getInstance())
            del dtf
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
    
    def set_autotrade(self): 
        clear_output()
        if (self.autotrade == True):
            self.autotrade = False
        elif(self.autotrade == False):
            self.autotrade = True
        for key in self.prs:
            self.prs.get(key).autotrade = self.autotrade
        print(self.autotrade)
        return
    
    def plots(self, x):
        dt0 = self.prs.get(x).prices
        #dt1 = pandas.DataFrame({'Percentage': self.prs.get(x).digit_percent.values()},
        #                      index = self.prs.get(x).digit_percent.keys())
        
        pplt = matplotlib.pyplot.figure(figsize = (17,10))
        plt1 = pplt.add_subplot(211)
        plt2 = pplt.add_subplot(212)
        plt1.plot(dt0)
        plt1.set_title('Tick Chart')
        N = len(self.prs.get(x).digit_percent)
        width = 0.70
        plt2.bar(numpy.arange(N), self.prs.get(x).digit_percent.values(), width)
        return
    
    def get_charts(self):
        plt = interactive(self.plots, x = self.volatility_indices)
        return(display(plt))
    
    '''
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
    
    def process_tick(self, message):
        quote = float(message['quote'])
        pid = message['id']
        symbol = message['symbol']
        time = datetime.datetime.fromtimestamp(int(message['epoch']))
        d = {'Open': [quote], 'High': [quote], 'Low': [quote], 'Close': [quote]}
        dtf = pandas.DataFrame(data = d, index = [time])
        
        if(symbol in self.prs):
            #minimum = min([len(x.prices.index) for x in self.prs.values()])
            #try: 
            #    self.standardized_prices = self.standardized_prices.reindex(range(minimum))
            #except:
            #    pass
            #self.standardized_prices = self.prs.get(symbol).update(dtf, minimum, self.standardized_prices).fillna(0)
            self.prs.get(symbol).update(dtf)
        else:
            self.prs[symbol] = pairs.Pair(symbol, dtf, pid, self.ws, self.size, self.getInstance())
            return
        del dtf
        return
        
    def process_buy(self, prp_id, message):
        shortcode = message['buy']['shortcode']
        contract_id = message['buy']['contract_id']
        transaction_id = message['buy']['transaction_id']
        for key in self.prs:
            if(key in shortcode):
                self.prs.get(key).transactions.loc[prp_id] = [contract_id, transaction_id]
        return
    '''
    