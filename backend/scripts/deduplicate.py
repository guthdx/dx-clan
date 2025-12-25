#!/usr/bin/env python3
"""
Deduplication script for DX Clan genealogy database.

Identifies duplicate person records (same name + birth year) and merges them
into a single canonical record, preserving all relationships.
"""

import asyncio
import argparse
from collections import defaultdict
from uuid import UUID

import asyncpg


DATABASE_URL = "postgresql://dx_clan:localdev@localhost:5432/dx_clan"


def normalize_name(name: str) -> str:
    """Normalize a name for comparison."""
    if not name:
        return ""
    # Lowercase, strip whitespace, normalize internal spaces
    return " ".join(name.lower().strip().split())


async def get_connection():
    """Get database connection."""
    return await asyncpg.connect(DATABASE_URL)


async def analyze_duplicates(conn, mode: str = "exact") -> dict:
    """
    Analyze and return duplicate clusters.

    mode="exact": Same name AND same birth_year (including both NULL)
    mode="fuzzy": Same name where one has birth_year and one doesn't
    """

    # Get all persons
    rows = await conn.fetch("""
        SELECT id, display_name, birth_year, death_year, gender,
               tribal_affiliation, notes, generation, created_at
        FROM persons
        ORDER BY display_name, birth_year
    """)

    if mode == "exact":
        # Group by normalized name + birth_year
        clusters = defaultdict(list)
        for row in rows:
            key = (normalize_name(row['display_name']), row['birth_year'])
            clusters[key].append(dict(row))

    elif mode == "fuzzy":
        # Group by normalized name only
        by_name = defaultdict(list)
        for row in rows:
            key = normalize_name(row['display_name'])
            by_name[key].append(dict(row))

        # Filter to clusters where some have birth_year and some don't
        clusters = {}
        for name, records in by_name.items():
            has_birth = [r for r in records if r['birth_year'] is not None]
            no_birth = [r for r in records if r['birth_year'] is None]

            # Only include if there's at least one with birth year and one without
            if has_birth and no_birth:
                # Use name as key (birth_year will be None for the key)
                clusters[(name, None)] = records

    # Filter to only duplicates
    duplicates = {k: v for k, v in clusters.items() if len(v) > 1}

    return duplicates


async def get_relationship_counts(conn, person_id: UUID) -> dict:
    """Get counts of relationships for a person."""

    # Parent relationships (this person is a parent)
    parent_of = await conn.fetchval(
        "SELECT COUNT(*) FROM parent_child WHERE parent_id = $1", person_id
    )

    # Child relationships (this person is a child)
    child_of = await conn.fetchval(
        "SELECT COUNT(*) FROM parent_child WHERE child_id = $1", person_id
    )

    # Marriage relationships
    marriages = await conn.fetchval(
        "SELECT COUNT(*) FROM marriages WHERE spouse1_id = $1 OR spouse2_id = $1",
        person_id
    )

    # Aliases
    aliases = await conn.fetchval(
        "SELECT COUNT(*) FROM person_aliases WHERE person_id = $1", person_id
    )

    return {
        'parent_of': parent_of,
        'child_of': child_of,
        'marriages': marriages,
        'aliases': aliases,
        'total': parent_of + child_of + marriages + aliases
    }


def score_record(record: dict, rel_counts: dict) -> int:
    """
    Score a record to determine which should be canonical.
    Higher score = better candidate for canonical record.
    """
    score = 0

    # Has birth year
    if record.get('birth_year'):
        score += 100

    # Has death year
    if record.get('death_year'):
        score += 50

    # Has gender
    if record.get('gender'):
        score += 20

    # Has tribal affiliation
    if record.get('tribal_affiliation'):
        score += 20

    # Has notes
    if record.get('notes'):
        score += 10

    # Has generation
    if record.get('generation'):
        score += 10

    # Relationship counts (more relationships = more important to keep)
    score += rel_counts.get('total', 0) * 5

    return score


async def select_canonical(conn, records: list) -> tuple:
    """
    Select the canonical record from a list of duplicates.
    Returns (canonical_record, duplicate_records)
    """
    scored = []
    for record in records:
        rel_counts = await get_relationship_counts(conn, record['id'])
        score = score_record(record, rel_counts)
        scored.append((score, record, rel_counts))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    canonical = scored[0][1]
    duplicates = [s[1] for s in scored[1:]]

    return canonical, duplicates


async def merge_relationships(conn, canonical_id: UUID, duplicate_id: UUID, dry_run: bool = True):
    """Merge all relationships from duplicate to canonical."""

    actions = []

    # Update parent_child where duplicate is parent
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM parent_child WHERE parent_id = $1", duplicate_id
    )
    if count > 0:
        actions.append(f"  - Move {count} 'parent of' relationships")
        if not dry_run:
            # Check for conflicts first
            await conn.execute("""
                UPDATE parent_child
                SET parent_id = $1
                WHERE parent_id = $2
                AND NOT EXISTS (
                    SELECT 1 FROM parent_child pc2
                    WHERE pc2.parent_id = $1 AND pc2.child_id = parent_child.child_id
                )
            """, canonical_id, duplicate_id)
            # Delete any remaining (conflicts)
            await conn.execute(
                "DELETE FROM parent_child WHERE parent_id = $1", duplicate_id
            )

    # Update parent_child where duplicate is child
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM parent_child WHERE child_id = $1", duplicate_id
    )
    if count > 0:
        actions.append(f"  - Move {count} 'child of' relationships")
        if not dry_run:
            await conn.execute("""
                UPDATE parent_child
                SET child_id = $1
                WHERE child_id = $2
                AND NOT EXISTS (
                    SELECT 1 FROM parent_child pc2
                    WHERE pc2.child_id = $1 AND pc2.parent_id = parent_child.parent_id
                )
            """, canonical_id, duplicate_id)
            await conn.execute(
                "DELETE FROM parent_child WHERE child_id = $1", duplicate_id
            )

    # Update marriages where duplicate is spouse1
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM marriages WHERE spouse1_id = $1", duplicate_id
    )
    if count > 0:
        actions.append(f"  - Move {count} marriages (as spouse1)")
        if not dry_run:
            await conn.execute("""
                UPDATE marriages
                SET spouse1_id = $1
                WHERE spouse1_id = $2
                AND NOT EXISTS (
                    SELECT 1 FROM marriages m2
                    WHERE (m2.spouse1_id = $1 AND m2.spouse2_id = marriages.spouse2_id)
                       OR (m2.spouse2_id = $1 AND m2.spouse1_id = marriages.spouse2_id)
                )
            """, canonical_id, duplicate_id)
            await conn.execute(
                "DELETE FROM marriages WHERE spouse1_id = $1", duplicate_id
            )

    # Update marriages where duplicate is spouse2
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM marriages WHERE spouse2_id = $1", duplicate_id
    )
    if count > 0:
        actions.append(f"  - Move {count} marriages (as spouse2)")
        if not dry_run:
            await conn.execute("""
                UPDATE marriages
                SET spouse2_id = $1
                WHERE spouse2_id = $2
                AND NOT EXISTS (
                    SELECT 1 FROM marriages m2
                    WHERE (m2.spouse1_id = $1 AND m2.spouse2_id = marriages.spouse1_id)
                       OR (m2.spouse2_id = $1 AND m2.spouse1_id = marriages.spouse1_id)
                )
            """, canonical_id, duplicate_id)
            await conn.execute(
                "DELETE FROM marriages WHERE spouse2_id = $1", duplicate_id
            )

    # Move aliases
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM person_aliases WHERE person_id = $1", duplicate_id
    )
    if count > 0:
        actions.append(f"  - Move {count} aliases")
        if not dry_run:
            await conn.execute("""
                UPDATE person_aliases
                SET person_id = $1
                WHERE person_id = $2
            """, canonical_id, duplicate_id)

    return actions


async def merge_person_data(conn, canonical: dict, duplicate: dict, dry_run: bool = True):
    """Merge any missing data from duplicate into canonical."""

    updates = []
    update_fields = {}

    # Fill in missing data from duplicate
    if not canonical.get('birth_year') and duplicate.get('birth_year'):
        update_fields['birth_year'] = duplicate['birth_year']
        updates.append(f"  - Add birth_year: {duplicate['birth_year']}")

    if not canonical.get('death_year') and duplicate.get('death_year'):
        update_fields['death_year'] = duplicate['death_year']
        updates.append(f"  - Add death_year: {duplicate['death_year']}")

    if not canonical.get('gender') and duplicate.get('gender'):
        update_fields['gender'] = duplicate['gender']
        updates.append(f"  - Add gender: {duplicate['gender']}")

    if not canonical.get('tribal_affiliation') and duplicate.get('tribal_affiliation'):
        update_fields['tribal_affiliation'] = duplicate['tribal_affiliation']
        updates.append(f"  - Add tribal_affiliation: {duplicate['tribal_affiliation']}")

    if not canonical.get('generation') and duplicate.get('generation'):
        update_fields['generation'] = duplicate['generation']
        updates.append(f"  - Add generation: {duplicate['generation']}")

    # Merge notes
    if duplicate.get('notes'):
        if canonical.get('notes'):
            if duplicate['notes'] not in canonical['notes']:
                update_fields['notes'] = canonical['notes'] + "\n" + duplicate['notes']
                updates.append("  - Merge notes")
        else:
            update_fields['notes'] = duplicate['notes']
            updates.append("  - Add notes")

    if update_fields and not dry_run:
        set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(update_fields.keys()))
        values = [canonical['id']] + list(update_fields.values())
        await conn.execute(
            f"UPDATE persons SET {set_clause} WHERE id = $1",
            *values
        )

    return updates


async def delete_duplicate(conn, duplicate_id: UUID, dry_run: bool = True):
    """Delete a duplicate person record."""
    if not dry_run:
        await conn.execute("DELETE FROM persons WHERE id = $1", duplicate_id)


async def run_deduplication(dry_run: bool = True, limit: int = None, verbose: bool = False, mode: str = "exact"):
    """Main deduplication process."""

    conn = await get_connection()

    try:
        mode_desc = "exact match (name + birth year)" if mode == "exact" else "fuzzy match (name only, merge NULL birth years)"
        print(f"\n{'=' * 60}")
        print(f"DX Clan Genealogy - Deduplication {'(DRY RUN)' if dry_run else '(LIVE)'}")
        print(f"Mode: {mode_desc}")
        print(f"{'=' * 60}\n")

        # Analyze duplicates
        print("Analyzing duplicates...")
        duplicates = await analyze_duplicates(conn, mode)

        total_clusters = len(duplicates)
        total_duplicates = sum(len(v) - 1 for v in duplicates.values())

        print(f"Found {total_clusters} duplicate clusters")
        print(f"Total duplicate records to merge: {total_duplicates}")
        print()

        if limit:
            print(f"Processing first {limit} clusters only\n")

        # Process each cluster
        processed = 0
        merged = 0

        for (name, birth_year), records in duplicates.items():
            if limit and processed >= limit:
                break

            processed += 1

            # Select canonical record
            canonical, dups = await select_canonical(conn, records)

            if verbose or dry_run:
                birth_str = f"b. {birth_year}" if birth_year else "no birth year"
                print(f"[{processed}/{total_clusters}] {canonical['display_name']} ({birth_str})")
                print(f"  Keeping: {str(canonical['id'])[:8]}...")
                print(f"  Merging {len(dups)} duplicate(s):")

            # Merge each duplicate
            for dup in dups:
                if verbose or dry_run:
                    print(f"    From: {str(dup['id'])[:8]}...")

                # Merge relationships
                actions = await merge_relationships(conn, canonical['id'], dup['id'], dry_run)
                if verbose and actions:
                    for action in actions:
                        print(action)

                # Merge person data
                updates = await merge_person_data(conn, canonical, dup, dry_run)
                if verbose and updates:
                    for update in updates:
                        print(update)

                # Delete duplicate
                if verbose or dry_run:
                    print(f"    Delete: {str(dup['id'])[:8]}...")
                await delete_duplicate(conn, dup['id'], dry_run)

                merged += 1

            if verbose or dry_run:
                print()

        print(f"\n{'=' * 60}")
        print(f"Summary:")
        print(f"  Clusters processed: {processed}")
        print(f"  Records merged: {merged}")
        if dry_run:
            print(f"\nThis was a DRY RUN - no changes were made.")
            print(f"Run with --execute to apply changes.")
        else:
            print(f"\nDeduplication complete!")

            # Get new count
            new_count = await conn.fetchval("SELECT COUNT(*) FROM persons")
            print(f"New person count: {new_count}")
        print(f"{'=' * 60}\n")

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='Deduplicate DX Clan genealogy database')
    parser.add_argument('--execute', action='store_true',
                        help='Actually execute changes (default is dry run)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit to first N clusters (for testing)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output')
    parser.add_argument('--fuzzy', action='store_true',
                        help='Use fuzzy matching (merge records with same name where one has birth year and one does not)')

    args = parser.parse_args()

    asyncio.run(run_deduplication(
        dry_run=not args.execute,
        limit=args.limit,
        verbose=args.verbose,
        mode="fuzzy" if args.fuzzy else "exact"
    ))


if __name__ == '__main__':
    main()
