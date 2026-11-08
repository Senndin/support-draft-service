BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE kb_articles (
    id SERIAL NOT NULL,
    slug TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    url TEXT NOT NULL,
    search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', title || ' ' || body)) STORED NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_kb_articles_slug UNIQUE (slug)
);

CREATE INDEX ix_kb_articles_search_vector ON kb_articles USING gin (search_vector);

UPDATE alembic_version SET version_num = 'bdf2365c46d7' WHERE version_num = '3021c65eeb7b';

COMMIT;
