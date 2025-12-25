#!/usr/bin/env python3
"""
Genealogy Parser for DX_Clan OCR output.

Parses the dot-notation genealogy format and imports into PostgreSQL.
Updated for Apple Vision OCR output.
"""

import re
import uuid
import asyncio
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


@dataclass
class ParsedPerson:
    """Parsed person data."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    display_name: str = ""
    birth_year: Optional[int] = None
    birth_year_circa: bool = False
    death_year: Optional[int] = None
    death_year_circa: bool = False
    generation: int = 0
    is_spouse: bool = False
    is_remarriage: bool = False
    notes: str = ""
    aliases: list = field(default_factory=list)
    parent_person: Optional['ParsedPerson'] = None
    spouse_of: Optional['ParsedPerson'] = None


MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def normalize_text(text: str) -> str:
    """Normalize OCR artifacts."""
    # Replace bullet points with dots
    text = text.replace('•', '.')
    text = text.replace('·', '.')
    # Fix common OCR errors
    text = re.sub(r'[†‡]', '+', text)  # Cross marks to plus
    text = text.replace('—', '-').replace('–', '-')
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('"', '"').replace('"', '"')
    # Fix OCR month typos
    text = re.sub(r'\bApI\b', 'Apr', text)
    text = re.sub(r'\bAaug\b', 'Aug', text)
    text = re.sub(r'\bJuI\b', 'Jul', text)
    text = re.sub(r'\bFeb\s*I\b', 'Feb', text)
    return text


def extract_year(text: str) -> tuple[Optional[int], bool]:
    """Extract year from text. Returns (year, is_circa)."""
    if not text:
        return None, False
    circa = re.search(r'ca\.?\s*(\d{4})', text, re.I)
    if circa:
        return int(circa.group(1)), True
    full = re.search(rf'{MONTH}\s+\d{{1,2}},?\s*(\d{{4}})', text)
    if full:
        return int(full.group(1)), False
    year = re.search(r'\b(\d{4})\b', text)
    if year:
        return int(year.group(1)), False
    return None, False


def parse_dates(text: str) -> tuple[Optional[int], bool, Optional[int], bool, str]:
    """Parse birth/death dates from text."""
    b_year, b_circa, d_year, d_circa = None, False, None, False

    # Death only: d. 1880 or d.1880
    d_match = re.search(rf'd\.?\s*({MONTH}\s+\d{{1,2}},?\s*\d{{4}}|\d{{4}})', text)
    if d_match:
        d_year, d_circa = extract_year(d_match.group(1))
        text = text[:d_match.start()] + text[d_match.end():]

    # Date range: 1830 - 1900 or Sep 6, 1830 - Apr 28, 1900
    range_pat = rf'({MONTH}\s+\d{{1,2}},?\s*\d{{4}}|ca\.?\s*\d{{4}}|\d{{4}})\s*[-–~]\s*({MONTH}\s+\d{{1,2}},?\s*\d{{4}}|ca\.?\s*\d{{4}}|\d{{4}})'
    range_match = re.search(range_pat, text)
    if range_match:
        b_year, b_circa = extract_year(range_match.group(1))
        if not d_year:
            d_year, d_circa = extract_year(range_match.group(2))
        text = text[:range_match.start()] + text[range_match.end():]
    elif not d_match:
        # Single date (year only or full date)
        single = re.search(rf'({MONTH}\s+\d{{1,2}},?\s*\d{{4}}|ca\.?\s*\d{{4}}|\b\d{{4}}\b)', text)
        if single:
            b_year, b_circa = extract_year(single.group(1))
            text = text[:single.start()] + text[single.end():]

    return b_year, b_circa, d_year, d_circa, text.strip()


def extract_aliases(name: str) -> tuple[str, list[str]]:
    """Extract aliases from name."""
    aliases = []

    # Quoted nicknames: 'Tuff' or "Babe"
    for m in re.finditer(r"['\"]([^'\"]+)['\"]", name):
        alias = m.group(1).strip()
        if alias and re.match(r'^[A-Za-z][A-Za-z\s\-\.]+$', alias) and len(alias) > 1:
            aliases.append(alias)
    name = re.sub(r"['\"][^'\"]+['\"]", '', name)

    # Parenthetical names
    for m in re.finditer(r'\(([^)]+)\)', name):
        c = m.group(1).strip()
        skip_words = ['no issue', 'adopted', 'see ', 'cont', ' sr', ' jr', 'halpin', 'gilland']
        if not any(x in c.lower() for x in skip_words):
            if len(c) > 1 and re.match(r'^[A-Za-z][A-Za-z\s\-\.]+$', c):
                aliases.append(c)
    name = re.sub(r'\([^)]*\)', '', name)

    # Clean name
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'[\s\.\,\+\*]+$', '', name)
    name = re.sub(r'^[\s\.\,\+\*]+', '', name)
    name = name.strip()

    return name, [a for a in aliases if a and len(a) > 1]


def parse_person(text: str, gen: int, is_spouse: bool = False, is_remarriage: bool = False) -> ParsedPerson:
    """Parse a person text into ParsedPerson."""
    person = ParsedPerson(generation=gen, is_spouse=is_spouse, is_remarriage=is_remarriage)

    # Extract notes
    notes = []
    for pat in [r'\(no issue\)', r'\(adopted\)']:
        m = re.search(pat, text, re.I)
        if m:
            notes.append(m.group())
            text = re.sub(pat, '', text, flags=re.I)
    person.notes = ' '.join(notes)

    # Parse dates
    b, bc, d, dc, text = parse_dates(text)
    person.birth_year, person.birth_year_circa = b, bc
    person.death_year, person.death_year_circa = d, dc

    # Extract aliases
    name, aliases = extract_aliases(text)
    person.display_name = name
    person.aliases = aliases

    return person


def parse_line(line: str) -> list[tuple[str, int, bool, bool]]:
    """
    Parse a line into list of (text, generation, is_spouse, is_remarriage).
    New format: dots followed by generation number, then name.
    e.g., "....3 Sophia LeCompte Sep 1850"
    or "..+Lillian LeClaire 1831"
    """
    entries = []
    line = normalize_text(line)

    # Pattern: [dots][generation_num] [name/content]
    # e.g., "....3 Sophia LeCompte"
    gen_match = re.match(r'^\.{0,20}\s*(\d)\s+(.+)', line)
    if gen_match:
        gen = int(gen_match.group(1))
        content = gen_match.group(2).strip()
        if content and len(content) > 2:
            entries.append((content, gen, False, False))
        return entries

    # Pattern: [dots]+ [name] (spouse)
    # e.g., "..+Lillian LeClaire" or ".+Thomas H Hill"
    spouse_match = re.match(r'^\.{0,20}\s*\+\s*(.+)', line)
    if spouse_match:
        content = spouse_match.group(1).strip()
        if content and len(content) > 2:
            entries.append((content, 0, True, False))
        return entries

    # Pattern: [dots]* [name] (remarriage reference - person being re-married)
    # e.g., "* Victor Ducheneaux, I"
    remarriage_ref = re.match(r'^\.{0,20}\s*\*\s*([^+].+)', line)
    if remarriage_ref:
        content = remarriage_ref.group(1).strip()
        if content and len(content) > 2 and not content.startswith('+'):
            entries.append((content, 0, False, True))
        return entries

    # Pattern: [dots]*+ [name] (remarriage spouse)
    # e.g., ".*+Emma 'Amy' LeBeau"
    remarriage_spouse = re.match(r'^\.{0,20}\s*\*\s*\+\s*(.+)', line)
    if remarriage_spouse:
        content = remarriage_spouse.group(1).strip()
        if content and len(content) > 2:
            entries.append((content, 0, True, True))
        return entries

    # Standalone generation number at start (no dots)
    # e.g., "1 Joseph LeCompte" or "2 Louisson LeCompte"
    standalone_gen = re.match(r'^(\d)\s+([A-Z].+)', line)
    if standalone_gen:
        gen = int(standalone_gen.group(1))
        content = standalone_gen.group(2).strip()
        if content and len(content) > 2:
            entries.append((content, gen, False, False))
        return entries

    # Standalone + at start
    if line.startswith('+'):
        content = line[1:].strip()
        if content and len(content) > 2:
            entries.append((content, 0, True, False))
        return entries

    # Check for name-like content (continuation line or standalone)
    # Must start with capital letter and have reasonable content
    if re.match(r'^[A-Z][a-z]+', line) and len(line) > 3:
        # Could be a continuation or standalone entry
        # Skip if it's clearly an index entry or header
        if not re.search(r'\.{3,}\s*\d+$', line) and \
           'INDEX' not in line.upper() and \
           'Descendant' not in line and \
           'Children,' not in line:
            entries.append((line, 0, False, False))

    return entries


def parse_genealogy_file(filepath: str) -> list[ParsedPerson]:
    """Parse the genealogy file into ParsedPerson list."""
    persons = []
    parent_stack = {}  # gen -> person
    current_target = None  # For spouse attachment
    pending_line = ""  # For multi-line handling

    # Read file
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    lines = content.split('\n')
    in_data = False

    for line_num, line in enumerate(lines):
        line = normalize_text(line)
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Skip page numbers
        if stripped.isdigit() and len(stripped) <= 3:
            continue

        # Start of structured data - look for "1 Joseph LeCompte" pattern
        if re.match(r'^1\s+Joseph\s+Le[Cc]ompte', stripped):
            in_data = True

        if not in_data:
            continue

        # Skip headers and index entries
        skip_patterns = [
            'PARTIAL INDEX', 'Descendant Tree', 'Paternal ancestors',
            'Maternal Ancestors', 'Children, Grandchildren',
            'Cont.', 'Edited', 'arrie'
        ]
        if any(x in stripped for x in skip_patterns):
            continue

        # Skip index-style entries (name followed by dots and page number)
        if re.search(r'\.{3,}\s*\d+$', stripped):
            continue

        # Skip standalone death dates (lines starting with "- " followed by date)
        # These are death dates that should be attached to previous person
        if re.match(rf'^-\s*{MONTH}', stripped) or re.match(r'^-\s*\d{4}', stripped):
            # TODO: Could merge with previous person's death_year
            continue

        # Skip standalone month names or partial dates (OCR split lines)
        if stripped in MONTH_NAMES or re.match(rf'^{MONTH}\s*\d{{0,2}},?\s*$', stripped):
            continue

        # Skip lines that are just years
        if re.match(r'^\d{4}$', stripped):
            continue

        # Handle continuation lines (dates that got split)
        if pending_line and re.match(r'^[A-Z][a-z]{2}\s+\d', stripped):
            # This looks like a date continuation
            pending_line += ' ' + stripped
            continue
        elif pending_line and re.match(r'^\d{4}', stripped):
            # Year continuation
            pending_line += ' ' + stripped
            continue
        elif pending_line:
            # Process pending line first
            entries = parse_line(pending_line)
            pending_line = ""
            for text, gen, is_spouse, is_remarriage in entries:
                person = process_entry(text, gen, is_spouse, is_remarriage,
                                       persons, parent_stack, current_target)
                if person:
                    persons.append(person)
                    if not person.is_spouse and person.generation > 0:
                        parent_stack[person.generation] = person
                        current_target = person

        # Check if line might have continuation
        if re.search(rf'{MONTH}\s+\d{{1,2}},?\s*$', stripped) or \
           re.search(r'-\s*$', stripped):
            pending_line = stripped
            continue

        # Parse current line
        entries = parse_line(stripped)

        for text, gen, is_spouse, is_remarriage in entries:
            person = process_entry(text, gen, is_spouse, is_remarriage,
                                   persons, parent_stack, current_target)
            if person:
                persons.append(person)
                if not person.is_spouse and person.generation > 0:
                    parent_stack[person.generation] = person
                    current_target = person
                elif is_remarriage and not is_spouse:
                    # This is a remarriage reference, update target
                    for p in reversed(persons):
                        if not p.is_spouse and text.lower()[:15] in p.display_name.lower():
                            current_target = p
                            break

    return persons


def process_entry(text: str, gen: int, is_spouse: bool, is_remarriage: bool,
                  persons: list, parent_stack: dict, current_target) -> Optional[ParsedPerson]:
    """Process a single entry and return ParsedPerson if valid."""
    # Clean text
    text = re.sub(r'^[\.\s]+', '', text)
    text = re.sub(r'[\.\s]+$', '', text)
    text = text.strip()

    if not text or len(text) < 3:
        return None

    # Skip garbage patterns
    if re.match(r'^[\.\s\d,_]+$', text):
        return None
    if text in ['I', 'II', 'III', 'IV', 'V', 'VI', 'Sr', 'Jr']:
        return None
    # Skip standalone months or partial dates that slipped through
    if text in MONTH_NAMES:
        return None
    # Skip entries that look like dates (start with - or are just date-like)
    if re.match(rf'^-?\s*{MONTH}', text) and not re.search(r'[A-Z][a-z]{3,}', text):
        return None
    if re.match(r'^-\s+\d', text):
        return None

    # Handle remarriage reference (just name, don't create person)
    if is_remarriage and not is_spouse:
        return None

    # Parse person
    person = parse_person(text, gen, is_spouse, is_remarriage)

    if not person.display_name or len(person.display_name) < 2:
        return None

    # Skip if name looks like garbage
    if re.match(r'^[_\s\.,]+$', person.display_name):
        return None

    # Attach spouse
    if is_spouse:
        target = current_target
        if target:
            person.spouse_of = target
            person.generation = target.generation

    # Handle parent-child for non-spouses
    elif gen > 0:
        if gen > 1 and (gen - 1) in parent_stack:
            person.parent_person = parent_stack[gen - 1]

    return person


async def import_to_database(persons: list[ParsedPerson], session):
    """Import to database."""
    from app.models import Person, PersonAlias, Marriage, ParentChild

    person_map = {}
    print(f"Importing {len(persons)} persons...")

    for i, p in enumerate(persons):
        if not p.display_name:
            continue

        person = Person(
            id=p.id, display_name=p.display_name,
            birth_year=p.birth_year, birth_year_circa=p.birth_year_circa,
            death_year=p.death_year, death_year_circa=p.death_year_circa,
            generation=p.generation or None, notes=p.notes or None
        )
        session.add(person)
        person_map[p.id] = person.id

        for alias in p.aliases:
            session.add(PersonAlias(person_id=person.id, alias_name=alias, alias_type='alternate'))

        if (i + 1) % 500 == 0:
            print(f"  Created {i + 1}...")
            await session.flush()

    await session.flush()
    print(f"Created {len(person_map)} persons")

    # Relationships
    marriages, parent_child = 0, 0
    pairs = set()

    for p in persons:
        if p.id not in person_map:
            continue

        if p.is_spouse and p.spouse_of and p.spouse_of.id in person_map:
            pair = tuple(sorted([str(p.id), str(p.spouse_of.id)]))
            if pair not in pairs:
                pairs.add(pair)
                order = 1
                if p.is_remarriage:
                    r = await session.execute(select(Marriage).where(
                        (Marriage.spouse1_id == p.spouse_of.id) | (Marriage.spouse2_id == p.spouse_of.id)
                    ))
                    order = len(r.scalars().all()) + 1
                session.add(Marriage(spouse1_id=p.spouse_of.id, spouse2_id=p.id, marriage_order=order))
                marriages += 1

        if p.parent_person and p.parent_person.id in person_map and not p.is_spouse:
            session.add(ParentChild(parent_id=p.parent_person.id, child_id=p.id, relationship_type='biological'))
            parent_child += 1

    await session.commit()
    print(f"Created {marriages} marriages, {parent_child} parent-child")


async def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('filepath', nargs='?', default='DX_Clan_ocr_clean.txt')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--clear', action='store_true')
    args = parser.parse_args()

    filepath = Path(args.filepath)
    if not filepath.is_absolute():
        for base in [Path.cwd(), Path(__file__).parent.parent.parent]:
            if (base / args.filepath).exists():
                filepath = base / args.filepath
                break

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print(f"Parsing {filepath}...")
    persons = parse_genealogy_file(str(filepath))

    total = len(persons)
    spouses = sum(1 for p in persons if p.is_spouse)
    with_dates = sum(1 for p in persons if p.birth_year or p.death_year)
    with_aliases = sum(1 for p in persons if p.aliases)
    with_parents = sum(1 for p in persons if p.parent_person)

    print(f"\nParsed {total} persons:")
    print(f"  - {total - spouses} primary")
    print(f"  - {spouses} spouses")
    print(f"  - {with_dates} with dates")
    print(f"  - {with_aliases} with aliases")
    print(f"  - {with_parents} with parent links")

    print("\nSample:")
    for p in persons[:30]:
        d = ""
        if p.birth_year: d += f" b.{'~' if p.birth_year_circa else ''}{p.birth_year}"
        if p.death_year: d += f" d.{'~' if p.death_year_circa else ''}{p.death_year}"
        s = f" [spouse of {p.spouse_of.display_name[:20]}...]" if p.spouse_of else ""
        parent = f" [child of {p.parent_person.display_name[:20]}...]" if p.parent_person else ""
        a = f" aka {p.aliases}" if p.aliases else ""
        print(f"  Gen {p.generation}: {p.display_name[:40]}{d}{s}{parent}{a}")

    if args.dry_run:
        print("\nDry run complete.")
        return

    from app.core.config import settings
    print("\nConnecting to database...")
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        if args.clear:
            await session.execute(text("TRUNCATE sources, parent_child, marriages, person_aliases, persons CASCADE"))
            await session.commit()
        await import_to_database(persons, session)

    await engine.dispose()
    print("\nComplete!")


if __name__ == '__main__':
    asyncio.run(main())
