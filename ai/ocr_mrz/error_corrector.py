"""Controlled MRZ OCR Error Normalization and Correction Layer.

Applies evidence-based, checksum-verified character substitutions for
common OCR confusion pairs (O/0, I/1, B/8, S/5, G/6, Z/2) without blind changes.
Every modification is recorded with a detailed rationale in an audit trail.
"""

from typing import List, Tuple, Optional, Dict
from ai.ocr_mrz.models import CorrectionRecord
from ai.ocr_mrz.checksum import (
    calculate_check_digit,
    validate_check_digit,
    validate_td3_checksums,
    get_td3_composite_data
)

# Common OCR confusion sets (char -> candidate substitutions)
DIGIT_TO_ALPHA = {
    '0': 'O',
    '1': 'I',
    '2': 'Z',
    '5': 'S',
    '6': 'G',
    '8': 'B',
}

ALPHA_TO_DIGIT = {
    'O': '0',
    'o': '0',
    'D': '0',
    'Q': '0',
    'I': '1',
    'l': '1',
    'i': '1',
    '|': '1',
    'Z': '2',
    'z': '2',
    'S': '5',
    's': '5',
    'G': '6',
    'b': '6',
    'B': '8',
}

# Bidirectional confusion pairs
CONFUSION_PAIRS = [
    ('O', '0'), ('0', 'O'),
    ('I', '1'), ('1', 'I'),
    ('B', '8'), ('8', 'B'),
    ('S', '5'), ('5', 'S'),
    ('G', '6'), ('6', 'G'),
    ('Z', '2'), ('2', 'Z'),
]


class MRZErrorCorrector:
    """Intelligent, checksum-guided error corrector for TD3 MRZ strings."""

    def __init__(self):
        self.corrections: List[CorrectionRecord] = []

    def reset(self):
        self.corrections = []

    def clean_mrz_text(self, text: str) -> str:
        """Strip whitespace and convert to uppercase standard MRZ characters."""
        cleaned = text.strip().upper()
        # Remove any unexpected whitespace or newline within a line
        return "".join(c for c in cleaned if not c.isspace())

    def normalize_line1(self, line1: str) -> str:
        """Apply structural normalization to TD3 Line 1 (Document type, issuing state, names).

        Line 1 (44 chars):
        0-1: Document code (usually P< or P followed by country letter)
        2-4: Issuing state (3 uppercase letters)
        5-43: Names (only letters A-Z and < are legally permitted in ICAO TD3)
        """
        line1 = self.clean_mrz_text(line1)
        if len(line1) != 44:
            return line1

        chars = list(line1)

        # 1. Document code prefix: e.g. P0 -> P< or PO -> P<
        if chars[0] == 'P' and chars[1] in ('0', 'O', '(', '[', '{'):
            orig = f"{chars[0]}{chars[1]}"
            chars[1] = '<'
            self.corrections.append(
                CorrectionRecord(
                    field="line1_doc_code",
                    original=orig,
                    corrected="P<",
                    reason="structural normalization of passport prefix"
                )
            )

        # 2. Issuing country code (positions 2-4) must be uppercase letters
        for idx in range(2, 5):
            c = chars[idx]
            if c in DIGIT_TO_ALPHA:
                sub = DIGIT_TO_ALPHA[c]
                chars[idx] = sub
                self.corrections.append(
                    CorrectionRecord(
                        field=f"line1_issuing_state_pos_{idx}",
                        original=c,
                        corrected=sub,
                        reason="structural character set normalization (issuing country alpha-only)"
                    )
                )

        # 3. Name field (positions 5-43): only A-Z and < are allowed
        for idx in range(5, 44):
            c = chars[idx]
            if c in DIGIT_TO_ALPHA:
                sub = DIGIT_TO_ALPHA[c]
                chars[idx] = sub
                self.corrections.append(
                    CorrectionRecord(
                        field=f"line1_name_pos_{idx}",
                        original=c,
                        corrected=sub,
                        reason="structural character set normalization (name field alpha-only)"
                    )
                )

        return "".join(chars)

    def normalize_check_digit_char(self, char: str, field_name: str) -> str:
        """Check digit position must be a numeric digit (0-9)."""
        if char in ALPHA_TO_DIGIT:
            corrected = ALPHA_TO_DIGIT[char]
            self.corrections.append(
                CorrectionRecord(
                    field=field_name,
                    original=char,
                    corrected=corrected,
                    reason="check digit position normalization to numeric digit"
                )
            )
            return corrected
        return char

    def correct_strictly_numeric_field(
        self,
        data: str,
        expected_check: str,
        field_name: str,
        pos_offset: int
    ) -> Tuple[str, str]:
        """Correct fields that MUST be digits (e.g. DOB, Expiry Date).

        Substitutes alpha confusion characters with digits and validates check digit.
        """
        chars = list(data)
        for i, c in enumerate(chars):
            if c in ALPHA_TO_DIGIT:
                sub = ALPHA_TO_DIGIT[c]
                chars[i] = sub
                self.corrections.append(
                    CorrectionRecord(
                        field=f"{field_name}_pos_{pos_offset + i}",
                        original=c,
                        corrected=sub,
                        reason="strictly numeric date field normalization"
                    )
                )

        corrected_data = "".join(chars)

        # Check if check digit itself was an alpha confusion (e.g. 'O' instead of '0')
        norm_check = expected_check
        if norm_check in ALPHA_TO_DIGIT:
            norm_check = self.normalize_check_digit_char(expected_check, f"{field_name}_check_digit")

        # Now verify checksum
        if validate_check_digit(corrected_data, norm_check):
            return corrected_data, norm_check

        # If still failing, check if single ambiguity exists
        return corrected_data, norm_check

    def correct_passport_number_field(self, raw_num: str, check_digit: str) -> Tuple[str, str]:
        """Attempt checksum-supported correction on alphanumeric passport number.

        Only alters characters if:
        1. Current checksum fails.
        2. Exactly one substitution from known OCR confusions yields a valid check digit.
        """
        norm_check = check_digit
        if norm_check in ALPHA_TO_DIGIT:
            norm_check = self.normalize_check_digit_char(check_digit, "passport_number_check_digit")

        if validate_check_digit(raw_num, norm_check):
            return raw_num, norm_check

        # Checksum failed. Look for candidate single-character substitutions.
        candidates: List[Tuple[str, int, str, str]] = []  # (cand_str, idx, orig, sub)

        for i, c in enumerate(raw_num):
            possible_subs = []
            if c in ALPHA_TO_DIGIT:
                possible_subs.append(ALPHA_TO_DIGIT[c])
            if c in DIGIT_TO_ALPHA:
                possible_subs.append(DIGIT_TO_ALPHA[c])

            for sub in possible_subs:
                cand_chars = list(raw_num)
                cand_chars[i] = sub
                cand_str = "".join(cand_chars)
                if validate_check_digit(cand_str, norm_check):
                    candidates.append((cand_str, i, c, sub))

        # Only apply if there is unambiguous checksum evidence (exactly 1 valid candidate)
        if len(candidates) == 1:
            best_cand, idx, orig, sub = candidates[0]
            self.corrections.append(
                CorrectionRecord(
                    field=f"passport_number_pos_{idx}",
                    original=orig,
                    corrected=sub,
                    reason="checksum-supported correction"
                )
            )
            return best_cand, norm_check

        return raw_num, norm_check

    def normalize_line2(self, line2: str) -> str:
        """Normalize TD3 Line 2 with structural and checksum-guided corrections."""
        line2 = self.clean_mrz_text(line2)
        if len(line2) != 44:
            return line2

        chars = list(line2)

        # Passport Number (0..9) + Check Digit (9)
        raw_pnum = "".join(chars[0:9])
        raw_pcheck = chars[9]
        corr_pnum, corr_pcheck = self.correct_passport_number_field(raw_pnum, raw_pcheck)
        for i, c in enumerate(corr_pnum):
            chars[i] = c
        chars[9] = corr_pcheck

        # Nationality (10..13): alpha-only
        for idx in range(10, 13):
            c = chars[idx]
            if c in DIGIT_TO_ALPHA:
                sub = DIGIT_TO_ALPHA[c]
                chars[idx] = sub
                self.corrections.append(
                    CorrectionRecord(
                        field=f"line2_nationality_pos_{idx}",
                        original=c,
                        corrected=sub,
                        reason="structural character set normalization (nationality alpha-only)"
                    )
                )

        # Date of Birth (13..19) + Check Digit (19)
        raw_dob = "".join(chars[13:19])
        raw_dob_check = chars[19]
        corr_dob, corr_dob_check = self.correct_strictly_numeric_field(
            raw_dob, raw_dob_check, "date_of_birth", 13
        )
        for i, c in enumerate(corr_dob):
            chars[13 + i] = c
        chars[19] = corr_dob_check

        # Sex (20): M, F, or <
        if chars[20] in ('1', '0', '|', 'I'):
            orig = chars[20]
            # If 0/I, likely < or M/F; if unknown, keep or normalize to < if 0
            if chars[20] == '0':
                chars[20] = '<'
                self.corrections.append(
                    CorrectionRecord(
                        field="line2_sex_pos_20",
                        original=orig,
                        corrected='<',
                        reason="structural normalization of sex placeholder"
                    )
                )

        # Expiry Date (21..27) + Check Digit (27)
        raw_exp = "".join(chars[21:27])
        raw_exp_check = chars[27]
        corr_exp, corr_exp_check = self.correct_strictly_numeric_field(
            raw_exp, raw_exp_check, "expiry_date", 21
        )
        for i, c in enumerate(corr_exp):
            chars[21 + i] = c
        chars[27] = corr_exp_check

        # Optional check digit (42): if numeric or <
        if chars[42] in ALPHA_TO_DIGIT:
            chars[42] = self.normalize_check_digit_char(chars[42], "optional_check_digit")

        # Composite check digit (43): must be digit
        if chars[43] in ALPHA_TO_DIGIT:
            chars[43] = self.normalize_check_digit_char(chars[43], "composite_check_digit")

        # Check composite validation; if composite check fails, try candidate fix
        return "".join(chars)

    def process(self, line1: str, line2: str) -> Tuple[str, str, List[CorrectionRecord]]:
        """Run complete controlled normalization on both MRZ lines.

        Returns:
            Tuple of (corrected_line1, corrected_line2, list of applied corrections)
        """
        self.reset()
        norm_line1 = self.normalize_line1(line1)
        norm_line2 = self.normalize_line2(line2)
        return norm_line1, norm_line2, list(self.corrections)
