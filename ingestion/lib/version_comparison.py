"""Quality comparison utilities for extraction versioning.

Compares extraction quality metrics between versions to detect improvements/regressions.
"""

import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class QualityMetricsCalculator:
    """Calculate quality metrics from extraction results."""
    
    def __init__(self):
        """Initialize calculator."""
        pass
    
    def calculate_metrics(self, extraction_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aggregate quality metrics from extraction results.
        
        Args:
            extraction_results: List of extraction result dicts
            
        Returns:
            Aggregated quality metrics
        """
        if not extraction_results:
            return {
                'sample_size': 0,
                'avg_confidence_score': 0.0,
                'field_confidence': {},
                'extraction_success_rate': 0.0
            }
        
        # Collect metrics
        confidence_scores = []
        field_confidences = defaultdict(list)
        successful_extractions = 0
        
        for result in extraction_results:
            if result.get('status') == 'success':
                successful_extractions += 1
                
                # Overall confidence
                metadata = result.get('extraction_metadata', {})
                if 'confidence_score' in metadata:
                    confidence_scores.append(metadata['confidence_score'])
                
                # Field-level confidence
                if 'field_confidence' in metadata:
                    for field, score in metadata['field_confidence'].items():
                        field_confidences[field].append(score)
        
        # Calculate aggregates
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        field_avg_confidence = {}
        for field, scores in field_confidences.items():
            field_avg_confidence[field] = sum(scores) / len(scores) if scores else 0.0
        
        success_rate = successful_extractions / len(extraction_results) if extraction_results else 0.0
        
        return {
            'sample_size': len(extraction_results),
            'avg_confidence_score': round(avg_confidence, 4),
            'field_confidence': field_avg_confidence,
            'extraction_success_rate': round(success_rate, 4),
            'successful_extractions': successful_extractions,
            'failed_extractions': len(extraction_results) - successful_extractions
        }
    
    def calculate_from_s3_extractions(
        self,
        s3_client,
        bucket: str,
        prefix: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Calculate metrics from existing S3 extractions.
        
        Args:
            s3_client: Boto3 S3 client
            bucket: S3 bucket name
            prefix: S3 prefix to scan for extraction JSONs
            limit: Maximum number of files to process
            
        Returns:
            Aggregated quality metrics
        """
        import json
        
        extraction_results = []
        
        # List objects in prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
        
        count = 0
        for page in page_iterator:
            for obj in page.get('Contents', []):
                if limit and count >= limit:
                    break
                
                key = obj['Key']
                if not key.endswith('.json'):
                    continue
                
                try:
                    # Download and parse extraction JSON
                    response = s3_client.get_object(Bucket=bucket, Key=key)
                    content = response['Body'].read().decode('utf-8')
                    extraction = json.loads(content)
                    
                    # Create result record
                    result = {
                        'status': 'success',
                        'extraction_metadata': extraction.get('extraction_metadata', {})
                    }
                    
                    extraction_results.append(result)
                    count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process {key}: {e}")
                    extraction_results.append({
                        'status': 'failed',
                        'error': str(e)
                    })
            
            if limit and count >= limit:
                break
        
        logger.info(f"Processed {len(extraction_results)} extractions from {prefix}")
        return self.calculate_metrics(extraction_results)


class VersionComparison:
    """Compare quality metrics between extraction versions."""
    
    def __init__(self, baseline_metrics: Dict[str, Any], new_metrics: Dict[str, Any]):
        """Initialize comparison.
        
        Args:
            baseline_metrics: Metrics from baseline version
            new_metrics: Metrics from new version
        """
        self.baseline = baseline_metrics
        self.new = new_metrics
    
    def generate_report(
        self,
        baseline_version: str,
        new_version: str
    ) -> Dict[str, Any]:
        """Generate comprehensive comparison report.
        
        Args:
            baseline_version: Baseline version string
            new_version: New version string
            
        Returns:
            Comparison report dict
        """
        improvements = {}
        regressions = []
        
        # Compare overall confidence score
        if 'avg_confidence_score' in self.baseline and 'avg_confidence_score' in self.new:
            old_val = self.baseline['avg_confidence_score']
            new_val = self.new['avg_confidence_score']
            delta = new_val - old_val
            delta_pct = (delta / old_val * 100) if old_val > 0 else 0
            
            improvements['avg_confidence_score'] = {
                'old': round(old_val, 4),
                'new': round(new_val, 4),
                'delta': f"{delta_pct:+.1f}%"
            }
            
            if delta < -0.01:  # More than 1% worse
                regressions.append({
                    'field': 'avg_confidence_score',
                    'old': old_val,
                    'new': new_val,
                    'delta': f"{delta_pct:.1f}%"
                })
        
        # Compare field-level confidence
        baseline_fields = self.baseline.get('field_confidence', {})
        new_fields = self.new.get('field_confidence', {})
        
        all_fields = set(baseline_fields.keys()) | set(new_fields.keys())
        
        for field in all_fields:
            old_val = baseline_fields.get(field, 0.0)
            new_val = new_fields.get(field, 0.0)
            
            delta = new_val - old_val
            delta_pct = (delta / old_val * 100) if old_val > 0 else 0
            
            improvements[field] = {
                'old': round(old_val, 4),
                'new': round(new_val, 4),
                'delta': f"{delta_pct:+.1f}%"
            }
            
            # Flag regressions (> 1% worse)
            if delta < -0.01:
                regressions.append({
                    'field': field,
                    'old': old_val,
                    'new': new_val,
                    'delta': f"{delta_pct:.1f}%"
                })
        
        # Compare success rates
        old_success = self.baseline.get('extraction_success_rate', 0.0)
        new_success = self.new.get('extraction_success_rate', 0.0)
        success_delta = new_success - old_success
        success_delta_pct = (success_delta / old_success * 100) if old_success > 0 else 0
        
        improvements['extraction_success_rate'] = {
            'old': round(old_success, 4),
            'new': round(new_success, 4),
            'delta': f"{success_delta_pct:+.1f}%"
        }
        
        if success_delta < -0.01:
            regressions.append({
                'field': 'extraction_success_rate',
                'old': old_success,
                'new': new_success,
                'delta': f"{success_delta_pct:.1f}%"
            })
        
        # Count new extractions (successful in new version but not in baseline)
        new_extractions = self.new.get('successful_extractions', 0) - self.baseline.get('successful_extractions', 0)
        
        # Overall recommendation
        has_significant_improvements = any(
            float(imp['delta'].rstrip('%')) > 2.0
            for imp in improvements.values()
            if isinstance(imp, dict) and 'delta' in imp
        )
        
        has_regressions = len(regressions) > 0
        
        if has_regressions:
            recommendation = "REVIEW_REQUIRED"
            recommendation_reason = f"Quality regressions detected in {len(regressions)} fields"
        elif has_significant_improvements:
            recommendation = "PROMOTE"
            recommendation_reason = "Significant quality improvements without regressions"
        elif new_extractions > 0:
            recommendation = "PROMOTE"
            recommendation_reason = f"{new_extractions} additional successful extractions"
        else:
            recommendation = "NEUTRAL"
            recommendation_reason = "No significant changes detected"
        
        return {
            'baseline_version': baseline_version,
            'new_version': new_version,
            'quality_improvements': improvements,
            'regressions': regressions,
            'new_extractions': max(0, new_extractions),
            'overall_improvement': improvements.get('avg_confidence_score', {}).get('delta', 'N/A'),
            'recommendation': recommendation,
            'recommendation_reason': recommendation_reason,
            'comparison_timestamp': self._get_timestamp()
        }
    
    def _get_timestamp(self) -> str:
        """Get current UTC timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def generate_comparison_report(
    baseline_metrics: Dict[str, Any],
    new_metrics: Dict[str, Any],
    baseline_version: str,
    new_version: str
) -> Dict[str, Any]:
    """Convenience function to generate comparison report.
    
    Args:
        baseline_metrics: Baseline version metrics
        new_metrics: New version metrics
        baseline_version: Baseline version string
        new_version: New version string
        
    Returns:
        Comparison report dict
    """
    comparison = VersionComparison(baseline_metrics, new_metrics)
    return comparison.generate_report(baseline_version, new_version)
