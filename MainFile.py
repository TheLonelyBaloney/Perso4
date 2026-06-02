from PrintMachine import *
from GetAPIStuff import *

def doStuff(): 

    events = getEventsStuff()
    event = events[0]

    event_markets = event['markets']

    
    for market in event_markets:
        print_market(market)
  
        conditionId = market['conditionId']
        getTradesByMarket(conditionId)

    return



if __name__ == "__main__":
    doStuff()

    print("Done!")