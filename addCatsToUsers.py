import duckdb
import joblib

clusterer = joblib.load('hdbscan_model.pkl')

import pandas as pd
import hdbscan
import pyarrow.parquet as pq
import pyarrow as pa


last_id = 0
chunk_size = 200_000
UsersPQ = pq.ParquetFile('Users2.parquet')
writer = None

while True:
    query = f"""SELECT address, COUNT(*) AS nTrades, COUNT(DISTINCT market_id) as nMarkets, AVG(CAST(won AS INTEGER)) AS win_rate, AVG(usd_amount) as avg_spent, SUM(usd_amount) as total_spent, MAX(usd_amount) as max_spent, AVG(price) as avg_price 
                FROM '{UsersPQ}'
                WHERE user_id > {last_id}
                GROUP BY address
                ORDER BY address
                LIMIT {chunk_size}"""
    user_stats = duckdb.query(query).to_df()
    if user_stats.empty:
        break
    last_id = user_stats['address'].iloc[-1]

    labels, strengths = hdbscan.approximate_predict(
        clusterer, user_stats[[]]
    )
    user_stats['category'] = labels
