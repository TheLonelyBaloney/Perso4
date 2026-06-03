import sqlite3

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
        trans_hash      TEXT UNIQUE
    )
    """)
    ####################################### Wallets
    cur.execute("""
    CREATE TABLE IF NOT EXISTS wallets (
        wallet      TEXT PRIMARY KEY,
        account_age INTEGER,
        first_seen  TEXT
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
    INSERT OR IGNORE INTO trades (conditionId, wallet, timestamp, price, size, trans_hash)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (trade['conditionId'], trade['proxyWallet'], trade['timestamp'], trade['price'], trade['size'],trade['transactionHash']))

    conn.commit()
    return

def CheckOutDB():
    conn = sqlite3.connect("polymarket.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT COUNT(*) FROM trades
    """)
    print(cur.fetchall())

    return



if __name__ == "__main__":
    CheckOutDB()
else:
    conn = startup()