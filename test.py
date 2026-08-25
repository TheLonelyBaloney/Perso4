from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
from random import randrange
import time

import duckdb
import hdbscan
import joblib
import pandas as pd
import requests
import xgboost as xgb

CATMODEL = joblib.load("hdbscan_model.pkl")
SCALER = joblib.load("scaler.pkl")

def getmarket(n:int):
    time = datetime.datetime.fromtimestamp(1758244600).isoformat()
    url = "https://gamma-api.polymarket.com/markets"
    response = requests.get(
        url,
        params={
            "limit":n,
            "volume_num_min":100000,
            "start_date_min":f'{time+'Z'}',
            "closed":"true",
            "offset":100
        }
    )
    return response.json()

def tradesByMarket(condition_id):


    nonTrivialTrades = []
    offset = 0
    while len(nonTrivialTrades) < 1000:
        url = "https://data-api.polymarket.com/trades"
        response = requests.get(
            url,
            params = {
                "limit":"1000",
                "market":condition_id,
                "side":"BUY",
                "offset": offset,
                "filterType":"CASH",
                "filterAmount":5
            }
        )
        trades = response.json()
        filteredTrades = [t for t in trades if 0.2<t['price']<0.9] 
        nonTrivialTrades.extend(filteredTrades)
        offset += 1000
        if offset == 4000: #Offset limit is 3000
            break

    return nonTrivialTrades
def stringToList(string):
    listOf = string.split(',')
    listOf[0] = listOf[0][2:-1]
    listOf[1] = listOf[1][2:-2]
    return listOf
def did_win(row):
    try:
        outcomes = row['outcomes']    
        prices = row['outcomePrices']    
        idx = outcomes.index(row['outcome'])
        return float(prices[idx]) >= 0.85
    except (ValueError, IndexError):
        return False
def get_end_date(m):
    if 'endDate' in m and m['endDate']:
        return m['endDate']
    if m.get('events') and len(m['events']) > 0 and m['events'][0].get('endDate'):
        return m['events'][0]['endDate']
    if m.get('closedTime'):
        return m['closedTime']
    if 'umaEndDate' in m and m['umaEndDate']:
        return m['umaEndDate']
    return KeyError
def get_start_date(m):
    if m.get('startDate'):
        return m['startDate']
    if m.get('events') and len(m['events']) > 0 and m['events'][0].get('startDate'):
        return m['events'][0]['startDate']
    if m.get('createdAt'):
        return m['createdAt']
    if m.get('acceptingOrdersTimestamp'):
        return m['acceptingOrdersTimestamp']
    return KeyError
def timeSinceLastTrade(df):
    df = df.sort_values('timestamp').copy()
    df['prev_timestamp'] = df.groupby(['proxyWallet'])['timestamp'].shift(1)
    df['refTime'] = df['prev_timestamp'].fillna(df['last_trade'])

    df['time_since_last_trade'] = df['timestamp'] - df['refTime']
    return df
def getUserData(u):
    offset = 0
    userTrades=[]
    while True:
        url = "https://data-api.polymarket.com/trades"
        response = requests.get(
            url,
            params={
                "limit":1000,
                "offset":offset,
                "filterType":"CASH",
                "filterAmount":2,
                "user":u,
                "side":"BUY"
            }
        )
        userTrades.extend(response.json())
        if len(userTrades) < offset+1000 or offset == 3000:
            break
        offset += 1000
    if len(userTrades) == 0:
        return
    try:
        uTradesDf = pd.DataFrame(userTrades)[[
            'side','size','price','timestamp','outcome','conditionId']]
    except ValueError:
        print(userTrades)
    except KeyError:
        return 
    uMarkets = list(set(uTradesDf['conditionId'].to_list()))
    offset = 0
    uMarketList = []
    while offset < len(uMarkets):
        time.sleep(0.2) # Give the api some rest
        url = "https://gamma-api.polymarket.com/markets"

        response = requests.get(
            url,
            params={
                "condition_ids":uMarkets[offset:offset+50],
                "closed":"true",
            }
        )
        try:
            for m in response.json():
                try:
                    marketdetails = [m['conditionId'],stringToList(m['outcomes']),stringToList(m['outcomePrices']),get_start_date(m),get_end_date(m)]
                    uMarketList.append(marketdetails)
                except KeyError as e:
                    print(m)
                    print(e)
                    exit()
                    continue
            offset += 50
        except requests.exceptions.JSONDecodeError:
            print(response)
    uMarketDf = pd.DataFrame(uMarketList, columns=['conditionId', 'outcomes', 'outcomePrices', 'startDate', 'endDate'])
    #trade_ids = set(uTradesDf['conditionId'].dropna())
    #market_ids = set(uMarketDf['conditionId'].dropna())

    #print(f"Unique conditionIds missed: {len(trade_ids)-len(market_ids)}")
    if len(uTradesDf) == 0:
        print("no trades")
        exit()
    uTradesDf = uTradesDf.merge(uMarketDf, on='conditionId', how='left')
    uTradesDf = uTradesDf.dropna()
    uTradesDf = uTradesDf[uTradesDf['conditionId']!=CONDITION_ID] # Removes trades from market thats looked at
    uTradesDf = uTradesDf[uTradesDf['timestamp'] < datetime.datetime.fromisoformat(end_date).timestamp()] # Removes trades that are too late / in the future (might need to find a diff cutoff)
    if len(uTradesDf) == 0:                                                                               # And kinda makes the condition filter obselete
        return
    uTradesDf['won'] = uTradesDf.apply(did_win, axis=1).astype(int)
    uTradesDf = uTradesDf.sort_values(by=["timestamp"],ascending=True)

    MainFeatures = {}
    MainFeatures['proxyWallet'] = u
    MainFeatures['avg_price'] = uTradesDf['price'].mean()
    MainFeatures['highest_price_yet'] = uTradesDf['price'].max()
    MainFeatures['lowest_price_yet'] = uTradesDf['price'].min()
    MainFeatures['avg_spent'] = uTradesDf['size'].mean()
    MainFeatures['max_spent'] = uTradesDf['size'].max()
    MainFeatures['nMarkets'] = uTradesDf['conditionId'].nunique()
    MainFeatures['nTrades'] = len(uTradesDf)
    MainFeatures['total_spent'] = uTradesDf['size'].sum()
    MainFeatures['win_rate'] = uTradesDf['won'].sum()/MainFeatures['nTrades']
    MainFeatures['last_trade'] = uTradesDf['timestamp'].iloc[-1]
    if randrange(30) == 7:
        print("peekaboo")
    return MainFeatures

def collectUserDataThreads(userList,threads:int):
    results = []
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {
            executor.submit(getUserData, u): u
            for u in userList
        }
        for future in as_completed(futures):
            result = future.result()
            if result is not None: 
                results.append(result)
    return results
def getPrediction(X_df,model,features,diff=""):
    X_data = xgb.DMatrix(X_df[features].to_numpy())
    prediction = model.predict(X_data)
    decision = (prediction > 0.8).astype(int)
    X_df['prediction'+diff] = decision
    return X_df
def LOOKFORMARKET(markets):
    i = 15
    try:
        while True:
            SELECTEDMARKET = markets[i]
            CONDITION_ID = SELECTEDMARKET['conditionId']
            return SELECTEDMARKET
            search = duckdb.query(f"""SELECT * FROM '{MARKETSTRAINED}' WHERE condition_id = '{CONDITION_ID}' """)
            if len(search) >= 1:
                i += 1
                print("Market skipped")
                continue
            return SELECTEDMARKET
    except IndexError:
        return None
#### BUNCH OF FUNCS YOU CAN IGNORE
##########################################################
MARKETSTRAINED = "x:/PolymarketData/markets.parquet"
markets = getmarket(100)
SELECTEDMARKET = LOOKFORMARKET(markets)
print(SELECTEDMARKET['slug'])
CONDITION_ID = SELECTEDMARKET['conditionId']
end_date = get_end_date(SELECTEDMARKET)
start_date = get_start_date(SELECTEDMARKET)

trades = tradesByMarket(CONDITION_ID)
CATEGORYFEATURES = ['avg_price', 'avg_spent', 'max_spent', 'nMarkets', 'nTrades', 'total_spent', 'win_rate']
XGBOOSTFEATURES = [
            "time_since_start", 
            "time_until_end", 
            "hour_of_day", 
            "day_of_week", 
            "winrate",
            "cum_spent_prior",
            "cum_max_spent",
            "highest_price_yet",
            "lowest_price_yet",
            "avg_price",
            "time_since_last_trade",
            "usd_amount",
            "token_amount",
            "price",
            "direction"
        ]
feature_cols = [
        "time_since_start", 
        "time_until_end", 
        "hour_of_day", 
        "day_of_week", 
        "winrate",
        "cum_spent_prior",
        "cum_max_spent",
        "highest_price_yet",
        "lowest_price_yet",
        "avg_price",
        "time_since_last_trade",
        "role",
        "usd_amount",
        "token_amount",
        "price",
        "direction"
    ]

users = list(set([t['proxyWallet'] for t in trades]))
if len(users) == 0:
    exit()
print(f"There are {len(users)} Users in {len(trades)} Trades")
all_features = collectUserDataThreads(users,9)

#################################################
####### HDBSCAN CATEGORIES + DATAFRAME MANIPULATIONS AND STUFF TO GET NECESSARY XGBOOST FEATURES
MainFeaturesDf = pd.DataFrame(all_features)
labels,strength = hdbscan.approximate_predict(CATMODEL, SCALER.transform(MainFeaturesDf[CATEGORYFEATURES]))
MainFeaturesDf['Group'] = labels
MainFeaturesDf['GroupStrength'] = strength
TradesDf = pd.DataFrame(trades)
MainFeaturesDf = MainFeaturesDf.merge(TradesDf[['proxyWallet','size','price','timestamp','side','outcome']],on="proxyWallet",how="left")
MainFeaturesDf.dropna()

market_start = datetime.datetime.fromisoformat(start_date).timestamp()
market_end = datetime.datetime.fromisoformat(end_date).timestamp()
MainFeaturesDf['time_since_start'] = MainFeaturesDf['timestamp'] - market_start
MainFeaturesDf['time_until_end'] = market_end - MainFeaturesDf['timestamp']

MainFeaturesDf = timeSinceLastTrade(MainFeaturesDf)
MainFeaturesDf['token_amount'] = MainFeaturesDf['size']*MainFeaturesDf['price']
MainFeaturesDf['role'] = 1 #Assume everyone is taker since it doesn't show in trades api
MainFeaturesDf['direction'] = (MainFeaturesDf['side'] == "BUY").astype(int)
MainFeaturesDf = MainFeaturesDf.rename(columns={"max_spent":"cum_max_spent","total_spent":"cum_spent_prior","win_rate":"winrate","size":"usd_amount"})
MainFeaturesDf['timestamp'] = pd.to_datetime(MainFeaturesDf['timestamp'], unit='s')  
MainFeaturesDf['hour_of_day'] = MainFeaturesDf['timestamp'].dt.hour
MainFeaturesDf['day_of_week'] = MainFeaturesDf['timestamp'].dt.day_of_week
FEATUREDF = MainFeaturesDf[feature_cols + ['Group','outcome']]
#######################################################################################
########### FIND MARKET WINNER (FOR TESTING ONLY) + MAKE PREDICTION
marketResult = stringToList(SELECTEDMARKET.get('outcomePrices'))
winningindex = int(float(marketResult[1]) > 0.9)
winner = stringToList(SELECTEDMARKET.get('outcomes'))[winningindex]

NoisyUsers = FEATUREDF[FEATUREDF['Group']==-1]
Users0 = FEATUREDF[FEATUREDF['Group']== 0]
Users1 = FEATUREDF[FEATUREDF['Group']== 1]
Users2 = FEATUREDF[FEATUREDF['Group']== 2]
if len(Users0) != 0:
    Users0Model = joblib.load("xgboostedMFUsers0.joblib")
    Users0 = getPrediction(Users0,Users0Model,feature_cols)
if len(Users1) != 0:
    Users1Model = joblib.load("xgboostedMFUsers1.joblib")
    Users1 = getPrediction(Users1,Users1Model,feature_cols)
if len(Users2) != 0:
    Users2Model = joblib.load("xgboostedMFUsers2.joblib")
    Users2 = getPrediction(Users2,Users2Model,feature_cols)
if len(NoisyUsers) != 0:
    NoisyUsersModelNEW = joblib.load("xgboostedMFNewNoisy.joblib")
    NoisyUsersModelOLD = joblib.load("xgboostedMFNoisyUsers.joblib")
    NoisyUsers = getPrediction(NoisyUsers,NoisyUsersModelNEW,XGBOOSTFEATURES)
    NoisyUsers = getPrediction(NoisyUsers,NoisyUsersModelOLD,feature_cols,"old")

    
predictedDfs = pd.concat([NoisyUsers,Users0,Users1,Users2])
del NoisyUsers,Users0,Users1,Users2 #cuz concat makes hard copy per pandas doc
predictedDfs['correctPredict'] = (predictedDfs['prediction'] == 1) == (predictedDfs['outcome'] == winner)
print(predictedDfs['correctPredict'].value_counts())
print(predictedDfs.groupby(['outcome'])['correctPredict'].value_counts())

predictedDfs['correctPredictOLD'] = (predictedDfs['predictionold'] == 1) == (predictedDfs['outcome'] == winner)
print(predictedDfs['correctPredictOLD'].value_counts())
print(predictedDfs.groupby(['outcome'])['correctPredictOLD'].value_counts())