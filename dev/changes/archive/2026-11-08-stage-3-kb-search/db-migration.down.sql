BEGIN;

DROP INDEX ix_kb_articles_search_vector;

DROP TABLE kb_articles;

DROP EXTENSION IF EXISTS pg_trgm;

UPDATE alembic_version SET version_num = '3021c65eeb7b' WHERE version_num = 'bdf2365c46d7';

COMMIT;
