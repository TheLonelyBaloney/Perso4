import datetime

import joblib
import pandas as pd
import requests

CATMODEL = joblib.load("hdbscan_model.pkl")
SCALER = joblib.load("scaler.pkl")

def getmarket(n:int):
    time = datetime.datetime.fromtimestamp(1773973069).isoformat()
    url = "https://gamma-api.polymarket.com/markets"
    response = requests.get(
        url,
        params={
            "limit":n,
            "volume_num_min":300000,
            "start_date_min":f'{time+'Z'}',
            "closed":"true"
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
        filteredTrades = [t for t in trades if 0.1<t['price']<0.9] 
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
        outcomes = list(row['outcomes'])       # works for list OR ndarray
        prices = list(row['outcomePrices'])    # same safety net
        idx = outcomes.index(row['outcome'])
        return prices[idx] == "1"
    except (ValueError, IndexError, TypeError):
        return False
    
##########################################################
markets = getmarket(100)
SELECTEDMARKET = markets[5]
print(SELECTEDMARKET)
condition_id = SELECTEDMARKET['conditionId']
end_date = SELECTEDMARKET['endDate']

trades = tradesByMarket(condition_id)
CATEGORYFEATURES = ['avg_price', 'avg_spent', 'max_spent', 'nMarkets', 'nTrades', 'total_spent', 'win_rate']
users = list(set([t['proxyWallet'] for t in trades]))
all_features = []
for u in users[:1]:
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

    uTradesDf = pd.DataFrame(userTrades)[[
        'side','size','price','timestamp','outcome','conditionId']]
    uMarkets = list(set(uTradesDf['conditionId'].to_list()))

    offset = 0
    uMarketList = []
    while offset < len(uMarkets):
        url = "https://gamma-api.polymarket.com/markets"

        response = requests.get(
            url,
            params={
                "condition_ids":uMarkets[offset:offset+50],
                "end_date_max": end_date
            }
        ).json()
        for m in response:
            try:
                uMarketList.append([m['conditionId'],stringToList(m['outcomes']),stringToList(m['outcomePrices']),m['startDate'],m['endDate']])
            except KeyError:
                continue
        offset += 50
    uMarketDf = pd.DataFrame(uMarketList, columns=['conditionId', 'outcomes', 'outcomePrices', 'startDate', 'endDate'])
    print(uMarketDf.head())
    uTradesDf = uTradesDf.merge(uMarketDf, on='conditionId', how='left')
    uTradesDf['won'] = uTradesDf.apply(did_win, axis=1).astype(int)
    uTradesDf = uTradesDf.sort_values(by=["timestamp"],ascending=True)
    uTradesDf = uTradesDf.dropna()
    print(uTradesDf.head())
    exit()


    CatFeatures = {}
    CatFeatures['user'] = u
    CatFeatures['avg_price'] = uTradesDf['price'].mean()
    CatFeatures['avg_spent'] = uTradesDf['size'].mean()
    CatFeatures['max_spent'] = uTradesDf['size'].max()
    CatFeatures['nMarkets'] = uTradesDf['conditionId'].nunique()
    CatFeatures['nTrades'] = uTradesDf['side'].count()
    CatFeatures['total_spent'] = uTradesDf['size'].sum()
    CatFeatures['win_rate'] = uTradesDf['won'].sum()/CatFeatures['nTrades']
    all_features.append(CatFeatures)

CatfeaturesDf = pd.DataFrame(all_features)