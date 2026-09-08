from PIL import Image, ImageChops, ImageOps
import io


def perform_ela(image_path, output_path="ela_output.jpg", quality=90):

    # Open the original image
    original = Image.open(image_path).convert("RGB")

    # Recompress the image in memory
    buffer = io.BytesIO()
    original.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)

    # Open the recompressed image
    recompressed = Image.open(buffer).convert("RGB")

    # Calculate pixel-level differences
    difference = ImageChops.difference(original, recompressed)

    # Convert difference map to grayscale
    difference = difference.convert("L")

    # Automatically enhance contrast for visualization
    enhanced = ImageOps.autocontrast(difference)

    # Save the ELA evidence image
    enhanced.save(output_path)

    print(f"ELA result saved to: {output_path}")

    return {
        "signal": "ELA",
        "score": None,
        "severity": "review",
        "anomaly_detected": None,
        "evidence_path": output_path,
        "explanation": (
            "Compression-level differences were analyzed "
            "for possible visual inconsistencies."
        )
    }


if __name__ == "__main__":
    image_path = input("Enter the image path: ")
    perform_ela(image_path)