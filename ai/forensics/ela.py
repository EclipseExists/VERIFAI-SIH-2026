from PIL import Image, ImageChops, ImageOps
import io


def perform_ela(image_path, output_path="ela_output.jpg", quality=90):

    original = Image.open(image_path).convert("RGB")

    buffer = io.BytesIO()
    original.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)

    recompressed = Image.open(buffer).convert("RGB")

    difference = ImageChops.difference(original, recompressed)
    difference = difference.convert("L")

    enhanced = ImageOps.autocontrast(difference)

    enhanced.save(output_path)

    print(f"ELA result saved to: {output_path}")

    return {
        "signal": "ELA",
        "score": None,
        "severity": "review",
        "anomaly_detected": None,
        "evidence_path": output_path,
        "explanation": "Compression-level differences were analyzed for possible visual inconsistencies."
    }


if __name__ == "__main__":
    image_path = input("Enter the image path: ")
    perform_ela(image_path)