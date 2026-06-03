import sqlite3

conn = sqlite3.connect("LEARNINGpolymarket.db")
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        market    TEXT,
        wallet    TEXT,
        timestamp TEXT,
        side      TEXT,
        price     REAL,
        size      REAL,
        UNIQUE(wallet, timestamp, market)
    )
""")

conn.commit()

# ALWAYS HAVE (?,?,?,?,?,?) when inserting to prevent sqlinject 
# OR IGNORE is if its a duplicate using the unique id from the 
# above table for trades
cur.execute("""
    INSERT OR IGNORE INTO trades (market, wallet, timestamp, side, price, size)
    VALUES (?, ?, ?, ?, ?, ?)
""", ("Will Trump win?", "0xABC123", "2024-01-01", "BUY", 0.72, 50.00))
cur.execute("""
    INSERT OR IGNORE INTO trades (market, wallet, timestamp, side, price, size)
    VALUES (?, ?, ?, ?, ?, ?)
""", ("Will Trump win?", "0xDEF456", "2024-01-02", "SELL", 0.68, 30.00))

cur.execute("""
    INSERT OR IGNORE INTO trades (market, wallet, timestamp, side, price, size)
    VALUES (?, ?, ?, ?, ?, ?)
""", ("Will it rain?", "0xABC123", "2024-01-03", "BUY", 0.45, 100.00))
##################################################


cur.execute("SELECT * FROM trades")

# All trades on a specific market
cur.execute("SELECT * FROM trades WHERE market = 'Will Trump win?'")
print(cur.fetchall())

# All trades by a specific wallet
cur.execute("SELECT * FROM trades WHERE wallet = '0xABC123'")
print(cur.fetchall())

# All BUY trades above a certain price
cur.execute("SELECT * FROM trades WHERE side = 'BUY' AND price > 0.50")
print(cur.fetchall())
#############################################


# How many trades do we have total?
cur.execute("SELECT COUNT(*) FROM trades")
print(cur.fetchone())

# What's the average price across all trades?
cur.execute("SELECT AVG(price) FROM trades")
print(cur.fetchone())

# What's the total volume (size) traded?
cur.execute("SELECT SUM(size) FROM trades")
print(cur.fetchall()) #fetch one or fetch all does the same since it only returns 1 thing
########################################################


# Average price per market          ##  Returns a list (because of group by) of tuples of size 2 (because of the comma between selectmarket)
#                                       and avg(price). for each tuple we can access inside via row['market'] and row['avg_price] because of 
#                                       the "as avg_price"
cur.execute("""
    SELECT market, AVG(price) as avg_price 
    FROM trades
    GROUP BY market
""") 

print(cur.fetchall())

# Number of trades per wallet
cur.execute("""
    SELECT wallet, COUNT(*) as trade_count
    FROM trades
    GROUP BY wallet
""")
print(cur.fetchall())

# Total volume per wallet
cur.execute("""
    SELECT wallet, SUM(size) as total_volume
    FROM trades
    GROUP BY wallet
""")
print(cur.fetchall())
################################################################

cur.execute("""
    CREATE TABLE IF NOT EXISTS wallets (
        wallet      TEXT PRIMARY KEY,
        account_age INTEGER,
        first_seen  TEXT
    )
""")
conn.commit()
################################################################
cur.execute("""
    INSERT OR IGNORE INTO wallets (wallet, account_age, first_seen)
    VALUES (?, ?, ?)
""", ("0xABC123", 342, "2023-01-01"))

cur.execute("""
    INSERT OR IGNORE INTO wallets (wallet, account_age, first_seen)
    VALUES (?, ?, ?)
""", ("0xDEF456", 45, "2023-12-01"))

conn.commit()
##############################################################
#                           #SELECT makes the tuple(t.wallet,t.market,t.price,w.account_age) where t is defined at FROM trades t
#                           #and w after JOIN wallets. ON represents the condition that will need to be satisfied (same wallet name)
cur.execute("""
    SELECT t.wallet, t.market, t.price, w.account_age
    FROM trades t  
    JOIN wallets w ON t.wallet = w.wallet  
""")
print(cur.fetchall())

cur.execute("""
    SELECT 
        w.account_age,
        AVG(t.price) as avg_price,
        COUNT(*) as trade_count
    FROM trades t
    JOIN wallets w ON t.wallet = w.wallet
    GROUP BY w.account_age
""")
print("")
print(cur.fetchall())

conn.close()