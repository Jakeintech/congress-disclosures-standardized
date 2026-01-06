import boto3
import pandas as pd
import os

def find_filing_types_in_silver_parquet(bucket, prefix, target_types):
    s3 = boto3.client('s3')
    
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        
        found = {t: [] for t in target_types}
        
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if not key.endswith('.parquet'):
                    continue
                    
                print(f"Checking {key}...")
                # Download parquet file
                local_filename = f"temp_{os.path.basename(key)}"
                s3.download_file(bucket, key, local_filename)
                
                try:
                    df = pd.read_parquet(local_filename)
                    
                    # Filter for target types
                    for f_type in target_types:
                        matches = df[df['filing_type'] == f_type]
                        if not matches.empty:
                            print(f"Found {len(matches)} matches for Type {f_type}")
                            for idx, row in matches.iterrows():
                                pdf_key = row['pdf_s3_key']
                                # Check if it has text layer via HeadObject
                                try:
                                    head = s3.head_object(Bucket=bucket, Key=pdf_key)
                                    meta = head.get('Metadata', {})
                                    if meta.get('has_text_layer') == 'true':
                                        print(f"Sample PDF Key (Text Layer): {pdf_key}")
                                        found[f_type].append(pdf_key)
                                        if len(found[f_type]) >= 1: # Just need one good one
                                            break
                                except:
                                    pass
                except Exception as e:
                    print(f"Error reading parquet {key}: {e}")
                finally:
                    if os.path.exists(local_filename):
                        os.remove(local_filename)
                
                if all(len(l) > 0 for l in found.values()):
                    return found
                        
        return found
            
    except Exception as e:
        print(f"Error listing objects: {e}")

if __name__ == "__main__":
    bucket = "congress-disclosures-standardized"
    prefix = "silver/house/financial/filings/year=2024/"
    find_filing_types_in_silver_parquet(bucket, prefix, ["G"])
