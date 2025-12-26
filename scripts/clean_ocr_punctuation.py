#!/usr/bin/env python3
"""
Clean OCR punctuation before + and * markers in genealogy OCR output.

Fixes:
- † → + (OCR misread plus sign)
- • → . (bullet to dot)
- Strips garbage (-, ,, ;, :, spaces) between dots and +/* markers
"""

import re
from pathlib import Path


def clean_line(line):
    """Clean a single line of OCR text."""
    # First: convert † to + (OCR misread)
    line = line.replace('†', '+')
    # Convert • to . (bullet to dot)
    line = line.replace('•', '.')
    # Normalize em-dash and en-dash to hyphen (for date ranges)
    line = line.replace('—', '-')  # em-dash
    line = line.replace('–', '-')  # en-dash

    # Fix semicolons in dates: "Jan 22; 1978" → "Jan 22, 1978"
    # Pattern: Month Day; Year or Month; Year
    line = re.sub(r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\.?\s*\d{1,2})\s*;\s*(\d{4})', r'\1, \2', line)
    line = re.sub(r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\.?)\s*;\s*(\d{4})', r'\1 \2', line)
    # Fix trailing semicolons after date fragments: "Jul 2;" → "Jul 2,"
    line = re.sub(r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\.?\s*\d{1,2})\s*;\s*$', r'\1,', line)

    # Match lines starting with punctuation before + or *
    match = re.match(r'^([.\s\-,;:]+)([+*])(.*)$', line)
    if match:
        prefix, marker, rest = match.groups()
        # Count dots only
        dot_count = prefix.count('.')
        # Reconstruct clean line
        return '.' * dot_count + marker + rest
    return line


def clean_file(filepath):
    """Clean all lines in a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned = [clean_line(line.rstrip('\n')) for line in lines]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(cleaned))

    return len(lines)


def main():
    ocr_dir = Path(__file__).parent.parent / 'ocr_output'

    if not ocr_dir.exists():
        print(f"Error: {ocr_dir} does not exist")
        return

    files = sorted(ocr_dir.glob('page-*.txt'))
    print(f"Processing {len(files)} OCR files...")

    total_lines = 0
    for txt_file in files:
        lines = clean_file(txt_file)
        total_lines += lines

    print(f"Done! Cleaned {total_lines} lines across {len(files)} files.")


if __name__ == '__main__':
    main()
