import boto3
import json

client = boto3.client('lambda')
for year in [2024, 2025]:
    print(f"Invoking for year {year}...")
    try:
        response = client.invoke(
            FunctionName='congress-disclosures-development-index-to-silver',
            Payload=json.dumps({'year': year})
        )
        print(f"Invoked for {year}: Status {response['StatusCode']}")
        payload = response['Payload'].read().decode('utf-8')
        print(f"Response: {payload[:200]}...")
    except Exception as e:
        print(f"Error invoking for {year}: {e}")
