"""Structured data extractors for House financial disclosure PDFs.

This module provides format-agnostic extraction of structured data from PDFs,
handling both text-based and image-based documents with automatic fallback.
"""

from .pdf_analyzer import PDFAnalyzer, PDFFormat, TemplateType
from .base_extractor import BaseExtractor

__all__ = ["PDFAnalyzer", "PDFFormat", "TemplateType", "BaseExtractor"]
