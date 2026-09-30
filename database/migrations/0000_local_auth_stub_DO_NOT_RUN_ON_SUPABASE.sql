-- LOCAL TESTING ONLY. Do not run this against the real Supabase project.
--
-- Supabase already provides `auth.users` automatically. This file exists
-- solely so the real schema (0001_initial_schema.sql) can be applied and
-- tested against a plain local Postgres instance, which has no
-- Supabase Auth installed. Every table below that references a user
-- references `auth.users(id)` — on Supabase that FK resolves to their
-- real table with no changes needed; locally, it resolves to this stub.

CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT
);
