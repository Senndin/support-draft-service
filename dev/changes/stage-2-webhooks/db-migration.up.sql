BEGIN;

CREATE TABLE tickets (
    id BIGSERIAL NOT NULL,
    event_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    message TEXT NOT NULL,
    reply_url TEXT NOT NULL,
    status TEXT DEFAULT 'received' NOT NULL,
    draft TEXT,
    final_message TEXT,
    article_ids INTEGER[],
    attempts INTEGER DEFAULT 0 NOT NULL,
    next_attempt_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    locked_until TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    idempotency_key UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_tickets_event_id UNIQUE (event_id)
);

CREATE INDEX ix_tickets_status_next_attempt_at ON tickets (status, next_attempt_at);

UPDATE alembic_version SET version_num = '3021c65eeb7b' WHERE version_num = '325acc2e9ced';

COMMIT;
