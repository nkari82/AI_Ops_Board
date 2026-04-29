"""baseline crawled_posts schema

Revision ID: 20260428_0001
Revises:
Create Date: 2026-04-28 22:10:00
"""

from alembic import op


revision = "20260428_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS crawled_posts (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            url VARCHAR(1000) NOT NULL,
            source VARCHAR(2000) NOT NULL,
            source_type VARCHAR(500) NOT NULL,
            content TEXT,
            score INTEGER,
            extra_data JSON,
            embedding vector(1536),
            summary TEXT,
            domain VARCHAR(500),
            category VARCHAR(500),
            tags JSON,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            doc_type VARCHAR(100),
            tech_stack JSON
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_crawled_posts_id ON crawled_posts (id)")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uix_crawled_post_url'
            ) THEN
                ALTER TABLE crawled_posts
                ADD CONSTRAINT uix_crawled_post_url UNIQUE (url);
            END IF;
        END
        $$;
        """
    )
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS content TEXT")
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS score INTEGER")
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS extra_data JSON")
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS embedding vector(1536)")
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS summary TEXT")
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS domain VARCHAR(500)")
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS category VARCHAR(500)")
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS tags JSON")
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()")
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()")
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS doc_type VARCHAR(100)")
    op.execute("ALTER TABLE crawled_posts ADD COLUMN IF NOT EXISTS tech_stack JSON")


def downgrade() -> None:
    pass
