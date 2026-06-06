import time
from PrintMachine import *
from GetAPIStuff import *
from db import *
import pandas as pd
import numpy as np
import scipy
import sklearn

def doData(): 

    events = getEventsStuff()
    eventcount = 5
    for event in events[5:]:

        print(eventcount)
        eventcount += 1

        event_markets = event['markets']

        
        for market in event_markets:

            if float(market['volume']) < 50000:
                continue

            conditionId = market['conditionId']
            trades = getTradesByMarket(conditionId)

            if len(trades) == 0: #well duhhh
                continue
            if not insertMarketToDB(conn,market):
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
                user = getUserByProxyWallet(proxyWallet)
                if 'error' in user.keys():
                    #insertUserToDB(conn,{"createdAt":"NULL","proxyWallet":0}) #deleted account? (JUST NEED TO DO ONCE, ALL TRADES WITH NO WALLET COUNT FOR HIM)
                    continue
                insertUserToDB(conn,user)
                #####
    return







if __name__ == "__main__":
    doData()


    print("Done!")