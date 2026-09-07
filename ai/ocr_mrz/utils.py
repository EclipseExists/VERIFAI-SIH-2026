"""Utility Helpers for VERIFAI OCR + MRZ Subsystem.

Provides image decoding, synthetic test document generation, and coordinate helpers.
"""

import io
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple, List, Dict


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes into a BGR numpy array using OpenCV."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image bytes into a valid image.")
    return img


def create_synthetic_passport_image(
    line1: str,
    line2: str,
    title: str = "PASSPORT / PASSEPORT",
    country: str = "UTOPIA",
    width: int = 1200,
    height: int = 800
) -> np.ndarray:
    """Generate a clean synthetic passport document image with visual layout and TD3 MRZ.

    No real PII is used. Generated for automated visual testing and demonstration.
    """
    # Create background (light grey/cream typical for passports)
    img = Image.new("RGB", (width, height), color=(245, 245, 240))
    draw = ImageDraw.Draw(img)

    # Document border
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(100, 100, 100), width=3)
    draw.rectangle([(30, 30), (width - 30, height - 30)], outline=(180, 180, 180), width=1)

    # Top Header
    draw.text((60, 50), country, fill=(20, 30, 80))
    draw.text((60, 80), title, fill=(40, 40, 40))

    # Photo placeholder (simulated biometric portrait box)
    photo_box = [(60, 140), (320, 480)]
    draw.rectangle(photo_box, fill=(220, 225, 230), outline=(120, 120, 130), width=2)
    draw.text((120, 300), "[PHOTO / BIOMETRIC]", fill=(100, 100, 110))

    # Field labels and simulated text in the visual inspection zone (VIZ)
    fields = [
        ("Type / Type", "P"),
        ("Country Code / Code pays", country[:3].upper()),
        ("Passport No. / No de passeport", line2[0:9]),
        ("Surname / Nom", line1[5:44].split("<<")[0].replace("<", " ")),
        ("Given Names / Prenoms", line1[5:44].split("<<")[1].replace("<", " ") if "<<" in line1 else "DOE"),
        ("Nationality / Nationalite", line2[10:13]),
        ("Date of birth / Date de naissance", f"19{line2[13:15]}-{line2[15:17]}-{line2[17:19]}"),
        ("Sex / Sexe", line2[20]),
        ("Date of expiry / Date d'expiration", f"20{line2[21:23]}-{line2[23:25]}-{line2[25:27]}"),
    ]

    y_offset = 140
    for label, val in fields:
        draw.text((360, y_offset), label, fill=(120, 120, 120))
        draw.text((360, y_offset + 18), str(val), fill=(10, 10, 10))
        y_offset += 40

    # Separator above MRZ
    draw.line([(30, height - 200), (width - 30, height - 200)], fill=(160, 160, 160), width=2)

    # MRZ Zone (monospaced appearance)
    # Line 1
    draw.text((60, height - 160), line1, fill=(0, 0, 0))
    # Line 2
    draw.text((60, height - 100), line2, fill=(0, 0, 0))

    # Convert PIL to OpenCV BGR
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    return cv_img
