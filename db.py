import json
import sqlite3
from datetime import datetime

def startup():
    conn = sqlite3.connect("polymarket.db")
    cur = conn.cursor()
    ######################################## Trades
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        conditionId     TEXT,
        wallet          TEXT,
        timestamp       TEXT,
        price           REAL,
        size            REAL,
        outcome         TEXT,
        trans_hash      TEXT UNIQUE
    )
    """)
    ####################################### Wallets
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        wallet      TEXT PRIMARY KEY,
        account_age INTEGER
    )
    """)
    ####################################### Markets
    cur.execute("""
    CREATE TABLE IF NOT EXISTS markets (
        conditionId TEXT PRIMARY KEY,
        volume      REAL,
        outcome     TEXT
    )
    """)
    conn.commit()
    return conn

def insertTradeToDB(conn,trade):

    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO trades (conditionId, wallet, timestamp, price, size, outcome, trans_hash)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (trade['conditionId'], trade['proxyWallet'], trade['timestamp'], trade['price'], trade['size'], trade['outcome'], trade['transactionHash']))

    conn.commit()
    return

def insertMarketToDB(conn, market):

    cur = conn.cursor()
    
    if "1" not in json.loads(market['outcomePrices']):
        return False
    
    outcome = json.loads(market['outcomes'])[json.loads(market['outcomePrices']).index("1")]

    cur.execute("""
    INSERT OR IGNORE INTO markets (conditionId, volume, outcome)
    VALUES (?, ?, ?)
    """, (market['conditionId'], market['volume'], outcome)
    )

    conn.commit()
    return True

def insertUserToDB(conn,user):

    cur = conn.cursor()

    dateCreated = user.get('createdAt')

    unix =  datetime.fromisoformat(dateCreated.replace("Z", "+00:00")).timestamp()

    cur.execute("""
    INSERT OR IGNORE INTO users (wallet, account_age)
    VALUES (?, ?)
    """, (user.get('proxyWallet'),unix)
    )
    
    conn.commit()
    return


def CheckOutDB():
    conn = sqlite3.connect("polymarket.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) FROM markets
        """)
    print("  Number of markets: "+str(cur.fetchall()))

    cur.execute("""
    SELECT COUNT(*) FROM trades
    """)
    print("  Number of trades: "+str(cur.fetchall()))

    cur.execute("""
    SELECT COUNT(*) FROM users
    """)
    print("  Number of users: "+str(cur.fetchall()))

    return



if __name__ == "__main__":
    CheckOutDB()
else:
    conn = startup()