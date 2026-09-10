import os
from pathlib import Path
from typing import Dict, Any, Tuple

from ai.forensics.ela import perform_ela
from ai.forensics.noise_analysis import analyze_noise


def analyze_document(image_path: str) -> Dict[str, Any]:
    """
    Run ELA and noise analysis on a document image.
    Bridged to the backend API contract.

    Returns:
        Dict matching the backend forensics contract:
        - ela_score: float | None
        - suspicious_regions: list
        - noise_inconsistency_score: float | None
        - overall_manipulation_probability: float | None
        - ela_image_path: str | None
        - noise_image_path: str | None
    """
    input_path = Path(image_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Document image not found: {image_path}")

    # Create evidence paths next to the source document
    output_dir = input_path.parent
    file_stem = input_path.stem

    ela_path = output_dir / f"{file_stem}_ela.png"
    noise_path = output_dir / f"{file_stem}_noise.png"

    # Run ELA analysis
    ela_result = perform_ela(
        image_path,
        output_path=str(ela_path)
    )

    # Run noise analysis
    noise_result = analyze_noise(
        image_path,
        output_path=str(noise_path)
    )

    # Check if we got valid scores back, otherwise compute defaults based on evidence presence
    ela_score = ela_result.get("score")
    if ela_score is None and ela_path.exists():
        ela_score = _compute_ela_score_from_image(str(ela_path))
        
    noise_score = noise_result.get("score")
    if noise_score is None:
        noise_score = _compute_noise_score_from_image(image_path)

    # Calculate overall probability if scores exist
    scores = [float(s) for s in [ela_score, noise_score] if s is not None]
    overall_prob = round(float(sum(scores) / len(scores)), 3) if scores else None

    # Store visual forensic evidence matching backend schema
    forensic_evidence = {
        "ela_score": float(ela_score) if ela_score is not None else None,
        "suspicious_regions": noise_result.get("suspicious_regions", []),
        "noise_inconsistency_score": float(noise_score) if noise_score is not None else None,
        "overall_manipulation_probability": overall_prob,
        "ela_image_path": str(ela_path) if ela_path.exists() else None,
        "noise_image_path": str(noise_path) if noise_path.exists() else None
    }

    return forensic_evidence


def _compute_ela_score_from_image(ela_image_path: str) -> float:
    """
    Compute a normalized ELA anomaly score from the ELA evidence image.
    Higher mean brightness = more compression inconsistency.
    """
    try:
        from PIL import Image
        import numpy as np
        img = Image.open(ela_image_path).convert("L")
        arr = np.array(img, dtype=float)
        mean_val = arr.mean()
        score = min(mean_val / 50.0, 1.0)
        return round(float(score), 3)
    except Exception:
        return 0.15


def _compute_noise_score_from_image(image_path: str) -> float:
    """
    Compute localized noise inconsistency score across homogeneous/flat regions.
    High inconsistency across flat regions indicates potential digital splicing.
    """
    try:
        from PIL import Image
        import numpy as np
        img = Image.open(image_path).convert("L")
        arr = np.array(img, dtype=float)

        # 3x3 discrete Laplacian operator
        lap = (
            arr[1:-1, :-2]
            + arr[1:-1, 2:]
            + arr[:-2, 1:-1]
            + arr[2:, 1:-1]
            - 4.0 * arr[1:-1, 1:-1]
        )

        block_size = 32
        h, w = lap.shape
        block_sigmas = []
        for y in range(0, h - block_size + 1, block_size):
            for x in range(0, w - block_size + 1, block_size):
                blk = lap[y:y + block_size, x:x + block_size]
                med = np.median(blk)
                mad = np.median(np.abs(blk - med))
                sigma = 1.4826 * mad
                block_sigmas.append(sigma)

        block_sigmas = np.array(block_sigmas)
        valid = block_sigmas[(block_sigmas > 0.05) & (block_sigmas < np.percentile(block_sigmas, 80))]
        if len(valid) < 5:
            return 0.10

        mean_s = np.mean(valid)
        std_s = np.std(valid)
        cv = std_s / (mean_s + 1e-5)
        score = min(max((cv - 0.15) / 1.2, 0.05), 1.0)
        return round(float(score), 3)
    except Exception:
        return 0.15


if __name__ == "__main__":
    image_path = input("Enter the image path: ")
    evidence = analyze_document(image_path)
    print("\nForensic Evidence:")
    print(evidence)
