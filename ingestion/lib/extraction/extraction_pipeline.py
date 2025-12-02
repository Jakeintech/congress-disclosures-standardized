"""
Extraction Pipeline Orchestrator

Manages the complete text extraction workflow.
"""

import logging
from typing import Union, List, Optional
from enum import Enum

from .text_extraction_strategy import TextExtractionStrategy
from .extraction_result import ExtractionResult
from .direct_text_extractor import DirectTextExtractor

logger = logging.getLogger(__name__)


class PDFType(Enum):
    """PDF type classification."""
    TEXT_BASED = "text"
    IMAGE_BASED = "image"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class ExtractionPipeline:
    """Orchestrates the complete extraction workflow."""

    def __init__(
        self,
        strategies: Optional[List[TextExtractionStrategy]] = None,
        min_confidence: float = 0.7,
        min_characters: int = 100,
        enable_fallback: bool = True
    ):
        """
        Initialize extraction pipeline.

        Args:
            strategies: List of extraction strategies (creates defaults if None)
            min_confidence: Minimum confidence to accept result (default: 0.7)
            min_characters: Minimum characters to accept result (default: 100)
            enable_fallback: Enable automatic fallback on failure (default: True)
        """
        # Initialize strategies
        if strategies is None:
            self.strategies = self._create_default_strategies()
        else:
            self.strategies = sorted(strategies, key=lambda s: s.get_priority())

        self.min_confidence = min_confidence
        self.min_characters = min_characters
        self.enable_fallback = enable_fallback

        logger.info(f"Initialized ExtractionPipeline with {len(self.strategies)} strategies")

    def _create_default_strategies(self) -> List[TextExtractionStrategy]:
        """Create default extraction strategies."""
        return [
            DirectTextExtractor(),  # Priority 0 - try first
        ]

    def extract(
        self,
        pdf_source: Union[str, bytes],
        preferred_strategy: Optional[str] = None
    ) -> ExtractionResult:
        """
        Execute extraction pipeline.

        Args:
            pdf_source: Either file path (str) or PDF bytes (bytes)
            preferred_strategy: Name of preferred strategy (optional)

        Returns:
            ExtractionResult with text and metadata
        """
        logger.info("Starting extraction pipeline")

        # If preferred strategy specified, try that first
        if preferred_strategy:
            strategy = self._get_strategy_by_name(preferred_strategy)
            if strategy:
                logger.info(f"Using preferred strategy: {preferred_strategy}")
                result = self._try_strategy(strategy, pdf_source)
                if self._is_quality_acceptable(result):
                    return result
                logger.warning(f"Preferred strategy failed quality check")

        # Try strategies in priority order
        results = []
        for strategy in self.strategies:
            if not strategy.can_handle(pdf_source):
                logger.debug(f"Strategy {strategy.get_strategy_name()} cannot handle PDF")
                continue

            logger.info(f"Trying strategy: {strategy.get_strategy_name()}")
            result = self._try_strategy(strategy, pdf_source)

            # Store result
            results.append(result)

            # Check if quality is acceptable
            if self._is_quality_acceptable(result):
                logger.info(f"Strategy {strategy.get_strategy_name()} succeeded")
                return result

            # If fallback disabled, return first result
            if not self.enable_fallback:
                logger.info("Fallback disabled, returning first result")
                return result

            logger.warning(
                f"Strategy {strategy.get_strategy_name()} produced low quality result "
                f"(confidence={result.confidence_score:.2f}, chars={result.character_count})"
            )

        # All strategies tried - return best result
        if results:
            best_result = max(results, key=lambda r: r.confidence_score)
            logger.warning(
                f"All strategies completed. Best result: {best_result.strategy_name} "
                f"(confidence={best_result.confidence_score:.2f})"
            )
            best_result.add_warning("All extraction strategies completed but quality below threshold")
            return best_result

        # No strategies could handle PDF
        logger.error("No extraction strategies could process PDF")
        return ExtractionResult(
            text="",
            confidence_score=0.0,
            extraction_method="none",
            strategy_name="none",
            page_count=0,
            character_count=0,
            word_count=0,
            processing_time_seconds=0.0,
            estimated_cost_usd=0.0,
            quality_metrics={},
            warnings=["No extraction strategies could process PDF"],
            recommendations=["Check PDF format and try manual review"]
        )

    def _try_strategy(
        self, strategy: TextExtractionStrategy, pdf_source: Union[str, bytes]
    ) -> ExtractionResult:
        """
        Try an extraction strategy and handle errors.

        Args:
            strategy: Strategy to try
            pdf_source: PDF source

        Returns:
            ExtractionResult (may contain error)
        """
        try:
            return strategy.extract_text(pdf_source)
        except Exception as e:
            logger.error(f"Strategy {strategy.get_strategy_name()} failed: {e}", exc_info=True)
            return ExtractionResult(
                text="",
                confidence_score=0.0,
                extraction_method=strategy.get_strategy_name(),
                strategy_name=strategy.get_strategy_name(),
                page_count=0,
                character_count=0,
                word_count=0,
                processing_time_seconds=0.0,
                estimated_cost_usd=0.0,
                quality_metrics={"error": str(e)},
                warnings=[f"Extraction failed: {e}"],
                recommendations=["Try alternative extraction method"]
            )

    def _is_quality_acceptable(self, result: ExtractionResult) -> bool:
        """
        Validate extraction quality.

        Args:
            result: Extraction result to validate

        Returns:
            True if quality is acceptable
        """
        # Check for errors
        if "error" in result.quality_metrics:
            return False

        # Check minimum character count
        if result.character_count < self.min_characters:
            logger.debug(
                f"Below minimum characters: {result.character_count} < {self.min_characters}"
            )
            return False

        # Check minimum confidence
        if result.confidence_score < self.min_confidence:
            logger.debug(
                f"Below minimum confidence: {result.confidence_score:.2f} < {self.min_confidence}"
            )
            return False

        return True

    def _get_strategy_by_name(self, name: str) -> Optional[TextExtractionStrategy]:
        """Get strategy by name."""
        for strategy in self.strategies:
            if strategy.get_strategy_name() == name:
                return strategy
        return None

    def classify_pdf_type(self, pdf_source: Union[str, bytes]) -> PDFType:
        """
        Classify PDF type (text-based vs image-based).
        
        Args:
            pdf_source: PDF source

        Returns:
            PDFType enum value
        """
        try:
            # Try direct text extraction to see if we get meaningful text
            direct_extractor = DirectTextExtractor()
            result = direct_extractor.extract_text(pdf_source)

            avg_chars_per_page = (
                result.character_count / result.page_count if result.page_count > 0 else 0
            )

            # Classification logic
            if avg_chars_per_page > 200:
                return PDFType.TEXT_BASED
            elif avg_chars_per_page > 50:
                return PDFType.HYBRID
            elif avg_chars_per_page > 0:
                return PDFType.IMAGE_BASED
            else:
                return PDFType.UNKNOWN

        except Exception as e:
            logger.warning(f"PDF classification failed: {e}")
            return PDFType.UNKNOWN

    def get_recommended_strategy(
        self, pdf_source: Union[str, bytes]
    ) -> Optional[TextExtractionStrategy]:
        """
        Get recommended strategy based on PDF analysis.

        Args:
            pdf_source: PDF source

        Returns:
            Recommended strategy or None
        """
        # Always return direct text since OCR is removed
        return self._get_strategy_by_name("direct_text")
