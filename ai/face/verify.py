from deepface import DeepFace
import numpy as np


class FaceVerificationError(Exception):
    """Raised when a face cannot be detected in one of the provided images."""
    pass


def _get_embedding(image_path: str):
    try:
        result = DeepFace.represent(
            img_path=image_path,
            model_name="Facenet",
            detector_backend="opencv",
            enforce_detection=False
        )
    except ValueError as e:
        raise FaceVerificationError(
            f"Could not detect a face in image: {image_path}"
        ) from e
    return result[0]["embedding"]


def _cosine_similarity(vec_a, vec_b) -> float:
    vec_a = np.array(vec_a)
    vec_b = np.array(vec_b)
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    return float(dot_product / (norm_a * norm_b))


def _get_band(similarity_score: float) -> str:
    if similarity_score >= 0.60:
        return "match"
    elif similarity_score >= 0.50:
        return "uncertain"
    else:
        return "mismatch"


def verify_faces(image_path_1: str, image_path_2: str) -> dict:
    """
    Compare two face images and return a similarity score + band.

    Args:
        image_path_1: file path to the first image (e.g. document photo)
        image_path_2: file path to the second image (e.g. live/probe photo)

    Returns:
        dict: {"similarity_score": float (0.0-1.0), "band": "match" | "uncertain" | "mismatch"}
    Raises:
        FaceVerificationError: if a face cannot be detected in either image

    Known limitation:
        This function does not itself check image quality (blur, darkness,
        resolution). Testing showed that severely blurred or underlit images
        can still pass face detection but produce an incorrect "mismatch"
        result for the same person (false negative). This module assumes
        the upstream Image Quality Gate (see Project Bible Section 7) has
        already rejected/flagged unusable images before they reach this
        function.
    """

    embedding_1 = _get_embedding(image_path_1)
    embedding_2 = _get_embedding(image_path_2)

    similarity_score = _cosine_similarity(embedding_1, embedding_2)
    band = _get_band(similarity_score)

    return {
        "similarity_score": round(similarity_score, 4),
        "band": band,
    }


if __name__ == "__main__":
    # Quick manual test — run with: python3 ai/face/verify.py
    result = verify_faces("doc_photo.jpg", "live_photo.jpg")
    print(result)
