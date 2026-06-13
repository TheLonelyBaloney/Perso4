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
    
    print(precision_by_price[['actual_win_rate', 'avg_price', 'count', 'expected_return']])
    return precision_by_price

if __name__ == "__main__":
    print("your p < 0.05")