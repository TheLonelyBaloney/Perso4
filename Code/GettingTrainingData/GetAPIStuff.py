from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import requests

from GettingTrainingData.db import insertUserToDB

global LOWERBOUNDPRICE
LOWERBOUNDPRICE = 0.1
global HIGHERBOUNDPRICE
HIGHERBOUNDPRICE = 0.9

def APIgetEventsStuff(limit=100,offset=0,start_date_min=1755659232):

    url = "https://gamma-api.polymarket.com/events"

    response = requests.get(
        url,
        params={
            "limit":f"{limit}",
            "offset":f"{offset}",
            "archived":"True",
            "volume_min":"1000000",
            "start_date_min":f"{start_date_min}",
            "closed":"true",
            "exclude_tag_id":21 ###can add more (21: crypto)
        }
    )
    events = response.json()

    return events

def APIgetTradesByMarket(condition_id):

    nonTrivialTrades = []
    offset = 0
    while len(nonTrivialTrades) < 1000: #At least 1000 non-trivial trades, if too much trouble can skip and just do 4 batches of 1000 with offset to 3000
        url = "https://data-api.polymarket.com/trades"
        response = requests.get(
            url,
            params = {
                "limit":"1000",
                "market":condition_id,
                "side":"BUY",
                "offset": offset,
                "filterType":"CASH",
                "filterAmount":2
            }
        )
        trades = response.json()
        filteredTrades = [t for t in trades if LOWERBOUNDPRICE<t['price']<HIGHERBOUNDPRICE] #Lets get rid of those pesky 0.01 priced trades grrr
        nonTrivialTrades.extend(filteredTrades)
        offset += 1000
        if offset == 4000: #Offset limit is 3000
            break

    return nonTrivialTrades

def APIgetUserByProxyWallet(wallet):
    url = "https://gamma-api.polymarket.com/public-profile"

    response = requests.get(
        url, 
        params={
            "address":wallet
    })

    user = response.json()

    return user

def APIgetMarkets(offset=0):
    url = "https://gamma-api.polymarket.com/markets"

    response = requests.get(
        url,
        params={
            "limit":100,
            "offset":offset,
            "volume_num_min":300000,
            "start_date_min":1755659232,
            "closed":"true"
        }
    )

    markets = response.json()
    return markets

def APIgetUsersTrades(user):

    wallet = user['proxyWallet']
    nTrades = 0
    offset = 0
    nWins = 0
    totalTradeSize = 0
    totalPrice = 0
    maxTradeSize = 0
    while True:
        url = "https://data-api.polymarket.com/trades?&takerOnly=true"
        response = requests.get(
            url,
            params={
                "limit":1000,
                "offset":offset,
                "filterType":"CASH",
                "filterAmount":2,
                "user":wallet,
                "side":"BUY"
            }
        )
        trades = response.json()
        nTrades += len(trades)
        for trade in trades:
            nWins += trade['outcomeIndex']
            totalTradeSize += trade['size']
            totalPrice += trade['price']
            if trade['size'] > maxTradeSize:
                maxTradeSize = trade['size']

        if len(trades)< 1000 or offset == 3000:
            break
        offset += 1000
    user['nTrades'] = nTrades
    user['nWins'] = nWins
    user['totalSize'] = totalTradeSize
    user['totalPrice'] = totalPrice
    user['maxSize'] = maxTradeSize

    ####### getnMarkets from api
    url = "https://data-api.polymarket.com/traded"

    response = requests.get(
        url,
        params={
            "user":wallet
    })
    traded = response.json()
    user['nMarkets'] = traded['traded']
    return user

def collectAllUsersTrades(walletsList, conn):
    results = []
    
    # fetch all users in parallel 9 (10 was too much) workers check if pc works or burns guh
    with ThreadPoolExecutor(max_workers=9) as executor:
        futures = {
            executor.submit(APIgetUsersTrades, w): w
            for w in walletsList
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    if conn == None:
        return results
    
    for user in results:
        insertUserToDB(conn, user)

if __name__ == "__main__":
    #print(APIgetMarkets()[0]) # 0xffdbbf2c3b9aa808abbcb35beb2b20a93572570aa5dd1bd1b630cade2f809f26
    #print(APIgetTradesByMarket(0xffdbbf2c3b9aa808abbcb35beb2b20a93572570aa5dd1bd1b630cade2f809f26)[0]) # 0xfde390670e0dd39f2a780bb569b882feaee8b73d
    #print(APIgetUserByProxyWallet('0xfde390670e0dd39f2a780bb569b882feaee8b73d'))
    print("wrong place buddy")