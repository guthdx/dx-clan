#!/usr/bin/env python3
"""
Import parsed genealogy data into PostgreSQL database.

Reads from the JSON file created by smart_parser.py and populates
the persons, marriages, parent_child, and person_aliases tables.
"""

import asyncio
import json
import argparse
from uuid import uuid4

import asyncpg


DATABASE_URL = "postgresql://dx_clan:localdev@localhost:5432/dx_clan"


async def get_connection():
    """Get database connection."""
    return await asyncpg.connect(DATABASE_URL)


async def clear_database(conn):
    """Clear all genealogy tables."""
    print("Clearing existing data...")

    # Delete in order to respect foreign keys
    await conn.execute("DELETE FROM parent_child")
    await conn.execute("DELETE FROM marriages")
    await conn.execute("DELETE FROM person_aliases")
    await conn.execute("DELETE FROM persons")

    print("  Cleared all tables")


async def import_persons(conn, persons: list) -> dict:
    """
    Import all persons into the database.
    Returns a mapping from name to person ID.
    """
    print(f"Importing {len(persons)} persons...")

    name_to_id = {}

    for i, person in enumerate(persons):
        if i % 500 == 0:
            print(f"  Imported {i}/{len(persons)} persons...")

        person_id = uuid4()

        await conn.execute("""
            INSERT INTO persons (
                id, display_name, birth_year, birth_year_circa,
                death_year, death_year_circa, gender, generation
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
            person_id,
            person['name'],
            person['birth_year'],
            person.get('birth_year_circa', False),
            person['death_year'],
            person.get('death_year_circa', False),
            person['gender'],
            person['generation']
        )

        # Store mapping from lowercase name to ID
        name_to_id[person['name'].lower()] = person_id

    print(f"  Imported {len(persons)} persons")
    return name_to_id


async def import_parent_child_relationships(conn, persons: list, name_to_id: dict):
    """Import parent-child relationships."""
    print("Importing parent-child relationships...")

    count = 0
    errors = 0

    for person in persons:
        child_id = name_to_id.get(person['name'].lower())
        if not child_id:
            continue

        for parent_name in person.get('parents', []):
            parent_id = name_to_id.get(parent_name.lower())
            if not parent_id:
                errors += 1
                continue

            # Check if relationship already exists
            exists = await conn.fetchval("""
                SELECT 1 FROM parent_child
                WHERE parent_id = $1 AND child_id = $2
            """, parent_id, child_id)

            if not exists:
                await conn.execute("""
                    INSERT INTO parent_child (id, parent_id, child_id)
                    VALUES ($1, $2, $3)
                """, uuid4(), parent_id, child_id)
                count += 1

    print(f"  Imported {count} parent-child relationships ({errors} unresolved)")


async def import_marriages(conn, persons: list, name_to_id: dict):
    """Import marriage relationships."""
    print("Importing marriages...")

    count = 0
    errors = 0
    seen = set()  # Track seen pairs to avoid duplicates

    for person in persons:
        person_id = name_to_id.get(person['name'].lower())
        if not person_id:
            continue

        for spouse_name in person.get('spouses', []):
            spouse_id = name_to_id.get(spouse_name.lower())
            if not spouse_id:
                errors += 1
                continue

            # Create a canonical pair key to avoid duplicates
            pair = tuple(sorted([str(person_id), str(spouse_id)]))
            if pair in seen:
                continue
            seen.add(pair)

            # Check if marriage already exists
            exists = await conn.fetchval("""
                SELECT 1 FROM marriages
                WHERE (spouse1_id = $1 AND spouse2_id = $2)
                   OR (spouse1_id = $2 AND spouse2_id = $1)
            """, person_id, spouse_id)

            if not exists:
                await conn.execute("""
                    INSERT INTO marriages (id, spouse1_id, spouse2_id, marriage_order)
                    VALUES ($1, $2, $3, 1)
                """, uuid4(), person_id, spouse_id)
                count += 1

    print(f"  Imported {count} marriages ({errors} unresolved)")


async def run_import(json_file: str, clear: bool = True):
    """Run the import process."""
    print(f"\n{'=' * 60}")
    print(f"DX Clan Genealogy - Database Import")
    print(f"{'=' * 60}\n")

    # Load data
    print(f"Loading data from {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        persons = json.load(f)
    print(f"  Loaded {len(persons)} persons")

    conn = await get_connection()

    try:
        if clear:
            await clear_database(conn)

        # Import persons
        name_to_id = await import_persons(conn, persons)

        # Import relationships
        await import_parent_child_relationships(conn, persons, name_to_id)
        await import_marriages(conn, persons, name_to_id)

        # Summary
        person_count = await conn.fetchval("SELECT COUNT(*) FROM persons")
        pc_count = await conn.fetchval("SELECT COUNT(*) FROM parent_child")
        marriage_count = await conn.fetchval("SELECT COUNT(*) FROM marriages")

        print(f"\n{'=' * 60}")
        print("Import complete!")
        print(f"  Persons: {person_count}")
        print(f"  Parent-child relationships: {pc_count}")
        print(f"  Marriages: {marriage_count}")
        print(f"{'=' * 60}\n")

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='Import genealogy data into database')
    parser.add_argument('--json', default='/Users/guthdx/terminal_projects/dx_clan/backend/data/parsed_genealogy.json',
                        help='Path to JSON file')
    parser.add_argument('--no-clear', action='store_true',
                        help="Don't clear existing data")

    args = parser.parse_args()

    asyncio.run(run_import(args.json, clear=not args.no_clear))


if __name__ == '__main__':
    main()
