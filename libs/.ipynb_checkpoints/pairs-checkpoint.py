import websocket
import numpy
import json
import pandas
from sklearn import *
from statsmodels.tsa.stattools import adfuller
from scipy import stats
import warnings

class Pair:
    
    standardized_prices = []
    sym = ''
    ws = None
    curr_high = None
    curr_low = None
    pid = ''
    
    
    def __init__(self, symbol, dataframe, ws):
        self.sym = symbol
        self.ws = ws
        self.prices = dataframe
        self.curr_high = float(self.prices['Close'][len(self.prices.axes[0].tolist())-1])
        self.curr_low = self.curr_high
        self.ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))
        return
    
    def update(self, symbol, pid, time, quote):
        quote = float(quote)
        self.pid = pid
        ts0 = self.prices.axes[0].tolist()[len(self.prices.axes[0].tolist())-1]
        if(ts0.minute == time.minute):
            cl = quote
            self.curr_high = max(quote, self.curr_high)
            self.curr_low = min(self.curr_low, quote)
            opn =  self.prices['Close'][len(self.prices.axes[0].tolist())-2]
            d = {'Open': [opn], 'High': [self.curr_high], 'Low': [self.curr_low], 'Close': [cl]}
            dtf = pandas.DataFrame(data = d, index = [time])
            ts2 = self.prices.axes[0].tolist()[len(self.prices.axes[0].tolist())-2]
            self.prices = self.prices[:ts2]
            self.prices = pandas.concat([self.prices, dtf])
        else:
            ts = self.prices.axes[0].tolist()[0]
            self.prices = self.prices.drop(ts)
            cl = quote
            self.curr_high = quote
            self.curr_low = quote
            opn =  self.prices['Close'][len(self.prices.axes[0].tolist())-1]
            d = {'Open': [opn], 'High': [self.curr_high], 'Low': [self.curr_low], 'Close': [cl]}
            dtf = pandas.DataFrame(data = d, index = [time])
            self.prices = pandas.concat([self.prices, dtf])
            self.prices = self.prices.round(5)
        self.standardize_prices()
        return
    
    def standardize_prices(self):
        y_np = numpy.array(self.prices['Close'].tolist())
        self.standardized_prices = ( (y_np-y_np.mean())/y_np.std() ).tolist()
        return
    
    def co_integration(self, prs, ct_mat, spreads):
        ct_mat = ct_mat
        spreads = spreads
        adfs = dict()
        spd = pandas.DataFrame()
        
        for ky in prs:
            x = prs.get(ky).standardized_prices
            y = prs.get(self.sym).standardized_prices
            if(len(x) == len(y) and len(x) > 0 and len(y) > 0):
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                s_x = list(map(lambda a: a*slope, x))
                spread = [a - b for a, b in zip(y, s_x)]
                spd[ky] = pandas.Series(spread)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    adf = adfuller(spread, maxlag=1)
                adfs[ky] = adf[1]
                
        spreads[self.sym] = spd
            
        df0 = pandas.DataFrame(adfs, index = [self.sym])
        if( (ct_mat is not None and self.sym in ct_mat.index) is True):
            ct_mat.loc[self.sym] = df0.loc[self.sym]
        else:
            ct_mat = pandas.concat([ct_mat, df0], sort = True)
        
        adfs = None
        spd = None
        spread = None
        
        return([ct_mat, spreads])