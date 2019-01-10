import websocket
import json
import pandas
import threading
import datetime
import pairs
import numpy
import matplotlib.pyplot
import IPython.display as ipd
import time
import threading

class SharedObjects:
    account = pandas.DataFrame()
    ws = None
    prs = dict()
    error = None
    
    size = 1440
    ipairs = []
    coint_mat = pandas.DataFrame()
    spreads = dict()
    
    stake = 0.5
    corr_mat = pandas.DataFrame()
    #dataset0 = pandas.DataFrame()
    traded_currencies = []
    alert = False
    corr_bd = 0.5
    bool_ping = True
    
    def ping(self):
        self.ws.send(json.dumps({"ping": 1}))
        time.sleep(180)
        if (bool_ping is True):
            tr = threading.Timer(1, self.ping)
            tr.start()
        return
    
    def login(self):
        self.ws.run_forever()
        return
        
    def __init__(self, ws):
        self.ws = ws
        self.forex_major = ['frxAUDJPY', 'frxAUDUSD', 'frxEURAUD', 'frxEURCAD', 
                  'frxEURCHF', 'frxEURGBP', 'frxEURJPY', 'frxEURUSD', 
                  'frxGBPAUD', 'frxGBPJPY', 'frxGBPUSD', 'frxUSDCAD', 'frxUSDCHF', 'frxUSDJPY']
        self.volatility_index = ['R_10', 'R_25', 'R_50', 'R_75', 'R_100', 'RDBEAR', 'RDBULL']
        self.coint_mat = pandas.DataFrame()
        self.spreads = dict()
        self.corr_bd = 0.3
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
            self.set_error(message['error'])
        return
            
    
    def set_error(self, message):
        self.error = pandas.DataFrame(columns = [0])
        for key in message:
            self.error.loc[key] = {0: message[key]}
        return
    
    def subscribe(self, sym):
        self.ws.send(json.dumps({"ticks": sym, "subscribe": 1}))
        return
    
    def unsubscribe(self, pid):
        self.ws.send(json.dumps({"forget": pid}))
        return
    
    def logout(self):
        bool_ping = False
        for key in self.prs:
            self.unsubscribe(self.prs.get(key).pid)
        prs = None
        self.ws.send(json.dumps({'logout': 1}))
        self.ws = None
        return
    
    def process_account(self, message):
        sl = message['authorize']
        sl.pop('account_list')
        sl.pop('scopes')
        sl.pop('upgradeable_landing_companies')
        self.account = pandas.DataFrame(columns = [0])
        for key in sl:
            self.account.loc[key] = {0: str(sl[key])}
        for sym in self.forex_major:
            self.req_history(sym)
        tr = threading.Timer(1, self.ping)
        tr.start()
        return
    
    def req_history(self, sym):
        self.ws.send(json.dumps({"ticks_history": sym,
              "end": "latest",
              "start": 1,
              "style": "candles",
              "adjust_start_time": 1,
              "count": self.size}))
        return
    
    def process_tick(self, message):
        quote = float(message['quote'])
        pid = message['id']
        symbol = message['symbol']
        time = datetime.datetime.fromtimestamp(int(message['epoch']))
        if(symbol in self.prs):
            self.prs.get(symbol).update(symbol, pid, time, quote)
            #self.prs.get(symbol).standardize_prices()
            resp = self.prs.get(symbol).co_integration(self.prs, self.coint_mat, self.spreads)
            self.coint_mat = resp[0]
            self.coint_mat = self.coint_mat.fillna(0.999)
            self.coint_mat= self.coint_mat.round(5)
            self.spreads = resp[1]
            self.pair_selection()
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
        if sym not in self.prs:
            self.prs[sym] = pairs.Pair(sym, dt, self.ws)
        return
    
    def pairwise_spreadplot(self, y, x):
        dff = pandas.DataFrame()
        dff[y] = self.spreads.get(y)[x]
        dff['mean'] = dff[y].mean()
        dff['upper'] = dff['mean'] + (2.05*dff[y].std())
        dff['lower'] = dff['mean'] - (2.05*dff[y].std())
        dff['buy'] = dff[y][((dff[y] < dff['lower']) & (dff[y].shift(1) > dff['lower']) | 
                          (dff[y] <  dff['mean']) & (dff[y].shift(1) >  dff['mean']))]

        dff['sell'] = dff[y][((dff[y] > dff['upper']) & (dff[y].shift(1) < dff['upper']) | 
                           (dff[y] >  dff['mean']) & (dff[y].shift(1) <  dff['mean']))]
        #return(dff.plot(figsize = (17, 10), style=['g', '--r', '--b', '--b', 'm^','cv']))
        return(dff)
    
    def pairwise_spread(self, y):
        dff = self.spreads.get(y)
        dff = dff.drop(columns=[y])
        dff = dff.round(5)
        return(dff)
    
    def pairwise_plot(self, y, x):
        
        dtf = pandas.DataFrame()
        yy = self.prs.get(y).standardized_prices
        dtf[y] = yy
        xx = self.prs.get(x).standardized_prices
        dtf[x] = xx
        dff = self.pairwise_spreadplot(y, x)
        
        pplt = matplotlib.pyplot.figure(figsize = (17,10))
        plt1 = pplt.add_subplot(211)
        plt2 = pplt.add_subplot(212)
        plt1.plot(dtf)
        plt1.set_title('Standardized Prices')
        plt2.plot(dff[y], 'g', dff['mean'], '--r', dff['upper'], '--b', dff['lower'], '--b', dff['buy'], 'm^', dff['sell'], 'cv')
        plt2.set_title('Spreads')
        
        return
    
    def pair_selection(self):
        prs = self.prs
        self.ipairs = []
        dtf = pandas.DataFrame()
        for key in prs:
            yy = prs.get(key).standardized_prices
            dtf[key] = pandas.Series(yy)
        self.dataset0 = dtf
        self.corr_mat = dtf.corr(method='kendall').replace(1, 0)
        self.corr_mat = self.corr_mat.round(5)
        for key in prs.keys():
            for ky in prs.keys():
                #if(self.corr_mat.loc[key][ky] >= self.corr_bd and 
                #   self.coint_mat.loc[key][ky] < 0.05 and 
                #   self.coint_mat.loc[ky][key] < 0.05 ):
                #    if ([ky, key] not in self.ipairs):
                #        self.ipairs.append([key,ky])
                if(self.corr_mat.loc[key][ky] <= -self.corr_bd and 
                     self.coint_mat.loc[key][ky] < 0.05 and 
                     self.coint_mat.loc[ky][key] < 0.05):
                    if ([key, ky] not in self.ipairs):
                        self.ipairs.append([key,ky, self.corr_mat.loc[key][ky]])
                else:
                    return
        if(self.alert == True):
            self.signal()
        return
    
    def signal(self):
        signals = []
        for pr in self.ipairs:
            dff = pandas.DataFrame()
            dff['spread'] = self.spreads.get(pr[0])[pr[1]]
            dff['mean'] = dff['spread'].mean()
            dff['upper'] = dff['mean'] + (2.05*dff['spread'].std())
            dff['lower'] = dff['mean'] - (2.05*dff['spread'].std())
            index = len(dff.index.values) - 1 
            
            y = self.prs.get(pr[0]).standardized_prices()
            x = self.prs.get(pr[1]).standardized_prices()
            b = stats.linregress(x, y).slope
            
            if(dff['spread'][index] < dff['lower'][index]):
                signals.append({pr[0]: ['Buy', 1], pr[1]: ['Sell', abs(b)]})
                display(ipd.Audio('libs/beep.wav', autoplay=True))
                #self.Buy(pr[0], self.quantity * 1)
                #self.Sell(pr[1], self.quantity * abs(b))
            elif(dff['spread'][index] > dff['upper'][index]):
                signals.append({pr[0]: ['Sell', 1], pr[1]: ['Buy', abs(b)]})
                display(ipd.Audio('libs/beep.wav', autoplay=True))
                #self.Sell(pr[0], self.quantity * 1)
                #self.Buy(pr[1], self.quantity * abs(b))
        return(signals)