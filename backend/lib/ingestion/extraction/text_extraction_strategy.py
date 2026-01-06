"""
Text Extraction Strategy Pattern

Defines the interface for different text extraction strategies.
"""

from abc import ABC, abstractmethod
from typing import Union
from .extraction_result import ExtractionResult


class TextExtractionStrategy(ABC):
    """Abstract base class for text extraction strategies."""

    @abstractmethod
    def extract_text(self, pdf_source: Union[str, bytes]) -> ExtractionResult:
        """
        Extract text from PDF source.

        Args:
            pdf_source: Either a file path (str) or PDF bytes (bytes)

        Returns:
            ExtractionResult containing text and metadata
        """
        pass

    @abstractmethod
    def estimate_cost(self, pdf_source: Union[str, bytes]) -> float:
        """
        Estimate cost in USD for this extraction method.

        Args:
            pdf_source: Either a file path (str) or PDF bytes (bytes)

        Returns:
            Estimated cost in USD
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Return strategy identifier.

        Returns:
            String identifier for this strategy
        """
        pass

    @abstractmethod
    def can_handle(self, pdf_source: Union[str, bytes]) -> bool:
        """
        Check if this strategy can handle the given PDF.

        Args:
            pdf_source: Either a file path (str) or PDF bytes (bytes)

        Returns:
            True if this strategy can process the PDF
        """
        pass

    def get_priority(self) -> int:
        """
        Get priority for this strategy (lower = higher priority).

        Returns:
            Integer priority (0 = highest priority)
        """
        return 100  # Default low priority
