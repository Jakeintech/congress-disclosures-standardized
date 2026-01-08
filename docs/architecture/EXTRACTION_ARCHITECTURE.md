# Extraction Architecture - Robust Text Extraction with OCR Fallback

**Version**: 2.0
**Last Updated**: 2025-11-28
**Status**: Design Phase

---

## Executive Summary

This document defines a robust, production-grade extraction architecture for congressional disclosure documents. The system prioritizes **cost-effective direct text extraction** while providing **intelligent fallback to OCR** when needed.

### Key Design Principles

1. **Prefer Direct Text Extraction**: Try to extract text directly from PDF (pypdf) first - it's fast, cheap, and accurate
2. **OCR as Fallback**: Only use OCR when direct extraction fails or produces poor quality text
3. **Image Preprocessing**: Apply intelligent image preprocessing before OCR to improve accuracy
4. **Modular Strategy Pattern**: Each extraction method is a self-contained strategy
5. **Comprehensive Metadata**: Track which method was used, confidence scores, and quality metrics

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                  EXTRACTION PIPELINE                          │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  1. PDF Analysis (PDFAnalyzer)                               │
│     - Check if PDF is text-based, image-based, or hybrid    │
│     - Determine template type (PTR, Form A, Form B, etc.)   │
│     - Estimate OCR necessity                                 │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  2. Text Extraction Strategy Selection                       │
│     Strategy 1: DirectTextExtractor (pypdf)                  │
│     Strategy 2: OCRTextExtractor (pytesseract)               │
│     Strategy 3: HybridTextExtractor (both)                   │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  3. Text Quality Validation                                  │
│     - Check character count                                  │
│     - Validate expected patterns (dates, names, etc.)        │
│     - Calculate confidence score                             │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  4. Structured Data Extraction                               │
│     - PTRExtractor (Periodic Transaction Reports)            │
│     - FormABExtractor (Annual/Candidate Reports)             │
│     - ExtensionExtractor (Extension Requests)                │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  5. Output Generation                                        │
│     - Structured JSON with extraction metadata               │
│     - Quality metrics and confidence scores                  │
│     - Recommendations for manual review                      │
└──────────────────────────────────────────────────────────────┘
```

---

## Class Hierarchy

### Core Classes

```python
# Base Strategy Interface
class TextExtractionStrategy(ABC):
    """Abstract base class for text extraction strategies."""

    @abstractmethod
    def extract_text(self, pdf_source: Union[str, bytes]) -> ExtractionResult:
        """Extract text from PDF."""
        pass

    @abstractmethod
    def estimate_cost(self, pdf_source: Union[str, bytes]) -> float:
        """Estimate cost in USD for this extraction method."""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return strategy identifier."""
        pass


# Strategy 1: Direct Text Extraction (Preferred)
class DirectTextExtractor(TextExtractionStrategy):
    """Extract text directly from PDF using pypdf."""

    def extract_text(self, pdf_source) -> ExtractionResult:
        # Use pypdf to extract text
        # Fast, free, works for 70-80% of documents
        pass


# Strategy 2: OCR with Image Preprocessing (Fallback)
class OCRTextExtractor(TextExtractionStrategy):
    """Extract text from images using pytesseract with preprocessing."""

    def __init__(self, preprocessor: ImagePreprocessor):
        self.preprocessor = preprocessor

    def extract_text(self, pdf_source) -> ExtractionResult:
        # 1. Convert PDF pages to images (pdf2image)
        # 2. Apply image preprocessing
        # 3. Run pytesseract OCR
        # 4. Combine results
        pass


# Strategy 3: Hybrid Extraction (Best of Both)
class HybridTextExtractor(TextExtractionStrategy):
    """Combine direct text extraction with OCR for best results."""

    def extract_text(self, pdf_source) -> ExtractionResult:
        # Try direct extraction first
        # If quality is poor, fallback to OCR
        # Merge results intelligently
        pass


# Image Preprocessing Pipeline
class ImagePreprocessor:
    """Preprocess images before OCR to improve accuracy."""

    def preprocess(self, image: PIL.Image) -> PIL.Image:
        """Apply preprocessing pipeline."""
        # 1. Grayscale conversion
        # 2. Noise reduction (cv2.fastNlMeansDenoising)
        # 3. Binarization (cv2.threshold / Otsu's method)
        # 4. Deskew correction
        # 5. Border removal
        # 6. Contrast enhancement
        pass

    def detect_quality_issues(self, image: PIL.Image) -> Dict[str, Any]:
        """Detect image quality issues (blur, low contrast, skew)."""
        pass


# Extraction Pipeline Orchestrator
class ExtractionPipeline:
    """Orchestrates the complete extraction workflow."""

    def __init__(self):
        self.strategies = [
            DirectTextExtractor(),
            OCRTextExtractor(ImagePreprocessor()),
            HybridTextExtractor()
        ]

    def extract(self, pdf_source: Union[str, bytes]) -> ExtractionResult:
        """
        Execute extraction pipeline with intelligent fallback.

        Flow:
        1. Analyze PDF (text-based vs image-based)
        2. Select optimal strategy
        3. Execute extraction
        4. Validate quality
        5. Fallback if needed
        6. Return best result with metadata
        """
        # Analyze PDF
        analyzer = PDFAnalyzer(pdf_source)
        analysis = analyzer.analyze()

        # Select strategy based on PDF type
        if analysis['pdf_format'] == PDFFormat.TEXT:
            strategy = self.strategies[0]  # DirectTextExtractor
        elif analysis['pdf_format'] == PDFFormat.IMAGE:
            strategy = self.strategies[1]  # OCRTextExtractor
        else:
            strategy = self.strategies[2]  # HybridTextExtractor

        # Execute extraction
        result = strategy.extract_text(pdf_source)

        # Validate quality
        if not self._is_quality_acceptable(result):
            # Fallback to next strategy
            result = self._fallback_extraction(pdf_source, strategy)

        return result

    def _is_quality_acceptable(self, result: ExtractionResult) -> bool:
        """Validate extraction quality."""
        # Check minimum character count
        if len(result.text) < 100:
            return False

        # Check for expected patterns
        if not self._has_expected_patterns(result.text):
            return False

        return True

    def _fallback_extraction(self, pdf_source, failed_strategy) -> ExtractionResult:
        """Try next best extraction strategy."""
        pass


# Extraction Result Container
@dataclass
class ExtractionResult:
    """Container for extraction results and metadata."""

    text: str
    confidence_score: float
    extraction_method: str
    page_count: int
    character_count: int
    estimated_cost: float
    processing_time_seconds: float
    quality_metrics: Dict[str, Any]
    warnings: List[str]
    recommendations: List[str]
```

---

## Extraction Flow Diagram

```
                    ┌─────────────┐
                    │   PDF File  │
                    └──────┬──────┘
                           │
                           ▼
                  ┌────────────────┐
                  │  PDFAnalyzer   │
                  │  - Text-based? │
                  │  - Image-based?│
                  │  - Hybrid?     │
                  └────────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
   ┌──────────┐    ┌──────────┐    ┌──────────┐
   │   TEXT   │    │  HYBRID  │    │  IMAGE   │
   │   PDF    │    │   PDF    │    │   PDF    │
   └─────┬────┘    └─────┬────┘    └─────┬────┘
         │               │               │
         ▼               ▼               ▼
   ┌──────────┐    ┌──────────┐    ┌──────────┐
   │ Direct   │    │ Hybrid   │    │   OCR    │
   │ pypdf    │    │ Strategy │    │ Strategy │
   └─────┬────┘    └─────┬────┘    └─────┬────┘
         │               │               │
         │               │               │
         │               │               ▼
         │               │        ┌──────────────┐
         │               │        │ pdf2image    │
         │               │        │ Convert PDF  │
         │               │        │ to images    │
         │               │        └──────┬───────┘
         │               │               │
         │               │               ▼
         │               │        ┌──────────────┐
         │               │        │Preprocessing │
         │               │        │- Grayscale   │
         │               │        │- Denoise     │
         │               │        │- Binarize    │
         │               │        │- Deskew      │
         │               │        └──────┬───────┘
         │               │               │
         │               │               ▼
         │               │        ┌──────────────┐
         │               │        │ pytesseract  │
         │               │        │ OCR          │
         │               │        └──────┬───────┘
         │               │               │
         └───────────────┴───────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │Quality Check │
                  │- Min chars?  │
                  │- Patterns?   │
                  │- Confidence? │
                  └──────┬───────┘
                         │
                ┌────────┴────────┐
                │                 │
              PASS              FAIL
                │                 │
                ▼                 ▼
         ┌──────────┐      ┌──────────┐
         │ Continue │      │ Fallback │
         │   to     │      │   to     │
         │Structured│      │  Next    │
         │Extraction│      │ Strategy │
         └──────────┘      └──────────┘
```

---

## Image Preprocessing Pipeline

OCR accuracy depends heavily on image quality. Here's the preprocessing pipeline:

### 1. Grayscale Conversion
```python
import cv2
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
```

### 2. Noise Reduction
```python
# Remove salt-and-pepper noise
denoised = cv2.fastNlMeansDenoising(gray, h=10)
```

### 3. Binarization (Otsu's Method)
```python
# Convert to binary (black/white only)
_, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
```

### 4. Deskew Correction
```python
# Detect and correct rotation
angle = detect_skew(binary)
rotated = rotate_image(binary, angle)
```

### 5. Border Removal
```python
# Remove black borders that confuse OCR
cropped = remove_borders(rotated)
```

### 6. Contrast Enhancement
```python
# Enhance contrast for better character recognition
enhanced = cv2.equalizeHist(cropped)
```

---

## Integration with Existing System

### Update Lambda Handler (house_fd_extract_structured_code)

```python
def lambda_handler(event, context):
    """Updated handler using new extraction pipeline."""

    for record in event.get('Records', []):
        body = json.loads(record['body'])
        doc_id = body['doc_id']

        # Download PDF from S3
        pdf_bytes = download_pdf_from_s3(doc_id)

        # Use new extraction pipeline
        pipeline = ExtractionPipeline()
        extraction_result = pipeline.extract(pdf_bytes)

        # Route to appropriate structured extractor
        if body['filing_type'] == 'P':
            extractor = PTRExtractor()
            structured = extractor.extract_from_text(extraction_result.text)

        # Add extraction metadata
        structured['extraction_metadata'] = {
            'method': extraction_result.extraction_method,
            'confidence_score': extraction_result.confidence_score,
            'processing_time': extraction_result.processing_time_seconds,
            'quality_metrics': extraction_result.quality_metrics,
            'warnings': extraction_result.warnings
        }

        # Upload to S3
        upload_to_s3(doc_id, structured)
```

---

## Cost Analysis

| Method | Cost per Page | Speed | Accuracy | Use Case |
|--------|---------------|-------|----------|----------|
| **Direct pypdf** | $0.00 | ⚡⚡⚡ Fast (0.1s/page) | 95% for text PDFs | Text-based PDFs (70% of documents) |
| **pytesseract OCR** | $0.00 | 🐢 Slow (3-5s/page) | 80-90% with preprocessing | Image PDFs (20% of documents) |
| **AWS Textract** | $0.015/page | ⚡ Medium (1s/page) | 95%+ | Premium fallback (10% of documents) |

**Estimated Monthly Costs** (10,000 documents):
- **Current (Textract only)**: $15,000/month
- **With Direct Text**: $2,000/month (87% cost reduction)
- **With OCR Fallback**: $3,000/month (80% cost reduction)

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
- [ ] Implement `TextExtractionStrategy` interface
- [ ] Implement `DirectTextExtractor` (pypdf)
- [ ] Implement `ExtractionResult` dataclass
- [ ] Add unit tests

### Phase 2: OCR Support (Week 2)
- [ ] Implement `ImagePreprocessor` with cv2
- [ ] Implement `OCRTextExtractor` (pytesseract)
- [ ] Add preprocessing tests
- [ ] Benchmark OCR accuracy improvements

### Phase 3: Pipeline Orchestration (Week 3)
- [ ] Implement `ExtractionPipeline`
- [ ] Add quality validation logic
- [ ] Implement fallback mechanism
- [ ] Integration tests

### Phase 4: Lambda Integration (Week 4)
- [ ] Update `house_fd_extract_structured_code` handler
- [ ] Deploy to development environment
- [ ] Run E2E tests on all filing types
- [ ] Performance profiling

### Phase 5: Production Rollout (Week 5)
- [ ] Gradual rollout (10% → 50% → 100%)
- [ ] Monitor extraction quality
- [ ] Cost tracking
- [ ] Documentation updates

---

## Success Metrics

### Quality Metrics
- **Extraction Success Rate**: >95% of documents successfully extracted
- **Confidence Score**: >0.85 average confidence
- **Manual Review Rate**: <10% of documents require human review

### Cost Metrics
- **Cost per Document**: <$0.20 (down from $1.50)
- **Monthly Textract Spend**: <$2,000 (down from $15,000)

### Performance Metrics
- **Average Processing Time**: <5 seconds per document
- **P95 Processing Time**: <15 seconds per document

---

## Dependencies

### Python Packages
```txt
# Core PDF processing
PyPDF2==3.0.1
pypdf==4.0.0

# OCR
pytesseract==0.3.10
pdf2image==1.16.3

# Image preprocessing
opencv-python==4.8.1.78
Pillow==10.1.0
numpy==1.24.3

# Existing
boto3==1.28.0
```

### System Dependencies (Lambda Layer)
```bash
# Tesseract OCR
tesseract-ocr==5.3.0
libtesseract-dev==5.3.0

# Image processing
libopencv-dev==4.5.4
poppler-utils==22.02.0  # For pdf2image
```

---

## Risk Mitigation

### Risk 1: OCR Accuracy Lower Than Expected
**Mitigation**: Benchmark on real documents, tune preprocessing parameters, fallback to Textract for low confidence

### Risk 2: Lambda Timeout (15 min limit)
**Mitigation**: Process PDFs page-by-page, implement checkpointing, split large documents

### Risk 3: Lambda Package Size (>250 MB)
**Mitigation**: Use Lambda Layers for heavy dependencies (OpenCV, Tesseract), optimize package size

### Risk 4: Slow OCR Processing
**Mitigation**: Parallel page processing, caching, selective OCR (only problematic pages)

---

## Future Enhancements

1. **Machine Learning Integration**: Train custom models for specific form types
2. **GPU Acceleration**: Use GPU-enabled Lambda for faster OCR
3. **Caching Layer**: Cache extracted text to avoid re-processing
4. **Quality Prediction**: Predict extraction quality before processing
5. **Adaptive Strategy Selection**: Learn which strategy works best for each document type

---

**Document Status**: Design Complete - Ready for Implementation

**Next Steps**: Begin Phase 1 implementation (Core Infrastructure)
