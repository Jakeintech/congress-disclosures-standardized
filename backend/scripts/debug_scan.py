import boto3
import os

table = boto3.resource("dynamodb", region_name="us-east-1").Table("house_fd_documents")

documents = []
scan_kwargs = {}
done = False

print("Scanning...")
while not done:
    response = table.scan(**scan_kwargs)
    items = response.get('Items', [])
    documents.extend(items)
    print(f"Got {len(items)} items. Total: {len(documents)}")
    
    start_key = response.get('LastEvaluatedKey')
    if start_key:
        scan_kwargs['ExclusiveStartKey'] = start_key
    else:
        done = True

print(f"Total documents: {len(documents)}")

found = False
for doc in documents:
    if doc['doc_id'] == "10063228":
        print("FOUND 10063228!")
        print(doc)
        found = True
        break

if not found:
    print("10063228 NOT FOUND in scan results.")
