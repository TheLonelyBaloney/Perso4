import requests

global LOWERBOUNDPRICE
LOWERBOUNDPRICE = 0.1
global HIGHERBOUNDPRICE
HIGHERBOUNDPRICE = 0.9

def getEventsStuff():

    url = "https://gamma-api.polymarket.com/events"

    response = requests.get(
        url,
        params={
            "limit":"100",
            "offset":"200",
            "archived":"True",
            "volume_min":"400000",
            "start_date_min":"1748822400",
            "closed":"true",
            "exclude_tag_id":21 ###can add more (21: crypto)
        }
    )
    events = response.json()

    return events

def getTradesByMarket(condition_id):

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
                "offset": offset
            }
        )
        trades = response.json()
        filteredTrades = [t for t in trades if LOWERBOUNDPRICE<t['price']<HIGHERBOUNDPRICE] #Lets get rid of those pesky 0.01 priced trades grrr
        nonTrivialTrades.extend(filteredTrades)
        offset += 1000
        if offset == 4000: #Offset limit is 3000
            break

    return nonTrivialTrades

def getUserByProxyWallet(wallet):
    url = "https://gamma-api.polymarket.com/public-profile"

    response = requests.get(
        url, 
        params={
            "address":wallet
    })

    user = response.json()

    return user

if __name__ == "__main__":
    print("wrong place buddy")