import json
import logging
import os
import boto3
from urllib.parse import unquote_plus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

# Layer prefix mapping
LAYER_PREFIXES = {
    'bronze': 'bronze/',
    'silver': 'silver/',
    'gold': 'gold/'
}

def handler(event, context):
    """
    List S3 objects in a specific layer (bronze/silver/gold).
    Supports folder navigation and pagination.
    """
    try:
        # Extract parameters
        path_params = event.get('pathParameters', {})
        query_params = event.get('queryStringParameters') or {}
        
        layer = path_params.get('layer', '').lower()
        prefix = query_params.get('prefix', '')
        max_keys = int(query_params.get('maxKeys', '1000'))
        continuation_token = query_params.get('continuationToken')
        
        # Validate layer
        if layer not in LAYER_PREFIXES:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Invalid layer. Must be one of: {list(LAYER_PREFIXES.keys())}'})
            }
        
        # Build full S3 prefix
        base_prefix = LAYER_PREFIXES[layer]
        if prefix:
            # URL decode and normalize prefix
            prefix = unquote_plus(prefix)
            if not prefix.endswith('/'):
                prefix += '/'
            full_prefix = base_prefix + prefix
        else:
            full_prefix = base_prefix
        
        bucket = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
        
        logger.info(f"Listing objects in {bucket}/{full_prefix}")
        
        # List objects with delimiter for folder structure
        list_params = {
            'Bucket': bucket,
            'Prefix': full_prefix,
            'Delimiter': '/',
            'MaxKeys': max_keys
        }
        
        if continuation_token:
            list_params['ContinuationToken'] = continuation_token
        
        response = s3_client.list_objects_v2(**list_params)
        
        # Process folders (common prefixes)
        folders = []
        for cp in response.get('CommonPrefixes', []):
            folder_key = cp['Prefix']
            folder_name = folder_key[len(full_prefix):].rstrip('/')
            folders.append({
                'name': folder_name,
                'type': 'folder',
                'key': folder_key,
                'path': folder_key[len(base_prefix):]
            })
        
        # Process files
        files = []
        for obj in response.get('Contents', []):
            # Skip the prefix itself
            if obj['Key'] == full_prefix:
                continue
            
            file_key = obj['Key']
            file_name = file_key[len(full_prefix):]
            
            files.append({
                'name': file_name,
                'type': 'file',
                'key': file_key,
                'size': obj['Size'],
                'lastModified': obj['LastModified'].isoformat(),
                'url': f"https://{bucket}.s3.amazonaws.com/{file_key}"
            })
        
        # Build response
        result = {
            'layer': layer,
            'prefix': prefix,
            'bucket': bucket,
            'folders': sorted(folders, key=lambda x: x['name']),
            'files': sorted(files, key=lambda x: x['name']),
            'truncated': response.get('IsTruncated', False),
            'keyCount': response.get('KeyCount', 0)
        }
        
        if response.get('NextContinuationToken'):
            result['nextContinuationToken'] = response['NextContinuationToken']
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Failed to list S3 objects: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
