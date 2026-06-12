
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


def LinearRegressionME(df,price): #with or without price

    if price:
        X = df[['account_age_at_trade', 'timeFromEnd', 'sizeToVolumePct','price']] 
    else:
        X = df[['account_age_at_trade', 'timeFromEnd', 'sizeToVolumePct']] 
    Y = df.loc[X.index, 'won']

    X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train) # (xi-x_bar)/var since some feature values reach the 100k's and some are [0,1]
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000) #
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    print(f"Accuracy: {model.score(X_test_scaled, y_test):.3f}")
    print(classification_report(y_test, y_pred))  

    weights = pd.Series(model.coef_[0], index=X.columns)
    print(weights.sort_values(ascending=False))

    return 



if __name__ == "__main__":
    print("bzzz *model noises")