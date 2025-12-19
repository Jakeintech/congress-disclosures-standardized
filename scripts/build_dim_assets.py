#!/usr/bin/env python3
"""
Build dim_assets dimension table from PTR transactions with stock API enrichment.

This script:
1. Loads unique assets from silver/structured PTR data
2. Extracts ticker symbols using regex
3. Enriches with Yahoo Finance API (sector, industry, market cap)
4. Writes to gold/dimensions/dim_assets
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import json
from datetime import datetime
import logging
from collections import Counter

from ingestion.lib.enrichment import StockAPIEnricher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


from concurrent.futures import ThreadPoolExecutor, as_completed

import duckdb

from botocore.config import Config

def config_boto():
    return Config(max_pool_connections=50)

def load_unique_assets_from_silver(bucket_name: str) -> pd.DataFrame:
    """Load unique assets from consolidated silver tabular Parquet files using DuckDB."""
    logger.info("Loading assets from Silver Tabular layer via DuckDB...")

    assets = []
    asset_occurrences = Counter()
    asset_first_seen = {}
    asset_last_seen = {}

    current_year = datetime.now().year
    years = [current_year - 1, current_year]
    
    try:
        con = duckdb.connect(database=':memory:')
        con.execute("INSTALL httpfs;")
        con.execute("LOAD httpfs;")
        # S3_REGION should be accessible if we import it or define it, 
        # but let's assume it's us-east-1 for now or get from env
        s3_reg = os.environ.get('AWS_REGION', 'us-east-1')
        con.execute(f"SET s3_region='{s3_reg}';")

        for year in years:
            logger.info(f"Processing year {year}...")
            
            # Paths
            tx_path = f"s3://{bucket_name}/silver/house/financial/tabular/year={year}/filing_type=P/transactions.parquet"
            sh_path = f"s3://{bucket_name}/silver/house/financial/tabular/year={year}/filing_type=A/holdings.parquet"

            # Load Transactions
            try:
                df_tx = con.execute(f"SELECT asset_name, transaction_date FROM read_parquet('{tx_path}')").df()
                for _, row in df_tx.iterrows():
                    name = str(row['asset_name']).strip() if row['asset_name'] else ""
                    if not name: continue
                    date = row['transaction_date']
                    asset_occurrences[name] += 1
                    assets.append(name)
                    if date:
                        if name not in asset_first_seen or str(date) < str(asset_first_seen[name]):
                            asset_first_seen[name] = date
                        if name not in asset_last_seen or str(date) > str(asset_last_seen[name]):
                            asset_last_seen[name] = date
                logger.info(f"  Loaded {len(df_tx):,} transactions from {year}")
            except Exception:
                logger.warning(f"  No transactions found for {year} in tabular layer")

            # Load Holdings
            try:
                df_sh = con.execute(f"SELECT asset_name FROM read_parquet('{sh_path}')").df()
                for _, row in df_sh.iterrows():
                    name = str(row['asset_name']).strip() if row['asset_name'] else ""
                    if not name: continue
                    asset_occurrences[name] += 1
                    assets.append(name)
                logger.info(f"  Loaded {len(df_sh):,} holdings from {year}")
            except Exception:
                logger.warning(f"  No holdings found for {year} in tabular layer")

    except Exception as e:
        logger.error(f"DuckDB asset loading failed: {e}")
        return pd.DataFrame()

    if not assets:
        return pd.DataFrame()

    unique_assets = pd.DataFrame({'asset_name': list(set(assets))})
    unique_assets['occurrence_count'] = unique_assets['asset_name'].map(asset_occurrences)
    unique_assets['first_seen_date'] = unique_assets['asset_name'].map(asset_first_seen)
    unique_assets['last_seen_date'] = unique_assets['asset_name'].map(asset_last_seen)

    today = datetime.now().strftime('%Y-%m-%d')
    unique_assets['first_seen_date'] = unique_assets['first_seen_date'].fillna(today)
    unique_assets['last_seen_date'] = unique_assets['last_seen_date'].fillna(today)

    return unique_assets


def enrich_assets(assets_df: pd.DataFrame, stock_enricher: StockAPIEnricher, bucket_name: str) -> pd.DataFrame:
    """Enrich assets using vectorized cache lookups and delta enrichment."""
    logger.info("Enriching assets using Vectorized Data Lake approach...")

    # 1. Vectorized Ticker Extraction (Parallel)
    logger.info("  Step 1: Parallel ticker extraction & classification...")
    records = assets_df.to_dict('records')
    
    def extract_info(row):
        asset_name = row['asset_name']
        ticker, method = stock_enricher.extract_ticker_from_name(asset_name) or (None, None)
        asset_type = stock_enricher.classify_asset_type(asset_name)
        return {
            'asset_name': asset_name,
            'extracted_ticker': ticker,
            'extraction_method': method,
            'asset_type': asset_type
        }

    extracted_data = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(extract_info, r): r for r in records}
        completed = 0
        for future in as_completed(futures):
            extracted_data.append(future.result())
            completed += 1
            if completed % 1000 == 0:
                logger.info(f"    [{completed}/{len(records)}] Assets pre-processed...")

    extracted_df = pd.DataFrame(extracted_data)
    assets_df = assets_df.merge(extracted_df, on='asset_name')

    # 2. Vectorized Cache Join (DuckDB)
    logger.info("  Step 2: Vectorized cache join with DuckDB...")
    cache_path = f"s3://{bucket_name}/silver/house/financial/tabular/cache/stock_enrichment.parquet"
    
    con = duckdb.connect(database=':memory:')
    con.execute("INSTALL httpfs; LOAD httpfs;")
    s3_reg = os.environ.get('AWS_REGION', 'us-east-1')
    con.execute(f"SET s3_region='{s3_reg}';")

    try:
        # Load cache into a DuckDB view
        con.execute(f"CREATE VIEW stock_cache AS SELECT * FROM read_parquet('{cache_path}')")
        
        # Register the assets_df with DuckDB
        con.register('raw_assets', assets_df)
        
        # Join assets with consolidated cache
        # We join on extracted_ticker = ticker_symbol
        query = """
            SELECT 
                r.*,
                c.company_name,
                c.sector,
                c.industry,
                c.market_cap,
                c.market_cap_category,
                c.exchange,
                c.is_publicly_traded as cache_is_publicly_traded,
                c.ticker_symbol as cache_ticker,
                c.ownership_indicator,
                c.cleaned_asset_name
            FROM raw_assets r
            LEFT JOIN stock_cache c ON r.extracted_ticker = c.ticker_symbol
        """
        joined_df = con.execute(query).df()
        logger.info(f"  Joined {len(joined_df):,} assets with consolidated cache")
    except Exception as e:
        logger.warning(f"  Vectorized cache join failed: {e}. Falling back to row-level lookups.")
        joined_df = assets_df
        joined_df['cache_ticker'] = None
        joined_df['company_name'] = None
        joined_df['sector'] = None
        joined_df['industry'] = None
        joined_df['market_cap'] = None
        joined_df['market_cap_category'] = None
        joined_df['exchange'] = None
        joined_df['cache_is_publicly_traded'] = None
        joined_df['ownership_indicator'] = None
        joined_df['cleaned_asset_name'] = None

    # 3. Identify Delta (Assets needing API/individual cache calls)
    # We only enrich if:
    # - Ticker was extracted BUT not found in the consolidated cache join
    # - OR its a stock/etf and we want to ensure fresh data (though for speed we trust cache)
    
    # We define 'needs_enrichment' as: has ticker but no cache info
    needs_enrichment = joined_df[
        (joined_df['extracted_ticker'].notna()) & (joined_df['cache_ticker'].isna())
    ].copy()

    if not needs_enrichment.empty:
        logger.info(f"  Step 3: Enriching Delta of {len(needs_enrichment):,} new/missing assets...")
        
        records_to_enrich = needs_enrichment.to_dict('records')
        enriched_results = {}

        def process_delta_record(idx, row):
            asset_name = row['asset_name']
            # Re-use the existing parallel logic
            enriched = stock_enricher.enrich_asset(asset_name)
            return asset_name, enriched

        # Parallel process only the delta
        with ThreadPoolExecutor(max_workers=50) as executor:
            future_to_name = {executor.submit(process_delta_record, i, r): r['asset_name'] for i, r in enumerate(records_to_enrich)}
            for future in as_completed(future_to_name):
                name, res = future.result()
                enriched_results[name] = res

        # Map results back to joined_df
        for name, res in enriched_results.items():
            mask = joined_df['asset_name'] == name
            joined_df.loc[mask, 'company_name'] = res.get('company_name')
            joined_df.loc[mask, 'sector'] = res.get('sector')
            joined_df.loc[mask, 'industry'] = res.get('industry')
            joined_df.loc[mask, 'market_cap_category'] = res.get('market_cap_category')
            joined_df.loc[mask, 'exchange'] = res.get('exchange')
            joined_df.loc[mask, 'is_publicly_traded'] = res.get('is_publicly_traded', False)
            joined_df.loc[mask, 'enrichment_status'] = res.get('enrichment_status')
            joined_df.loc[mask, 'ownership_indicator'] = res.get('ownership_indicator')
            joined_df.loc[mask, 'cleaned_asset_name'] = res.get('cleaned_asset_name')
    else:
        logger.info("  Step 3: No new assets found. Build is nearly instant!")

    # 4. Final Cleanup
    # Fill in missing values from cache where delta enrichment didn't apply
    joined_df['ticker_symbol'] = joined_df['extracted_ticker']
    joined_df['is_publicly_traded'] = joined_df['cache_is_publicly_traded'].fillna(False)
    joined_df['is_crypto'] = joined_df['asset_type'] == 'Cryptocurrency'
    joined_df['created_at'] = datetime.utcnow().isoformat()
    joined_df['updated_at'] = datetime.utcnow().isoformat()
    # Filling enrichment_status if retrieved from cache
    joined_df['enrichment_status'] = joined_df['enrichment_status'].fillna('success_from_cache')
    
    # For non-stock assets or those without extracted tickers, set default enrichment status
    joined_df.loc[joined_df['extracted_ticker'].isna(), 'enrichment_status'] = 'non_stock_asset'
    joined_df.loc[joined_df['asset_type'] == 'Cryptocurrency', 'enrichment_status'] = 'non_stock_asset'
    joined_df.loc[joined_df['asset_type'] == 'Other', 'enrichment_status'] = 'non_stock_asset'

    # Ensure cleaned_asset_name is populated
    joined_df['cleaned_asset_name'] = joined_df['cleaned_asset_name'].fillna(joined_df['asset_name'].str.strip())

    # Select and reorder columns to match the expected output schema
    final_columns = [
        'asset_name', 'cleaned_asset_name', 'ownership_indicator', 'ticker_symbol',
        'company_name', 'asset_type', 'sector', 'industry', 'market_cap_category',
        'is_publicly_traded', 'is_crypto', 'exchange', 'enrichment_status',
        'first_seen_date', 'last_seen_date', 'occurrence_count',
        'created_at', 'updated_at'
    ]
    
    # Add any missing columns with None if they weren't generated
    for col in final_columns:
        if col not in joined_df.columns:
            joined_df[col] = None

    return joined_df[final_columns]


def assign_asset_keys(df: pd.DataFrame) -> pd.DataFrame:
    """Assign surrogate keys to assets."""
    # Sort by occurrence (most common first), then alphabetically
    df = df.sort_values(['occurrence_count', 'asset_name'], ascending=[False, True]).reset_index(drop=True)
    df['asset_key'] = df.index + 1
    return df


def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write dim_assets to gold layer."""
    logger.info("Writing to gold layer...")

    # Save locally
    output_dir = Path('data/gold/dimensions/dim_assets')
    output_dir.mkdir(parents=True, exist_ok=True)

    # No partitioning for assets (relatively small table)
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(
        output_file,
        engine='pyarrow',
        compression='snappy',
        index=False
    )
    logger.info(f"  Wrote {len(df)} records -> {output_file}")

    # Also save CSV for reference
    csv_file = output_dir / 'dim_assets.csv'
    df.to_csv(csv_file, index=False)
    logger.info(f"  CSV: {csv_file}")

    # Upload to S3
    s3 = boto3.client('s3')

    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)

        s3_key = 'gold/house/financial/dimensions/dim_assets/part-0000.parquet'
        s3.upload_file(tmp.name, bucket_name, s3_key)
        logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")

        os.unlink(tmp.name)


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("Building dim_assets dimension table")
    logger.info("=" * 80)

    # Initialize enrichers
    stock_enricher = StockAPIEnricher(use_cache=True)

    # Load unique assets from silver layer
    assets_df = load_unique_assets_from_silver(bucket_name)

    # 2. Enrich with Vectorized approach (DuckDB Join + Delta Parallelism)
    enriched_df = enrich_assets(assets_df, stock_enricher, bucket_name)

    # Handle empty results
    if len(enriched_df) == 0:
        logger.warning("No assets found to process - skipping write to Gold layer")
        return

    # Assign surrogate keys
    final_df = assign_asset_keys(enriched_df)

    logger.info("\n" + "=" * 80)
    logger.info("FINAL ENRICHMENT SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total unique assets: {len(final_df):,}")
    logger.info(f"  With ticker symbol: {final_df['ticker_symbol'].notna().sum():,} ({final_df['ticker_symbol'].notna().sum() / len(final_df) * 100:.1f}%)")
    logger.info(f"  With sector info: {final_df['sector'].notna().sum():,} ({final_df['sector'].notna().sum() / len(final_df) * 100:.1f}%)")
    logger.info(f"  Publicly traded: {final_df['is_publicly_traded'].sum():,} ({final_df['is_publicly_traded'].sum() / len(final_df) * 100:.1f}%)")
    logger.info(f"  With ownership indicator: {final_df['ownership_indicator'].notna().sum():,}")

    logger.info(f"\nAsset type breakdown:")
    for asset_type, count in final_df['asset_type'].value_counts().items():
        logger.info(f"  {asset_type}: {count:,} ({count/len(final_df)*100:.1f}%)")

    logger.info(f"\nEnrichment status breakdown:")
    for status, count in final_df['enrichment_status'].value_counts().items():
        logger.info(f"  {status}: {count:,} ({count/len(final_df)*100:.1f}%)")

    logger.info(f"\nOwnership indicator breakdown:")
    ownership_counts = final_df['ownership_indicator'].value_counts()
    for indicator, count in ownership_counts.items():
        logger.info(f"  {indicator}: {count:,}")
    logger.info(f"  None/Unknown: {final_df['ownership_indicator'].isna().sum():,}")

    logger.info(f"\nTop 10 most common assets:")
    top_assets = final_df.nlargest(10, 'occurrence_count')[['cleaned_asset_name', 'ticker_symbol', 'asset_type', 'occurrence_count']]
    for idx, row in top_assets.iterrows():
        ticker_str = f"({row['ticker_symbol']})" if pd.notna(row['ticker_symbol']) else "(no ticker)"
        logger.info(f"  {row['cleaned_asset_name'][:50]} {ticker_str} - {row['asset_type']} - {row['occurrence_count']:,} occurrences")
    logger.info("=" * 80)

    # Write to gold layer
    write_to_gold(final_df, bucket_name)

    logger.info("\n✅ dim_assets build complete!")


if __name__ == '__main__':
    main()
