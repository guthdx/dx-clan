#!/usr/bin/env python3
"""
Smart genealogy parser for DX Clan database.

This parser reads OCR output intelligently, using generation numbers (1-9)
as the primary indicator of hierarchy, not the inconsistent dot notation.

Key insights:
- Numbers 1-9 at line start indicate generation level
- + or † indicates a spouse
- * indicates a second/subsequent spouse listing
- Dots/periods are unreliable due to OCR noise
"""

import re
import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path


@dataclass
class Person:
    """Represents a person in the genealogy."""
    name: str
    birth_year: Optional[int] = None
    birth_year_circa: bool = False
    death_year: Optional[int] = None
    death_year_circa: bool = False
    gender: Optional[str] = None
    generation: Optional[int] = None
    notes: str = ""

    # Relationships - stored as names for later resolution
    parents: list = field(default_factory=list)
    spouses: list = field(default_factory=list)
    children: list = field(default_factory=list)


@dataclass
class ParsedEntry:
    """A parsed line from the genealogy document."""
    generation: int
    is_spouse: bool
    is_relisting: bool  # For * entries - person re-listed for additional marriages
    name: str
    birth_year: Optional[int]
    birth_year_circa: bool
    death_year: Optional[int]
    death_year_circa: bool
    raw_line: str


def extract_years(text: str) -> tuple:
    """
    Extract birth and death years from a text string.
    Returns (birth_year, birth_circa, death_year, death_circa)
    """
    birth_year = None
    death_year = None
    birth_circa = False
    death_circa = False

    # Pattern for date ranges like "Sep 14, 1910 - Jul 20, 1981" or "1893 - Dec 21, 1915"
    # The pattern handles: YEAR - [optional month day] YEAR
    range_pattern = r'(\d{4})\s*[-–]\s*(?:[A-Za-z]+\s+\d+,?\s*)?(\d{4})'
    range_match = re.search(range_pattern, text)
    if range_match:
        birth_year = int(range_match.group(1))
        death_year = int(range_match.group(2))
        # Skip the date_pattern logic since we already found the range
    else:
        # Pattern for full dates like "May 3, 1941"
        date_pattern = r'([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})'
        dates = re.findall(date_pattern, text)

        if len(dates) >= 2:
            birth_year = int(dates[0][2])
            death_year = int(dates[1][2])
        elif len(dates) == 1:
            # Single date - check context
            if 'b.' in text.lower() or '-' not in text:
                birth_year = int(dates[0][2])
            elif 'd.' in text.lower():
                death_year = int(dates[0][2])
            else:
                birth_year = int(dates[0][2])

    # Try simpler year patterns if no dates found
    if birth_year is None and death_year is None:
        year_pattern = r'\b(1[6-9]\d{2}|20[0-2]\d)\b'
        years = re.findall(year_pattern, text)

        if len(years) >= 2:
            birth_year = int(years[0])
            death_year = int(years[1])
        elif len(years) == 1:
            birth_year = int(years[0])

    # Check for circa indicators
    if birth_year and re.search(r'c\.?\s*' + str(birth_year), text):
        birth_circa = True
    if death_year and re.search(r'c\.?\s*' + str(death_year), text):
        death_circa = True

    # Validate years are reasonable (1650-2025)
    # Reject obvious OCR errors like 199, 1097, 9694
    if birth_year and (birth_year < 1650 or birth_year > 2025):
        birth_year = None
        birth_circa = False
    if death_year and (death_year < 1650 or death_year > 2025):
        death_year = None
        death_circa = False

    # Also check death is not before birth
    if birth_year and death_year and death_year < birth_year:
        # Keep the more plausible one (usually birth year is more reliable)
        death_year = None
        death_circa = False

    return birth_year, birth_circa, death_year, death_circa


def clean_name(text: str) -> str:
    """Extract and clean the person's name from text."""
    # Remove date information (full dates like "May 30, 1982")
    name = re.sub(r'[A-Za-z]{3}\s+\d{1,2},?\s*\d{4}', '', text)
    name = re.sub(r'\b\d{4}\b', '', name)

    # Remove partial dates stuck at end, including with trailing garbage
    # Handles: "Jun 29", "Aug 1B", "Mar 1B, (a)", "Oct 30, 197", "Apr 29"
    name = re.sub(r'\s+[A-Za-z]{3}\s+\d+[A-Za-z]?[;:,]?\s*\d*\s*(\([a-z]\))?\s*$', '', name)

    # Remove dates with full format but OCR errors (like "Jul 2, 19 78" or "Feb 6, 198B")
    name = re.sub(r'\s*-?\s*[A-Za-z]{3}\s+\d{1,2},?\s*\d+\s*\d*[A-Za-z]?\s*$', '', name)

    # Remove trailing numbers (like "78" at end of "Brandy Lee Goff 78")
    name = re.sub(r'\s+\d+\s*$', '', name)

    # Remove OCR garbage fragments (like "sua 19," or "E991")
    name = re.sub(r'\s+[a-z]+\s+\d+[,;]?\s*$', '', name)
    name = re.sub(r'\s+[A-Z]\d+\s*$', '', name)

    # Remove parenthetical notes like "(baby)" or "(a)"
    name = re.sub(r'\([a-z]+\)\s*', '', name)

    # Remove common suffixes that got separated
    name = re.sub(r'\s*[-–]\s*$', '', name)

    # Remove various markers (including colons and semicolons)
    name = re.sub(r'[•†*+\.]+', ' ', name)

    # Replace colons and semicolons with space (they shouldn't be in names)
    name = re.sub(r'[:;]', ' ', name)

    # Remove OCR artifacts (em-dash, tilde, equals, etc.)
    name = re.sub(r'[—~=|\\@#$%^&*<>]', '', name)

    # Clean up
    name = re.sub(r'\s+', ' ', name).strip()

    # Run date removal again after cleanup (catches more cases)
    name = re.sub(r'\s+[A-Za-z]{3}\s+\d+[A-Za-z]?[;:,]?\s*\d*\s*$', '', name)

    # Remove leading/trailing punctuation
    name = re.sub(r'^[,\-\s]+|[,\-\s]+$', '', name)

    # Remove leading generation numbers (1-9) that got stuck in the name
    # Pattern: starts with single digit followed by space and uppercase letter
    name = re.sub(r'^(\d)\s+(?=[A-Z])', '', name)

    # Also remove if it's just digits and spaces at the start
    name = re.sub(r'^[\d\s]+(?=[A-Za-z])', '', name)

    return name


def is_valid_name(name: str) -> bool:
    """
    Check if a name is valid (not garbage OCR).
    Returns False for names that are:
    - Too short (< 3 chars)
    - Only numbers/punctuation
    - Don't contain any letters
    - Look like dates (month + number)
    - Are mostly garbage characters
    """
    if not name or len(name) < 3:
        return False

    # Must contain at least one letter
    if not re.search(r'[A-Za-z]', name):
        return False

    # Should not be just numbers with spaces/punctuation
    if re.match(r'^[\d\s\.\-\,\+]+$', name):
        return False

    # Reject names that look like dates (e.g., "Jun 9", "Oct 19", "Qct 19")
    if re.match(r'^[A-Za-z]{3,4}\s+\d+$', name):
        return False

    # Reject names that are mostly lowercase garbage (like "on 20", "tep' 159")
    if re.match(r'^[a-z]+[\s\'\d]+$', name):
        return False

    # Reject names with numbers in the middle (like "Teacy 1 Sehe")
    # But allow suffixes like "Jr" "Sr" "II" "III" at end
    name_without_suffix = re.sub(r',?\s*(Jr|Sr|II|III|IV|I)\s*$', '', name, flags=re.IGNORECASE)
    if re.search(r'\s\d+\s', name_without_suffix):
        return False

    return True


def parse_line(line: str) -> Optional[ParsedEntry]:
    """
    Parse a single line from the genealogy document.
    Returns None if the line doesn't contain a person entry.
    """
    original_line = line
    line = line.strip()

    if not line:
        return None

    # Skip index pages and page numbers
    if re.match(r'^\d+$', line):
        return None
    if 'INDEX OF DESCENDANT' in line.upper():
        return None
    if re.match(r'^[A-Za-z]+,\s*[A-Za-z]+\.+\s*\d+$', line):
        return None

    # Detect if this is a spouse entry
    # NOTE: + or † indicates a spouse
    # NOTE: * indicates a RE-LISTING of a person for additional marriages
    #       (the person is NOT a spouse, they are being re-listed so their
    #        next spouse can be shown). Treat * entries as regular persons.
    is_spouse = False
    is_relisting = False  # Person re-listed for additional marriages

    if line.startswith(('+', '†', '.+', '..+', '...+')):
        is_spouse = True
    elif line.startswith(('*', '.*', '..*', '...*')):
        # This is a re-listing of a person, NOT a spouse entry
        is_relisting = True
        # Strip the * prefix for cleaner parsing
        line = re.sub(r'^[.*]+\s*', '', line)

    # Extract generation number - look for pattern like "5 Name" or ".5 Name"
    # Also handle OCR noise like commas, colons, semicolons: "....,5 Name"
    gen_match = re.match(r'^[•.*†+,;:\-/\s]*(\d)\s+', line)
    if gen_match:
        generation = int(gen_match.group(1))
        line = line[gen_match.end():]
    else:
        # Try to find generation number elsewhere in the line
        gen_search = re.search(r'(?:^|\s)(\d)\s+[A-Z]', line)
        if gen_search:
            generation = int(gen_search.group(1))
        else:
            # If no generation found, might be continuation or spouse
            generation = None

    # If this is a spouse line, we don't need a generation number
    if is_spouse and generation is None:
        generation = 0  # Will be handled specially

    if generation is None:
        return None

    # Extract years
    birth_year, birth_circa, death_year, death_circa = extract_years(line)

    # Extract name
    name = clean_name(line)

    # Validate name is not garbage OCR
    if not is_valid_name(name):
        return None

    return ParsedEntry(
        generation=generation,
        is_spouse=is_spouse,
        is_relisting=is_relisting,
        name=name,
        birth_year=birth_year,
        birth_year_circa=birth_circa,
        death_year=death_year,
        death_year_circa=death_circa,
        raw_line=original_line
    )


def preprocess_lines(lines: list) -> list:
    """
    Preprocess OCR lines to handle multi-line entries.

    Handles cases like:
    - Line 1: "6"              (just generation number)
    - Line 2: "Franklin Delano Ducheneaux"  (name)
    - Line 3: "Jan 30, 1940"   (birth date on separate line)

    These should all be joined into one entry.
    """
    processed = []
    i = 0

    # Pattern for lines that are just dates (birth/death info)
    date_only_pattern = re.compile(
        r'^[•.*†+,;:\-/\s]*'  # Optional OCR noise prefix
        r'('
        r'[A-Za-z]{3}\s+\d{1,2},?\s*\d{4}'  # "Jan 30, 1940"
        r'|'
        r'\d{4}\s*[-–]\s*'  # "1940 -" (partial date range)
        r'|'
        r'[-–]\s*[A-Za-z]{3}\s+\d{1,2},?\s*\d{4}'  # "- Mar 13, 1976"
        r'|'
        r'[A-Za-z]{3}\s+\d{1,2},?\s*\d{4}\s*[-–]\s*[A-Za-z]{3}\s+\d{1,2},?\s*\d{4}'  # Full range
        r'|'
        r'\d{4}'  # Just a year like "1952"
        r')'
        r'\s*$'
    )

    # Pattern for lines ending with partial date (month day,) needing year from next line
    partial_date_ending = re.compile(r'[A-Za-z]{3}\s+\d{1,2},\s*$')
    year_only_pattern = re.compile(r'^[•.*†+,;:\-/\s]*(\d{4})\s*$')

    # Pattern for lines that look like date fragments (year, month day, ranges)
    # Matches: "1940 - Jan 1," or "1963" or "Jan 1, 1963" etc.
    date_fragment_pattern = re.compile(
        r'^[•.*†+,;:\-/\s]*'  # Optional leading punctuation
        r'('
        r'\d{4}'  # Year
        r'|'
        r'\d{4}\s*[-–]'  # Year followed by dash (death range start)
        r'|'
        r'\d{4}\s*[-–]\s*[A-Za-z]{3}\s+\d{1,2},?'  # "1940 - Jan 1,"
        r')'
    )

    while i < len(lines):
        line = lines[i].rstrip()

        # Check if this line is just a generation number (with optional prefixes)
        # Pattern: punctuation/dots followed by single digit, nothing else meaningful
        just_gen = re.match(r'^[•.*†+,;:\-/\s]*(\d)\s*$', line)

        if just_gen and i + 1 < len(lines):
            # This is just a generation number - join with next line(s)
            next_line = lines[i + 1].rstrip()
            combined = line + ' ' + next_line
            i += 2

            # Check if the following line is just a date - join it too
            while i < len(lines):
                following = lines[i].rstrip()
                if date_only_pattern.match(following):
                    combined = combined + ' ' + following
                    i += 1
                else:
                    break

            processed.append(combined)
        else:
            # Check if current line ends with partial date like "May 20,"
            # and next line(s) are date fragments (year, "1940 - Jan 1,", etc.)
            if i + 1 < len(lines) and partial_date_ending.search(line):
                combined = line
                j = i + 1
                # Keep joining while next lines look like date fragments
                while j < len(lines):
                    next_line = lines[j].rstrip()
                    if date_fragment_pattern.match(next_line):
                        combined = combined + ' ' + next_line
                        j += 1
                    else:
                        break
                if j > i + 1:  # We joined at least one line
                    processed.append(combined)
                    i = j
                    continue

            # Check if current line is a name and next line is just a date
            # (handles cases where gen+name are together but date is separate)
            if i + 1 < len(lines):
                next_line = lines[i + 1].rstrip()
                if date_only_pattern.match(next_line):
                    # Join name line with date line
                    combined = line + ' ' + next_line
                    processed.append(combined)
                    i += 2
                    continue

            processed.append(line)
            i += 1

    return processed


def parse_ocr_pages(ocr_dir: str, start_page: int = 3, end_page: int = 251) -> list:
    """
    Parse all OCR pages and build a list of parsed entries with context.

    Returns a list of (entry, parent_context) tuples.
    """
    entries = []

    # Stack to track the current person at each generation level
    # gen_stack[generation] = most recent person at that generation
    gen_stack = {}

    for page_num in range(start_page, end_page + 1):
        page_file = Path(ocr_dir) / f"page-{page_num:03d}.txt"
        if not page_file.exists():
            continue

        with open(page_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Preprocess to handle multi-line entries
        lines = preprocess_lines(lines)

        for line_num, line in enumerate(lines):
            # Handle multi-line entries by joining continuation lines
            entry = parse_line(line)

            if entry is None:
                continue

            # Determine parent context
            parent_name = None

            if entry.is_spouse:
                # Spouses attach to the most recent non-spouse entry
                if entries and not entries[-1][0].is_spouse:
                    parent_name = None  # Will be linked as spouse, not child
                    spouse_of = entries[-1][0].name
                else:
                    spouse_of = None
            elif entry.generation > 1:
                # Children attach to the parent at generation - 1
                parent_gen = entry.generation - 1
                if parent_gen in gen_stack:
                    parent_name = gen_stack[parent_gen]

            # Update the generation stack
            if not entry.is_spouse:
                gen_stack[entry.generation] = entry.name
                # Clear any higher generations (they're no longer in context)
                for g in list(gen_stack.keys()):
                    if g > entry.generation:
                        del gen_stack[g]

            entries.append((entry, parent_name, page_num))

    return entries


def build_persons_dict(entries: list) -> dict:
    """
    Build a dictionary of persons from parsed entries.
    Uses (name, birth_year) as key for deduplication.

    IMPORTANT: Only use the FIRST appearance's parent relationship.
    This is because in genealogy documents, the first appearance is usually
    the primary listing under the person's actual parents. Subsequent
    appearances are references under spouse's families (wrong parents).
    """
    persons = {}
    # Track which persons have already had their parents set
    parents_set = set()

    current_person = None

    for entry, parent_name, page_num in entries:
        # Create a key for this person
        key = (entry.name.lower(), entry.birth_year)

        is_new_person = key not in persons

        if is_new_person:
            persons[key] = Person(
                name=entry.name,
                birth_year=entry.birth_year,
                birth_year_circa=entry.birth_year_circa,
                death_year=entry.death_year,
                death_year_circa=entry.death_year_circa,
                generation=entry.generation if not entry.is_spouse else None
            )

        person = persons[key]

        # Update with any new information
        if entry.death_year and not person.death_year:
            person.death_year = entry.death_year
            person.death_year_circa = entry.death_year_circa

        if entry.generation and not person.generation:
            person.generation = entry.generation

        # Handle relationships
        if entry.is_spouse and current_person:
            # This is a spouse of the current person
            current_person_key = (current_person.name.lower(), current_person.birth_year)
            if current_person_key in persons:
                curr = persons[current_person_key]
                if entry.name not in curr.spouses:
                    curr.spouses.append(entry.name)
                if curr.name not in person.spouses:
                    person.spouses.append(curr.name)
        else:
            # This is a regular person entry
            current_person = person

            # ONLY add parent relationship for the FIRST appearance
            # This prevents wrong parent relationships from subsequent listings
            # BOTH directions (parent->child and child->parent) should only be set once
            if parent_name and key not in parents_set:
                parents_set.add(key)

                # Find the parent in our persons dict
                parent_key = None
                for k, p in persons.items():
                    if k[0] == parent_name.lower():
                        parent_key = k
                        break

                if parent_key:
                    parent = persons[parent_key]
                    # Add bidirectional relationship ONLY for first appearance
                    if entry.name not in parent.children:
                        parent.children.append(entry.name)
                    if parent.name not in person.parents:
                        person.parents.append(parent.name)
            # NOTE: If key is already in parents_set, we do NOT add any relationships
            # This prevents subsequent appearances from creating wrong parent-child links

    return persons


def infer_gender(name: str, spouses: list, children: list) -> Optional[str]:
    """Infer gender from name and relationships."""
    name_lower = name.lower()

    # Female indicators
    female_names = ['mary', 'anna', 'annie', 'marie', 'rose', 'ruth', 'regina',
                    'lois', 'delores', 'ann', 'lisa', 'collette', 'lorelei',
                    'margaret', 'josephine', 'sophia', 'angelique', 'catherine',
                    'elizabeth', 'julia', 'esther', 'emma', 'lillian', 'lillie']

    male_names = ['john', 'james', 'joseph', 'william', 'henry', 'louis',
                  'wayne', 'theodore', 'bazil', 'zachary', 'guthrie', 'bud',
                  'frank', 'charles', 'george', 'peter', 'thomas', 'michael']

    first_name = name.split()[0].lower() if name else ''

    if any(fn in first_name for fn in female_names):
        return 'F'
    if any(mn in first_name for mn in male_names):
        return 'M'

    # Check for suffixes
    if ', sr' in name_lower or ', jr' in name_lower or ', ii' in name_lower:
        return 'M'  # Usually male

    return None


def merge_duplicates(persons: dict) -> dict:
    """
    Merge duplicate person entries.

    When the same person appears with (name, birth_year) and (name, None),
    merge them into a single entry, preferring the one with birth_year.
    Also shares children between spouses.
    """
    from collections import defaultdict

    # Group by normalized name
    by_name = defaultdict(list)
    for key, person in persons.items():
        normalized = key[0]  # name is already lowercase
        by_name[normalized].append((key, person))

    merged = {}

    for name, entries in by_name.items():
        if len(entries) == 1:
            # No duplicates
            merged[entries[0][0]] = entries[0][1]
        else:
            # Multiple entries with same name - merge them
            # Prefer the one with birth_year
            with_birth = [e for e in entries if e[0][1] is not None]
            without_birth = [e for e in entries if e[0][1] is None]

            if with_birth:
                # Use the entry with birth year as base
                base_key, base = with_birth[0]
            else:
                # Use first entry if none have birth year
                base_key, base = without_birth[0]

            # Merge data from other entries
            for key, other in entries:
                if key == base_key:
                    continue

                # Merge death year if missing
                if not base.death_year and other.death_year:
                    base.death_year = other.death_year
                    base.death_year_circa = other.death_year_circa

                # Merge generation if missing
                if not base.generation and other.generation:
                    base.generation = other.generation

                # Merge parents (take first non-empty)
                if not base.parents and other.parents:
                    base.parents = other.parents

                # Merge spouses (union)
                for spouse in other.spouses:
                    if spouse not in base.spouses:
                        base.spouses.append(spouse)

                # Merge children (union)
                for child in other.children:
                    if child not in base.children:
                        base.children.append(child)

            merged[base_key] = base

    return merged


def share_children_between_spouses(persons: dict) -> None:
    """
    Ensure that children's parent lists include both parents when married.

    IMPORTANT: This does NOT add arbitrary parent relationships.
    It ONLY adds the spouse of an existing parent as a second parent.
    If a child already has parent A, and A is married to B, then B is added.

    CRITICAL: A child can have at most 2 biological parents. This function
    will NOT add more than 2 parents to any person.
    """
    # Build a lookup by name for finding persons
    by_name = {}
    for key, person in persons.items():
        by_name[key[0]] = person  # key[0] is lowercase name

    # For each person who has exactly 1 parent, try to add the second parent
    # (the spouse of the first parent)
    for key, person in persons.items():
        # Only process if person has exactly 1 parent
        if len(person.parents) != 1:
            continue

        parent_name = person.parents[0]
        parent_key = parent_name.lower()

        if parent_key not in by_name:
            continue

        parent = by_name[parent_key]

        # Add the FIRST spouse as second parent (most likely the biological parent)
        # We only add ONE spouse to avoid creating more than 2 parents
        for spouse_name in parent.spouses:
            if spouse_name not in person.parents:
                person.parents.append(spouse_name)
                # Also add this person to spouse's children list
                spouse_key = spouse_name.lower()
                if spouse_key in by_name:
                    spouse = by_name[spouse_key]
                    if person.name not in spouse.children:
                        spouse.children.append(person.name)
                # Stop after adding one spouse (now have 2 parents)
                break


def export_to_json(persons: dict, output_file: str):
    """Export persons dictionary to JSON for import into database."""
    # First merge duplicates
    persons = merge_duplicates(persons)

    # Share children between spouses
    share_children_between_spouses(persons)

    output = []

    for key, person in persons.items():
        person.gender = infer_gender(person.name, person.spouses, person.children)
        output.append({
            'name': person.name,
            'birth_year': person.birth_year,
            'birth_year_circa': person.birth_year_circa,
            'death_year': person.death_year,
            'death_year_circa': person.death_year_circa,
            'gender': person.gender,
            'generation': person.generation,
            'parents': person.parents,
            'spouses': person.spouses,
            'children': person.children
        })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return len(output)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Smart genealogy parser')
    parser.add_argument('--ocr-dir', default='/Users/guthdx/terminal_projects/dx_clan/ocr_output',
                        help='Directory containing OCR page files')
    parser.add_argument('--output', default='/Users/guthdx/terminal_projects/dx_clan/backend/data/parsed_genealogy.json',
                        help='Output JSON file')
    parser.add_argument('--start-page', type=int, default=3,
                        help='First page to parse (skip index)')
    parser.add_argument('--end-page', type=int, default=251,
                        help='Last page to parse')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    print(f"Parsing OCR pages {args.start_page} to {args.end_page}...")
    entries = parse_ocr_pages(args.ocr_dir, args.start_page, args.end_page)
    print(f"Found {len(entries)} entries")

    print("Building person records...")
    persons = build_persons_dict(entries)
    print(f"Created {len(persons)} unique persons")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    print(f"Exporting to {args.output}...")
    count = export_to_json(persons, args.output)
    print(f"Exported {count} persons")

    # Print some statistics
    with_parents = sum(1 for p in persons.values() if p.parents)
    with_children = sum(1 for p in persons.values() if p.children)
    with_spouses = sum(1 for p in persons.values() if p.spouses)
    with_birth = sum(1 for p in persons.values() if p.birth_year)

    print(f"\nStatistics:")
    print(f"  Persons with parents:  {with_parents}")
    print(f"  Persons with children: {with_children}")
    print(f"  Persons with spouses:  {with_spouses}")
    print(f"  Persons with birth year: {with_birth}")


if __name__ == '__main__':
    main()
