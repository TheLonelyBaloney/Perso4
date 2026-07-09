import duckdb
import pandas as pd
import sqlite3
import pyarrow.parquet as pq
import pyarrow as pa
from duckdb.sqltypes import VARCHAR

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