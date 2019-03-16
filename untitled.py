
    prop = ''
    ipairs = []
    contract_type = []
    stake = 0.5
    #dataset0 = pandas.DataFrame()
    alert = False
    automate = False
    corr_bd = 0.5
    period = 5
    closed = False
    
    
    
     def co_integration(self, prs, ct_mat):
        ct_mat = ct_mat
        adfs = dict()
        
        for ky in prs.copy():
            spd = pandas.DataFrame()
            x = []
            y = []
            if('standardized_prices' in prs.get(ky).prices.columns and 
               'standardized_prices' in self.prices.columns and
                  ky is not self.sym):
                x = prs.get(ky).prices['standardized_prices']
                y = self.prices['standardized_prices']
                if(len(x) == len(y) and len(x) > 0 and len(y) > 0):
                    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                    s_x = list(map(lambda a: a*slope, x))
                    spread = [a - b for a, b in zip(y, s_x)]
                    spd['spread'] = spread
                    spd['mean'] = spd['spread'].mean()
                    spd['upper'] = spd['mean'] + (2.05*spd['spread'].std())
                    spd['lower'] = spd['mean'] - (2.05*spd['spread'].std())
                    spd = spd.round(5)
                    spd['buy'] = spd['spread'][((spd['spread'] < spd['lower']) & (spd['spread'].shift(1) > spd['lower']) | 
                                      (spd['spread'] <  spd['mean']) & (spd['spread'].shift(1) >  spd['mean']))]
                    spd['sell'] = spd['spread'][((spd['spread'] > spd['upper']) & (spd['spread'].shift(1) < spd['upper']) | 
                                       (spd['spread'] >  spd['mean']) & (spd['spread'].shift(1) <  spd['mean']))]
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        adf = adfuller(pandas.Series(spread).fillna(0), maxlag=1)
                    adfs[ky] = adf[1]
                    del spread, s_x, slope, intercept, r_value, p_value, std_err
            self.spreads[ky] = spd
            del x, y, spd
        
        df0 = pandas.DataFrame(adfs, index = [self.sym])
        if( (ct_mat is not None and self.sym in ct_mat.index) is True):
            ct_mat.loc[self.sym] = df0.loc[self.sym]
        else:
            ct_mat = pandas.concat([ct_mat, df0], sort = True)
        
        del adfs
        return(ct_mat)
    '''
    
    '''
    def corr(self):
        dtf = pandas.DataFrame()
        minimum = min([len(x.prices.index) for x in self.prs.values()])
        
        for key in self.prs.copy():
            if('standardized_prices' in self.prs.get(key).prices.columns):
                yy = self.prs.get(key).prices[-minimum:]['standardized_prices']
                dtf[key] = pandas.Series(yy)
        self.corr_mat = dtf.corr(method='kendall').replace(1, 0)
        self.corr_mat = self.corr_mat.round(5)
        del dtf
        
        for key in self.prs.keys():
            if(key in self.volatility_indices):
                df = self.prs.get(key).prices
                l_ts = df.index[len(df.index) - 1]
                if(df.loc[l_ts]['RSI'] > df.loc[l_ts]['UPPER_RSI'] or df.loc[l_ts]['RSI'] > df.loc[l_ts]['LOWER_RSI']):
                    #########################
                    display(ipd.Audio('sounds/beep.wav', autoplay=True))
                    pass
                del df
                pass
            for ky in self.prs.keys():
                if(key not in self.volatility_indices and ky not in self.volatility_indices and key is not ky):
                    if(self.corr_mat.loc[key][ky] <= -self.corr_mat.min().min() and 
                         self.coint_mat.loc[key][ky] < 0.05 and self.coint_mat.loc[ky][key] < 0.05):
                        #######################
                        pass
                    pass
        
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
    
    '''
    
    '''
    
    
    
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
        '''
    
    
    '''
    plots_tables = ['pairwise_forex_major', 'pairwise_volatility_indices', 
                    'tables_forex_major', 'tables_volatility_indices', 
                    'ta', 'proposals']
    
    
    def views(self):
        stake_widget = widgets.Text(value=str(self.params.get('amount')), description='Stake:', disabled=self.automate, continuous_update=True)
        payout_widget = widgets.Text(value = '%', description='Payout:',disabled=True, continuous_update=True)

        barrier_widget = widgets.Text(value=str(self.params.get('barrier')), description='Barrier:', disabled=self.automate, continuous_update=True)
        contr_type_widget = widgets.Dropdown(options=self.contract_type, value=str(self.params.get('contract_type')), description='', disabled=self.automate, continuous_update=True)
        barrier2_widget = widgets.Text(value=str(self.params.get('barrier2')), description='Barrier2:', disabled=self.automate, continuous_update=True)

        dur_widget = widgets.Text(value=str(self.params.get('duration')), description='Duration:', disabled=self.automate, continuous_update=True)
        dur_type_widget = widgets.Dropdown(options=['Ticks', 'Seconds','Minutes', 'Hours', 'Days'], value='Minutes',disabled=self.automate, continuous_update=True)

        sym_widget = widgets.Dropdown(options=self.volatility_indices + self.forex_major, description='Pair:', disabled=False, continuous_update=True, value = self.curr_symbol)
        proposal_bt = widgets.Button(description='Proposal', disabled=False, tooltip='Proposal')
        save_proposal_bt = widgets.Button(description='Save Proposal', disabled=False, tooltip='Save Proposal')
        unsub_sym_bt = widgets.Button(description='Unsubscribe Pair', disabled=False, tooltip='Unsubscribe Pair')

        hbox1 = widgets.HBox([ stake_widget, payout_widget, sym_widget ])
        hbox2 = widgets.HBox([  barrier_widget, contr_type_widget, barrier2_widget])
        hbox3 = widgets.HBox([  dur_widget, dur_type_widget])
        hbox4 = widgets.HBox([ proposal_bt, save_proposal_bt, unsub_sym_bt])
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

        reload_pairs_bt = widgets.Button(description='Reload Pairs', disabled=False, tooltip='Reload Pairs')
        
        children = [vbox0, vbox1, vbox2, reload_pairs_bt]
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
        reload_pairs_bt.on_click(self.reload_pairs)
        return(tab)
    
    def reload_pairs0(self):
        for sym in self.prs:
            try:
                self.prs.get(sym).standardize_prices()
                resp = self.prs.get(sym).co_integration(self.prs, self.coint_mat, self.spreads)
                self.coint_mat = resp[0]
                self.coint_mat = self.coint_mat.fillna(0.999)
                self.coint_mat= self.coint_mat.round(5)
                self.spreads = resp[1]
            except:
                pass
        return
    def reload_pairs(self, dummy=None): 
        threading.Thread(target=self.reload_pairs0).start()
        return
    def make_proposal(self, dummy=None): 
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
        if(change['new'].strip() == '' or change['new'].strip() == str(None)):
            del self.params['barrier']
            self.params['barrier'] = '+' + str(self.prs.get(self.curr_symbol).trading_pip)
        return
    def change_contract_type(self, change): 
        self.params['contract_type'] = change['new']
        return
    def change_barrier2(self, change): 
        self.params['barrier2'] = change['new']
        if(change['new'].strip() == '' or change['new'].strip() == str(None)):
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
        clear_output()
        self.automate = bool(change['new'])
        return
    def remove_proposal(self, dummy=None):
        self.unsubscribe(self.prop)
        self.proposals = self.proposals.drop(self.prop)
        return
    def make_purchase(self, dummy=None): 
        self.buy('single')
        return
    def makeall_purchase(self, dummy=None): 
        self.buy('all')
        return
        '''
    
    
    
    
    
    '''
    def buy(self, qunty='single'):
        try:
            if (qunty == 'all'):
                for key in self.proposal.index:
                    self.ws.send(json.dumps(
                        {"buy": key, 
                         "price": self.proposal.loc[key]['amount']}))
            else:
                self.ws.send(json.dumps(
                        {"buy": self.prop, 
                         "price": self.proposal.loc[self.prop]['amount']}))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
        return
    '''
    
    '''
    Pairs
    
    '''
    
    '''
    def hedge_onetouch_proposal(self, amount, duration, duration_unit):
        try:
            self.ws.send(json.dumps({
                                 "proposal": 1,
                                 "amount": str(amount),
                                 "basis": "stake",
                                 "contract_type": "ONETOUCH",
                                 "currency": "USD",
                                 "duration": str(duration),
                                 "duration_unit": duration_unit,
                                 "barrier": "+" + str(self.barrier),
                                 "symbol": self.sym
                                }))
            self.ws.send(json.dumps({
                                 "proposal": 1,
                                 "amount": str(amount),
                                 "basis": "stake",
                                 "contract_type": "ONETOUCH",
                                 "currency": "USD",
                                 "duration": str(duration),
                                 "duration_unit": duration_unit,
                                 "barrier": "-" + str(self.barrier),
                                 "symbol": self.sym
                                }))
        except websocket.WebSocketConnectionClosedException as e:
            self.ws.run_forever()
        return
        return
    '''