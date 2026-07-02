import joblib
import seaborn as sns
from CleanData import CleanData
from RealWorldTest.RealWorldTesting import *
from GettingTrainingData.PrintMachine import *
from GettingTrainingData.GetAPIStuff import *
from modelsMachine import *
from GettingTrainingData.db import *
import pandas as pd
import matplotlib.pyplot as plt
import os
global my_path
my_path = os.path.dirname(os.path.abspath(__file__))

def doData(): 
    
    events = APIgetEventsStuff(start_date_min=1735775999,offset = 1810)
    count = 0
    for event in events:
        markets = event['markets']
        try:
            for market in markets:
                print(count)
                print_market(market)
                count+=1
                conditionId = market['conditionId']
                cur = conn.cursor()
                cur.execute("SELECT conditionId FROM markets WHERE conditionId = ?",(conditionId,))
                if cur.fetchone():
                    print("Already have market")
                    continue
                trades = APIgetTradesByMarket(conditionId)

                if len(trades) == 0: #well duhhh
                    print("no trades")
                    continue
                print(len(trades))
                if not insertMarketToDB(conn,market,event): #### INSERT MARKET TO DB HERE
                    print("insert Failed")
                    continue
                
                walletList = []
                for trade in trades:
                    insertTradeToDB(conn,trade) #### INSERT TRADE TO DB
                    proxyWallet = trade['proxyWallet']
                    ##### check DB first 
                    cur = conn.cursor()
                    cur.execute("SELECT wallet FROM users WHERE wallet = ?", (proxyWallet,))
                    if cur.fetchone():
                        continue 
                    #####  else
                    user = APIgetUserByProxyWallet(proxyWallet)
                    if 'error' in user.keys(): #deletedAcc
                        continue
                    walletList.append(user)
                collectAllUsersTrades(walletList,conn) #Decided to do some multithreading to speed up the api calls so all the inserts are in here
                #####^^^^ ALLINSERTS IN HERE FOR USERS^^^^
                print(f'With count: {count}')  
                CheckOutDB()
        except KeyError:
            continue
    return


def doStats():

    df_trades  = pd.read_sql("SELECT * FROM trades",conn)
    df_markets = pd.read_sql("SELECT * FROM markets", conn).rename(columns={'outcome': 'market_outcome','createdAt':'marketCreate'})
    df_users   = pd.read_sql("SELECT * FROM users", conn)

    df = CleanData(df_trades,df_markets,df_users) 

    print(df.shape) 
    print(df.describe())
    print(df.columns)

    features = ['price', 'size', 'volume', 'size/vol', 'commentCount','weightedVol','nTrades','nMark/nTrades','avgSize','nWins/nTrades','avgPrice','maxSize','startToLastUpdate','createdToStart','tradeTimeFromEnd','account_age_at_trade','window_trade_count','hour_of_day','market_avg_size_so_far','tradeByUserPerMarket','profilePic']
    
    corr_matrix = df[features].corr()
    print(corr_matrix)

    plt.figure(figsize=(20, 16))
    sns.heatmap(corr_matrix, 
                annot=True,      # show values
                fmt='.2f',       # 2 decimal places
                cmap='coolwarm', # red to blue
                center=0)        # center colormap at 0

    plt.title('Feature Correlation Matrix')
    #plt.savefig(my_path+"/Figs/CorrelationMatrixV2.png", dpi=150)
    #plt.show()
    
    #########################################################################################
    ###################### If price >0.5 just bet bro #######################################
    #print("-"*20+"Base") 
    #BaseLineME(df)
    '''
    accuracy = 72%
    '''
    #Note MARKET WIN RATE IS IN FEATURETEST.PY
    #########################################################################################
    ##############      LOGISTIC REGRESSION!!! ##############################################
    ##################### WITH PRICE
    #LogisticRegressionME(df,features)
    # 72.2 
    #######################################################################################
    ################ RANDOM FOREST!!!  ####################################################
    #RandomForestME(df,price=False)
    # 64.9 with usertradecount
    # 64.4 with user trade count and window trade count
    # 66.4 with user trade count and window trade count and market avg size(65.7 with so far) and hour of day
    ################# WITH PRICE
    #RandomForestME(df,features)
    # 80.0 ish 
    ####################################################################################
    ########### XGBOOST IT #############################################################
    #XGBoostME(df,price=False)
    # 65.8 with user trade count, significant with p-value = 0.0000
    # 65.78 with user trade count and (window trade count, significant with p-value = 0.0005)

    # 65.91 with (hour of day, significant with p-value = 0.0071), user trade count and window trade count
    # 66.36 with user trade count and window trade count and market avg size so far (67.36 without so far) and hour of day wowie significant with p-value = 0.0000
    ############# WITH PRICE

    print("--------------------XGB WITH PRICE")
    model = XGBoostME(df,features,20)
    testOnNewMarkets(model,features)
    #XGBoostME(market_features,['avg_price', 'last_price', 'price_std', 'n_trades', 
    #                 'n_unique_traders', 'avg_size', 'total_volume', 
    #                  'avg_account_age','account_age_std', 'buy_pressure']) #itsbaaad
    # 82.14 with user trade count and window trade count and market avg size so far (without so far its 84.24) and hour of day wowie
    ##################################################################################
    ############ NEURAL NETWORK ######################################################
    #NeuralNetworkME(df,price=False)
    #NeuralNetworkME(df,price=True)

    #PATH = os.path.join(os.path.dirname((os.path.abspath(__file__)),'models','polymarket_xgb.pkl')
    #joblib.dump(model, PATH)
    return 

def doTestRuns():
    PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'polymarket_xgb.pkl')
    model = joblib.load(PATH)

    testOnNewMarkets(model)

    return

if __name__ == "__main__":
    #doData()
    doStats()
    #doTestRuns()
    print("Done!")