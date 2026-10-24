"""create documents and chunks tables

Revision ID: a3f1c2d4e5b6
Revises: 16819e74e340
Create Date: 2026-10-24 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a3f1c2d4e5b6'
down_revision: Union[str, None] = '16819e74e340'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('documents',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('slug', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('celex', sa.String(length=50), nullable=False),
    sa.Column('language', sa.String(length=5), nullable=False),
    sa.Column('source_url', sa.Text(), nullable=False),
    sa.Column('retrieved_at', sa.String(length=50), nullable=False),
    sa.Column('source_sha256', sa.String(length=64), nullable=False),
    sa.Column('chunk_max_words', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('chunks',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('chunk_id', sa.String(length=100), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('split_reason', sa.String(length=20), nullable=False),
    sa.Column('citation', sa.String(length=100), nullable=False),
    sa.Column('chapter', sa.String(length=10), nullable=True),
    sa.Column('chapter_title', sa.String(length=255), nullable=True),
    sa.Column('section', sa.Integer(), nullable=True),
    sa.Column('section_title', sa.String(length=255), nullable=True),
    sa.Column('article_number', sa.Integer(), nullable=True),
    sa.Column('article_title', sa.String(length=255), nullable=True),
    sa.Column('article_id', sa.String(length=50), nullable=True),
    sa.Column('paragraph', sa.String(length=10), nullable=True),
    sa.Column('paragraph_index', sa.Integer(), nullable=True),
    sa.Column('point', sa.String(length=20), nullable=True),
    sa.Column('recital_number', sa.Integer(), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('lead_in', sa.Text(), server_default='', nullable=False),
    sa.Column('word_count', sa.Integer(), nullable=False),
    sa.Column('text_sha256', sa.String(length=64), nullable=False),
    sa.Column('source_anchor', sa.String(length=50), nullable=False),
    sa.Column('source_url', sa.Text(), nullable=False),
    sa.Column('cross_refs', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('footnote_refs', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('chunk_id')
    )
    op.create_index('ix_chunks_document_ordinal', 'chunks', ['document_id', 'ordinal'], unique=False)
    op.create_index('ix_chunks_document_article', 'chunks', ['document_id', 'article_number'], unique=False)
    op.create_index('ix_chunks_type', 'chunks', ['type'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_chunks_type', table_name='chunks')
    op.drop_index('ix_chunks_document_article', table_name='chunks')
    op.drop_index('ix_chunks_document_ordinal', table_name='chunks')
    op.drop_table('chunks')
    op.drop_table('documents')
