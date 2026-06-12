import time

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from PrintMachine import *
from GetAPIStuff import *
from modelsMachine import *
from db import *
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy
import sklearn

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

    # quick stats on every column
    print(df.shape)
    print(df.describe())

    #########################################################################################
    ##############      LOGISTIC REGRESSION!!! ##############################################
    LinearRegressionME(df,price=False)
    '''
    accuracy = 52.9%

    account_age_at_trade    0.083594
    timeFromEnd             0.012295
    sizeToVolumePct        -0.006053
    '''
    ##################### WITH PRICE
    LinearRegressionME(df,price=True)
    '''
    accuracy = 72.2%
    price                   1.315195
    timeFromEnd             0.041112
    account_age_at_trade    0.021879
    sizeToVolumePct         0.006112
    '''
    #######################################################################################
    ################ RANDOM FOREST!!!  ####################################################
    X = df[['account_age_at_trade', 'timeFromEnd', 'sizeToVolumePct','size']]
    y = df.loc[X.index, 'won']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # no need to scale for Random Forest
    model_rf = RandomForestClassifier(
        n_estimators=100,    # number of trees
        max_depth=10,        # max depth per tree
        max_features=2,
        random_state=42,
        n_jobs=-1            # use all CPU cores
    )

    model_rf.fit(X_train, y_train)

    print(f"Accuracy: {model_rf.score(X_test, y_test):.3f}") #59.8%!!!! (without price)
    print(classification_report(y_test, model_rf.predict(X_test)))

    importances = pd.Series(model_rf.feature_importances_, index=X.columns)
    print(importances.sort_values(ascending=False))
    '''
    account_age_at_trade    0.368335
    timeFromEnd             0.282054
    size                    0.189767
    sizeToVolumePct         0.159844
    '''
    ################# WITH PRICE
    X = df[['account_age_at_trade', 'timeFromEnd', 'sizeToVolumePct','size','price']] 
    y = df.loc[X.index, 'won']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # no need to scale for Random Forest
    model_rf = RandomForestClassifier(
        n_estimators=100,    # number of trees
        max_depth=10,        # max depth per tree
        max_features=2,
        random_state=42,
        n_jobs=-1            # use all CPU cores
    )

    model_rf.fit(X_train, y_train)

    print(f"Accuracy: {model_rf.score(X_test, y_test):.3f}") #75.3% with price though...
    print(classification_report(y_test, model_rf.predict(X_test)))

    importances = pd.Series(model_rf.feature_importances_, index=X.columns)
    print(importances.sort_values(ascending=False))
    '''
    price                   0.814493
    timeFromEnd             0.091580
    account_age_at_trade    0.038694
    sizeToVolumePct         0.031958
    size                    0.023275  
    '''
    return




if __name__ == "__main__":
    #doData()
    doStats()

    print("Done!")