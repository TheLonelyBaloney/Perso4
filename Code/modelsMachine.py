
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from FeatureTests import backtestModel, expectedReturn, test_feature_importance

def BaseLineME(df):

    y_true = df['won']
    y_baseline = (df['price'] > 0.5).astype(int)

    print(f"Baseline accuracy: {accuracy_score(y_true, y_baseline):.3f}")
    print(classification_report(y_true, y_baseline))


def LogisticRegressionME(df,price): #with or without price

    if price:
        X = df[['account_age_at_trade', 'timeFromEnd', 'sizeToVolumePct','price','user_trade_count','window_trade_count','hour_of_day']] 
    else:
        X = df[['account_age_at_trade', 'timeFromEnd', 'sizeToVolumePct','user_trade_count','window_trade_count','hour_of_day']] 
    Y = df.loc[X.index, 'won']

    X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42) #standard is 42 for the weights in comment

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train) # (xi-x_bar)/var since some feature values reach the 100k's and some are [0,1]
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000) 
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    print(f"Train accuracy: {model.score(X_train, y_train):.3f}")
    print(f"Test accuracy:  {model.score(X_test, y_test):.3f}")
    print(classification_report(y_test, y_pred))  

    weights = pd.Series(model.coef_[0], index=X.columns)
    print(weights.sort_values(ascending=False))

    return 


def RandomForestME(df,price):
    df_sample = df.sample(100000, random_state=42)
    
    if price:
        X = df_sample[['account_age_at_trade', 'timeFromEnd', 'size', 'volume', 'price', 'user_trade_count', 'window_trade_count','market_avg_size_so_far','hour_of_day']]
    else:
        X = df_sample[['account_age_at_trade', 'timeFromEnd', 'size','volume','user_trade_count','window_trade_count','hour_of_day','market_avg_size_so_far']]
    y = df_sample.loc[X.index, 'won']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42) #standard is 42 for the weights in comment

    # no need to scale for Random Forest
    model = RandomForestClassifier(
        n_estimators=100,    # number of trees
        max_depth=10,        # max depth per tree
        max_features=3,
        random_state=42,
        n_jobs=1           
    )

    model.fit(X_train, y_train)
    

    print(f"Train accuracy: {model.score(X_train, y_train):.3f}")
    print(f"Test accuracy:  {model.score(X_test, y_test):.3f}")
    print(classification_report(y_test, model.predict(X_test)))

    importances = pd.Series(model.feature_importances_, index=X.columns)
    print(importances.sort_values(ascending=False))

    results = expectedReturn(df,model)

    return

def XGBoostME(df, price):
    if price:
        X = df[['account_age_at_trade', 'timeFromEnd', 'size', 'volume', 'price', 'user_trade_count', 'window_trade_count','market_avg_size_so_far','hour_of_day']]
    else:
        X = df[['account_age_at_trade', 'timeFromEnd', 'size', 'volume', 'user_trade_count', 'window_trade_count','hour_of_day','market_avg_size_so_far']]
    
    y = df.loc[X.index, 'won']
    
    model = XGBClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='logloss',
        random_state=42
    )
    
    cv = RepeatedStratifiedKFold(
        n_splits=5,    
        random_state=42
    )

    #for feature in X.columns:
       # test_feature_importance(model, X, y, cv, feature)

    backtestModel(df,model)

    scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy', n_jobs=-1)
    print(f"Individual folds: {scores.round(3)}")
    print(f"Mean accuracy:    {scores.mean():.4f}")
    print(f"Std deviation:    {scores.std():.4f}")
    
    model.fit(X, y)
    importances = pd.Series(model.feature_importances_, index=X.columns)
    print(importances.sort_values(ascending=False))

    results = expectedReturn(df,model)
    
    return


def NeuralNetworkME(df, price):
    if price:
        X = df[['account_age_at_trade', 'timeFromEnd', 'size', 'volume', 'price','user_trade_count','window_trade_count','hour_of_day']]
    else:
        X = df[['account_age_at_trade', 'timeFromEnd', 'size', 'volume','user_trade_count','window_trade_count','hour_of_day']]

    y = df.loc[X.index, 'won']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Scale the data
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Convert to PyTorch tensors
    X_train_t = torch.tensor(X_train_scaled, dtype=torch.float32)
    X_test_t = torch.tensor(X_test_scaled, dtype=torch.float32)
    y_train_t = torch.tensor(y_train.values, dtype=torch.float32).unsqueeze(1)
    y_test_t = torch.tensor(y_test.values, dtype=torch.float32).unsqueeze(1)

    # Build the model
    model = nn.Sequential(
        nn.Linear(X_train_t.shape[1], 64),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(64, 32),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(32, 16),
        nn.ReLU(),
        nn.Linear(16, 1),
        nn.Sigmoid()
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.BCELoss()

    # DataLoader for batching
    dataset = TensorDataset(X_train_t, y_train_t)
    loader = DataLoader(dataset, batch_size=1024, shuffle=True)

    # Training loop
    best_loss = float('inf')
    patience, patience_counter = 7, 0

    rounds = 75
    for epoch in range(rounds):
        model.train()
        for X_batch, y_batch in loader:
            optimizer.zero_grad()
            loss = loss_fn(model(X_batch), y_batch)
            loss.backward()
            optimizer.step()

        # Check validation loss for early stopping
        model.eval()
        with torch.no_grad():
            val_loss = loss_fn(model(X_test_t), y_test_t).item()
        print(f"Epoch {epoch+1}/{rounds} - val_loss: {val_loss:.4f}")

        if val_loss < best_loss:
            best_loss = val_loss
            patience_counter = 0
            best_weights = model.state_dict()  # save best weights
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break

    # Restore best weights and evaluate
    model.load_state_dict(best_weights)
    model.eval()
    with torch.no_grad():
        y_pred = (model(X_test_t) > 0.5).int().numpy()

    print(f"Train accuracy: {model.score(X_train, y_train):.3f}")
    print(f"Test accuracy:  {model.score(X_test, y_test):.3f}")
    print(classification_report(y_test, y_pred))



if __name__ == "__main__":
    print("bzzz *model noises")