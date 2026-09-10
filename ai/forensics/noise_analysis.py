from PIL import Image, ImageFilter, ImageChops


def analyze_noise(image_path, output_path="noise_output.jpg"):
    """
    Analyze local noise/texture consistency in an image.

    image_path: path to the input image
    output_path: where the noise analysis result will be saved
    """

    # Open the original image
    original = Image.open(image_path).convert("RGB")

    # Create a blurred version of the image
    blurred = original.filter(ImageFilter.GaussianBlur(radius=2))

    # Calculate the difference between original and blurred image
    noise = ImageChops.difference(original, blurred)

    # Convert the noise map to grayscale
    noise = noise.convert("L")

    # Increase contrast so noise patterns are easier to see
    noise = noise.point(lambda pixel: min(pixel * 5, 255))

    # Save the noise evidence image
    noise.save(output_path)

    print(f"Noise analysis result saved to: {output_path}")

    # Numerical scoring using localized noise inconsistency across homogeneous regions.
    # In authentic documents, background sensor noise is uniform (low score).
    # Spliced or digitally manipulated documents exhibit localized noise disparity.
    noise_score = _compute_local_noise_inconsistency(image_path)

    anomaly_detected = bool(noise_score >= 0.50) if noise_score is not None else False
    severity = "high" if noise_score and noise_score >= 0.60 else ("medium" if noise_score and noise_score >= 0.40 else "low")
    suspicious_regions = []

    return {
        "signal": "Noise Consistency",
        "score": noise_score,
        "severity": severity,
        "anomaly_detected": anomaly_detected,
        "evidence_path": output_path,
        "suspicious_regions": suspicious_regions,
        "explanation": (
            "Local noise and texture differences were analyzed "
            "to identify regions that may require further investigation."
        )
    }


def _compute_local_noise_inconsistency(image_path: str) -> float:
    """Compute normalized noise inconsistency score across flat regions."""
    try:
        import numpy as np
        img = Image.open(image_path).convert("L")
        arr = np.array(img, dtype=float)

        # 3x3 discrete Laplacian operator for high-frequency noise extraction
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
    analyze_noise(image_path)