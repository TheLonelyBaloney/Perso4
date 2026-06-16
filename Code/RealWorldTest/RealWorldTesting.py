from datetime import datetime
import json
import os
import sys

import joblib
import pandas as pd
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from CleanData import CleanData, count_trades_in_window
from GettingTrainingData.PrintMachine import print_market
from GettingTrainingData.db import startup
from GettingTrainingData.GetAPIStuff import APIgetTradesByMarket

def testOnNewMarkets(model, epsilon=0.05):
    conn = startup()
    FEATURES = ['account_age_at_trade', 'timeFromEnd', 'size', 'volume', 'price', 'user_trade_count', 'window_trade_count','market_avg_size_so_far','hour_of_day']
    # fetch new closed markets
    offset = 100
    while offset < 4000:
        response = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={
                "limit": 100,
                "offset":offset,
                "closed": "true",
                "volume_num_min": "600000",
                "start_date_min": 1765659232, #diff date from db markets

            }
        )
        markets = response.json()
        for market in markets:
            
            conditionId = market.get('conditionId')
            if "1" not in json.loads(market['outcomePrices']): #ended in 50/50
                continue
            
            # skip markets already in training data
            cur = conn.cursor()
            cur.execute("SELECT conditionId FROM markets WHERE conditionId = ?", (conditionId,))
            if cur.fetchone():
                continue  # already seen this market

            trades = APIgetTradesByMarket(conditionId)
            if not trades or len(trades) < 100:
                continue

            outcome = json.loads(market['outcomes'])[json.loads(market['outcomePrices']).index("1")]
            market_info = {
                "conditionId" : conditionId,
                "volume": float(market.get('volume')),
                "market_outcome": outcome,
                "endDate": market.get('endDate')
            }
            tradeInfoKeys = ['proxyWallet','timestamp','price','size','outcome']
            trade_df = pd.DataFrame(trades)[tradeInfoKeys]
            trade_df['conditionId'] = conditionId
            trade_df = trade_df.rename(columns={'proxyWallet': 'wallet'})

            walletsList = trade_df['wallet'].unique().tolist()

            wallets = []
            seenwallets = set()
            for wallet in walletsList:
                if wallet in seenwallets:
                    print('seen')
                    continue
                url = "https://gamma-api.polymarket.com/public-profile"
                response = requests.get(
                    url, 
                    params={
                        "address":wallet
                })

                user = response.json()
                if 'error' in user.keys():
                    continue
                if not user.get('createdAt'):
                    continue
                wallets.append({
                    "wallet":user.get("proxyWallet"),
                    "account_age": datetime.fromisoformat(user.get('createdAt').replace("Z", "+00:00")).timestamp()
                })
                seenwallets.add(wallet)
                

            market_df = pd.DataFrame([market_info])
            user_df = pd.DataFrame(wallets)

            df = CleanData(trade_df,market_df,user_df)

            X = df[FEATURES]
            y = df['won']

            test_df = df.loc[X.index].copy() # copy from df the test data by index
            test_df['predicted_won'] = model.predict(X) # put result into a column
            test_df['confidence'] = model.predict_proba(X)[:, 1]

            # make new df where we only take trades we took (ie.) if we predicted it was right/allign we the market outcome and only with good confidence
            bought_trades = test_df[(test_df['predicted_won'] == 1) & (test_df['confidence'] > 0.80)].copy()
            
            # if the trade we bought won (row['won']==1) than we gain 1-price -platformcut, according to polymarket doc fee is = marketrate*p*q and market rate is about 0.05 for all markets
            bought_trades['return'] = bought_trades.apply(
                lambda row: (1 - row['price'] - (epsilon * (1-row['price']) * row['price'])) if row['won'] == 1 # the cost of a trade is already taken into account with -'price'
                            else (-row['price'] - (epsilon * (1-row['price']) * row['price'])), axis=1
            )

            # summary
            min_confidence = bought_trades['confidence'].min()
            total_trades    = len(bought_trades)
            total_invested  = bought_trades['price'].sum()
            total_return    = bought_trades['return'].sum()
            win_rate        = bought_trades['won'].mean()
            rate            = total_return / total_invested * 100
            print("-"*20)
            print(f"At MarketFeeRate:{epsilon*100}%")
            print(f"Trades taken:    {total_trades}")
            print(f"Win rate:        {win_rate:.3f}")
            print(f"Total invested:  ${total_invested:,.2f}")
            print(f"Total return:    ${total_return:,.2f}")
            print(f"ROI:             {rate:.2f}%")
            print(f"Min confidence:  {min_confidence}")

            bought_trades['price_bucket'] = pd.cut(bought_trades['price'], bins=[0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]) #cuts the df into bins by 'price'
        
            bucket_summary = bought_trades.groupby('price_bucket').agg(
                count        = ('return', 'count'),
                win_rate     = ('won', 'mean'),
                total_return = ('return', 'sum'),
                avg_return   = ('return', 'mean')
            )
            print(bucket_summary)
        offset += 100
        
    return 







if __name__ == "__main__":
    

    print('yo')