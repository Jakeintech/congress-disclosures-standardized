"""
Extraction Result Container

Stores text extraction results along with comprehensive metadata.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class ExtractionResult:
    """Container for text extraction results and metadata."""

    # Core extraction data
    text: str
    confidence_score: float  # 0.0 to 1.0

    # Extraction method metadata
    extraction_method: str  # "direct_text", "ocr", "hybrid", "textract"
    strategy_name: str  # Name of the strategy used

    # Document properties
    page_count: int
    character_count: int
    word_count: int

    # Performance metrics
    processing_time_seconds: float
    estimated_cost_usd: float

    # Quality metrics
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Timestamp
    extraction_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    # Optional PDF properties
    pdf_properties: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Calculate derived fields."""
        if self.character_count == 0:
            self.character_count = len(self.text)

        if self.word_count == 0:
            self.word_count = len(self.text.split())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "confidence_score": self.confidence_score,
            "extraction_method": self.extraction_method,
            "strategy_name": self.strategy_name,
            "page_count": self.page_count,
            "character_count": self.character_count,
            "word_count": self.word_count,
            "processing_time_seconds": self.processing_time_seconds,
            "estimated_cost_usd": self.estimated_cost_usd,
            "quality_metrics": self.quality_metrics,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "extraction_timestamp": self.extraction_timestamp,
            "pdf_properties": self.pdf_properties
        }

    def is_quality_acceptable(self, min_chars: int = 100, min_confidence: float = 0.7) -> bool:
        """Check if extraction quality meets minimum standards."""
        if self.character_count < min_chars:
            return False

        if self.confidence_score < min_confidence:
            return False

        return True

    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)

    def add_recommendation(self, recommendation: str):
        """Add a recommendation."""
        self.recommendations.append(recommendation)
