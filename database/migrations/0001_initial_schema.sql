-- Code Archaeologist — initial schema.
--
-- PROPOSAL, not final. Per Team Structure doc, M1 coordinates schema
-- changes. This file exists because the Database Design doc's column
-- lists for the "core" tables (repositories, analysis_jobs,
-- repository_files, commits, pull_requests, issues, contributors,
-- code_entities, dependencies, risk_records, knowledge_items,
-- knowledge_gaps) came through blank — only knowledge_embeddings,
-- evidence, offboarding_sessions, and offboarding_questions had columns
-- spelled out. Everything below marked INFERRED is reconstructed from
-- what M3's actual Phase 1-8 code queries and from the API Contract's
-- request/response shapes, not copied from an authoritative column list.
-- Get M1 to confirm or correct before this is treated as final.
--
-- Run 0000_local_auth_stub first if testing outside real Supabase.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

-- ---------------------------------------------------------------------
-- Repository
-- ---------------------------------------------------------------------

-- INFERRED. Columns match POST /repositories request+response exactly
-- (github_url, status) plus user_id for the isolation rule.
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    github_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_repositories_user_id ON repositories(user_id);

-- INFERRED. Status values per API Contract: queued, running, completed, failed.
CREATE TABLE analysis_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX idx_analysis_jobs_repository_id ON analysis_jobs(repository_id);

-- INFERRED. Matches what M3's Phase 1/2/4 code already reads (path,
-- language, content) plus size/hash for change detection on re-analysis.
CREATE TABLE repository_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    language TEXT,
    content TEXT,
    size INT,
    hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_repository_files_repository_id ON repository_files(repository_id);

-- ---------------------------------------------------------------------
-- Git history (M2's domain — INFERRED, confirm with M2)
-- ---------------------------------------------------------------------

-- INFERRED. Matches exactly what Phase 2's signals.py reads:
-- author, message, timestamp (change_frequency, revert_count,
-- activity_recency_days all key off these three fields).
CREATE TABLE commits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    commit_hash TEXT NOT NULL,
    author TEXT,
    message TEXT,
    "timestamp" TIMESTAMPTZ,
    diff TEXT
);
CREATE INDEX idx_commits_repository_id ON commits(repository_id);

-- INFERRED. Not yet consumed by any M3 module directly; included because
-- the API/evidence model references pull requests as an evidence source.
CREATE TABLE pull_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    external_id TEXT,
    title TEXT,
    description TEXT,
    author TEXT,
    status TEXT,
    created_at TIMESTAMPTZ,
    merged_at TIMESTAMPTZ
);
CREATE INDEX idx_pull_requests_repository_id ON pull_requests(repository_id);

-- INFERRED. Same reasoning as pull_requests.
CREATE TABLE issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    external_id TEXT,
    title TEXT,
    description TEXT,
    author TEXT,
    status TEXT,
    created_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ
);
CREATE INDEX idx_issues_repository_id ON issues(repository_id);

-- INFERRED. Matches exactly what Phase 2's signals.py and Phase 8's
-- question_generator.py read: external_id, name, commit_count.
CREATE TABLE contributors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    external_id TEXT,
    name TEXT,
    email_hash TEXT,
    commit_count INT NOT NULL DEFAULT 0,
    first_seen TIMESTAMPTZ,
    last_seen TIMESTAMPTZ
);
CREATE INDEX idx_contributors_repository_id ON contributors(repository_id);

-- ---------------------------------------------------------------------
-- Static parsing (M3 Phase 1 — CONFIRMED, matches entity_extractor.py exactly)
-- ---------------------------------------------------------------------

CREATE TABLE code_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    file_id UUID NOT NULL REFERENCES repository_files(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('function', 'class', 'method')),
    name TEXT NOT NULL,
    start_line INT,
    end_line INT,
    signature TEXT
);
CREATE INDEX idx_code_entities_repository_id ON code_entities(repository_id);
CREATE INDEX idx_code_entities_file_id ON code_entities(file_id);

CREATE TABLE dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    source_entity_id UUID NOT NULL REFERENCES code_entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES code_entities(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL
);
CREATE INDEX idx_dependencies_repository_id ON dependencies(repository_id);
CREATE INDEX idx_dependencies_target_entity_id ON dependencies(target_entity_id);

-- ---------------------------------------------------------------------
-- Risk (M3 Phase 2 — CONFIRMED, matches risk_scorer.py's score_file() output)
-- ---------------------------------------------------------------------

CREATE TABLE risk_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    file_id UUID NOT NULL REFERENCES repository_files(id) ON DELETE CASCADE,
    score FLOAT NOT NULL,
    signals JSONB NOT NULL,
    explanation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_risk_records_repository_id ON risk_records(repository_id);

-- ---------------------------------------------------------------------
-- Knowledge (M3 Phase 5 — CONFIRMED, matches knowledge_store.py exactly)
-- ---------------------------------------------------------------------

CREATE TABLE knowledge_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_knowledge_items_repository_id ON knowledge_items(repository_id);

CREATE TABLE knowledge_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    context TEXT,
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    resolved_knowledge_item_id UUID REFERENCES knowledge_items(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX idx_knowledge_gaps_repository_id ON knowledge_gaps(repository_id);
CREATE INDEX idx_knowledge_gaps_status ON knowledge_gaps(status);

-- Vector dimension is 384 to match Phase 4's embeddings.py, which uses
-- the all-MiniLM-L6-v2 model (or its own documented fallback, same
-- dimension either way). If M1/M4 ever swap embedding models, this
-- dimension must change to match — it is not arbitrary.
CREATE TABLE knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    knowledge_item_id UUID REFERENCES knowledge_items(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_knowledge_embeddings_repository_id ON knowledge_embeddings(repository_id);
-- IVFFlat index for approximate nearest-neighbor search at scale. Requires
-- ANALYZE after bulk inserts to be effective; harmless if the table is small.
CREATE INDEX idx_knowledge_embeddings_vector ON knowledge_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ---------------------------------------------------------------------
-- Evidence — CONFIRMED shape from Database Design doc, but NOT YET
-- WRITTEN TO by any delivered M3 code. historian.py currently builds
-- evidence as an in-memory list per question and never persists it here.
-- "Evidence assembly" is M3's explicit ownership — this is an open gap
-- in Phase 5/7, not something for M1/M2 to fix.
-- ---------------------------------------------------------------------

CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL
        CHECK (source_type IN ('file', 'commit', 'pull_request', 'issue', 'knowledge_item')),
    source_id UUID,
    file_id UUID REFERENCES repository_files(id),
    commit_id UUID REFERENCES commits(id),
    pull_request_id UUID REFERENCES pull_requests(id),
    issue_id UUID REFERENCES issues(id),
    knowledge_item_id UUID REFERENCES knowledge_items(id),
    excerpt TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_evidence_repository_id ON evidence(repository_id);

-- ---------------------------------------------------------------------
-- Offboarding (M3 Phase 8 — CONFIRMED, matches question_generator.py /
-- report_builder.py exactly)
-- ---------------------------------------------------------------------

CREATE TABLE offboarding_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    contributor_id UUID NOT NULL REFERENCES contributors(id),
    status TEXT NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX idx_offboarding_sessions_repository_id ON offboarding_sessions(repository_id);

CREATE TABLE offboarding_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES offboarding_sessions(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    answer TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'answered'))
);
CREATE INDEX idx_offboarding_questions_session_id ON offboarding_questions(session_id);
