
import boto3
import duckdb
import os
import sys

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def check_valid_bioguides():
    print(f"Checking for valid bioguide_ids in House dim_members")
    
    conn = duckdb.connect(database=':memory:')
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    session = boto3.Session()
    creds = session.get_credentials().get_frozen_credentials()
    conn.execute(f"SET s3_access_key_id='{creds.access_key}';")
    conn.execute(f"SET s3_secret_access_key='{creds.secret_key}';")
    if creds.token:
        conn.execute(f"SET s3_session_token='{creds.token}';")
    conn.execute("SET s3_region='us-east-1';")
    
    path = f"s3://{S3_BUCKET}/gold/house/financial/dimensions/dim_members/year=2025/part-0000.parquet"
    
    try:
        # Count non-null bioguide_ids
        query = f"SELECT COUNT(*) as count, COUNT(bioguide_id) as non_null_count FROM read_parquet('{path}')"
        res = conn.execute(query).fetchall()
        print(f"Total Rows: {res[0][0]}")
        print(f"Non-Null Bioguide IDs: {res[0][1]}")
        
        # Show a few valid ones if they exist
        if res[0][1] > 0:
            query = f"SELECT bioguide_id, full_name, member_key FROM read_parquet('{path}') WHERE bioguide_id IS NOT NULL LIMIT 5"
            res = conn.execute(query).fetchall()
            print("\nSample Valid Bioguide IDs:")
            for row in res:
                print(row)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_valid_bioguides()
