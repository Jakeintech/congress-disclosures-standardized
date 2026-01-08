"""
API Endpoint: GET /v1/analytics/filtered-transactions

Returns congressional transactions filtered by amount, crypto exposure, and committee correlation.

Query Parameters:
- days: Number of days to look back (default: 30)
- limit: Max results (default: 100, max: 1000)
- min_amount: Minimum transaction amount in USD (default: 50000)
- tier: Amount tier filter (tier_1_50k_plus, tier_2_100k_plus, etc.)
- crypto_only: Filter to crypto only (true/false, default: false)
- min_correlation: Minimum committee correlation score 0.0-1.0 (default: 0.0)
"""

import json
import boto3
import os
from datetime import datetime, timedelta

s3 = boto3.client('s3')

BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def lambda_handler(event, context):
    """API handler for high-value transactions."""

    # Parse query parameters
    params = event.get('queryStringParameters') or {}

    days = int(params.get('days', 30))
    limit = min(int(params.get('limit', 100)), 1000)  # Max 1000
    min_amount = int(params.get('min_amount', 50000))
    tier = params.get('tier')
    crypto_only = params.get('crypto_only', 'false').lower() == 'true'
    min_correlation = float(params.get('min_correlation', 0.0))

    try:
        # Read transaction filters aggregate from S3
        s3_key = "data/gold/aggregates/transaction_filters/transaction_filters.parquet"

        print(f"Fetching from s3://{BUCKET}/{s3_key}")
        obj = s3.get_object(Bucket=BUCKET, Key=s3_key)

        import pandas as pd
        import io

        df = pd.read_parquet(io.BytesIO(obj['Body'].read()))

        # Apply filters
        print(f"Loaded {len(df):,} transactions, applying filters...")

        # Filter by date
        if days > 0:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
            df = df[df['transaction_date'] >= cutoff_date]

        # Filter by amount
        df = df[df['amount_low'] >= min_amount]

        # Filter by tier if specified
        if tier:
            df = df[df['amount_tier'] == tier]

        # Filter crypto if requested
        if crypto_only:
            df = df[df['is_crypto'] == True]

        # Filter by committee correlation
        if min_correlation > 0:
            df = df[df['committee_correlation_score'] >= min_correlation]

        # Sort by relevance: recent, high correlation, high amount
        df = df.sort_values(
            ['is_within_7d', 'committee_correlation_score', 'amount_low'],
            ascending=[False, False, False]
        )

        # Limit results
        df = df.head(limit)

        print(f"Returning {len(df):,} transactions after filtering")

        # Convert to JSON-friendly format
        records = df.to_dict('records')

        # Format dates
        for record in records:
            for field in ['transaction_date', 'filing_date', 'computed_at']:
                if field in record and record[field]:
                    if isinstance(record[field], pd.Timestamp):
                        record[field] = record[field].isoformat()
                    else:
                        record[field] = str(record[field])

            # Convert numpy booleans to Python booleans
            for field in ['is_crypto', 'is_within_7d', 'is_within_14d', 'is_within_30d']:
                if field in record and record[field] is not None:
                    record[field] = bool(record[field])

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'data': records,
                'count': len(records),
                'filters': {
                    'days': days,
                    'min_amount': min_amount,
                    'tier': tier,
                    'crypto_only': crypto_only,
                    'min_correlation': min_correlation
                },
                'metadata': {
                    'generated_at': datetime.utcnow().isoformat(),
                    'source': f's3://{BUCKET}/{s3_key}'
                }
            })
        }

    except s3.exceptions.NoSuchKey:
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Transaction filters data not yet available',
                'message': 'Run compute_agg_transaction_filters.py to generate data'
            })
        }
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
