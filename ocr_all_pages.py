#!/usr/bin/env python3
"""OCR all pages using Apple Vision framework."""

import os
import sys
from pathlib import Path

import objc
from Foundation import NSURL
from Quartz import CIImage
import Vision


def ocr_image(image_path: str) -> str:
    """Perform OCR on an image using Apple Vision."""
    image_url = NSURL.fileURLWithPath_(image_path)
    ci_image = CIImage.imageWithContentsOfURL_(image_url)

    if ci_image is None:
        return f"Error: Could not load image {image_path}"

    handler = Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(
        ci_image, None
    )

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)

    success, error = handler.performRequests_error_([request], None)

    if not success:
        return f"Error: {error}"

    results = request.results()
    lines = []

    for observation in results:
        text = observation.topCandidates_(1)[0].string()
        lines.append(text)

    return "\n".join(lines)


def main():
    input_dir = Path("highres_pages")
    output_dir = Path("ocr_output")
    output_dir.mkdir(exist_ok=True)

    pages = sorted(input_dir.glob("page-*.png"))
    total = len(pages)

    print(f"Processing {total} pages with Apple Vision OCR...")

    for i, page in enumerate(pages, 1):
        output_file = output_dir / f"{page.stem}.txt"

        text = ocr_image(str(page))
        output_file.write_text(text)

        if i % 10 == 0 or i == total:
            print(f"  {i}/{total} complete")

    print("Done! Combining into single file...")

    # Combine all text files
    combined = []
    for txt_file in sorted(output_dir.glob("page-*.txt")):
        combined.append(txt_file.read_text())

    Path("DX_Clan_ocr_clean.txt").write_text("\n".join(combined))
    print("Saved to DX_Clan_ocr_clean.txt")


if __name__ == "__main__":
    main()
