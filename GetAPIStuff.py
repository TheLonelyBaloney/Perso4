import requests

def getEventsStuff():

    url = "https://gamma-api.polymarket.com/events"

    response = requests.get(
        url,
        params={
            "limit":"100",
            "archived":"True",
            "volume_min":"40000",
            "start_date_min":"1748822400",
            "closed":"true"
        }
    )
    events = response.json()

    return events

def getTradesByMarket(condition_id):
    print(condition_id)
    url = "https://data-api.polymarket.com/trades"
    response = requests.get(
        url,
        params = {
            "limit":"1000",
            "market":condition_id,
            "side":"BUY"
        }
    )
    print(response.text)
    trades = response.json()
    print(trades)

    return 


if __name__ == "__main__":
    print("wrong place buddy")