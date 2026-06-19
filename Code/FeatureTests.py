import pandas as pd
from sklearn.model_selection import cross_val_predict

from modelsMachine import *

from scipy import stats


def test_feature_importance(model, X, y, cv, feature_name):
    """
    Compare model accuracy with vs without a feature
    using a paired t-test across CV folds
    """
    # scores with feature
    scores_with = cross_val_score(model, X, y, cv=cv, scoring='accuracy', n_jobs=-1)
    
    # scores without feature
    X_without = X.drop(columns=[feature_name])
    scores_without = cross_val_score(model, X_without, y, cv=cv, scoring='accuracy', n_jobs=-1)
    
    # paired t-test
    t_stat, p_value = stats.ttest_rel(scores_with, scores_without)
    
    print(f"\nFeature: {feature_name}")
    print(f"Mean with:    {scores_with.mean():.4f}")
    print(f"Mean without: {scores_without.mean():.4f}")
    print(f"Difference:   {scores_with.mean() - scores_without.mean():.4f}")
    print(f"T-statistic:  {t_stat:.4f}")
    print(f"P-value:      {p_value:.4f}")


def expectedReturn(df, model, epsilon=0.02):
    X = df[['account_age_at_trade', 'timeFromEnd', 'volume', 'price', 'user_trade_count', 'window_trade_count','market_avg_size_so_far','hour_of_day']]
    y = df['won']
    
    df['predicted_won'] = cross_val_predict(model, X, y, cv=5)
    df['predicted_prob'] = cross_val_predict(model, X, y, cv=5, method='predict_proba')[:, 1]
    df['price_bucket'] = pd.cut(df['price'], 
                                             bins=[0, 0.2, 0.3, 0.4, 0.5, 
                                                   0.6, 0.7, 0.8, 0.9])
    
    predicted_wins = df[df['predicted_won'] == 1].copy()
    
    predicted_wins['price_bucket'] = pd.cut(predicted_wins['price'], 
                                             bins=[0, 0.2, 0.3, 0.4, 0.5, 
                                                   0.6, 0.7, 0.8, 0.9])
    
    precision_by_price = predicted_wins.groupby('price_bucket').agg(
        actual_win_rate = ('won', 'mean'),
        count           = ('won', 'count')
    )
    
    precision_by_price['avg_price'] = [0.1, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]
    precision_by_price['expected_return'] = (precision_by_price['actual_win_rate'] 
                                            - precision_by_price['avg_price'] 
                                            - epsilon)

    comparison = pd.DataFrame({
    'market_win_rate': df.groupby('price_bucket')['won'].mean(),
    'model_win_rate': precision_by_price['actual_win_rate'],
    'model_count': precision_by_price['count'],
    'total_count': df.groupby('price_bucket')['won'].count(),
    'expected_return':(precision_by_price['actual_win_rate'] - precision_by_price['avg_price'] - epsilon)
    })

    comparison['selection_rate'] = comparison['model_count'] / comparison['total_count']
    print(comparison)

    return precision_by_price

def backtestModel(df, model, features, epsilon=0.05):
    X = df[features]
    y = df['won']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model.fit(X_train, y_train)
    
    # predict on unseen 20%
    test_df = df.loc[X_test.index].copy() # copy from df the test data by index
    test_df['predicted_won'] = model.predict(X_test) # put result into a column
    
    # make new df where we only take trades we took (ie.) if we predicted it was right/allign we the market outcome
    bought_trades = test_df[test_df['predicted_won'] == 1].copy()
    
    # if the trade we bought won (row['won']==1) than we gain 1-price -platformcut, according to polymarket doc fee is = marketrate*p*q and market rate is about 0.05 for all markets
    bought_trades['return'] = bought_trades.apply(
        lambda row: (1 - row['price'] - (epsilon * (1-row['price']) * row['price'])) if row['won'] == 1 # the cost of a trade is already taken into account with -'price'
                    else (-row['price'] - (epsilon * (1-row['price']) * row['price'])), axis=1
    )
    
    # summary
    total_trades    = len(bought_trades)
    total_invested  = bought_trades['price'].sum()
    total_return    = bought_trades['return'].sum()
    win_rate        = bought_trades['won'].mean()
    rate            = total_return / total_invested * 100
    
    print(f"At MarketFeeRate:{epsilon*100}%")
    print(f"Trades taken:    {total_trades}")
    print(f"Win rate:        {win_rate:.3f}")
    print(f"Total invested:  ${total_invested:,.2f}")
    print(f"Total return:    ${total_return:,.2f}")
    print(f"ROI:             {rate:.2f}%")
    
  
    bought_trades['price_bucket'] = pd.cut(bought_trades['price'], bins=[0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]) #cuts the df into bins by 'price'
    
    bucket_summary = bought_trades.groupby('price_bucket').agg(
        count        = ('return', 'count'),
        win_rate     = ('won', 'mean'),
        total_return = ('return', 'sum'),
        avg_return   = ('return', 'mean')
    )
    print(bucket_summary)
    
    return bought_trades

if __name__ == "__main__":
    print("your p < 0.05")