
import sys
import os
import boto3

# Add current directory to path
sys.path.append(os.getcwd())

# Mock environment if needed, or rely on .env if loaded.
# The project seems to use specific lib. checking api/lib imports.
# It uses ParquetQueryBuilder from api.lib.

try:
    from api.lib import ParquetQueryBuilder
except ImportError:
    print("ImportError: Can't import api.lib. Make sure to run from project root.")
    sys.exit(1)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def check_bill():
    print(f"Checking bucket: {S3_BUCKET}")
    qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
    
    # 119-sconres-23
    filters = {
        'congress': 119,
        'bill_type': 'sconres',
        'bill_number': 23
    }
    
    print(f"Querying gold/congress/dim_bill with filters: {filters}")
    
    try:
        # Check if bucket/key exists first to avoid vague parquet errors
        s3 = boto3.client('s3')
        # Just check prefix
        # resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix='gold/congress/dim_bill', MaxKeys=1)
        # if 'Contents' not in resp:
        #     print("Prefix gold/congress/dim_bill not found in S3.")
        #     return

        df = qb.query_parquet('gold/congress/dim_bill', filters=filters, limit=1)
        if df.empty:
            print("Result: Bill NOT found in Gold layer.")
        else:
            print("Result: Bill FOUND in Gold layer.")
            print(df.iloc[0].to_dict())
            
    except Exception as e:
        print(f"Error querying parquet: {e}")

if __name__ == "__main__":
    check_bill()
