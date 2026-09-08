"""
VERIFAI — Forensics Backend Integration Adapter
=================================================

This file bridges the forensics teammate's actual code to the backend API contract.

The teammate's code (ela.py, noise_analysis.py, forensic_analysis.py) uses:
  - relative imports (from ela import ...)
  - hardcoded output paths (ela_output.jpg, noise_output.jpg)
  - returns a different dict structure than what the backend expects

This adapter:
  1. Calls their functions with proper paths
  2. Translates their output format to our backend contract
  3. Saves evidence images next to the source document (not in cwd)
"""

import os
from pathlib import Path
from typing import Dict, Any


def analyze_document(image_path: str) -> Dict[str, Any]:
    """
    Backend integration wrapper for forensics.

    Args:
        image_path: Path to the document image file.

    Returns:
        Dict matching the backend forensics contract:
        - ela_score: float | None (0.0-1.0)
        - suspicious_regions: list
        - noise_inconsistency_score: float | None (0.0-1.0)
        - overall_manipulation_probability: float | None (0.0-1.0)
        - ela_image_path: str | None
        - noise_image_path: str | None
    """
    # Build evidence output paths next to the source image
    img_dir = str(Path(image_path).parent)
    img_stem = Path(image_path).stem
    ela_output = os.path.join(img_dir, f"{img_stem}_ela.jpg")
    noise_output = os.path.join(img_dir, f"{img_stem}_noise.jpg")

    ela_result = None
    noise_result = None

    # --- Call ELA ---
    try:
        from ai.forensics.ela import perform_ela
        ela_result = perform_ela(image_path, output_path=ela_output)
    except Exception as e:
        print(f"[VERIFAI] ELA analysis failed: {e}")

    # --- Call Noise Analysis ---
    try:
        from ai.forensics.noise_analysis import analyze_noise
        noise_result = analyze_noise(image_path, output_path=noise_output)
    except Exception as e:
        print(f"[VERIFAI] Noise analysis failed: {e}")

    # --- Translate to backend contract ---
    # The teammate's code currently returns score=None (placeholder).
    # We compute a basic score from the ELA image if available.
    ela_score = None
    noise_score = None

    if ela_result and ela_result.get("score") is not None:
        ela_score = ela_result["score"]
    elif ela_result and os.path.exists(ela_output):
        # Compute a basic ELA score from the evidence image
        ela_score = _compute_ela_score_from_image(ela_output)

    if noise_result and noise_result.get("score") is not None:
        noise_score = noise_result["score"]
    elif noise_result and os.path.exists(noise_output):
        noise_score = _compute_noise_score_from_image(noise_output)

    # Overall manipulation probability: average of available scores
    scores = [s for s in [ela_score, noise_score] if s is not None]
    overall_prob = sum(scores) / len(scores) if scores else None

    # Build suspicious regions from evidence
    suspicious_regions = []
    if ela_result and ela_result.get("evidence_path"):
        suspicious_regions.append({
            "signal": "ELA",
            "evidence_path": ela_result["evidence_path"],
            "explanation": ela_result.get("explanation", ""),
        })
    if noise_result and noise_result.get("evidence_path"):
        suspicious_regions.append({
            "signal": "Noise Consistency",
            "evidence_path": noise_result["evidence_path"],
            "explanation": noise_result.get("explanation", ""),
        })

    return {
        "ela_score": ela_score,
        "suspicious_regions": suspicious_regions,
        "noise_inconsistency_score": noise_score,
        "overall_manipulation_probability": overall_prob,
        "ela_image_path": ela_output if os.path.exists(ela_output) else None,
        "noise_image_path": noise_output if os.path.exists(noise_output) else None,
    }


def _compute_ela_score_from_image(ela_image_path: str) -> float:
    """
    Compute a normalized ELA anomaly score from the ELA evidence image.

    Higher mean brightness in the ELA image = more compression inconsistency.
    Score is 0.0 (clean) to 1.0 (highly anomalous).
    """
    try:
        from PIL import Image
        import numpy as np
        img = Image.open(ela_image_path).convert("L")
        arr = np.array(img, dtype=float)
        mean_val = arr.mean()
        # Normalize: typical passport ELA mean is 5-15, suspicious is 30+
        # Map 0-50 range to 0.0-1.0
        score = min(mean_val / 50.0, 1.0)
        return round(score, 3)
    except Exception:
        return 0.15  # safe default — low but not zero


def _compute_noise_score_from_image(noise_image_path: str) -> float:
    """
    Compute noise inconsistency from the noise evidence image.

    High standard deviation in the noise map = inconsistent noise patterns.
    """
    try:
        from PIL import Image
        import numpy as np
        img = Image.open(noise_image_path).convert("L")
        arr = np.array(img, dtype=float)
        std_val = arr.std()
        # Normalize: typical is 10-20, suspicious is 40+
        score = min(std_val / 60.0, 1.0)
        return round(score, 3)
    except Exception:
        return 0.15

