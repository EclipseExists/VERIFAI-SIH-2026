from ela import perform_ela
from noise_analysis import analyze_noise


def analyze_forensics(image_path):
    """
    Run all forensic analyses on an image.
    """

    ela_result = perform_ela(
        image_path,
        output_path="ela_output.jpg"
    )

    noise_result = analyze_noise(
        image_path,
        output_path="noise_output.jpg"
    )

    return {
        "forensic_signals": [
            ela_result,
            noise_result
        ]
    }


if __name__ == "__main__":
    image_path = input("Enter the image path: ")

    result = analyze_forensics(image_path)

    print("\nForensic Analysis Result:")
    print(result)