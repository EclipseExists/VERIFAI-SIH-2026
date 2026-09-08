"""Intelligent MRZ Detection and Multi-Factor Scoring System.

Evaluates OCR candidate lines using character length proximity, valid MRZ charset,
filler '<' frequency, ICAO P< document prefix, line 2 numeric structure,
and vertical spatial consistency rather than simple length thresholds.
"""

import re
from typing import List, Tuple, Optional, Dict, Any
from ai.ocr_mrz.models import OCRLine, MRZDetectionResult, BoundingBox


VALID_MRZ_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<")


class MRZDetector:
    """Intelligent TD3 MRZ line detector and scoring engine."""

    def __init__(self, min_confidence_threshold: float = 0.65):
        self.min_confidence_threshold = min_confidence_threshold

    def clean_candidate(self, text: str) -> str:
        """Strip whitespace, replace common noisy symbols, convert to uppercase."""
        # Clean text preserving valid MRZ characters
        t = text.strip().upper()
        # Replace common OCR misreads of filler character '<'
        t = t.replace('«', '<').replace('‹', '<').replace('>', '<')
        # Remove inner whitespace
        return "".join(c for c in t if not c.isspace())

    def score_line_length(self, text: str, target: int = 44) -> float:
        """Score how close the line length is to 44 characters."""
        length = len(text)
        if length == 0:
            return 0.0
        diff = abs(length - target)
        if diff == 0:
            return 1.0
        elif diff <= 2:
            return 0.9
        elif diff <= 5:
            return 0.7
        elif diff <= 10:
            return 0.4
        return 0.0

    def score_charset_purity(self, text: str) -> float:
        """Fraction of characters belonging to the valid MRZ alphabet [A-Z0-9<]."""
        if not text:
            return 0.0
        valid_count = sum(1 for c in text if c in VALID_MRZ_CHARS)
        return valid_count / len(text)

    def score_filler_frequency(self, text: str) -> float:
        """Score based on typical frequency of '<' characters (15% - 60%)."""
        if not text:
            return 0.0
        filler_count = text.count('<')
        ratio = filler_count / len(text)

        if 0.15 <= ratio <= 0.65:
            return 1.0
        elif 0.08 <= ratio < 0.15:
            return ratio / 0.15
        elif ratio > 0.65:
            return max(0.0, 1.0 - (ratio - 0.65) * 2.5)
        else:
            return 0.1

    def score_line1_structure(self, text: str) -> float:
        """Evaluate structural features specific to TD3 Line 1:

        - Starts with 'P<' or 'P' + letter
        - Contains '<<' separating surname from given names
        - High alphabetic/filler concentration (no legal digits)
        """
        if len(text) < 10:
            return 0.0

        score = 0.0
        # 1. Document prefix: starts with P< or P[A-Z]
        if text.startswith("P<"):
            score += 0.45
        elif text.startswith("P") and text[1].isalpha():
            score += 0.35
        elif text.startswith("P"):
            score += 0.20

        # 2. Contains << name delimiter
        if "<<" in text:
            score += 0.35

        # 3. Mostly letters and < (digits in line 1 should be close to 0)
        digits_count = sum(1 for c in text if c.isdigit())
        if digits_count == 0:
            score += 0.20
        elif digits_count <= 2:
            score += 0.10

        return min(1.0, score)

    def score_line2_structure(self, text: str) -> float:
        """Evaluate structural features specific to TD3 Line 2:

        - Contains birthdate (YYMMDD) and expiry date (YYMMDD)
        - Contains digits at check digit positions
        - Contains nationality code (letters)
        - Contains sex marker ('M', 'F', or '<')
        """
        if len(text) < 10:
            return 0.0

        score = 0.0

        # High digit ratio in line 2 (passports, dates, check digits)
        digit_count = sum(1 for c in text if c.isdigit())
        ratio = digit_count / len(text)
        if 0.25 <= ratio <= 0.60:
            score += 0.40
        elif ratio > 0.15:
            score += 0.25

        # If length is approximately 44, check fixed offsets
        if len(text) >= 28:
            # Check DOB region (13..19)
            dob_substr = text[13:19]
            if sum(1 for c in dob_substr if c.isdigit()) >= 4:
                score += 0.25

            # Check Expiry region (21..27)
            exp_substr = text[21:27]
            if sum(1 for c in exp_substr if c.isdigit()) >= 4:
                score += 0.25

            # Check Sex indicator at pos 20
            if len(text) > 20 and text[20] in ('M', 'F', '<', 'X'):
                score += 0.10

        return min(1.0, score)

    def score_line(self, text: str, is_line1: bool) -> Tuple[float, Dict[str, float]]:
        """Calculate aggregate score for an individual line candidate."""
        cleaned = self.clean_candidate(text)
        len_score = self.score_line_length(cleaned, target=44)
        purity_score = self.score_charset_purity(cleaned)
        filler_score = self.score_filler_frequency(cleaned)
        struct_score = self.score_line1_structure(cleaned) if is_line1 else self.score_line2_structure(cleaned)

        # Weighted composite score
        total = (
            0.25 * len_score +
            0.25 * purity_score +
            0.20 * filler_score +
            0.30 * struct_score
        )

        breakdown = {
            "length": len_score,
            "purity": purity_score,
            "filler": filler_score,
            "structure": struct_score,
            "total": total,
        }
        return total, breakdown

    def evaluate_pair_geometry(self, box1: Optional[BoundingBox], box2: Optional[BoundingBox]) -> float:
        """Verify spatial consistency between Line 1 and Line 2."""
        if not box1 or not box2:
            return 0.8  # neutral fallback if bboxes not provided

        # Line 1 should be vertically above Line 2
        if box1.y_max > box2.y_max:
            return 0.2  # inverted order

        # Widths should be comparable
        w1, w2 = box1.width, box2.width
        max_w = max(w1, w2, 1.0)
        width_ratio = min(w1, w2) / max_w
        if width_ratio < 0.7:
            return 0.5

        # Horizontal alignment
        x_diff = abs(box1.x_min - box2.x_min)
        if x_diff > 0.2 * max_w:
            return 0.6

        return 1.0

    def detect_from_ocr_lines(self, ocr_lines: List[OCRLine]) -> MRZDetectionResult:
        """Scan a list of OCR lines, detect TD3 MRZ lines, and score confidence."""
        if not ocr_lines:
            return MRZDetectionResult(
                mrz_present=False,
                confidence=0.0,
                line1=None,
                line2=None,
                raw_candidates=[]
            )

        best_score = 0.0
        best_line1: Optional[str] = None
        best_line2: Optional[str] = None
        best_breakdown: Dict[str, float] = {}

        n = len(ocr_lines)

        # First pass: check adjacent pairs
        for i in range(n):
            cand1_raw = ocr_lines[i].text
            cand1_clean = self.clean_candidate(cand1_raw)
            score1, bd1 = self.score_line(cand1_clean, is_line1=True)

            if score1 < 0.35:
                continue

            # Look for line 2 either immediately adjacent or nearby
            for j in range(i + 1, min(i + 4, n)):
                cand2_raw = ocr_lines[j].text
                cand2_clean = self.clean_candidate(cand2_raw)
                score2, bd2 = self.score_line(cand2_clean, is_line1=False)

                if score2 < 0.35:
                    continue

                geo_score = self.evaluate_pair_geometry(
                    ocr_lines[i].bounding_box, ocr_lines[j].bounding_box
                )

                pair_score = (0.45 * score1) + (0.45 * score2) + (0.10 * geo_score)

                if pair_score > best_score:
                    best_score = pair_score
                    best_line1 = cand1_clean
                    best_line2 = cand2_clean
                    best_breakdown = {
                        "line1_score": score1,
                        "line2_score": score2,
                        "geometry_score": geo_score,
                        "composite": pair_score,
                    }

        # Second pass fallback: If lines were merged into one text block with newlines
        if best_score < self.min_confidence_threshold:
            for item in ocr_lines:
                if "\n" in item.text:
                    sub_lines = [self.clean_candidate(l) for l in item.text.split("\n") if l.strip()]
                    if len(sub_lines) >= 2:
                        s1, _ = self.score_line(sub_lines[0], is_line1=True)
                        s2, _ = self.score_line(sub_lines[1], is_line1=False)
                        p_score = (s1 + s2) / 2.0
                        if p_score > best_score:
                            best_score = p_score
                            best_line1 = sub_lines[0]
                            best_line2 = sub_lines[1]
                            best_breakdown = {
                                "line1_score": s1,
                                "line2_score": s2,
                                "geometry_score": 1.0,
                                "composite": p_score,
                            }

        # Pad or truncate candidate lines if within 1-2 characters of 44
        if best_line1 and len(best_line1) != 44:
            if len(best_line1) < 44 and len(best_line1) >= 40:
                best_line1 = best_line1.ljust(44, '<')
            elif len(best_line1) > 44 and len(best_line1) <= 46:
                best_line1 = best_line1[:44]

        if best_line2 and len(best_line2) != 44:
            if len(best_line2) < 44 and len(best_line2) >= 40:
                best_line2 = best_line2.ljust(44, '<')
            elif len(best_line2) > 44 and len(best_line2) <= 46:
                best_line2 = best_line2[:44]

        mrz_present = (best_score >= self.min_confidence_threshold) and (best_line1 is not None) and (best_line2 is not None)

        return MRZDetectionResult(
            mrz_present=mrz_present,
            confidence=round(best_score, 3),
            line1=best_line1 if mrz_present else None,
            line2=best_line2 if mrz_present else None,
            raw_candidates=[ocr_lines[i].text for i in range(min(5, len(ocr_lines)))],
            score_breakdown=best_breakdown
        )
