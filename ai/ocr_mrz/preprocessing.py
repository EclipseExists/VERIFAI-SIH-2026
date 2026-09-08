"""Non-destructive Image Preprocessing Pipeline for Passport & MRZ OCR.

Provides modular image transformations (resizing, grayscale conversion,
contrast enhancement via CLAHE, denoising, adaptive/Otsu binarization,
and deskewing) without mutating the input image.
"""

import cv2
import numpy as np
from typing import Tuple, Dict, Any, Optional


def resize_image(image: np.ndarray, target_width: int = 1600) -> Tuple[np.ndarray, float]:
    """Resize image to a target width while maintaining aspect ratio.

    Args:
        image: Source image numpy array (BGR or Grayscale).
        target_width: Desired width in pixels.

    Returns:
        Tuple of (resized_image, scale_factor).
    """
    h, w = image.shape[:2]
    if w <= target_width:
        return image.copy(), 1.0

    scale = target_width / float(w)
    new_h = int(h * scale)
    resized = cv2.resize(image, (target_width, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Safely convert an image to single-channel grayscale without modifying source."""
    if len(image.shape) == 2:
        return image.copy()
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def enhance_contrast_clahe(
    gray: np.ndarray,
    clip_limit: float = 2.5,
    tile_grid_size: Tuple[int, int] = (8, 8)
) -> np.ndarray:
    """Enhance contrast using Contrast Limited Adaptive Histogram Equalization (CLAHE)."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(gray.copy())


def denoise_image(gray: np.ndarray, method: str = "bilateral") -> np.ndarray:
    """Denoise grayscale image while preserving sharp character edges."""
    if method == "bilateral":
        # Bilateral filter preserves sharp edges crucial for OCR characters
        return cv2.bilateralFilter(gray.copy(), d=9, sigmaColor=75, sigmaSpace=75)
    elif method == "gaussian":
        return cv2.GaussianBlur(gray.copy(), (3, 3), 0)
    else:
        return cv2.fastNlMeansDenoising(gray.copy(), h=10)


def binarize_adaptive(gray: np.ndarray, block_size: int = 21, c_constant: int = 10) -> np.ndarray:
    """Convert grayscale image to binary using adaptive Gaussian thresholding."""
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c_constant
    )


def binarize_otsu(gray: np.ndarray) -> np.ndarray:
    """Convert grayscale image to binary using Otsu's thresholding."""
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def detect_skew_angle(gray: np.ndarray) -> float:
    """Compute skew angle in degrees using image moments / minAreaRect on edge contours."""
    # Find edges using Canny
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    # Find coordinates of all non-zero edge pixels
    pts = cv2.findNonZero(edges)
    if pts is None or len(pts) < 100:
        return 0.0

    rect = cv2.minAreaRect(pts)
    angle = rect[-1]

    # Normalize OpenCV minAreaRect angle
    if angle < -45:
        angle = -(90 + angle)
    elif angle > 45:
        angle = 90 - angle
    else:
        angle = -angle

    # Only return angle if it's within a realistic document tilt range (-30 to +30 deg)
    if -30.0 <= angle <= 30.0:
        return float(angle)
    return 0.0


def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image by given angle in degrees around its center with border replication."""
    if abs(angle) < 0.2:
        return image.copy()

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def detect_and_deskew(image: np.ndarray) -> Tuple[np.ndarray, float]:
    """Detect skew angle and deskew image if tilted."""
    gray = to_grayscale(image)
    angle = detect_skew_angle(gray)
    if abs(angle) >= 0.5:
        return rotate_image(image, angle), angle
    return image.copy(), 0.0


def extract_mrz_region(image: np.ndarray, bottom_ratio: float = 0.35) -> np.ndarray:
    """Extract the bottom portion of the image where the MRZ typically resides.

    Args:
        image: Document image (BGR or Grayscale).
        bottom_ratio: Fraction of height from the bottom to retain (default 35%).
    """
    h = image.shape[0]
    start_y = int(h * (1.0 - bottom_ratio))
    return image[start_y:h, :].copy()


def preprocess_for_ocr(image: np.ndarray) -> Dict[str, Any]:
    """Execute complete non-destructive preprocessing pipeline for document OCR.

    Returns:
        Dictionary containing:
        - original: Untouched copy
        - resized: Resized image
        - deskewed: Resized and deskewed image
        - gray: Contrast-enhanced grayscale
        - binary: Clean binarized image
        - mrz_roi: Cropped lower region for dedicated MRZ OCR
        - scale_factor: Resizing scale applied
        - skew_angle: Deskew angle corrected
    """
    orig_copy = image.copy()
    resized, scale = resize_image(orig_copy, target_width=1600)
    deskewed, angle = detect_and_deskew(resized)

    gray = to_grayscale(deskewed)
    denoised = denoise_image(gray, method="bilateral")
    clahe_gray = enhance_contrast_clahe(denoised, clip_limit=2.5)
    binary = binarize_otsu(clahe_gray)
    mrz_roi = extract_mrz_region(clahe_gray, bottom_ratio=0.35)

    return {
        "original": orig_copy,
        "resized": resized,
        "deskewed": deskewed,
        "gray": clahe_gray,
        "binary": binary,
        "mrz_roi": mrz_roi,
        "scale_factor": scale,
        "skew_angle": angle,
    }
