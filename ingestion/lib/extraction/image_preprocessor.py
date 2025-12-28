"""
Image Preprocessor for OCR

Applies preprocessing pipeline to improve OCR accuracy.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocess images before OCR to improve accuracy."""

    def __init__(self, enable_preprocessing: bool = True):
        """
        Initialize image preprocessor.

        Args:
            enable_preprocessing: Whether to enable preprocessing (default: True)
        """
        self.enable_preprocessing = enable_preprocessing

        # Import optional dependencies
        self._cv2 = None
        self._PIL = None

    @property
    def cv2(self):
        """Lazy load OpenCV."""
        if self._cv2 is None:
            try:
                import cv2
                self._cv2 = cv2
            except ImportError:
                logger.warning("OpenCV not installed. Install with: pip install opencv-python")
                raise ImportError("opencv-python required for image preprocessing")
        return self._cv2

    @property
    def PIL(self):
        """Lazy load PIL."""
        if self._PIL is None:
            try:
                from PIL import Image
                self._PIL = Image
            except ImportError:
                logger.warning("PIL not installed. Install with: pip install Pillow")
                raise ImportError("Pillow required for image preprocessing")
        return self._PIL

    def preprocess(self, image) -> Any:
        """
        Apply preprocessing pipeline to image.

        Pipeline:
        1. Grayscale conversion
        2. Noise reduction
        3. Binarization (Otsu's method)
        4. Deskew correction
        5. Border removal
        6. Contrast enhancement

        Args:
            image: PIL Image or numpy array

        Returns:
            Preprocessed PIL Image
        """
        if not self.enable_preprocessing:
            return image

        try:
            # Convert PIL Image to numpy array if needed
            if hasattr(image, 'mode'):  # PIL Image
                img_array = np.array(image)
            else:
                img_array = image

            # Step 1: Grayscale conversion
            gray = self._convert_to_grayscale(img_array)

            # Step 2: Noise reduction
            denoised = self._denoise(gray)

            # Step 3: Binarization
            binary = self._binarize(denoised)

            # Step 4: Deskew
            deskewed = self._deskew(binary)

            # Step 5: Remove borders
            cropped = self._remove_borders(deskewed)

            # Step 6: Enhance contrast
            enhanced = self._enhance_contrast(cropped)

            # Convert back to PIL Image
            return self.PIL.fromarray(enhanced)

        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}, returning original")
            return image

    def _convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale."""
        if len(image.shape) == 3:
            return self.cv2.cvtColor(image, self.cv2.COLOR_BGR2GRAY)
        return image

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """Remove salt-and-pepper noise."""
        return self.cv2.fastNlMeansDenoising(image, h=10)

    def _binarize(self, image: np.ndarray) -> np.ndarray:
        """Convert to binary (black/white) using Otsu's method."""
        _, binary = self.cv2.threshold(
            image, 0, 255, self.cv2.THRESH_BINARY + self.cv2.THRESH_OTSU
        )
        return binary

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Detect and correct skew/rotation."""
        try:
            # Detect skew angle
            angle = self._detect_skew_angle(image)

            if abs(angle) < 0.5:  # Skip if nearly straight
                return image

            # Rotate image
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = self.cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = self.cv2.warpAffine(
                image, M, (w, h),
                flags=self.cv2.INTER_CUBIC,
                borderMode=self.cv2.BORDER_REPLICATE
            )

            logger.debug(f"Deskewed image by {angle:.2f} degrees")
            return rotated

        except Exception as e:
            logger.warning(f"Deskew failed: {e}")
            return image

    def _detect_skew_angle(self, image: np.ndarray) -> float:
        """
        Detect skew angle using Hough Line Transform.

        Returns:
            Skew angle in degrees
        """
        try:
            # Edge detection
            edges = self.cv2.Canny(image, 50, 150, apertureSize=3)

            # Hough Line Transform
            lines = self.cv2.HoughLines(edges, 1, np.pi / 180, 200)

            if lines is None:
                return 0.0

            # Calculate median angle
            angles = []
            for rho, theta in lines[:, 0]:
                angle = (theta - np.pi / 2) * 180 / np.pi
                angles.append(angle)

            median_angle = np.median(angles)
            return median_angle

        except Exception as e:
            logger.warning(f"Skew detection failed: {e}")
            return 0.0

    def _remove_borders(self, image: np.ndarray) -> np.ndarray:
        """Remove black borders that can confuse OCR."""
        try:
            # Find contours
            contours, _ = self.cv2.findContours(
                image, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                return image

            # Get bounding box of largest contour
            largest_contour = max(contours, key=self.cv2.contourArea)
            x, y, w, h = self.cv2.boundingRect(largest_contour)

            # Crop to bounding box
            cropped = image[y:y+h, x:x+w]

            return cropped

        except Exception as e:
            logger.warning(f"Border removal failed: {e}")
            return image

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance contrast using histogram equalization."""
        try:
            return self.cv2.equalizeHist(image)
        except Exception as e:
            logger.warning(f"Contrast enhancement failed: {e}")
            return image

    def detect_quality_issues(self, image) -> Dict[str, Any]:
        """
        Detect image quality issues.

        Returns:
            Dict with quality metrics:
            - blur_score: Variance of Laplacian (higher = sharper)
            - contrast_score: Standard deviation (higher = more contrast)
            - skew_angle: Detected skew in degrees
            - has_borders: Whether black borders detected
        """
        try:
            # Convert to numpy array if needed
            if hasattr(image, 'mode'):  # PIL Image
                img_array = np.array(image)
            else:
                img_array = image

            # Convert to grayscale
            gray = self._convert_to_grayscale(img_array)

            # Blur detection (Laplacian variance)
            blur_score = self.cv2.Laplacian(gray, self.cv2.CV_64F).var()

            # Contrast detection (std dev)
            contrast_score = gray.std()

            # Skew detection
            skew_angle = self._detect_skew_angle(gray)

            # Border detection (check edges for dark regions)
            has_borders = self._has_dark_borders(gray)

            return {
                "blur_score": float(blur_score),
                "contrast_score": float(contrast_score),
                "skew_angle": float(skew_angle),
                "has_borders": has_borders,
                "is_sharp": blur_score > 100,
                "is_high_contrast": contrast_score > 50,
                "is_skewed": abs(skew_angle) > 1.0
            }

        except Exception as e:
            logger.error(f"Quality detection failed: {e}")
            return {
                "error": str(e),
                "blur_score": 0,
                "contrast_score": 0,
                "skew_angle": 0,
                "has_borders": False
            }

    def _has_dark_borders(self, image: np.ndarray, threshold: int = 10) -> bool:
        """Check if image has dark borders."""
        try:
            h, w = image.shape[:2]
            border_size = min(h, w) // 20  # Check 5% of image size

            # Check top, bottom, left, right borders
            top = image[:border_size, :].mean()
            bottom = image[-border_size:, :].mean()
            left = image[:, :border_size].mean()
            right = image[:, -border_size:].mean()

            # If any border is very dark, consider it a border
            return any(x < threshold for x in [top, bottom, left, right])

        except Exception:
            return False
