#!/usr/bin/env python3
"""
Build Gold Analytics: Stock Congress Activity

Aggregates congressional activity per stock/ticker - showing which stocks
have the most legislative exposure (bills affecting their sector + member trades).

Output: gold/analytics/fact_stock_congress_activity/
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))

import pandas as pd
import boto3
from io import BytesIO
from datetime import datetime
from collections import defaultdict
import logging

from lib.congress_sector_mapper import map_policy_area_to_sector, FINANCIAL_SECTORS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def read_parquet_from_s3(s3_client, prefix: str) -> pd.DataFrame:
    """Read all Parquet files from an S3 prefix."""
    logger.info(f"Reading from s3://{BUCKET_NAME}/{prefix}")
    
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    if 'Contents' not in response:
        logger.warning(f"No files found in {prefix}")
        return pd.DataFrame()
    
    dfs = []
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            response_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
            df = pd.read_parquet(BytesIO(response_obj['Body'].read()))
            dfs.append(df)
    
    if not dfs:
        return pd.DataFrame()
    
    return pd.concat(dfs, ignore_index=True)


def build_stock_activity():
    """Build stock-level congressional activity summary."""
    s3 = boto3.client('s3')
    
    # 1. Read FD transactions
    logger.info("Loading FD transactions...")
    transactions_df = read_parquet_from_s3(s3, 'gold/house/financial/facts/fact_ptr_transactions/')
    if transactions_df.empty:
        logger.warning("No FD transactions found")
        transactions_df = pd.DataFrame(columns=['ticker', 'filer_name', 'transaction_type', 'filing_year'])
    else:
        logger.info(f"Loaded {len(transactions_df)} transactions")
    
    # 2. Read Congress bills
    logger.info("Loading Congress bills...")
    bills_df = read_parquet_from_s3(s3, 'gold/congress/dim_bill/')
    if bills_df.empty:
        logger.warning("No bills found")
        bills_df = pd.DataFrame(columns=['bill_id', 'policy_area', 'congress'])
    else:
        logger.info(f"Loaded {len(bills_df)} bills")
    
    # 3. Aggregate transactions by ticker
    stock_stats = defaultdict(lambda: {
        'ticker': '',
        'members_trading_count': 0,
        'total_transactions': 0,
        'buy_count': 0,
        'sell_count': 0,
        'sectors': set(),
    })
    
    if not transactions_df.empty and 'ticker' in transactions_df.columns:
        for ticker, group in transactions_df.groupby('ticker'):
            if pd.isna(ticker) or str(ticker).strip() == '':
                continue
            
            ticker_str = str(ticker).upper().strip()
            stock_stats[ticker_str]['ticker'] = ticker_str
            stock_stats[ticker_str]['members_trading_count'] = group['filer_name'].nunique()
            stock_stats[ticker_str]['total_transactions'] = len(group)
            
            if 'transaction_type' in group.columns:
                tx_types = group['transaction_type'].str.lower().fillna('')
                stock_stats[ticker_str]['buy_count'] = tx_types.str.contains('purchase|buy', regex=True).sum()
                stock_stats[ticker_str]['sell_count'] = tx_types.str.contains('sale|sell', regex=True).sum()
    
    # 4. Count bills per sector and map to approximate tickers
    sector_bill_counts = defaultdict(int)
    if not bills_df.empty and 'policy_area' in bills_df.columns:
        for _, bill in bills_df.iterrows():
            sector = map_policy_area_to_sector(bill.get('policy_area'))
            sector_bill_counts[sector] += 1
    
    # 5. Build final records
    records = []
    for ticker, stats in stock_stats.items():
        records.append({
            'ticker': ticker,
            'members_trading_count': stats['members_trading_count'],
            'total_transactions': stats['total_transactions'],
            'buy_count': stats['buy_count'],
            'sell_count': stats['sell_count'],
            'legislative_exposure_score': 0,  # Would need sector-ticker mapping
        })
    
    # 6. Add sector-level bill counts as separate records
    for sector, bill_count in sector_bill_counts.items():
        records.append({
            'ticker': f"SECTOR:{sector}",
            'members_trading_count': 0,
            'total_transactions': 0,
            'buy_count': 0,
            'sell_count': 0,
            'legislative_exposure_score': bill_count,
        })
    
    if not records:
        logger.warning("No stock activity records generated")
        return pd.DataFrame()
    
    df = pd.DataFrame(records)
    df['gold_created_at'] = datetime.utcnow().isoformat()
    
    return df


def write_gold_parquet(df: pd.DataFrame, prefix: str):
    """Write DataFrame to Gold layer."""
    s3 = boto3.client('s3')
    
    s3_key = f"{prefix}/part-0000.parquet"
    buffer = BytesIO()
    df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
    buffer.seek(0)
    
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
    logger.info(f"Wrote {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")


def main():
    logger.info("=" * 80)
    logger.info("Building Gold Analytics: Stock Congress Activity")
    logger.info("=" * 80)
    
    df = build_stock_activity()
    
    if df.empty:
        logger.error("No data to write")
        return
    
    logger.info(f"\nSummary:")
    logger.info(f"  Total records: {len(df)}")
    stock_records = df[~df['ticker'].str.startswith('SECTOR:')]
    sector_records = df[df['ticker'].str.startswith('SECTOR:')]
    logger.info(f"  Stock tickers: {len(stock_records)}")
    logger.info(f"  Sector summaries: {len(sector_records)}")
    if len(stock_records) > 0:
        top_traded = stock_records.nlargest(5, 'total_transactions')[['ticker', 'total_transactions']]
        logger.info(f"  Top traded stocks:\n{top_traded.to_string(index=False)}")
    
    write_gold_parquet(df, 'gold/analytics/fact_stock_congress_activity')
    
    logger.info("\n✅ Stock congress activity build complete!")


if __name__ == '__main__':
    main()
