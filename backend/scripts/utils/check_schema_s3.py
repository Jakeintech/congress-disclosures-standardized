
import boto3
import duckdb
import os
import sys

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def check_schema():
    print(f"Checking schema in bucket: {S3_BUCKET}")
    
    conn = duckdb.connect(database=':memory:')
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    
    session = boto3.Session()
    creds = session.get_credentials().get_frozen_credentials()
    conn.execute(f"SET s3_access_key_id='{creds.access_key}';")
    conn.execute(f"SET s3_secret_access_key='{creds.secret_key}';")
    if creds.token:
        conn.execute(f"SET s3_session_token='{creds.token}';")
    conn.execute("SET s3_region='us-east-1';")
    
    path = f"s3://{S3_BUCKET}/gold/house/financial/facts/fact_ptr_transactions/part-0000.parquet"
    print(f"Reading: {path}")
    
    try:
        # Just grab one file to check schema
        # We need to list files first to be sure one exists at that path pattern
        # But let's try reading with glob if possible or list first
        
        s3 = boto3.client('s3')
        # List one object in the prefix
        resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix='gold/house/financial/facts/fact_ptr_transactions/', MaxKeys=1)
        if 'Contents' not in resp:
            print("No files found in prefix")
            return
            
        key = resp['Contents'][0]['Key']
        full_path = f"s3://{S3_BUCKET}/{key}"
        print(f"Inspecting file: {full_path}")
        
        rel = conn.execute(f"DESCRIBE SELECT * FROM read_parquet('{full_path}')").fetchall()
        print("\nSchema:")
        for col in rel:
            print(f"  {col[0]}: {col[1]}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
