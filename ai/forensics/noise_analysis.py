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

    # Save the noise analysis result
    noise.save(output_path)

    print(f"Noise analysis result saved to: {output_path}")

    # Return information for the forensic pipeline
    return {
    "signal": "Noise Consistency",
    "score": None,
    "severity": "review",
    "anomaly_detected": None,
    "evidence_path": output_path,
    "explanation": "Local noise and texture differences were visualized to identify regions that may require further investigation."
}


if __name__ == "__main__":
    image_path = input("Enter the image path: ")
    analyze_noise(image_path)