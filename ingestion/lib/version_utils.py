"""Version management utilities for extraction versioning.

Provides version comparison, registry management, and quality metrics tracking.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def compare_versions(version1: str, version2: str) -> int:
    """Compare two semantic versions.
    
    Args:
        version1: First version string (e.g., "1.1.0")
        version2: Second version string (e.g., "1.0.0")
        
    Returns:
        1 if version1 > version2
        0 if version1 == version2
        -1 if version1 < version2
    """
    try:
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        # Pad with zeros if needed
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for i in range(max_len):
            if v1_parts[i] > v2_parts[i]:
                return 1
            elif v1_parts[i] < v2_parts[i]:
                return -1
        
        return 0
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid version format: {version1} or {version2}: {e}")
        raise ValueError(f"Invalid semantic version: {version1} or {version2}")


def is_newer_version(version: str, baseline: str) -> bool:
    """Check if version is newer than baseline.
    
    Args:
        version: Version to check
        baseline: Baseline version to compare against
        
    Returns:
        True if version > baseline
    """
    return compare_versions(version, baseline) > 0


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse semantic version string into components.
    
    Args:
        version: Version string (e.g., "1.2.3")
        
    Returns:
        Tuple of (major, minor, patch)
    """
    try:
        parts = version.split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except (ValueError, IndexError) as e:
        logger.error(f"Failed to parse version {version}: {e}")
        raise ValueError(f"Invalid semantic version: {version}")


class ExtractionVersionRegistry:
    """Manages extraction version metadata in DynamoDB."""
    
    def __init__(self, table_name: str, dynamodb_client=None):
        """Initialize registry.
        
        Args:
            table_name: DynamoDB table name
            dynamodb_client: Optional boto3 DynamoDB client
        """
        self.table_name = table_name
        self.dynamodb = dynamodb_client or boto3.client('dynamodb')
        
    def register_version(
        self,
        extractor_class: str,
        extractor_version: str,
        deployment_date: Optional[str] = None,
        quality_metrics: Optional[Dict[str, Any]] = None,
        changelog: Optional[str] = None,
        is_production: bool = False
    ) -> None:
        """Register a new extractor version.
        
        Args:
            extractor_class: Extractor class name (e.g., "PTRExtractor")
            extractor_version: Version string (e.g., "1.1.0")
            deployment_date: ISO timestamp of deployment
            quality_metrics: Quality metrics dict
            changelog: Description of changes
            is_production: Whether this is the production version
        """
        deployment_date = deployment_date or datetime.utcnow().isoformat() + "Z"
        
        item = {
            'extractor_class': {'S': extractor_class},
            'extractor_version': {'S': extractor_version},
            'deployment_date': {'S': deployment_date},
            'is_production': {'BOOL': is_production},
            'updated_at': {'S': datetime.utcnow().isoformat() + "Z"}
        }
        
        if changelog:
            item['changelog'] = {'S': changelog}
            
        if quality_metrics:
            # Store as JSON string
            import json
            item['quality_metrics'] = {'S': json.dumps(quality_metrics)}
        
        try:
            self.dynamodb.put_item(
                TableName=self.table_name,
                Item=item
            )
            logger.info(f"Registered version {extractor_class} v{extractor_version}")
        except ClientError as e:
            logger.error(f"Failed to register version: {e}")
            raise
    
    def get_version(self, extractor_class: str, extractor_version: str) -> Optional[Dict[str, Any]]:
        """Get version metadata.
        
        Args:
            extractor_class: Extractor class name
            extractor_version: Version string
            
        Returns:
            Version metadata dict or None if not found
        """
        try:
            response = self.dynamodb.get_item(
                TableName=self.table_name,
                Key={
                    'extractor_class': {'S': extractor_class},
                    'extractor_version': {'S': extractor_version}
                }
            )
            
            if 'Item' not in response:
                return None
            
            return self._deserialize_item(response['Item'])
        except ClientError as e:
            logger.error(f"Failed to get version: {e}")
            return None
    
    def get_production_version(self, extractor_class: str) -> Optional[Dict[str, Any]]:
        """Get current production version for extractor class.
        
        Args:
            extractor_class: Extractor class name
            
        Returns:
            Production version metadata or None
        """
        try:
            # Query for production versions of this extractor
            response = self.dynamodb.query(
                TableName=self.table_name,
                KeyConditionExpression='extractor_class = :class',
                FilterExpression='is_production = :true',
                ExpressionAttributeValues={
                    ':class': {'S': extractor_class},
                    ':true': {'BOOL': True}
                },
                Limit=1
            )
            
            if not response.get('Items'):
                return None
            
            return self._deserialize_item(response['Items'][0])
        except ClientError as e:
            logger.error(f"Failed to get production version: {e}")
            return None
    
    def list_versions(self, extractor_class: str) -> List[Dict[str, Any]]:
        """List all versions for an extractor class.
        
        Args:
            extractor_class: Extractor class name
            
        Returns:
            List of version metadata dicts, sorted by version (newest first)
        """
        try:
            response = self.dynamodb.query(
                TableName=self.table_name,
                KeyConditionExpression='extractor_class = :class',
                ExpressionAttributeValues={
                    ':class': {'S': extractor_class}
                }
            )
            
            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            
            # Sort by version (newest first)
            items.sort(key=lambda x: parse_version(x['extractor_version']), reverse=True)
            
            return items
        except ClientError as e:
            logger.error(f"Failed to list versions: {e}")
            return []
    
    def promote_to_production(self, extractor_class: str, extractor_version: str) -> None:
        """Promote version to production.
        
        Args:
            extractor_class: Extractor class name
            extractor_version: Version to promote
        """
        # First, demote current production version
        current_production = self.get_production_version(extractor_class)
        if current_production:
            try:
                self.dynamodb.update_item(
                    TableName=self.table_name,
                    Key={
                        'extractor_class': {'S': extractor_class},
                        'extractor_version': {'S': current_production['extractor_version']}
                    },
                    UpdateExpression='SET is_production = :false, updated_at = :now',
                    ExpressionAttributeValues={
                        ':false': {'BOOL': False},
                        ':now': {'S': datetime.utcnow().isoformat() + "Z"}
                    }
                )
                logger.info(f"Demoted {extractor_class} v{current_production['extractor_version']} from production")
            except ClientError as e:
                logger.error(f"Failed to demote current production: {e}")
                raise
        
        # Promote new version
        try:
            self.dynamodb.update_item(
                TableName=self.table_name,
                Key={
                    'extractor_class': {'S': extractor_class},
                    'extractor_version': {'S': extractor_version}
                },
                UpdateExpression='SET is_production = :true, updated_at = :now',
                ExpressionAttributeValues={
                    ':true': {'BOOL': True},
                    ':now': {'S': datetime.utcnow().isoformat() + "Z"}
                }
            )
            logger.info(f"Promoted {extractor_class} v{extractor_version} to production")
        except ClientError as e:
            logger.error(f"Failed to promote version: {e}")
            raise
    
    def rollback_version(self, extractor_class: str, target_version: str) -> None:
        """Rollback to a previous version.
        
        Args:
            extractor_class: Extractor class name
            target_version: Version to rollback to
        """
        logger.info(f"Rolling back {extractor_class} to version {target_version}")
        self.promote_to_production(extractor_class, target_version)
    
    def _deserialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize DynamoDB item to Python dict.
        
        Args:
            item: DynamoDB item with type descriptors
            
        Returns:
            Plain Python dict
        """
        import json
        
        result = {}
        for key, value in item.items():
            if 'S' in value:
                result[key] = value['S']
                # Try to parse JSON strings
                if key == 'quality_metrics':
                    try:
                        result[key] = json.loads(value['S'])
                    except (json.JSONDecodeError, TypeError):
                        pass
            elif 'N' in value:
                result[key] = float(value['N'])
            elif 'BOOL' in value:
                result[key] = value['BOOL']
            elif 'M' in value:
                result[key] = self._deserialize_item(value['M'])
            elif 'L' in value:
                result[key] = [self._deserialize_value(v) for v in value['L']]
        
        return result
    
    def _deserialize_value(self, value: Dict[str, Any]) -> Any:
        """Deserialize a single DynamoDB value."""
        if 'S' in value:
            return value['S']
        elif 'N' in value:
            return float(value['N'])
        elif 'BOOL' in value:
            return value['BOOL']
        elif 'M' in value:
            return self._deserialize_item(value['M'])
        elif 'L' in value:
            return [self._deserialize_value(v) for v in value['L']]
        return None
