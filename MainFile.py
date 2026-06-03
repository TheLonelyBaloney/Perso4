from PrintMachine import *
from GetAPIStuff import *

global AVERAGEMULTTHRESHOLD
AVERAGEMULTTHRESHOLD = 3

def doStuff(): 

    events = getEventsStuff()
    event = events[0]

    event_markets = event['markets']

    
    for market in event_markets:
        print(market)
        print_market(market)
        
        outcome = market['outcomes'][market['outcomePrices'].index("1")]
        volume = market['volume']
        

        conditionId = market['conditionId']
        trades = getTradesByMarket(conditionId)
        if len(trades) == 0: #well duhhh
            break

        tradeSizeAverage = sum([float(t['size']) for t in trades])/len(trades)
        
        tradesDataSet = []
        for trade in trades:

            dataPoint = {}
            dataPoint['wallet'] = trade['proxyWallet']
            dataPoint['size'] = trade['size']
            dataPoint['price'] = trade['price']
            dataPoint['timestamp'] = trade['timestamp']
            dataPoint['m_volume'] = volume
            dataPoint['success'] = trade['outcomeIndex'] #check if outcomeIndex means if he won or not
            # 
            # If want to pull Username and check profile and shi just go 'name' and 'pseudoname'
            tradesDataSet.append(dataPoint)

            if trade['size'] > AVERAGEMULTTHRESHOLD*tradeSizeAverage:
                print_trade(trade)
                print(dataPoint['success'])
        
        print(tradeSizeAverage)

    return



if __name__ == "__main__":
    doStuff()

    print("Done!")