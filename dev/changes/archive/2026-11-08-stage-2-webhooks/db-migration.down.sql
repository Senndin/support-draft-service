BEGIN;

DROP INDEX ix_tickets_status_next_attempt_at;

DROP TABLE tickets;

UPDATE alembic_version SET version_num = '325acc2e9ced' WHERE version_num = '3021c65eeb7b';

COMMIT;
