import pandas as pd
import sqlite3
import pyarrow.parquet as pq



conn = sqlite3.connect(r'X:\PolymarketData\polymarket_full.db')
parquet_file = pq.ParquetFile(r'X:\PolymarketData\trades.parquet')

total_rows = 0
# read in batches
for i, batch in enumerate(parquet_file.iter_batches(batch_size=150000)):
    df_chunk = batch.to_pandas()
    print(df_chunk.shape)
    df_chunk.to_sql('trades', conn, if_exists='append' if i > 0 else "replace", index=False)
    total_rows += len(df_chunk)
    print(f"Processed {total_rows:,} rows so far...")
    

cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM trades")
print(cur.fetchone())