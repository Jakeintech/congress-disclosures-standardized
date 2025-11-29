"""
Extraction Module

Provides robust text extraction from PDFs with intelligent fallback strategies.

Usage:
    from ingestion.lib.extraction import ExtractionPipeline

    pipeline = ExtractionPipeline()
    result = pipeline.extract("/path/to/document.pdf")

    print(f"Extracted {result.character_count} characters")
    print(f"Confidence: {result.confidence_score:.2%}")
    print(f"Method: {result.extraction_method}")
"""

from .extraction_result import ExtractionResult
from .text_extraction_strategy import TextExtractionStrategy
from .direct_text_extractor import DirectTextExtractor
from .image_preprocessor import ImagePreprocessor
from .ocr_text_extractor import OCRTextExtractor
from .extraction_pipeline import ExtractionPipeline, PDFType

__all__ = [
    "ExtractionResult",
    "TextExtractionStrategy",
    "DirectTextExtractor",
    "ImagePreprocessor",
    "OCRTextExtractor",
    "ExtractionPipeline",
    "PDFType",
]

__version__ = "1.0.0"
