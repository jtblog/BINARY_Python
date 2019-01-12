import websocket
import json
import pandas
import datetime
import pairs
import numpy
import matplotlib.pyplot
import IPython.display as ipd
import time
import threading
from ipywidgets import interact, interactive, fixed, interact_manual
import ipywidgets as widgets
import re
import os
from IPython.display import clear_output
import random

class SharedObjects:
    account = pandas.DataFrame()
    curr_symbol = ''
    debug = ''
    ws = None
    prs = dict()
    error = None
    f_pips = pandas.DataFrame()
    prop = ''
    
    size = 1440
    ipairs = []
    contract_type = []
    coint_mat = pandas.DataFrame()
    spreads = dict()
    
    stake = 0.5
    corr_mat = pandas.DataFrame()
    #dataset0 = pandas.DataFrame()
    traded_currencies = []
    alert = False
    automate = False
    corr_bd = 0.5
    bool_ping = True
    period = 5
    params = {
      "proposal": 1,
      "amount": stake,
      "basis": "stake",
      "contract_type": "ONETOUCH",
      "currency": "USD",
      "duration": period,
      "duration_unit": "m",
      "barrier": "",
      "barrier2": "",
      "symbol": curr_symbol
    }
    proposals = pandas.DataFrame(columns=['symbol','basis','amount','payout','duration','contract', 'spot', 'barrier', 'barrier2'])
    closed = False
    
    def ping(self, dummy=None):
        try:
            self.ws.send(json.dumps({"ping": 1}))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
        time.sleep(60)
        if (self.bool_ping is True):
            tr = threading.Timer(1, self.ping)
            tr.start()
        return
    
    def login(self, ws=None, closed=False):
        self.closed = closed
        if(ws is not None):
            self.ws = ws
        self.ws.run_forever()
        return
        
    def __init__(self, ws):
        self.ws = ws
        self.contract_type = ['UPORDOWN', 'EXPIRYRANGE', 'ONETOUCH', 'DIGITDIFF', 'DIGITMATCH', 'DIGITOVER', 'DIGITUNDER', 'NOTOUCH', 'CALL', 'RANGE', 'DIGITODD', 'PUT', 'EXPIRYMISS', 'DIGITEVEN', 'TICKHIGH', 'TICKLOW', 'RESETCALL', 'RESETPUT']
        self.forex_major = ['frxAUDJPY', 'frxAUDUSD', 'frxEURAUD', 'frxEURCAD', 
                  'frxEURCHF', 'frxEURGBP', 'frxEURJPY', 'frxEURUSD', 
                  'frxGBPAUD', 'frxGBPJPY', 'frxGBPUSD', 'frxUSDCAD', 'frxUSDCHF', 'frxUSDJPY']
        self.volatility_indices = ['R_10', 'R_25', 'R_50', 'R_75', 'R_100', 'RDBEAR', 'RDBULL']
        self.coint_mat = pandas.DataFrame()
        self.spreads = dict()
        self.corr_bd = 0.3
        if ( os.path.isfile('data/five_min_pips.csv') ):
            self.f_pips = pandas.read_csv('data/five_min_pips.csv')
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
            self.set_error(message, message['error'])
        if ('proposal' in message):
            self.process_proposal(message)
        return
            
    
    def set_error(self, message, err_message):
        self.error = pandas.DataFrame(columns = [0])
        for key in err_message:
            self.error.loc[key] = {0: err_message[key]}
        if(err_message['code'] == 'ContractBuyValidationError'):
            self.debug = message
            if message['echo_req']['symbol'] in self.prs:
                sym = message['echo_req']['symbol']
                l = len(str(self.prs.get(message['echo_req']['symbol']).curr_low).split('.')[1])
                pip = [int(s) for s in re.findall(r'\b\d+\b', err_message['message'])][0] * 0.1
                if(l > 2):
                    pip = [int(s) for s in re.findall(r'\b\d+\b', err_message['message'])][0] * 0.001
                self.prs.get(message['echo_req']['symbol']).minimum_pip = pip
                if(len(self.f_pips.columns)>0):
                    self.prs.get(message['echo_req']['symbol']).trading_pip = self.f_pips[sym][0]
            return
        return
    
    def subscribe(self, sym):
        try:
            self.ws.send(json.dumps({"ticks": sym, "subscribe": 1}))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
        return
    
    def buy(self, qunty='single'):
        try:
            if (qunty == 'all'):
                for key in self.proposal.index:
                    self.ws.send(json.dumps(
                        {"buy": self.proposal.loc[key]['symbol'], 
                         "price": self.proposal.loc[key]['amount']}))
            else:
                self.ws.send(json.dumps(
                        {"buy": self.proposal.loc[self.prop]['symbol'], 
                         "price": self.proposal.loc[self.prop]['amount']}))
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
        self.bool_ping = False
        for key in self.prs:
            self.unsubscribe(self.prs.get(key).pid)
        prs = None
        self.ws.send(json.dumps({'logout': 1}))
        self.ws.close()
        self.ws = None
        self.closed = False
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
        for sym in self.volatility_indices:
            self.req_history(sym)
        tr = threading.Timer(1, self.ping)
        tr.start()
        return
    
    def req_history(self, sym):
        try:
            self.ws.send(json.dumps({"ticks_history": sym,
              "end": "latest",
              "start": 1,
              "style": "candles",
              "adjust_start_time": 1,
              "count": self.size}))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
        return
    
    def prime(self):
        try:
            for key in self.volatility_indices:
                self.ws.send(json.dumps({
                             "proposal": 1,
                             "amount": str(self.stake),
                             "basis": "stake",
                             "contract_type": "ONETOUCH",
                             "currency": "USD",
                             "duration": str(self.period),
                             "duration_unit": "m",
                             "barrier": "+0.0",
                             "symbol": key
                            }))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
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
        if (self.closed is True):
            for symb in self.prs:
                if(self.prs.get(symb).subscribed is False):
                    self.subscribe(symb)
        if sym not in self.prs:
            self.prs[sym] = pairs.Pair(sym, dt, self.ws)
            self.curr_symbol = sym
            threading.Thread(target=self.prime).start()
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
    
    def pairwise_forex_major(self):
        plt = interactive(self.pairwise_plot, y = self.forex_major, x = self.forex_major)
        return(display(plt))
    
    def pairwise_volatility_indices(self):
        plt = interactive(self.pairwise_plot, y = self.volatility_indices, x = self.volatility_indices)
        return(display(plt))
    
    def tables_forex_major(self):
        interactive(display(self.coint_mat.loc[self.forex_major, self.forex_major]))
        interactive(display(self.corr_mat.loc[self.forex_major, self.forex_major]))
        return
    
    def tables_volatility_indices(self):
        interactive(display(self.coint_mat.loc[self.volatility_indices, self.volatility_indices]))
        interactive(display(self.corr_mat.loc[self.volatility_indices, self.volatility_indices]))
        return
    
    def show_proposals(self):
        interactive(display(self.proposals))
        return()
    
    def TA_plot(self, y, rng):
        self.prs.get(y).TA(self.period, rng)
        return
    
    def ta(self):
        threading.Thread(target=self.ta_plot).start()
        return
    
    def ta_plot(self):
        plt = interactive(self.TA_plot, y = list(self.prs.keys()), rng = list(range(0, 1290)))
        return(display(plt))
    
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
                if(key not in self.volatility_indices and ky not in self.volatility_indices):
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
            indx = len(dff.index.values) - 1 
            
            y = self.prs.get(pr[0]).standardized_prices()
            x = self.prs.get(pr[1]).standardized_prices()
            b = stats.linregress(x, y).slope
            
            if(dff['spread'][indx] < dff['lower'][indx]):
                #signals.append({pr[0]: ['Buy', 1], pr[1]: ['Sell', abs(b)]})
                display(ipd.Audio('sounds/beep.wav', autoplay=True))
                #self.Buy(pr[0], self.quantity * 1)
                #self.Sell(pr[1], self.quantity * abs(b))
            elif(dff['spread'][indx] > dff['upper'][indx]):
                #signals.append({pr[0]: ['Sell', 1], pr[1]: ['Buy', abs(b)]})
                display(ipd.Audio('sounds/beep.wav', autoplay=True))
                #self.Sell(pr[0], self.quantity * 1)
                #self.Buy(pr[1], self.quantity * abs(b))
        return(signals)
    
    def process_proposal(self, message):
        pid = message['proposal']['id']
        symbol = message['echo_req']['symbol']
        basis = message['echo_req']['basis']
        amount = float(message['echo_req']['amount'])
        payout = ((float(message['proposal']['payout']) - amount ) / amount ) * 100
        duration = message['echo_req']['duration'] + message['echo_req']['duration_unit']
        contract = message['echo_req']['contract_type']
        spot = float(message['proposal']['spot'])
        barrier = ''
        barrier2 = ''
        if ('barrier' in message['echo_req']):
            barrier = message['echo_req']['barrier']
        if ('barrier2' in message['echo_req']):
            barrier2 = message['echo_req']['barrier2']
        
        if( (payout < 103) and symbol in self.volatility_indices[:5]):
            #display(ipd.Audio('sounds/beep.wav', autoplay=True))
            self.unsubscribe(pid)
        else:
            self.prs.get(symbol).trading_pip = abs(barrier)
            self.params['symbol'] = symbol
            self.params['basis'] = basis
            self.params['amount'] = amount
            self.params['payout'] = payout
            self.params['duration'] = duration
            self.params['contract_type'] = contract
            self.params['spot'] = spot
            self.params['barrier'] = barrier
            self.params['barrier2'] = barrier2

            df0 = pandas.DataFrame(prop, index = [pid])
            if( (pid in proposals.index) is True):
                proposals.loc[pid] = df0.loc[pid]
            else:
                proposals = pandas.concat([proposals, df0], sort = True)
            return
        return
    
    plots_tables = ['pairwise_forex_major', 'pairwise_volatility_indices', 
                    'tables_forex_major', 'tables_volatility_indices', 
                    'ta', 'proposals']
    
    def views(self):
        stake_widget = widgets.Text(value=str(self.params.get('amount')), description='Stake:', disabled=False, continuous_update=True)
        payout_widget = widgets.Text(value = '%', description='Payout:',disabled=True, continuous_update=True)

        barrier_widget = widgets.Text(value=str(self.params.get('barrier')), description='Barrier:', disabled=False, continuous_update=True)
        contr_type_widget = widgets.Dropdown(options=self.contract_type, value=str(self.params.get('contract_type')), description='', disabled=True, continuous_update=True)
        barrier2_widget = widgets.Text(value=str(self.params.get('barrier2')), description='Barrier2:', disabled=True, continuous_update=True)

        dur_widget = widgets.Text(value=str(self.params.get('duration')), description='Duration:', disabled=False, continuous_update=True)
        dur_type_widget = widgets.Dropdown(options=['Ticks', 'Seconds','Minutes', 'Hours', 'Days'], value='Minutes',disabled=False, continuous_update=True)

        sym_widget = widgets.Dropdown(options=self.volatility_indices + self.forex_major, description='Pair:', disabled=False, continuous_update=True, value = self.curr_symbol)
        proposal_bt = widgets.Button(description='Proposal', disabled=False, tooltip='Proposal')

        hbox1 = widgets.HBox([ stake_widget, payout_widget ])
        hbox2 = widgets.HBox([  barrier_widget, contr_type_widget, barrier2_widget])
        hbox3 = widgets.HBox([  dur_widget, dur_type_widget])
        hbox4 = widgets.HBox([  sym_widget, proposal_bt])
        vbox0 = widgets.VBox([hbox1, hbox2, hbox3, hbox4])

        alert_box = widgets.Checkbox(value=self.alert,description='Alert',disabled=False, continuous_update=True)
        logout_bt = widgets.Button(description='Log Out', disabled=False, tooltip='Log Out')

        ping_bt = widgets.Button(description='Ping', disabled=False, tooltip='Ping')
        automate_box = widgets.Checkbox(value=self.automate,description='Automate',disabled=False, continuous_update=True)

        hbox00 = widgets.HBox([ logout_bt, alert_box ])
        hbox01 = widgets.HBox([ ping_bt, automate_box ])
        vbox2 = widgets.VBox([hbox00, hbox01])
        
        plts_n_tbs = self.plots_tables
        random.shuffle(plts_n_tbs,random.random)
        view_widget0 = widgets.Select(options=plts_n_tbs, disabled=False)
        view_widget1 = widgets.Dropdown(options=list(self.proposals.index), disabled=False)
        if(self.prop is not ''):
            view_widget1.value = self.prop
        rem_bt = widgets.Button(description='Remove', disabled=False, tooltip='Remove')
        purchase_bt = widgets.Button(description='Purchase', disabled=True, tooltip='Purchase', continuous_update=True)
        purchaseall_bt = widgets.Button(description='Purchase All', disabled=True, tooltip='Purchase All', continuous_update=True)
        hbox5 = widgets.HBox([  rem_bt, purchase_bt])
        vbox1 = widgets.VBox([view_widget0, purchaseall_bt, view_widget1, hbox5])

        children = [vbox0, vbox1, vbox2]
        tab = widgets.Tab()
        tab.children = children
        
        proposal_bt.on_click(self.make_proposal)
        stake_widget.observe(self.change_stake, names='value')
        barrier_widget.observe(self.change_barrier, names='value')
        contr_type_widget.observe(self.change_contract_type, names='value')
        barrier2_widget.observe(self.change_barrier2, names='value')
        dur_widget.observe(self.change_duration, names='value')
        dur_type_widget.observe(self.change_duration_type, names='value')
        sym_widget.observe(self.change_symbol, names='value')
        logout_bt.on_click(self.logout)
        ping_bt.on_click(self.ping)
        alert_box.observe(self.set_alarm, names='value')
        automate_box.observe(self.set_automate, names='value')
        view_widget0.observe(self.sh_object_show, names='value')
        view_widget1.observe(self.set_prop, names='value')
        rem_bt.on_click(self.remove_proposal)
        purchase_bt.on_click(self.make_purchase)
        purchaseall_bt.on_click(self.makeall_purchase)
        return(tab)
    
    def make_proposal(self): 
        try:
            self.ws.send(json.dumps(self.params))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
        return
    def change_stake(self, change): 
        self.params['amount'] = change['new']
        return
    def change_barrier(self, change): 
        self.params['barrier'] = change['new']
        if(change['new'] == ''):
            del self.params['barrier']
        return
    def change_contract_type(self, change): 
        self.params['contract_type'] = change['new']
        return
    def change_barrier2(self, change): 
        self.params['barrier2'] = change['new']
        if(change['new'] == ''):
            del self.params['barrier2']
        return
    def change_duration(self, change): 
        self.params['duration'] = change['new']
        return
    def change_duration_type(self, change): 
        self.params['duration_type'] = change['new'][0].lower()
        return
    def change_symbol(self, change): 
        self.curr_symbol = change['new']
        self.params['symbol'] = change['new']
        return
    def sh_object_show(self, change):
        clear_output()
        switcher = {'pairwise_forex_major': self.pairwise_forex_major, 'pairwise_volatility_indices': self.pairwise_volatility_indices, 
                    'tables_forex_major': self.tables_forex_major, 'tables_volatility_indices': self.tables_volatility_indices, 
                    'ta': self.ta, 'proposals': self.show_proposals}
        #switcher = {'tables_volatility_indices': self.tables_volatility_indices, 'proposals': self.show_proposals}
        func = switcher.get(change['new'], lambda: "Invalid View")
        func()
        return
    def set_prop(self, change): 
        self.prop = change['new']
        return
    def set_alarm(self, change): 
        self.alert = bool(change['new'])
        return
    def set_automate(self, change): 
        self.automate = bool(change['new'])
        return
    def remove_proposal(self):
        self.unsubscribe(self.prop)
        self.proposals = self.proposals.drop(self.prop)
        return
    def make_purchase(self): 
        self.buy('single')
        return
    def makeall_purchase(self): 
        self.buy('all')
        return