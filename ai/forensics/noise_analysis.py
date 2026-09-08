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

    # Numerical scoring is not used yet because a simple
    # global score produced the same high value for both
    # genuine and tampered documents.
    noise_score = None

    # Region detection is also left empty until a
    # reliable localization method is implemented.
    suspicious_regions = []

    return {
        "signal": "Noise Consistency",
        "score": noise_score,
        "severity": "review",
        "anomaly_detected": None,
        "evidence_path": output_path,
        "suspicious_regions": suspicious_regions,
        "explanation": (
            "Local noise and texture differences were visualized "
            "to identify regions that may require further investigation."
        )
    }


if __name__ == "__main__":
    image_path = input("Enter the image path: ")
    analyze_noise(image_path)