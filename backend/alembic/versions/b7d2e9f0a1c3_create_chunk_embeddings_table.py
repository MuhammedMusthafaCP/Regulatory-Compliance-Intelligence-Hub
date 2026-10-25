"""create chunk_embeddings table

Revision ID: b7d2e9f0a1c3
Revises: a3f1c2d4e5b6
Create Date: 2026-10-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = 'b7d2e9f0a1c3'
down_revision: Union[str, None] = 'a3f1c2d4e5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No vector index yet: Step 3 starts with exact (sequential-scan) search.
    op.create_table('chunk_embeddings',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('chunk_id', sa.BigInteger(), nullable=False),
    sa.Column('model', sa.String(length=100), nullable=False),
    sa.Column('model_revision', sa.String(length=64), nullable=False),
    sa.Column('variant', sa.String(length=10), nullable=False),
    sa.Column('embedded_text_sha256', sa.String(length=64), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=False),
    sa.Column('embedded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['chunk_id'], ['chunks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('chunk_id', 'model', 'model_revision', 'variant', name='uq_chunk_embeddings_chunk_model_variant')
    )


def downgrade() -> None:
    op.drop_table('chunk_embeddings')
