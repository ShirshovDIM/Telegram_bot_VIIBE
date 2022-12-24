## All the logic with Ethernet
import pandas as pd
import pandas_datareader.data as web
from datetime import datetime
import numpy as np
from alpha_vantage.timeseries import TimeSeries


def get_historical_data(ticker, start = '2000-01-01', stop = datetime.now().strftime('%Y-%m-%d')):
    try:
        start = datetime.strptime(start,'%Y-%m-%d')
        stop = datetime.strptime(stop,'%Y-%m-%d')
        if stop >= start:
            return(web.get_data_yahoo(ticker, start=start, end=stop))
        elif stop < start:
            return(web.get_data_yahoo(ticker, start=stop, end=start))
    except OverflowError: 
        raise '<Enter proper dates limitations>'


def get_daily_data(ticker, api_token, operation):
    
    sim = '1. open' if operation == 'sell' else '4. close'
    try:
        ts = TimeSeries(key = api_token, output_format='pandas')
        return ts.get_intraday(symbol = ticker, interval='1min')[0][sim].head(1).reset_index().values[0]
    except Exception as ex:
        raise ex



def trader(df,money = 100000,stop_loss = 7, short_window = 30, long_window = 90):
    
    # initial df fixing
    df.columns = df.columns.map(lambda x: x.capitalize())
    df.index = df.index.map(lambda x: datetime.strftime(x, '%Y-%m-%d'))
    df.index = df.index.map(lambda x: datetime.strptime(x, '%Y-%m-%d'))

    # signal determination with stop-loss implemented
    short_crv = df.Close.rolling(short_window).mean()
    long_crv = df.Close.rolling(long_window).mean()
    asign = np.sign(short_crv - long_crv).dropna()
    signchange = (~(np.roll(asign, 1) - asign).isin([0,np.nan])).values
    
    asing = asign[signchange]
    dates = asing.index
    df = df.reset_index()


    df_test = pd.DataFrame(columns = ['date', 'signal', 'num_shares','share_price',
                                      'share_value', 'rest', 'cash'])

    cap = money

    stop_loss /= 100 

    if(asign[signchange].iloc[0] < 0):
        price_sale = np.round(df.Open[df.Date.shift(1) == dates[0]],2).values[0]
        df_test = pd.concat([df_test, pd.DataFrame({
            'date': [dates[0],df.Date[df.Date.shift(1) == dates[0]].values[0]],
            'signal':['sig sale', 'sale'],
            'num_shares':[0,0],
            'share_price':[np.nan, price_sale],
            'share_value':[np.nan, 0],
            'rest':[0, 0],
            'cash':[cap, cap]
            })])


    for i in dates:
        sign = asign[asign.index == i].values
        if sign == 1. and dates.get_loc(i) != (len(dates) - 1): 
            price_buy = np.round(df.Open[df.Date.shift(1) == dates[dates.get_loc(i)]],2).values[0]
            price_sale = np.round(df.Open[df.Date.shift(1) == dates[dates.get_loc(i) + 1]],2).values[0]
            amount_action = int(cap // price_buy)
            final_cash = cap
            for j in pd.bdate_range(df.Date[df.Date.shift(1) == dates[dates.get_loc(i)]].values[0],
                                    df.Date[df.Date.shift(1) == dates[dates.get_loc(i) + 1]].values[0]):
                try: 
                    if (df.Low[df.Date == j]/price_buy < (1 - stop_loss)).values[0]:
                        final_cash = (cap - price_buy * amount_action 
                                      + np.round((1 - stop_loss) * price_buy,2)
                                      * amount_action)
                        df_test = pd.concat([df_test, pd.DataFrame({
                            'date': [i,df.Date[df.Date.shift(1) == dates[dates.get_loc(i)]].values[0],
                            j,dates[dates.get_loc(i) + 1],
                            df.Date[df.Date.shift(1) == dates[dates.get_loc(i) + 1]].values[0]],
                            'signal':['sig buy', 'buy', 'stop-loss','sig sale', 'sale'],
                            'num_shares':[0,amount_action,amount_action,0,0],
                            'share_price':[np.nan, price_buy, np.round((1 - stop_loss)*price_buy,2),np.nan, price_sale],
                            'share_value':[np.nan, price_buy * amount_action, np.round((1 - stop_loss) * price_buy,2) * amount_action, np.nan, 0],
                            'rest':[0, cap - price_buy * amount_action, cap - price_buy * amount_action, 0, 0],
                            'cash':[cap, cap - price_buy * amount_action,final_cash,final_cash,final_cash]
                            })])
                        break
                except IndexError:
                    continue
            try:
                if cap == final_cash :
                    final_cash = (cap - price_buy * amount_action 
                                  + price_sale * amount_action)
                    df_test = pd.concat([df_test, pd.DataFrame({
                        'date': [i,df.Date[df.Date.shift(1) == dates[dates.get_loc(i)]].values[0],dates[dates.get_loc(i) + 1],
                        df.Date[df.Date.shift(1) == dates[dates.get_loc(i) + 1]].values[0]],
                        'signal':['sig buy', 'buy','sig sale', 'sale'],
                        'num_shares':[0,amount_action,amount_action,amount_action],
                        'share_price':[np.nan, price_buy,np.nan, price_sale],
                        'share_value':[np.nan, price_buy * amount_action,np.nan, price_sale * amount_action],
                        'rest':[0, cap - price_buy * amount_action, cap - price_buy * amount_action, cap - price_buy * amount_action],
                        'cash':[cap, cap - price_buy * amount_action, cap - price_buy * amount_action,final_cash]})])
            except IndexError:
                continue
            cap = df_test.cash.iloc[-1]
            
    df_test.date = df_test.date.map(lambda x: datetime.strftime(x, '%Y-%m-%d')).map(lambda x: datetime.strptime(x, '%Y-%m-%d'))
    df_test.index = range(len(df_test)) 
    df_test = df_test[:df_test[df_test.signal.isin(['sale','stop-loss']) & df_test.num_shares > 0].index[-1] + 1]
    

    return [df, df_test, np.round(df_test.cash.iloc[-1],2)]

