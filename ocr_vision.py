#!/usr/bin/env python3
"""OCR using Apple Vision framework."""

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

    # Create request handler
    handler = Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(
        ci_image, None
    )

    # Create text recognition request
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)

    # Perform request
    success, error = handler.performRequests_error_([request], None)

    if not success:
        return f"Error: {error}"

    # Extract text
    results = request.results()
    lines = []

    for observation in results:
        text = observation.topCandidates_(1)[0].string()
        lines.append(text)

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python ocr_vision.py <image_path> [output_path]")
        sys.exit(1)

    image_path = sys.argv[1]

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        output_path = None

    text = ocr_image(image_path)

    if output_path:
        Path(output_path).write_text(text)
        print(f"Saved to {output_path}")
    else:
        print(text)


if __name__ == "__main__":
    main()
