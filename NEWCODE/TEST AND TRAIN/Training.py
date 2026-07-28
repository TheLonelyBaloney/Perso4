import os
import traceback
import shutil
shutil.rmtree("C:/xgboost_cache/", ignore_errors=True) 
try: 
    from random import shuffle

    import joblib
    import polars as pl
    from sklearn import metrics
    import xgboost as xgb
    import glob
    from typing import Callable
    import numpy as np

    class TrueStreamingIterator(xgb.DataIter):

        
        def __init__(self, file_paths: list, 
                    feature_cols: list, target_col: str, 
                    chunk_size: int = 2_000_000):
            self._file_paths = file_paths
            self._feature_cols = feature_cols
            self._target_col = target_col
            self._chunk_size = chunk_size
            
            
            # Current state
            self._rounds = 0
            self._file_idx = 0
            self._offset = 0
            self._current_lazy = None  # The lazy query for current file
            self._current_batch = None  # The current chunk of data
            self._finished = False
            
            cache_dir = "C:/xgboost_cache/" 
            os.makedirs(cache_dir, exist_ok=True)
            super().__init__(cache_prefix=os.path.join(cache_dir, "cache"))
        
        def next(self, input_data: Callable):

            while True:
                if self._finished:
                    print("Iterator already finished, returning 0")
                    return False
                # If we have a current batch ready, return it
                if self._current_batch is not None and len(self._current_batch) > 0:
                    
                    X_batch = self._current_batch.select(self._feature_cols).to_numpy()
                    y_batch = self._current_batch.select(self._target_col).to_numpy().flatten()
                    
                    # Pass to XGBoost
                    input_data(data=X_batch, label=y_batch)
                    
                    self._current_batch = None
                    return True
                
                # Check if we've processed all files
                if self._file_idx >= len(self._file_paths):
                    self._finished = True
                    return False
                
                # Load the next file if we don't have a lazy query
                if self._current_lazy is None:
                    file_path = self._file_paths[self._file_idx]
                    print(file_path)

                    self._current_lazy = pl.scan_parquet(file_path).select(
                                    self._feature_cols + [self._target_col])
                    self._offset = 0  # Reset offset for this file
                
                chunk = (self._current_lazy
                    .slice(self._offset, self._chunk_size) 
                    .collect(engine="streaming")
                )
                
                if len(chunk) == 0:
                    self._current_lazy = None
                    self._file_idx += 1
                    self._offset = 0
                    continue
                
                self._current_batch = chunk
                self._offset += self._chunk_size
                #print(f"Processed {self._offset//1000000}M rows")
                
                continue
        
        def reset(self):
            self._rounds += 1
            print(f"resetting... ROUND{self._rounds}")
            self._file_idx = 0
            self._offset = 0
            self._current_lazy = None
            self._current_batch = None
            self._finished = False

    def evaluate_test_files_chunked(test_files, model, market_df, feature_cols, target_col, chunk_size=2_000_000):
        total_samples = 0
        total_correct = 0
        total_tp = 0
        total_fp = 0
        total_fn = 0
        total_tn = 0
        all_aucs = []  # Store AUC per chunk (small list of floats)
        
        print("Starting chunked evaluation...")
        
        for file_idx, test_file in enumerate(test_files):
            print(f"Testing")
            test_lazy = pl.scan_parquet(test_file).select(feature_cols + [target_col])

            offset = 0
            file_rows = 0
            file_correct = 0
            
            while True:
                chunk = (test_lazy
                    .slice(offset, chunk_size)
                    .collect(engine="streaming")
                )
                
                if len(chunk) == 0:
                    break  # No more data
                
                X_chunk = chunk.select(feature_cols).to_numpy()
                y_chunk = chunk.select(target_col).to_numpy().flatten()
                
                # Predict on this chunk
                dchunk = xgb.DMatrix(X_chunk)
                preds = model.predict(dchunk).astype(np.float32)
                pred_binary = (preds >= 0.5).astype(np.int32)
                
                # Update overall metrics
                chunk_size_actual = len(y_chunk)
                total_samples += chunk_size_actual
                file_rows += chunk_size_actual
                
                # Update confusion matrix components
                total_tp += ((pred_binary == 1) & (y_chunk == 1)).sum()
                total_fp += ((pred_binary == 1) & (y_chunk == 0)).sum()
                total_fn += ((pred_binary == 0) & (y_chunk == 1)).sum()
                total_tn += ((pred_binary == 0) & (y_chunk == 0)).sum()
                
                # Track correct predictions for this file
                file_correct += (pred_binary == y_chunk).sum()
                
                # Calculate AUC for this chunk (if enough samples)
                if len(y_chunk) > 1:
                    try:
                        chunk_auc = metrics.roc_auc_score(y_chunk, preds)
                        all_aucs.append(chunk_auc)
                    except ValueError:
                        # This can happen if all predictions are the same
                        pass
                
                # Progress update
                offset += chunk_size
                if offset % (chunk_size * 5) == 0:
                    print(f"  Processed {offset:,} rows from this file...")
                
                del chunk, X_chunk, y_chunk, dchunk, preds, pred_binary
            
            # Calculate file-level accuracy
            file_accuracy = file_correct / file_rows if file_rows > 0 else 0
            print(f"File complete: {file_rows:,} rows, Accuracy: {file_accuracy:.4f}")
        
        # Calculate overall metrics
        if total_samples == 0:
            print("No test data processed!")
            return None
        
        overall_accuracy = (total_tp + total_tn) / total_samples
        overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        overall_f1 = (2 * overall_precision * overall_recall / (overall_precision + overall_recall) 
                    if (overall_precision + overall_recall) > 0 else 0)
        
        # Average AUC across chunks
        overall_auc = np.mean(all_aucs) if all_aucs else 0
        
        return {
            'samples': total_samples,
            'accuracy': overall_accuracy,
            'precision': overall_precision,
            'recall': overall_recall,
            'f1': overall_f1,
            'auc': overall_auc
        }

    market_df = pl.read_parquet("X:/PolymarketData/markets.parquet")
    market_df = market_df.with_columns([
        pl.col("created_at").dt.epoch(time_unit="s").alias("created_at_unix"),
        pl.col("end_date").dt.epoch(time_unit="s").alias("end_date_unix")
    ])

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

    all_files = sorted(glob.glob("X:/PolymarketData/ByCats/Users2/preprocessed*.parquet"))
    print(f"Found {len(all_files)} files")


    train_files = all_files[:4]
    test_files = all_files[4:]


    print(f"Training on {len(train_files)} files")
    for f in train_files:
        print(f"  - {f}")

    print(f"Testing on {len(test_files)} files")
    for f in test_files:
        print(f"  - {f}")

      
    train_iterator = TrueStreamingIterator(
        file_paths=train_files,
        feature_cols=feature_cols,
        target_col=target_col,
        chunk_size=5_000_000  
    )

    dtrain = xgb.ExtMemQuantileDMatrix(
        data=train_iterator,
        max_bin=128
    )
    

    params = {
        'objective': 'binary:logistic',
        'tree_method': 'hist',
        'max_depth': 5,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'verbosity':3,
        'max_bin':128,
    }

    print("Starting training...") 
    model = xgb.train(params, dtrain, num_boost_round=100,early_stopping_rounds = 10, evals = [(dtrain, "train")],verbose_eval=True)

    print("Training complete!")
    joblib.dump(model,"xgboostedMF.joblib")
    ################################################################################
    print("\n" + "="*60)
    print("STARTING TEST EVALUATION")
    print("="*60)

    results = evaluate_test_files_chunked(
        test_files=test_files,
        model=model,
        market_df=market_df,
        feature_cols=feature_cols,
        target_col=target_col,
        chunk_size=1_000_000 
    )

    print("\n" + "="*60)
    print("="*60)
    print(f"Total samples:        {results['samples']:,}")
    print(f"Accuracy:             {results['accuracy']:.4f}")
    print(f"Precision:            {results['precision']:.4f}")
    print(f"Recall:               {results['recall']:.4f}")
    print(f"F1 Score:             {results['f1']:.4f}")
    print(f"AUC:                  {results['auc']:.4f}")

    
except Exception:
    traceback.print_exc()