import time
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from GettingTrainingData.PrintMachine import *
from GettingTrainingData.GetAPIStuff import *
from modelsMachine import *
from GettingTrainingData.db import *
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def doData(): 

    events = APIgetEventsStuff()
    eventcount =0
    for event in events:

        print(f"  {eventcount}")
        print_event(event)
        eventcount += 1

        event_markets = event['markets']

        
        for market in event_markets:

            if float(market.get('volume', 0)) < 50000:
                continue
            conditionId = market['conditionId']
            trades = APIgetTradesByMarket(conditionId)

            if len(trades) == 0: #well duhhh
                print("no trades")
                continue
            if not insertMarketToDB(conn,market):
                print("insert Failed")
                continue

            print_market(market)

            for trade in trades:

                insertTradeToDB(conn,trade)

                proxyWallet = trade['proxyWallet']

                ##### check DB first 
                cur = conn.cursor()
                cur.execute("SELECT wallet FROM users WHERE wallet = ?", (proxyWallet,))
                if cur.fetchone():
                    continue 
                #####  else
                user = APIgetUserByProxyWallet(proxyWallet)
                if 'error' in user.keys():
                    #insertUserToDB(conn,{"createdAt":"NULL","proxyWallet":0}) #deleted account? (JUST NEED TO DO ONCE, ALL TRADES WITH NO WALLET COUNT FOR HIM)
                    continue
                insertUserToDB(conn,user)
                #####
    return


def doStats():

    df_trades  = DBgetTrades(conn, 574024) # Total trades is 574024
    df_markets = pd.read_sql("SELECT * FROM markets", conn).rename(columns={'outcome': 'market_outcome'})
    df_users   = pd.read_sql("SELECT * FROM users", conn)

    ###### MERGE AND FIX DATA
    df = df_trades.merge(df_markets, on='conditionId', how='left').merge(df_users, on='wallet', how='left')
    df['won'] = (df['outcome'] == df['market_outcome']).astype(int)
    df['timestamp'] = df['timestamp'].astype(int)
    df['endDate'] = pd.to_datetime(df['endDate'], format='ISO8601') ## endDate -> datetime
    df['endDate'] = df['endDate'].apply(lambda x: x.timestamp() if pd.notna(x) else None )  ## datetime -> timestamp
    df = df.dropna(subset=['endDate']) #drop if endDate is Na (about 1% of them)
    df['timeFromEnd'] = (df['endDate']-df['timestamp'])
    df = df[df['timeFromEnd'] > 60] #Just cleaning up trades made after market end (lost about 80k trades)
    df = df[df['size'] >= 2] #Removing trades that are potentially test trades and bots, did a few tests and 2 seemed like the best cutoff (lost about 20k trades)
    df['sizeToVolumePct'] = (df['size']/df['volume']) #Add for a trade the percent of its size relative to the market its in
    df['is_deleted'] = df['account_age'].isna().astype(int) #Deleted accounts could be sus so maybe add a tag for if deleted
    df['account_age'] = df['account_age'].fillna(df['account_age'].median()) #Make deleted accounts have median age to not fuck around with data and still keep them
    df['account_age_at_trade'] = (df['timestamp'] - df['account_age']) #time between account creation and time trade is done (hypothesis is new accounts are more likely to be sus)

    trade_counts = df.groupby('wallet')['won'].count().rename('user_trade_count')  # seems to be a pretty good feature
    df = df.merge(trade_counts, on='wallet')

    df = count_trades_in_window(df) #Number of trades between [t0-t,t] where t is time of trade

    df['hour_of_day'] = pd.to_datetime(df['timestamp'], unit='s').dt.hour

    market_avg_size = df.groupby('conditionId')['size'].mean().rename('market_avg_size')
    df = df.merge(market_avg_size, on='conditionId')

    df = df.sort_values(['conditionId', 'timestamp'])
    df['market_avg_size_so_far'] = df.groupby('conditionId')['size'].transform(
        lambda x: x.expanding().mean().shift(1)  # shift(1) excludes current trade
    )

    trade_count_per_market = df.groupby(['wallet', 'conditionId'])['won'].count().rename('tradeByUserPerMarket')
    df = df.merge(trade_count_per_market, on=['wallet', 'conditionId'])


    # quick stats on every column
    print(df.shape) #474870,18
    print(df.columns)
    print(df.describe())

    features = ['account_age_at_trade', 'timeFromEnd', 'sizeToVolumePct', 'size', 'price','user_trade_count','window_trade_count','hour_of_day','market_avg_size_so_far']
    corr_matrix = df[features].corr()
    print(corr_matrix)


    sns.heatmap(corr_matrix, 
                annot=True,      # show values
                fmt='.2f',       # 2 decimal places
                cmap='coolwarm', # red=positive, blue=negative
                center=0)        # center colormap at 0

    plt.title('Feature Correlation Matrix')
    plt.show()

    #########################################################################################
    ###################### If price >0.5 just bet bro #######################################
    print("-"*20+"Base") 
    BaseLineME(df)
    '''
    accuracy = 72%
    '''

    #Note MARKET WIN RATE IS IN FEATURETEST.PY
    #########################################################################################
    ##############      LOGISTIC REGRESSION!!! ##############################################
    print("-"*20+"LR WITHOUT PRICE")
    #LogisticRegressionME(df,price=False) 
    '''
    accuracy = 52.9%

    account_age_at_trade    0.083594
    timeFromEnd             0.012295
    sizeToVolumePct        -0.006053
    '''
    # 54.6 with user trade count and window trade count
    ##################### WITH PRICE
    print("-"*20+"LR WITH PRICE")
    #LogisticRegressionME(df,price=True)
             #feels worse than just using price and no model haha (model just doing low price => not win and high price => win)
    '''
    accuracy = 72.2%

    price                   1.315195
    timeFromEnd             0.041112
    account_age_at_trade    0.021879
    sizeToVolumePct         0.006112
    '''
    # 72.2 with user trade count and window trade count
    #######################################################################################
    ################ RANDOM FOREST!!!  ####################################################
    print("-"*20+"RF WITHOUT PRICE")
    #RandomForestME(df,price=False)
    '''
    accuracy = 62.9

    volume                  0.328541
    account_age_at_trade    0.294820
    timeFromEnd             0.229161
    size                    0.147478                  
    '''
    # 64.9 with usertradecount
    # 64.4 with user trade count and window trade count
    # 66.4 with user trade count and window trade count and market avg size(65.7 with so far) and hour of day
    ################# WITH PRICE
    print("-"*20+"RF WITH PRICE")
    #RandomForestME(df,price=True)
    '''
    acc=79.2

    price                   0.716105
    volume                  0.151933
    timeFromEnd             0.094256
    account_age_at_trade    0.025831
    size                    0.011875 
    '''
    # 80.2 with user trade count
    # 80.6 with user trade count and window trade count
    # 82.9 with user trade count and window trade count and market avg (82.16 with so far) and hour of day
    ####################################################################################
    ########### XGBOOST IT #############################################################
    print("-"*20+"XGB WITHOUT PRICE")
    #XGBoostME(df,price=False)
    '''
    acc = 62.6

    volume                  0.330936   significant with p-value = 0.0000
    account_age_at_trade    0.241058   significant with p-value = 0.0000
    timeFromEnd             0.233566   significant with p-value = 0.0000
    size                    0.194440   significant with p-value = 0.0037
    '''
    # 65.8 with user trade count, significant with p-value = 0.0000
    # 65.78 with user trade count and (window trade count, significant with p-value = 0.0005)
    # 65.91 with (hour of day, significant with p-value = 0.0071), user trade count and window trade count
    # 66.36 with user trade count and window trade count and market avg size so far (67.36 without so far) and hour of day wowie significant with p-value = 0.0000
    ############# WITH PRICE
    print("-"*20+"XGB WITH PRICE")
    XGBoostME(df,price=True)
    '''
    acc = 79.7

    price                   0.722309
    volume                  0.142674
    timeFromEnd             0.083503
    account_age_at_trade    0.030687
    size                    0.020827
    '''
    # 79.7 with user trade count
    # 81.62 with user trade count and window trade count
    # 81.76 with hour of day, user trade count and window trade count
    # 82.14 with user trade count and window trade count and market avg size so far (without so far its 84.24) and hour of day wowie
    ##################################################################################
    ############ NEURAL NETWORK ######################################################
    print("-"*20+"NN WITHOUT PRICE")
    #NeuralNetworkME(df,price=False)
    print("-"*20+"NN WITH PRICE")
    #NeuralNetworkME(df,price=True)
    return 


def count_trades_in_window(df, t=3600):
    df = df.sort_values('timestamp').copy()
    df['window_trade_count'] = 0
    
    for id, group in df.groupby('conditionId'):
        timestamps = group['timestamp'].values
        counts = [(timestamps >= ts - t).sum() 
                  for ts in timestamps]
        df.loc[group.index, 'window_trade_count'] = counts
    
    return df

if __name__ == "__main__":
    #doData()
    doStats()

    print("Done!")