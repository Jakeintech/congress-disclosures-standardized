"""
API Endpoint: GET /v1/analytics/crypto-transactions

Returns cryptocurrency transaction activity and monthly aggregates.

Query Parameters:
- data_type: "transactions" or "aggregates" (default: "aggregates")
- category: Filter by crypto category (bitcoin, ethereum, crypto_exchanges, blockchain_funds, all_crypto)
- months: Number of months to return for aggregates (default: 12)
- limit: Max results for transaction data (default: 100, max: 1000)
"""

import json
import boto3
import os
from datetime import datetime

s3 = boto3.client('s3')

BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def lambda_handler(event, context):
    """API handler for crypto transactions."""

    # Parse query parameters
    params = event.get('queryStringParameters') or {}

    data_type = params.get('data_type', 'aggregates')
    category = params.get('category', 'all_crypto')
    months = int(params.get('months', 12))
    limit = min(int(params.get('limit', 100)), 1000)

    try:
        if data_type == 'aggregates':
            # Return monthly aggregates
            s3_key = "data/gold/aggregates/crypto_transactions/monthly_aggregates.parquet"

            print(f"Fetching aggregates from s3://{BUCKET}/{s3_key}")
            obj = s3.get_object(Bucket=BUCKET, Key=s3_key)

            import pandas as pd
            import io

            df = pd.read_parquet(io.BytesIO(obj['Body'].read()))

            # Filter by category
            if category and category != 'all':
                df = df[df['crypto_category'] == category]

            # Sort and limit
            df = df.sort_values(['year', 'month'], ascending=[False, False])
            df = df.head(months)

            # Convert to JSON
            records = df.to_dict('records')

            for record in records:
                if 'computed_at' in record and record['computed_at']:
                    record['computed_at'] = str(record['computed_at'])

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
                    'data_type': 'aggregates',
                    'category': category,
                    'metadata': {
                        'generated_at': datetime.utcnow().isoformat(),
                        'source': f's3://{BUCKET}/{s3_key}'
                    }
                })
            }

        else:  # data_type == 'transactions'
            # Return transaction-level data
            s3_key = "data/gold/aggregates/crypto_transactions/crypto_transactions.parquet"

            print(f"Fetching transactions from s3://{BUCKET}/{s3_key}")
            obj = s3.get_object(Bucket=BUCKET, Key=s3_key)

            import pandas as pd
            import io

            df = pd.read_parquet(io.BytesIO(obj['Body'].read()))

            # Filter by category
            if category and category != 'all_crypto':
                df = df[df['crypto_category'] == category]

            # Sort by date (most recent first)
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
            df = df.sort_values('transaction_date', ascending=False)

            # Limit
            df = df.head(limit)

            # Convert to JSON
            records = df.to_dict('records')

            for record in records:
                for field in ['transaction_date', 'filing_date', 'computed_at']:
                    if field in record and record[field]:
                        if isinstance(record[field], pd.Timestamp):
                            record[field] = record[field].isoformat()
                        else:
                            record[field] = str(record[field])

                # Convert numpy booleans
                for field in ['is_bitcoin', 'is_ethereum', 'is_crypto_exchanges', 'is_blockchain_funds']:
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
                    'data_type': 'transactions',
                    'category': category,
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
                'error': 'Crypto transactions data not yet available',
                'message': 'Run compute_agg_crypto_transactions.py to generate data'
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
