"""Command Line Interface for VERIFAI OCR + MRZ Module.

Allows testing and running passport verification directly from the terminal.

Usage:
    python -m ocr_mrz.cli path/to/passport.png
    python -m ocr_mrz.cli path/to/passport.png --mock
"""

import sys
import json
import argparse
from pathlib import Path
from ocr_mrz import process_passport


def main():
    parser = argparse.ArgumentParser(
        prog="ocr_mrz",
        description="VERIFAI Passport OCR & MRZ Inspection CLI"
    )
    parser.add_argument(
        "image_path",
        type=str,
        help="Path to passport image file (PNG, JPG, JPEG, WEBP, BMP, TIFF)"
    )
    parser.add_argument(
        "--engine",
        choices=["paddle", "mock"],
        default="paddle",
        help="OCR backend engine (default: 'paddle')"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Shorthand for --engine mock (fast dry-run testing)"
    )

    args = parser.parse_args()

    img_path = Path(args.image_path)
    if not img_path.exists():
        print(f"Error: Image file not found: {img_path}", file=sys.stderr)
        sys.exit(1)

    engine_type = "mock" if args.mock else args.engine

    print(f"Processing passport image: {img_path} (engine={engine_type})...")
    result = process_passport(str(img_path), engine_type=engine_type)

    output = result.model_dump()
    print("\n" + "=" * 60)
    print("VERIFICATION RESULT")
    print("=" * 60)
    print(json.dumps(output, indent=2, default=str))

    if result.success and result.mrz_present:
        print("\nSUMMARY:")
        print(f"  Holder Name:     {result.identity.name}")
        print(f"  Passport Number: {result.identity.passport_number}")
        print(f"  Nationality:     {result.identity.nationality}")
        print(f"  DOB:             {result.identity.date_of_birth}")
        print(f"  Expiry:          {result.identity.expiry_date}")
        print(f"  Checksum Valid:  {result.mrz_validation.overall}")
        print(f"  Tampering Risk:  {result.risk.tampering_detected}")
        if result.risk.details:
            print("  Risk Warnings:")
            for d in result.risk.details:
                print(f"    - {d}")
        sys.exit(0)
    else:
        print("\nVERIFICATION FAILED OR MRZ NOT LOCATED")
        for d in result.risk.details:
            print(f"  - {d}")
        sys.exit(1)


if __name__ == "__main__":
    main()
