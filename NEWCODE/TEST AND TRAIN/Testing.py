import joblib
import duckdb
from matplotlib import pyplot as plt
import pandas as pd
import xgboost as xgb
from sklearn import metrics
from sklearn.metrics import accuracy_score, classification_report
NoisyTestFile = 'x:/PolymarketData/ByCats/NoisyUsers/preprocessedNoisyUser_train4.parquet'
Users0TestFile = 'x:/PolymarketData/ByCats/Users0/preprocessedUsers0_train4.parquet'
Users1TestFile = 'x:/PolymarketData/ByCats/Users1/preprocessedUsers1_train4.parquet'
Users2TestFile = 'x:/PolymarketData/ByCats/Users2/preprocessedUsers2_train4.parquet'

def testingOnSubset(Testfile, model):
    
    feature_cols = [
        "time_since_start", 
        "time_until_end", 
        "hour_of_day", 
        "day_of_week", 
        "winrate",
        "cum_spent_prior",
        "cum_max_spent",
        "highest_price_yet",
        "lowest_price_yet",
        "avg_price",
        "time_since_last_trade",
        "role",
        "usd_amount",
        "token_amount",
        "price",
        "direction"
    ]
    testdf = duckdb.query(f"SELECT * FROM '{Testfile}' LIMIT 2_000_000").to_df()
    print("GOT DF")
    print(testdf.head())
    X_chunk = testdf[feature_cols].astype('float64')
    y_chunk = testdf['won']

    y_baseline = (X_chunk['price'] >= 0.5).astype(int)
    print(f"Baseline accuracy: {accuracy_score(y_chunk, y_baseline):.3f}")
    print("="*20)
    
    testdf = xgb.DMatrix(X_chunk.to_numpy())
    preds = model.predict(testdf)
    pred_binary = (preds >= 0.5).astype(int)
    accuracy = metrics.accuracy_score(y_chunk, pred_binary)
    auc = metrics.roc_auc_score(y_chunk, preds)  
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"AUC:       {auc:.4f}")
    print(classification_report(y_chunk, pred_binary))
    
    importance = model.get_score(importance_type='weight')
    named_importance = {
    feature_cols[int(k[1:])]: v 
    for k, v in importance.items()
    }
    for feature, score in sorted(named_importance.items(), key=lambda x: -x[1]):
        print(f"{feature}: {score}")
    
model = joblib.load("xgboostedMFUsers2.joblib")
testingOnSubset(Users2TestFile,model)