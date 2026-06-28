import pandas as pd


def CleanData(df_trades,df_markets,df_users):

    df = df_trades.merge(df_markets, on='conditionId', how='left').merge(df_users, on='wallet', how='left')

    df['won'] = (df['outcome'] == df['market_outcome']).astype(int)

    df['timestamp'] = df['timestamp'].astype(int)

    df['endDate'] = pd.to_datetime(df['endDate'], format='ISO8601') ## endDate -> datetime
    df['endDate'] = df['endDate'].apply(lambda x: x.timestamp() if pd.notna(x) else None )  ## datetime -> timestamp
    df = df.dropna(subset=['endDate']) #drop if endDate is Na (about 1% of them)
   
    df['startDate'] = pd.to_datetime(df['startDate'], format='ISO8601') ## endDate -> datetime
    df['startDate'] = df['startDate'].apply(lambda x: x.timestamp() if pd.notna(x) else None )  ## datetime -> timestamp
    df = df.dropna(subset=['startDate']) 

    df['updatedAt'] = pd.to_datetime(df['updatedAt'], format='ISO8601') ## endDate -> datetime
    df['updatedAt'] = df['updatedAt'].apply(lambda x: x.timestamp() if pd.notna(x) else None )  ## datetime -> timestamp
    df = df.dropna(subset=['updatedAt']) 

    df['marketCreate'] = pd.to_datetime(df['marketCreate'], format='ISO8601') ## endDate -> datetime
    df['marketCreate'] = df['marketCreate'].apply(lambda x: x.timestamp() if pd.notna(x) else None )  ## datetime -> timestamp
    df = df.dropna(subset=['marketCreate']) 

    df['createdAt'] = pd.to_datetime(df['createdAt'], format='ISO8601') ## endDate -> datetime
    df['createdAt'] = df['createdAt'].apply(lambda x: x.timestamp() if pd.notna(x) else None )  ## datetime -> timestamp
    df = df.dropna(subset=['createdAt']) 

    df['startToLastUpdate'] = (df['updatedAt'] - df['startDate'])

    df['createdToStart'] = (df['startDate'] - df['marketCreate'])

    df['tradeTimeFromEnd'] = (df['endDate']-df['timestamp'])
    df = df[df['tradeTimeFromEnd'] > 30] #Just cleaning up trades made after market end (lost about 80k trades)

    df['account_age_at_trade'] = (df['timestamp'] - df['createdAt']) #time between account creation and time trade is done (hypothesis is new accounts are more likely to be sus)

    df = count_trades_in_window(df) #Number of trades between [t0-t,t] where t is time of trade

    df['hour_of_day'] = pd.to_datetime(df['timestamp'], unit='s').dt.hour

    df = df.sort_values(['conditionId', 'timestamp'])
    df['market_avg_size_so_far'] = df.groupby('conditionId')['size'].transform(
        lambda x: x.expanding().mean().shift(1)  # shift(1) excludes current trade
    )

    trade_count_per_market = df.groupby(['wallet', 'conditionId'])['won'].count().rename('tradeByUserPerMarket')
    df = df.merge(trade_count_per_market, on=['wallet', 'conditionId'])

    df['size/vol'] = (df['size']/df['volume'])
    df['nMark/nTrades'] =(df['nMarkets']/df['nTrades'])
    df['nWins/nTrades'] = (df['nWins']/df['nTrades'])
    df['avgPrice'] = (df['totalPrice']/df['nTrades'])
    df['avgSize'] = (df['totalSize']/df['nTrades'])


    return df

def count_trades_in_window(df, t=3600):
    df = df.sort_values('timestamp').copy()
    df['window_trade_count'] = 0
    
    for id, group in df.groupby('conditionId'):
        timestamps = group['timestamp'].values
        counts = [(timestamps >= ts - t).sum() 
                  for ts in timestamps]
        df.loc[group.index, 'window_trade_count'] = counts
    
    return df


if __name__ == "__main__":
    print("get ouT!!")