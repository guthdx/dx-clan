"""Initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-12-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create persons table
    op.create_table(
        'persons',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('birth_year', sa.Integer(), nullable=True),
        sa.Column('birth_year_circa', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('death_year', sa.Integer(), nullable=True),
        sa.Column('death_year_circa', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('gender', sa.String(20), nullable=True),
        sa.Column('tribal_affiliation', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('generation', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_persons_display_name', 'persons', ['display_name'])
    op.create_index('idx_persons_birth_year', 'persons', ['birth_year'])

    # Create person_aliases table
    op.create_table(
        'person_aliases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alias_name', sa.String(255), nullable=False),
        sa.Column('alias_type', sa.String(50), nullable=True),
        sa.Column('is_primary', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_person_aliases_person_id', 'person_aliases', ['person_id'])
    op.create_index('idx_aliases_name', 'person_aliases', ['alias_name'])

    # Create marriages table
    op.create_table(
        'marriages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('spouse1_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('spouse2_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('marriage_order', sa.Integer(), server_default='1', nullable=True),
        sa.Column('marriage_year', sa.Integer(), nullable=True),
        sa.Column('divorce_year', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['spouse1_id'], ['persons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['spouse2_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('spouse1_id', 'spouse2_id', name='unique_marriage_pair')
    )
    op.create_index('idx_marriages_spouse1', 'marriages', ['spouse1_id'])
    op.create_index('idx_marriages_spouse2', 'marriages', ['spouse2_id'])

    # Create parent_child table
    op.create_table(
        'parent_child',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('child_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relationship_type', sa.String(50), server_default='biological', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['persons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['child_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('parent_id', 'child_id', name='unique_parent_child')
    )
    op.create_index('idx_parent_child_parent', 'parent_child', ['parent_id'])
    op.create_index('idx_parent_child_child', 'parent_child', ['child_id'])

    # Create sources table
    op.create_table(
        'sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_type', sa.String(100), nullable=True),
        sa.Column('source_text', sa.Text(), nullable=True),
        sa.Column('source_date', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sources_person_id', 'sources', ['person_id'])


def downgrade() -> None:
    op.drop_table('sources')
    op.drop_table('parent_child')
    op.drop_table('marriages')
    op.drop_table('person_aliases')
    op.drop_table('persons')
