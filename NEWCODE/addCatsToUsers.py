import sqlite3

import duckdb
import joblib



import pandas as pd
import hdbscan
import pyarrow.parquet as pq
import pyarrow as pa


import duckdb
def create_GROUPEDSQL():
    conn = duckdb.connect()
    conn.execute("PRAGMA temp_directory='X:/duckdb_tmp'")
    conn.execute("PRAGMA max_temp_directory_size='100GiB'")
    conn.execute("SET threads=3")
    conn.execute("PRAGMA memory_limit='8GB'")  
    conn.execute("SET enable_progress_bar = true")
    conn.execute("SET enable_progress_bar_print = true")
    conn.execute("PRAGMA preserve_insertion_order=false") 

    conn.execute("""
        COPY (
            SELECT address, COUNT(*) AS nTrades, approx_count_distinct(market_id) as nMarkets,
                AVG(CAST(won AS INTEGER)) AS win_rate, AVG(usd_amount) as avg_spent,
                SUM(usd_amount) as total_spent, MAX(usd_amount) as max_spent, AVG(price) as avg_price
            FROM 'X:/PolymarketData/Users2.parquet'
            GROUP BY address
        ) TO 'x:/PolymarketData/UsersSTATS.parquet' (FORMAT PARQUET, COMPRESSION 'zstd')
    """)

def predictCats():
    clusterer = joblib.load('hdbscan_model.pkl')
    scaler = joblib.load('scaler.pkl')
    UsersStats = 'x:/PolymarketData/UsersSTATS.parquet'
    category_dict = {}
    features = ['avg_price', 'avg_spent', 'max_spent', 'nMarkets', 'nTrades', 'total_spent', 'win_rate']

    for batch in pq.ParquetFile(UsersStats).iter_batches(batch_size=50_000):
        user_stats = batch.to_pandas()
        user_stats[features] = scaler.transform(user_stats[features])
        labels, _ = hdbscan.approximate_predict(clusterer, user_stats[features])
        category_dict.update(dict(zip(user_stats['address'], labels)))

    conn = sqlite3.connect('X:/PolymarketData/UsersCats.db')
    
    pd.DataFrame(list(category_dict.items()), columns=['address','category']).to_sql('UserCats',conn, if_exists='replace')
    conn.close()
    
def SeperateCats():

    conn=sqlite3.connect('X:/PolymarketData/UsersCats.db')

    usercats = pd.read_sql("SELECT * FROM UserCats",conn)

    for i in []:
        userNoise = usercats[usercats['category'] == i][['address']]
        if i == -1:
            i = "Noisy"
        usersPQ = 'X:/PolymarketData/Users2.parquet'

        con = duckdb.connect(f'X:/PolymarketData/ByCats/Users{i}.db')
        con.register('noise_addresses', userNoise)

        con.execute("SET enable_progress_bar = true")
        con.execute("SET enable_progress_bar_print = true")
        con.execute("PRAGMA temp_directory='X:/duckdb_tmp'")
        con.execute("PRAGMA max_temp_directory_size='100GiB'")
        con.execute("SET threads=3")
        
        con.execute(f"""
            CREATE TABLE Users{i} AS
            SELECT u.*
            FROM '{usersPQ}' u
            JOIN noise_addresses n ON u.address = n.address
        """)
        print("Category " + str(i) + " is Done")

    conn.close()
    con.close()

