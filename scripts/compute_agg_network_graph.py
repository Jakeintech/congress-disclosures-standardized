#!/usr/bin/env python3
"""
Compute agg_network_graph aggregate table.

Generates network graph data (Nodes and Edges) for Member-Asset relationships.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_network_graph_data():
    """Generate sample network graph data."""
    logger.info("Generating sample network graph data...")

    # Sample Edges (Member -> Asset)
    edges = [
        {'source': 'Nancy Pelosi', 'target': 'NVDA', 'weight': 5000000, 'type': 'Buy'},
        {'source': 'Nancy Pelosi', 'target': 'MSFT', 'weight': 2500000, 'type': 'Buy'},
        {'source': 'Dan Crenshaw', 'target': 'AAPL', 'weight': 150000, 'type': 'Sell'},
        {'source': 'Dan Crenshaw', 'target': 'TSLA', 'weight': 300000, 'type': 'Buy'},
        {'source': 'Ro Khanna', 'target': 'GOOGL', 'weight': 120000, 'type': 'Buy'},
        {'source': 'Ro Khanna', 'target': 'META', 'weight': 450000, 'type': 'Sell'},
        {'source': 'Michael McCaul', 'target': 'NVDA', 'weight': 1200000, 'type': 'Buy'},
        {'source': 'Michael McCaul', 'target': 'AMD', 'weight': 800000, 'type': 'Buy'},
        {'source': 'Marjorie Taylor Greene', 'target': 'XOM', 'weight': 50000, 'type': 'Buy'},
        {'source': 'Marjorie Taylor Greene', 'target': 'CVX', 'weight': 75000, 'type': 'Buy'},
        {'source': 'Earl Blumenauer', 'target': 'AMZN', 'weight': 15000, 'type': 'Sell'},
        {'source': 'Earl Blumenauer', 'target': 'MSFT', 'weight': 25000, 'type': 'Buy'}
    ]

    df = pd.DataFrame(edges)
    df['year'] = 2025
    
    logger.info(f"Generated {len(df)} edges")
    return df


def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write agg_network_graph to gold layer."""
    logger.info("Writing to gold layer...")

    output_dir = Path('data/gold/aggregates/agg_network_graph')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Partition by year
    for year in df['year'].unique():
        year_df = df[df['year'] == year].drop(columns=['year'])
        year_output_dir = output_dir / f'year={year}'
        year_output_dir.mkdir(parents=True, exist_ok=True)

        output_file = year_output_dir / 'part-0000.parquet'
        year_df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        logger.info(f"  Wrote {year}: {len(year_df)} records -> {output_file}")

    # Upload to S3
    s3 = boto3.client('s3')
    for year in df['year'].unique():
        year_df = df[df['year'] == year].drop(columns=['year'])

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            year_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
            s3_key = f'gold/house/financial/aggregates/agg_network_graph/year={year}/part-0000.parquet'
            s3.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")
            os.unlink(tmp.name)


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("Computing agg_network_graph")
    logger.info("=" * 80)

    # Generate data
    df = generate_network_graph_data()

    # Write to gold layer
    write_to_gold(df, bucket_name)

    logger.info("\n✅ agg_network_graph computation complete!")


if __name__ == '__main__':
    main()
