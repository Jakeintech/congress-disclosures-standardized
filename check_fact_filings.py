
import boto3
import duckdb
import os
import sys

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def check_fact_filings():
    print(f"Checking fact_filings schema in bucket: {S3_BUCKET}")
    
    conn = duckdb.connect(database=':memory:')
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    session = boto3.Session()
    creds = session.get_credentials().get_frozen_credentials()
    conn.execute(f"SET s3_access_key_id='{creds.access_key}';")
    conn.execute(f"SET s3_secret_access_key='{creds.secret_key}';")
    if creds.token:
        conn.execute(f"SET s3_session_token='{creds.token}';")
    conn.execute("SET s3_region='us-east-1';")
    
    # Try year=2025 or look for any file
    path = f"s3://{S3_BUCKET}/gold/house/financial/facts/fact_filings/year=2025/part-0000.parquet"
    print(f"Reading: {path}")
    
    try:
        rel = conn.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
        print("\nSchema:")
        for col in rel:
            print(f"  {col[0]}: {col[1]}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_fact_filings()
