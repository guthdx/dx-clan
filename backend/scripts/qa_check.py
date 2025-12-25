#!/usr/bin/env python3
"""
Quality Assurance checks for DX Clan genealogy database.

Identifies potential data quality issues:
- People with too many parents (>2)
- Dates embedded in names
- Impossible birth/death years
- Parent younger than child
- Generation inconsistencies
- Potential duplicates
- OCR artifacts in names
"""

import json
import re
import argparse
from collections import defaultdict
from pathlib import Path


def load_data(json_file: str) -> list:
    """Load parsed genealogy data."""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_parent_count(persons: list) -> list:
    """Find people with more than 2 parents."""
    issues = []
    for p in persons:
        if len(p.get('parents', [])) > 2:
            issues.append({
                'type': 'TOO_MANY_PARENTS',
                'severity': 'HIGH',
                'name': p['name'],
                'birth_year': p.get('birth_year'),
                'detail': f"Has {len(p['parents'])} parents: {', '.join(p['parents'])}"
            })
    return issues


def check_dates_in_names(persons: list) -> list:
    """Find names that contain date fragments."""
    issues = []
    # Patterns that suggest dates got into names
    date_patterns = [
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d',
        r'\b\d{4}\b',  # Year in name
        r'\b\d{1,2},\s*$',  # Trailing "20," etc.
    ]

    for p in persons:
        name = p['name']
        for pattern in date_patterns:
            if re.search(pattern, name):
                issues.append({
                    'type': 'DATE_IN_NAME',
                    'severity': 'MEDIUM',
                    'name': name,
                    'birth_year': p.get('birth_year'),
                    'detail': f"Name appears to contain date fragment"
                })
                break
    return issues


def check_impossible_dates(persons: list) -> list:
    """Find impossible birth/death years."""
    issues = []

    for p in persons:
        birth = p.get('birth_year')
        death = p.get('death_year')
        name = p['name']

        # Birth year sanity checks
        if birth:
            if birth < 1600:
                issues.append({
                    'type': 'BIRTH_TOO_EARLY',
                    'severity': 'HIGH',
                    'name': name,
                    'birth_year': birth,
                    'detail': f"Birth year {birth} is before 1600"
                })
            elif birth > 2024:
                issues.append({
                    'type': 'BIRTH_IN_FUTURE',
                    'severity': 'HIGH',
                    'name': name,
                    'birth_year': birth,
                    'detail': f"Birth year {birth} is in the future"
                })

        # Death year sanity checks
        if death:
            if death < 1600:
                issues.append({
                    'type': 'DEATH_TOO_EARLY',
                    'severity': 'HIGH',
                    'name': name,
                    'birth_year': birth,
                    'detail': f"Death year {death} is before 1600"
                })
            elif death > 2024:
                issues.append({
                    'type': 'DEATH_IN_FUTURE',
                    'severity': 'HIGH',
                    'name': name,
                    'birth_year': birth,
                    'detail': f"Death year {death} is in the future"
                })

        # Death before birth
        if birth and death and death < birth:
            issues.append({
                'type': 'DEATH_BEFORE_BIRTH',
                'severity': 'HIGH',
                'name': name,
                'birth_year': birth,
                'detail': f"Death ({death}) before birth ({birth})"
            })

        # Unrealistic lifespan (>120 years)
        if birth and death and (death - birth) > 120:
            issues.append({
                'type': 'UNREALISTIC_LIFESPAN',
                'severity': 'MEDIUM',
                'name': name,
                'birth_year': birth,
                'detail': f"Lifespan of {death - birth} years ({birth}-{death})"
            })

    return issues


def check_parent_child_ages(persons: list) -> list:
    """Find cases where parent is younger than or too close in age to child."""
    issues = []

    # Build lookup by name
    by_name = {}
    for p in persons:
        by_name[p['name'].lower()] = p

    for p in persons:
        child_birth = p.get('birth_year')
        if not child_birth:
            continue

        for parent_name in p.get('parents', []):
            parent = by_name.get(parent_name.lower())
            if not parent:
                continue

            parent_birth = parent.get('birth_year')
            if not parent_birth:
                continue

            age_diff = child_birth - parent_birth

            if age_diff < 0:
                issues.append({
                    'type': 'PARENT_YOUNGER_THAN_CHILD',
                    'severity': 'HIGH',
                    'name': p['name'],
                    'birth_year': child_birth,
                    'detail': f"Parent {parent_name} (b. {parent_birth}) is younger than child (b. {child_birth})"
                })
            elif age_diff < 12:
                issues.append({
                    'type': 'PARENT_TOO_YOUNG',
                    'severity': 'HIGH',
                    'name': p['name'],
                    'birth_year': child_birth,
                    'detail': f"Parent {parent_name} was only {age_diff} when child was born"
                })
            elif age_diff > 70:
                issues.append({
                    'type': 'PARENT_VERY_OLD',
                    'severity': 'LOW',
                    'name': p['name'],
                    'birth_year': child_birth,
                    'detail': f"Parent {parent_name} was {age_diff} when child was born"
                })

    return issues


def check_generation_consistency(persons: list) -> list:
    """Find generation number inconsistencies."""
    issues = []

    # Build lookup by name
    by_name = {}
    for p in persons:
        by_name[p['name'].lower()] = p

    for p in persons:
        child_gen = p.get('generation')
        if not child_gen:
            continue

        for parent_name in p.get('parents', []):
            parent = by_name.get(parent_name.lower())
            if not parent:
                continue

            parent_gen = parent.get('generation')
            if not parent_gen:
                continue

            if parent_gen >= child_gen:
                issues.append({
                    'type': 'GENERATION_MISMATCH',
                    'severity': 'MEDIUM',
                    'name': p['name'],
                    'birth_year': p.get('birth_year'),
                    'detail': f"Child gen {child_gen}, parent {parent_name} gen {parent_gen}"
                })

    return issues


def check_name_quality(persons: list) -> list:
    """Find names that look like OCR errors or data issues."""
    issues = []

    for p in persons:
        name = p['name']

        # Too short
        if len(name) < 4:
            issues.append({
                'type': 'NAME_TOO_SHORT',
                'severity': 'MEDIUM',
                'name': name,
                'birth_year': p.get('birth_year'),
                'detail': f"Name is only {len(name)} characters"
            })

        # Starts with number
        if re.match(r'^\d', name):
            issues.append({
                'type': 'NAME_STARTS_WITH_NUMBER',
                'severity': 'HIGH',
                'name': name,
                'birth_year': p.get('birth_year'),
                'detail': "Name starts with a number"
            })

        # Check for numbers in names (OCR errors - dates stuck in names)
        if re.search(r'\d', name):
            issues.append({
                'type': 'NAME_HAS_NUMBERS',
                'severity': 'HIGH',
                'name': name,
                'birth_year': p.get('birth_year'),
                'detail': "Name contains numbers (likely OCR date fragment)"
            })

        # Check for OCR punctuation artifacts (—, ~, =, |, \, etc.)
        ocr_artifacts = re.findall(r'[—~=|\\@#$%^&*<>]', name)
        if ocr_artifacts:
            issues.append({
                'type': 'NAME_HAS_OCR_ARTIFACTS',
                'severity': 'HIGH',
                'name': name,
                'birth_year': p.get('birth_year'),
                'detail': f"Contains OCR artifacts: {list(set(ocr_artifacts))}"
            })

        # Check for slashes (alternate names) - lower severity, might be valid
        if '/' in name:
            issues.append({
                'type': 'NAME_HAS_SLASH',
                'severity': 'LOW',
                'name': name,
                'birth_year': p.get('birth_year'),
                'detail': "Name contains slash (alternate name format)"
            })

        # All caps or all lowercase (unusual)
        if name == name.upper() and len(name) > 5:
            issues.append({
                'type': 'NAME_ALL_CAPS',
                'severity': 'LOW',
                'name': name,
                'birth_year': p.get('birth_year'),
                'detail': "Name is all uppercase"
            })

    return issues


def check_potential_duplicates(persons: list) -> list:
    """Find potential duplicate entries."""
    issues = []

    # Group by normalized name
    by_name = defaultdict(list)
    for p in persons:
        # Normalize: lowercase, remove extra spaces
        normalized = ' '.join(p['name'].lower().split())
        by_name[normalized].append(p)

    for name, entries in by_name.items():
        if len(entries) > 1:
            # Check if they have different birth years
            birth_years = [e.get('birth_year') for e in entries]
            if len(set(birth_years)) > 1 or all(b is None for b in birth_years):
                issues.append({
                    'type': 'POTENTIAL_DUPLICATE',
                    'severity': 'LOW',
                    'name': entries[0]['name'],
                    'birth_year': None,
                    'detail': f"{len(entries)} entries: birth years {birth_years}"
                })

    return issues


def check_orphaned_entries(persons: list) -> list:
    """Find people with no relationships at all."""
    issues = []

    for p in persons:
        parents = p.get('parents', [])
        spouses = p.get('spouses', [])
        children = p.get('children', [])

        if not parents and not spouses and not children:
            issues.append({
                'type': 'NO_RELATIONSHIPS',
                'severity': 'LOW',
                'name': p['name'],
                'birth_year': p.get('birth_year'),
                'detail': "Person has no parents, spouses, or children"
            })

    return issues


def run_all_checks(persons: list) -> list:
    """Run all QA checks and return issues."""
    all_issues = []

    checks = [
        ('Parent count', check_parent_count),
        ('Dates in names', check_dates_in_names),
        ('Impossible dates', check_impossible_dates),
        ('Parent-child ages', check_parent_child_ages),
        ('Generation consistency', check_generation_consistency),
        ('Name quality', check_name_quality),
        ('Potential duplicates', check_potential_duplicates),
        ('Orphaned entries', check_orphaned_entries),
    ]

    for check_name, check_func in checks:
        issues = check_func(persons)
        all_issues.extend(issues)
        print(f"  {check_name}: {len(issues)} issues")

    return all_issues


def main():
    parser = argparse.ArgumentParser(description='QA checks for genealogy data')
    parser.add_argument('--json',
                        default='/Users/guthdx/terminal_projects/dx_clan/backend/data/parsed_genealogy.json',
                        help='Path to parsed JSON file')
    parser.add_argument('--severity', choices=['HIGH', 'MEDIUM', 'LOW', 'ALL'],
                        default='ALL', help='Filter by severity')
    parser.add_argument('--type', help='Filter by issue type')
    parser.add_argument('--limit', type=int, default=50, help='Max issues to show')

    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print("DX Clan Genealogy - Quality Assurance Check")
    print(f"{'=' * 60}\n")

    # Load data
    print(f"Loading data from {args.json}...")
    persons = load_data(args.json)
    print(f"  Loaded {len(persons)} persons\n")

    # Run checks
    print("Running checks...")
    issues = run_all_checks(persons)

    # Filter
    if args.severity != 'ALL':
        issues = [i for i in issues if i['severity'] == args.severity]
    if args.type:
        issues = [i for i in issues if i['type'] == args.type]

    # Sort by severity
    severity_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    issues.sort(key=lambda x: (severity_order[x['severity']], x['type'], x['name']))

    # Summary
    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")

    by_severity = defaultdict(int)
    by_type = defaultdict(int)
    for issue in issues:
        by_severity[issue['severity']] += 1
        by_type[issue['type']] += 1

    print(f"\nBy Severity:")
    for sev in ['HIGH', 'MEDIUM', 'LOW']:
        print(f"  {sev}: {by_severity[sev]}")

    print(f"\nBy Type:")
    for issue_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {issue_type}: {count}")

    # Show issues
    print(f"\n{'=' * 60}")
    print(f"Issues (showing first {min(args.limit, len(issues))} of {len(issues)})")
    print(f"{'=' * 60}\n")

    for issue in issues[:args.limit]:
        birth = f"b. {issue['birth_year']}" if issue['birth_year'] else "no birth year"
        print(f"[{issue['severity']}] {issue['type']}")
        print(f"  Name: {issue['name']} ({birth})")
        print(f"  Detail: {issue['detail']}")
        print()

    if len(issues) > args.limit:
        print(f"... and {len(issues) - args.limit} more issues")
        print(f"Use --limit to see more, or --severity/--type to filter")


if __name__ == '__main__':
    main()
