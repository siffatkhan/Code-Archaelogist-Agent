-- Persist metadata needed to resume the repository workflow after an API restart.
ALTER TABLE repositories
    ADD COLUMN IF NOT EXISTS default_branch TEXT,
    ADD COLUMN IF NOT EXISTS last_analyzed_at TIMESTAMPTZ;