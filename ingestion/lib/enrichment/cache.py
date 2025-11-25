"""
Enrichment cache for storing API results in S3.

This reduces API calls and stays within rate limits by caching enrichment results.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError


class EnrichmentCache:
    """Cache for enrichment API results stored in S3."""

    def __init__(self, bucket_name: str = None, ttl_hours: int = 168):
        """
        Initialize enrichment cache.

        Args:
            bucket_name: S3 bucket name (defaults to S3_BUCKET_NAME env var)
            ttl_hours: Cache TTL in hours (default 168 = 1 week)
        """
        self.bucket_name = bucket_name or os.environ.get(
            'S3_BUCKET_NAME',
            'congress-disclosures-standardized'
        )
        self.ttl_hours = ttl_hours
        self.s3 = boto3.client('s3')

    def _get_cache_key(self, cache_type: str, identifier: str) -> str:
        """Generate S3 cache key."""
        # Sanitize identifier for S3 key
        safe_id = identifier.replace('/', '_').replace(' ', '_')
        return f'gold/house/financial/cache/{cache_type}/{safe_id}.json'

    def get(self, cache_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Get cached value.

        Args:
            cache_type: Type of cache (congress_api, stock_api, crypto_api)
            identifier: Unique identifier (bioguide_id, ticker, etc.)

        Returns:
            Cached data if found and not expired, None otherwise
        """
        cache_key = self._get_cache_key(cache_type, identifier)

        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=cache_key)
            data = json.loads(response['Body'].read().decode('utf-8'))

            # Check if cache is expired
            cached_at = datetime.fromisoformat(data.get('cached_at'))
            if datetime.utcnow() - cached_at > timedelta(hours=self.ttl_hours):
                return None  # Expired

            return data.get('data')

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None  # Not cached
            raise

    def set(self, cache_type: str, identifier: str, data: Dict[str, Any]):
        """
        Set cached value.

        Args:
            cache_type: Type of cache
            identifier: Unique identifier
            data: Data to cache
        """
        cache_key = self._get_cache_key(cache_type, identifier)

        cache_entry = {
            'cached_at': datetime.utcnow().isoformat(),
            'cache_type': cache_type,
            'identifier': identifier,
            'data': data
        }

        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=cache_key,
            Body=json.dumps(cache_entry, indent=2),
            ContentType='application/json'
        )

    def invalidate(self, cache_type: str, identifier: str):
        """Delete cached value."""
        cache_key = self._get_cache_key(cache_type, identifier)

        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=cache_key)
        except ClientError:
            pass  # Ignore if doesn't exist
