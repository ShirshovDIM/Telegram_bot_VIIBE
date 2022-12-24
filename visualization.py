import pandas as pd
import numpy as np
import plotly.graph_objects as go 
from datetime import datetime

def write_plots(fig):
    
    fig[0].write_image('plot.png', width=1024, scale = 2)
    fig[1].write_image('position.png', width=1024, scale = 2)

def graph(df, df_test, short_window = 30, long_window = 90):
    
    if short_window > long_window: 
        
        t = short_window
        short_window = long_window
        long_window = t

    elif short_window == long_window: 
        raise Exception

    short_crv = df.Close.rolling(short_window).mean()
    long_crv = df.Close.rolling(long_window).mean()

    activ_x = [pd.to_datetime(df.Date.iloc[0]), pd.to_datetime(df_test[df_test.signal == 'buy'].date.iloc[0])]
    
    activ_y = np.array([0,0])

    iter = df_test[df_test.signal.isin(['buy', 'sale', 'stop-loss'])].date.values


    for i in iter:

        activ_x.extend([pd.to_datetime(i), pd.to_datetime(i)])
        print(pd.to_datetime(i))
        if activ_y[len(activ_y) - 1] == 0:
            activ_y = np.append(activ_y, [np.where(df_test.signal[df_test.date == i] == 'buy', 0, 0),
                                          np.where(df_test.signal[df_test.date == i] == 'buy', 1, 0)])
        else: 
            activ_y = np.append(activ_y, [np.where(df_test.signal[df_test.date == i] == 'buy', 0, 1),
                                          np.where(df_test.signal[df_test.date == i] == 'buy', 1, 0)])

    activ_x.extend([df.Date.iloc[-1], df.Date.iloc[-1]])
    activ_y = np.append(activ_y, [0, 0])
    
    fig_list = [go.Scatter(x = df.Date,y = short_crv.values,mode = 'lines',line = {'color':'orange'}, name = 'short_slide'),
                go.Scatter(x = df.Date,y = long_crv.values,mode = 'lines',line = {'color':'brown'},  name = 'long_slide'),
                go.Scatter(x = df_test.date[df_test.signal.isin(['sig sale'])],
                           y = df.High[df.Date.isin(df_test.date[df_test.signal.isin(['sig sale'])].values)],
                           mode = 'markers',marker = {'size': 14, 'symbol': 'triangle-down', 'color':'darkred'},name = 'sigs_sale'),
                go.Scatter(x = df_test.date[df_test.signal.isin(['sig buy'])],
                           y = df.High[df.Date.isin(df_test.date[df_test.signal.isin(['sig buy'])].values)],
                           mode = 'markers',marker = {'size': 14, 'symbol': 'triangle-up', 'color': 'darkgreen'},name = 'sigs_buy'),
                go.Scatter(x = df_test.date[df_test.signal.isin(['stop-loss'])],
                           y = df.High[df.Date.isin(df_test.date[df_test.signal.isin(['stop-loss'])].values)],
                           mode = 'markers',marker = {'size': 14, 'symbol': 'triangle-down', 'color': 'black'},name = 'stop_loss'),
                go.Ohlc(x = df.Date.values, open = df.Open , high = df.High, low = df.Low, close = df.Close,  name = 'OHLC figure'),
                go.Scatter(x = activ_x, y = activ_y, mode = 'lines', line = {'color': 'black'}, name = 'position')]
    

    fig = go.Figure(data = fig_list[:-1])
    fig.update(layout_xaxis_rangeslider_visible=False)
    
    fig_new = go.Figure(data = fig_list[-1])
    fig_new.update_yaxes({'visible': False})
    
    fig_new.update_layout(yaxis_range = [-.0001, 2], height=300, ) 

    return [fig, fig_new]
