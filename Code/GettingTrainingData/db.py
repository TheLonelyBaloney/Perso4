import json
import os
import sqlite3
from datetime import datetime
import time

import pandas as pd
import requests

def startup():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'polymarket.db')
    
    conn = sqlite3.connect(DB_PATH)

    cur = conn.cursor()
    ######################################## Trades
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        conditionId     TEXT,
        wallet          TEXT,
        timestamp       TEXT,
        price           REAL,
        size            REAL,
        outcome         TEXT,
        outcomeIndex    BIT,
        profilePic      BIT,
        trans_hash      TEXT PRIMARY KEY
    )
    """)
    ####################################### Wallets
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        wallet      TEXT PRIMARY KEY,
        createdAt   TEXT,
        weightedVol REAL,
        nTrades     INT,
        nMarkets    INT,
        totalSize   REAL,
        nWins       INT,
        totalPrice  REAL,
        totalValue  REAL,
        maxSize     REAL
    )
    """)
    ####################################### Markets
    cur.execute("""
    CREATE TABLE IF NOT EXISTS markets (
        conditionId TEXT PRIMARY KEY,
        volume      REAL,
        outcome     TEXT,
        endDate     TEXT,
        slug        TEXT,
        startDate   TEXT,
        createdAt   TEXT,
        commentCount INT,
        competitive REAL,
        orderMinSize INT,
        updatedAt   TEXT
    )
    """)#cant use competitive
    conn.commit()
    return conn

def insertTradeToDB(conn,trade):

    if len(trade['profileImage'])>0:
        profilePic = 1 
    else:
        profilePic = 0
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO trades (conditionId, wallet, timestamp, price, size, outcome, outcomeIndex, profilePic, trans_hash)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (trade['conditionId'], trade['proxyWallet'], trade['timestamp'], trade['price'], trade['size'], trade['outcome'], trade['outcomeIndex'], profilePic, trade['transactionHash']))

    conn.commit()
    return

def insertMarketToDB(conn, market, event):

    cur = conn.cursor()
    
    if "1" not in json.loads(market['outcomePrices']):
        return False
    
    outcome = json.loads(market['outcomes'])[json.loads(market['outcomePrices']).index("1")]
    

    cur.execute("""
    INSERT OR IGNORE INTO markets (conditionId, volume, outcome, endDate, slug, startDate, createdAt, commentCount, competitive, orderMinSize, updatedAt)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (market['conditionId'], market['volume'], outcome, market['endDate'], market['slug'], market['startDate'], market['createdAt'], event['commentCount'], 0, market['orderMinSize'], market['updatedAt'])
    )

    conn.commit()
    return True

def insertUserToDB(conn,user):

    cur = conn.cursor()

    dateCreated = user.get('createdAt')
    if not dateCreated: ### For some reason some accounts dont have a createdAt attribute
        return

    cur.execute("""
    INSERT OR IGNORE INTO users (wallet, createdAt, weightedVol, nTrades, nMarkets, totalSize, nWins, totalPrice, totalValue, maxSize)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user.get('proxyWallet'),user['createdAt'],user['weightedVolume'],user['nTrades'],user['nMarkets'],user['totalSize'],user['nWins'], user['totalPrice'], user['totalValue'], user['maxSize'])
    )
    
    conn.commit()
    return
                  
def DBgetTrades(conn, limit=10000):
    return pd.read_sql(f"SELECT conditionId, wallet, timestamp, price, size, outcome, trans_hash FROM trades LIMIT {limit}", conn)

def DBgetMarkets(conn):

    return pd.read_sql("SELECT * FROM markets", conn)

def DBgetUsers(conn):

    return pd.read_sql("SELECT * FROM users", conn)

def CheckOutDB():

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'polymarket.db')

    conn = sqlite3.connect(DB_PATH)
    
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
    conn = startup()

else:
    conn = startup()