"""Add pgvector support for RAG pipeline

Revision ID: 001_pgvector
Revises: fb7e7764afa0
Create Date: 2026-04-21

This migration:
1. Enables the pgvector extension
2. Adds embedding column to ai_training_files table
3. Creates indexes for vector search performance
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '001_pgvector'
down_revision = 'fb7e7764afa0'
branch_labels = None
depends_on = None


def upgrade():
    """Enable pgvector and add embedding support."""
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Add embedding column to ai_training_files
    # Using Vector(1536) for OpenAI's text-embedding-3-small model
    op.add_column(
        'ai_training_files',
        sa.Column(
            'embedding',
            Vector(1536),
            nullable=True,
            comment='Vector embedding for semantic search (1536-dim for text-embedding-3-small)'
        )
    )
    
    # Create IVFFLAT index for fast vector similarity search
    # Using vector_cosine_ops for cosine distance (best for text embeddings)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_ai_training_files_embedding '
        'ON ai_training_files USING ivfflat (embedding vector_cosine_ops) '
        'WITH (lists = 100)'
    )
    
    # Analyze the table for query planner optimization
    op.execute('ANALYZE ai_training_files')


def downgrade():
    """Disable pgvector support and remove embedding column."""
    # Drop the index
    op.execute('DROP INDEX IF EXISTS ix_ai_training_files_embedding')
    
    # Remove embedding column
    op.drop_column('ai_training_files', 'embedding')
    
    # Drop pgvector extension (only if no other tables use it)
    op.execute('DROP EXTENSION IF NOT EXISTS vector CASCADE')
