from PrintMachine import *
from GetAPIStuff import *
from db import *

global AVERAGEMULTTHRESHOLD
AVERAGEMULTTHRESHOLD = 4

def doStuff(): 

    events = getEventsStuff()

    for event in events:

        event_markets = event['markets']

        
        for market in event_markets:
            if market['volume'] < 10000:
                continue
            print_market(market)

            conditionId = market['conditionId']
            trades = getTradesByMarket(conditionId)

            if len(trades) == 0: #well duhhh
                break
            
            for trade in trades:
                insertTradeToDB(conn,trade)
                
    return



if __name__ == "__main__":
    doStuff()

    print("Done!")