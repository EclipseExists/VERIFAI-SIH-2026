from pathlib import Path

from .ela import perform_ela
from .noise_analysis import analyze_noise


def analyze_document(image_path: str) -> tuple:
    """
    Run ELA and noise analysis on a document image.

    Returns:
        forensic_evidence: visual forensic evidence and paths
        risk_signals: empty list until reliable forensic
                      scoring is available
    """

    # Check that the input file exists
    input_path = Path(image_path)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Document image not found: {image_path}"
        )

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

    # Store visual forensic evidence
    forensic_evidence = {
        "ela_score": ela_result["score"],
        "suspicious_regions": noise_result.get(
            "suspicious_regions", []
        ),
        "noise_inconsistency_score": noise_result["score"],
        "overall_manipulation_probability": None,
        "ela_image_path": str(ela_path),
        "noise_image_path": str(noise_path)
    }

    # Do not send forensic evidence to the Risk Engine
    # until reliable scoring/normalization is available.
    risk_signals = []

    return forensic_evidence, risk_signals


if __name__ == "__main__":
    image_path = input("Enter the image path: ")

    evidence, signals = analyze_document(image_path)

    print("\nForensic Evidence:")
    print(evidence)

    print("\nRisk Signals:")
    print(signals)