import pandas as pd


def CleanData(df_trades,df_markets,df_users):

    df = df_trades.merge(df_markets, on='conditionId', how='left').merge(df_users, on='wallet', how='left')
    df['won'] = (df['outcome'] == df['market_outcome']).astype(int)
    df['timestamp'] = df['timestamp'].astype(int)
    df['endDate'] = pd.to_datetime(df['endDate'], format='ISO8601') ## endDate -> datetime
    df['endDate'] = df['endDate'].apply(lambda x: x.timestamp() if pd.notna(x) else None )  ## datetime -> timestamp
    df = df.dropna(subset=['endDate']) #drop if endDate is Na (about 1% of them)
    df['timeFromEnd'] = (df['endDate']-df['timestamp'])
    df = df[df['timeFromEnd'] > 60] #Just cleaning up trades made after market end (lost about 80k trades)
    df = df[df['size'] >= 2] #Removing trades that are potentially test trades and bots, did a few tests and 2 seemed like the best cutoff (lost about 20k trades)
    df['sizeToVolumePct'] = (df['size']/df['volume']) #Add for a trade the percent of its size relative to the market its in
    df['is_deleted'] = df['account_age'].isna().astype(int) #Deleted accounts could be sus so maybe add a tag for if deleted
    df['account_age'] = df['account_age'].fillna(df['account_age'].median()) #Make deleted accounts have median age to not fuck around with data and still keep them
    df['account_age_at_trade'] = (df['timestamp'] - df['account_age']) #time between account creation and time trade is done (hypothesis is new accounts are more likely to be sus)

    df = count_trades_in_window(df) #Number of trades between [t0-t,t] where t is time of trade

    df['hour_of_day'] = pd.to_datetime(df['timestamp'], unit='s').dt.hour

    market_avg_size = df.groupby('conditionId')['size'].mean().rename('market_avg_size')
    df = df.merge(market_avg_size, on='conditionId')

    df = df.sort_values(['conditionId', 'timestamp'])
    df['market_avg_size_so_far'] = df.groupby('conditionId')['size'].transform(
        lambda x: x.expanding().mean().shift(1)  # shift(1) excludes current trade
    )

    trade_count_per_market = df.groupby(['wallet', 'conditionId'])['won'].count().rename('tradeByUserPerMarket')
    df = df.merge(trade_count_per_market, on=['wallet', 'conditionId'])


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