from concurrent.futures import ThreadPoolExecutor, as_completed
import glob
import logging
from random import randrange
import time

import duckdb
from duckdb.sqltypes import VARCHAR
import pandas as pd
import sqlite3
import pyarrow.parquet as pq
import pyarrow as pa
import polars as pl
import requests

tradesPQ = 'X:/PolymarketData/trades.parquet'
marketPQ = 'X:/PolymarketData/markets.parquet'
usersPQ = 'X:/PolymarketData/users.parquet'
newUsersPQ = 'X:/PolymarketData/Users2.parquet'

def DidheWin(UserBets: pa.Array, OutcomePrices: pa.Array): # INPUTs are pyarrows from the users parquet and market parquet
    UserBets_pd = UserBets.to_pandas()
    OutcomePrices_pd = OutcomePrices.to_pandas()
    whereIs1 = OutcomePrices_pd.str.find("1")
    Won = ((whereIs1==2) & (UserBets_pd == "token1")) | ((whereIs1!=2) & (UserBets_pd != "token1"))
    
    return pa.array(Won)

def updateToAddWon():
    con = duckdb.connect()
    con.execute("PRAGMA enable_progress_bar")

    con.create_function(
        "my_func",
        DidheWin,
        [VARCHAR,VARCHAR],
        type="arrow",
        return_type="BOOLEAN"
    )


    con.sql(f"""
        COPY (
            SELECT a.*,
                my_func(a.nonusdc_side, b.outcome_prices) AS won
            FROM '{usersPQ}' a
            LEFT JOIN '{marketPQ}' b
            ON a.condition_id = b.condition_id
        ) TO 'x:/PolymarketData/Users2.parquet' (FORMAT PARQUET, COMPRESSION 'zstd')
    """)

#winrate = duckdb.query(f""" SELECT AVG(CAST(won AS INTEGER)) AS win_rate FROM '{newUsersPQ}'""")
#print(winrate) ~~ 0.49907

def addFEATUREStodb():

    conn = duckdb.connect("X:/PolymarketData/ByCats/NoisyUsers/NoisyUsers.db")
    conn.execute("SET enable_progress_bar = true")
    conn.execute("SET enable_progress_bar_print = true")
    conn.execute("ATTACH 'X:/PolymarketData/UsersCats.db' AS usercats_db")
    conn.execute("PRAGMA temp_directory='X:/duckdb_tmp'")
    conn.execute("PRAGMA max_temp_directory_size='300GiB'")
    conn.execute("SET threads=3")
    conn.execute("PRAGMA memory_limit='8GB'")
    conn.execute("SET preserve_insertion_order=false")  
    print("Starting...")
    # get address boundaries to split into ~20 chunks
    bounds = conn.execute("""
        SELECT address FROM usercats_db.UserCats
        WHERE category = -1
        ORDER BY address
    """).df()["address"].tolist()

    n_chunks = 5
    step = len(bounds) // n_chunks
    bounds = [bounds[i * step] for i in range(n_chunks)]

    bounds = [''] + bounds + [None] 
    print("Bucket bounds found...")
    for i in range(len(bounds) - 1):
        lower = bounds[i]
        upper = bounds[i+1]
        where_clause = f"address >= '{lower}'" if lower else "TRUE"
        if upper:
            where_clause += f" AND address < '{upper}'"

        query = f"""
            COPY (
                WITH base AS (
                    SELECT *,
                        ROW_NUMBER() OVER (PARTITION BY address ORDER BY timestamp) AS cum_trades,
                        SUM(usd_amount) OVER (
                        PARTITION BY address ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                        ) AS cum_spent_prior,
                        MAX(usd_amount) OVER (PARTITION BY address ORDER BY timestamp) AS cum_max_spent,
                        MAX(price) OVER (PARTITION BY address ORDER BY timestamp) AS highest_price_yet,
                        MIN(price) OVER (PARTITION BY address ORDER BY timestamp) AS lowest_price_yet,
                        SUM(CAST(won AS INTEGER)) OVER (
                        PARTITION BY address ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                        ) AS prior_wins,
                        SUM(price) OVER (
                        PARTITION BY address ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                        ) AS cum_price_prior,
                        timestamp - LAG(timestamp) OVER (PARTITION BY address ORDER BY timestamp) AS time_since_last_trade
                    FROM NoisyUsers
                    WHERE {where_clause}
                )
                SELECT * FROM base
            ) TO 'X:/PolymarketData/ByCats/NoisyUsers/NewNoisyUsers_part{i}.parquet' (FORMAT PARQUET, COMPRESSION 'zstd')
        """
        print(f"Running chunk {i}...")
        conn.execute(query)

def addmorefeatures(feature_cols,target_col):
    all_files = sorted(glob.glob("X:/PolymarketData/ByCats/NoisyUsers/*.parquet"))
    market_df = pl.read_parquet("X:/PolymarketData/markets.parquet")
    market_df = market_df.with_columns([
        pl.col("created_at").dt.epoch(time_unit="s").alias("created_at_unix"),
        pl.col("end_date").dt.epoch(time_unit="s").alias("end_date_unix")
    ])
    for i,file in enumerate(all_files):
        trades_lazy = pl.scan_parquet(file)
                            
        processed = (trades_lazy
            .join(market_df.lazy(), on="condition_id", how="left")
            .with_columns([
                pl.from_epoch(pl.col("timestamp"), time_unit="s").alias("timestamp_datetime"),
                pl.col("timestamp").alias("timestamp_unix"),
            ])
            .with_columns([
                (pl.col("timestamp_unix") - pl.col("created_at_unix")).alias("time_since_start"),
                (pl.col("end_date_unix") - pl.col("timestamp_unix")).alias("time_until_end"),
                (pl.col("timestamp_datetime").dt.hour()).alias("hour_of_day"),
                (pl.col("timestamp_datetime").dt.weekday()).alias("day_of_week"),
                (pl.col("prior_wins") / pl.col("cum_trades")).alias("winrate"),
                (pl.col("cum_price_prior") / pl.col("cum_trades")).alias("avg_price"),
                pl.when(pl.col("direction") == "BUY").then(1)
                    .when(pl.col("direction") == "SELL").then(0)
                    .otherwise(-1)
                    .alias("direction"),
            ])
            .select(feature_cols + [target_col])
        )
        processed.sink_parquet(f"X:/PolymarketData/ByCats/NoisyUsers/preprocessedNoisyUsers_train{i}.parquet")

def DidheWin(UserBets: pa.Array, OutcomePrices: pa.Array): # INPUTs are pyarrows from the users parquet and market parquet
    UserBets_pd = UserBets.to_pandas()
    OutcomePrices_pd = OutcomePrices.to_pandas()
    whereIs1 = OutcomePrices_pd.str.find("1")
    Won = ((whereIs1==2) & (UserBets_pd == "token1")) | ((whereIs1!=2) & (UserBets_pd != "token1"))
    
    return pa.array(Won)


def getMarketDATA(chunk):
    try:
        result = []
        url = "https://gamma-api.polymarket.com/markets"
        for attempt in range(2):
            try:
                response = requests.get(
                        url,
                        params={
                            "condition_ids":chunk,
                            "closed":"true",
                            "include_tag":True
                        },
                        timeout=15
                    )    
                data = response.json()
                break
            except (requests.exceptions.JSONDecodeError, requests.exceptions.RequestException) as e:
                print(e)
                time.sleep(1)

        for m in data:
            try:
                tags = [t['label'] for t in m.get('tags', [])]
                recurrences = m['events'][0]['series'][0]['recurrence']
            except KeyError:
                tags = [t['label'] for t in m.get('tags', [])]
                recurrences = "once"
            result.append({"condition_id":m["conditionId"],"tags":tags,"recurrences":recurrences})
        time.sleep(0.3)
    except Exception as e:
        print(e)
        exit()
    return result
    
def makeLookUp(marketfile,outputFile): 
    ids = duckdb.query(f"""SELECT DISTINCT condition_id from '{marketfile}'""").to_df()['condition_id'].tolist()
    print(len(ids))
    results = []
    start = time.time()
    chunks = [ids[i:i+20] for i in range(0, len(ids), 20)]
    completed = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(getMarketDATA, c): c for c in chunks}
        for future in as_completed(futures):
            results.extend(future.result())
            completed += 1
            print(completed)
            if completed % 50 == 0:
                elapsed = time.time() - start
                rate = completed / elapsed
                eta = (len(chunks) - completed) / rate / 60 if rate > 0 else float('inf')
                print(f"{completed}/{len(chunks)} chunks done, {len(results)} rows, ETA {eta} min")
            if completed % 2000 == 0:
                pd.DataFrame(results).to_parquet(outputFile + ".partial", compression="zstd")
                print(f"saved {len(results)}")

    pd.DataFrame(results).to_parquet(outputFile, compression="zstd")
    print(f"Done {len(results)} markets in lookup table")



def joinLookUpToMarketFile(marketfile,lookUpFile):
    conn = duckdb.connect()
    conn.execute("SET enable_progress_bar = true")
    conn.execute("SET enable_progress_bar_print = true")
    conn.execute("PRAGMA temp_directory='X:/duckdb_tmp'")
    conn.execute("PRAGMA max_temp_directory_size='300GiB'")
    conn.execute("SET threads=3")
    conn.execute("PRAGMA memory_limit='8GB'")
    conn.execute("SET preserve_insertion_order=false")  
    print("Starting...")

    conn.sql(f"""
        COPY (
            SELECT a.*, b.tags, b.recurrences
            FROM '{marketfile}' a
            LEFT JOIN '{lookUpFile}' b
                ON a.condition_id = b.condition_id
        ) TO 'x:/PolymarketData/taggedMarkets.parquet' (FORMAT PARQUET, COMPRESSION 'zstd')
    """)
    print("Wrote taggedMarkets.parquet")
    return

def dropInvalidRecurrenceRows(marketsPQ):
    duckdb.query(f"""
        COPY (
            SELECT * FROM '{marketsPQ}'
            WHERE NOT (recurrences IS NULL AND tags IS NULL) AND recurrences != ''
        ) TO 'X:/PolymarketData/Cleantaggedmarkets.parquet' (FORMAT PARQUET, COMPRESSION 'zstd')
    """)

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
target_col = "won"
#addFEATUREStodb()
#addmorefeatures(feature_cols,target_col)
#joinLookUpToMarketFile("X:/PolymarketData/markets.parquet","X:/PolymarketData/marketLookUp.parquet")
#dropInvalidRecurrenceRows("X:/PolymarketData/taggedmarkets.parquet") # going to rename Cleantaggedmarket to taggedmarket
processMetaModelData()