"""Reusable OCR Engine Wrapper Supporting PaddleOCR and Mock/Fallback.

Provides an extensible interface returning detected text, bounding boxes,
and confidence scores without hardcoding any document-specific information.
Handles both PaddleOCR 2.x and PaddleOCR 3.x/PaddleX pipelines seamlessly.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Union, Dict, Any
import numpy as np
from ai.ocr_mrz.models import OCRLine, BoundingBox


def _ensure_onednn_disabled():
    """Ensure OneDNN is disabled in Paddle inference on Windows CPU to prevent PIR issues."""
    try:
        import paddle.inference as p_inf
        if not hasattr(p_inf, "_verifai_patched"):
            orig_create_predictor = p_inf.create_predictor

            def patched_create_predictor(config):
                if hasattr(config, "disable_onednn"):
                    config.disable_onednn()
                return orig_create_predictor(config)

            p_inf.create_predictor = patched_create_predictor
            p_inf._verifai_patched = True
    except Exception:
        pass


class BaseOCREngine(ABC):
    """Abstract base class for all OCR engines in VERIFAI."""

    @abstractmethod
    def detect_text(self, image: np.ndarray) -> List[OCRLine]:
        """Perform text detection and recognition on an input image.

        Args:
            image: OpenCV numpy image array (BGR or Grayscale).

        Returns:
            List of OCRLine objects with text, bounding box coordinates, and confidence.
        """
        pass


class PaddleOCREngine(BaseOCREngine):
    """Production OCR engine powered by PaddleOCR (compatible with PaddleOCR 2.x and 3.x)."""

    def __init__(
        self,
        lang: str = "en",
        use_gpu: bool = False,
        **kwargs
    ):
        """Initialize PaddleOCR engine lazily to avoid heavy startup penalty."""
        self.lang = lang
        self.use_gpu = use_gpu
        self.extra_kwargs = kwargs
        self._ocr_instance = None
        _ensure_onednn_disabled()

    def _get_ocr(self):
        if self._ocr_instance is None:
            _ensure_onednn_disabled()
            try:
                from paddleocr import PaddleOCR
                try:
                    # PaddleOCR 3.x/PaddleX signature
                    self._ocr_instance = PaddleOCR(
                        lang=self.lang,
                        **self.extra_kwargs
                    )
                except (TypeError, ValueError):
                    # PaddleOCR 2.x legacy fallback
                    self._ocr_instance = PaddleOCR(
                        lang=self.lang,
                        use_angle_cls=True,
                        use_gpu=self.use_gpu
                    )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize PaddleOCR engine: {e}")
        return self._ocr_instance

    def detect_text(self, image: np.ndarray) -> List[OCRLine]:
        """Run text detection and recognition on image."""
        if image is None or image.size == 0:
            return []

        # Ensure image is 3-channel BGR for PaddleOCR/PaddleX
        import cv2
        if len(image.shape) == 2:
            input_img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif len(image.shape) == 3 and image.shape[2] == 4:
            input_img = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        else:
            input_img = image

        ocr = self._get_ocr()
        ocr_lines: List[OCRLine] = []

        try:
            # First try predict() (recommended in PaddleOCR 3.x)
            if hasattr(ocr, "predict"):
                raw_results = list(ocr.predict(input_img))
            else:
                raw_results = ocr.ocr(input_img)
        except Exception:
            # Fallback to ocr()
            raw_results = ocr.ocr(input_img)

        if not raw_results:
            return ocr_lines

        # Parse PaddleOCR 3.x PaddleX OCRResult dict format
        first_item = raw_results[0]
        if isinstance(first_item, dict) or hasattr(first_item, "get"):
            for res_dict in raw_results:
                texts = res_dict.get("rec_texts", [])
                scores = res_dict.get("rec_scores", [])
                polys = res_dict.get("rec_polys", [])

                for i in range(len(texts)):
                    text = str(texts[i])
                    score = float(scores[i]) if i < len(scores) else 0.9
                    poly = polys[i] if i < len(polys) else None

                    bbox = None
                    if poly is not None:
                        # poly can be numpy array or list of [x, y]
                        pts = [[float(p[0]), float(p[1])] for p in poly]
                        bbox = BoundingBox(points=pts)

                    ocr_lines.append(
                        OCRLine(text=text, bounding_box=bbox, confidence=score)
                    )
            return ocr_lines

        # Parse PaddleOCR 2.x list format: [ [ [box, (text, score)], ... ] ]
        for page in raw_results:
            if page is None:
                continue
            for line_item in page:
                if not line_item or len(line_item) < 2:
                    continue
                box_coords = line_item[0]
                text_info = line_item[1]
                text = str(text_info[0]) if isinstance(text_info, (tuple, list)) else str(text_info)
                confidence = float(text_info[1]) if isinstance(text_info, (tuple, list)) and len(text_info) > 1 else 0.9

                bbox = BoundingBox(
                    points=[[float(p[0]), float(p[1])] for p in box_coords]
                )

                ocr_lines.append(
                    OCRLine(
                        text=text,
                        bounding_box=bbox,
                        confidence=confidence
                    )
                )

        return ocr_lines


class MockOCREngine(BaseOCREngine):
    """Test engine allowing injected or pre-configured OCR responses for fast unit tests."""

    def __init__(self, predefined_lines: Optional[List[OCRLine]] = None):
        if predefined_lines is not None:
            self.predefined_lines = predefined_lines
        else:
            self.predefined_lines = [
                OCRLine(
                    text="P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<",
                    confidence=0.98
                ),
                OCRLine(
                    text="L898902C36UTO7408122F3210237ZE12345678901210",
                    confidence=0.97
                )
            ]

    def set_lines(self, lines: List[OCRLine]):
        self.predefined_lines = lines

    def detect_text(self, image: np.ndarray) -> List[OCRLine]:
        return list(self.predefined_lines)


def get_ocr_engine(engine_type: str = "paddle", **kwargs) -> BaseOCREngine:
    """Factory helper to instantiate an OCR engine."""
    if engine_type.lower() == "paddle":
        return PaddleOCREngine(**kwargs)
    elif engine_type.lower() == "mock":
        return MockOCREngine(**kwargs)
    else:
        raise ValueError(f"Unknown OCR engine type: {engine_type}")
