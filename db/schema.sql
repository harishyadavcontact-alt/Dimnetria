CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE people (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  full_name TEXT NOT NULL,
  primary_country TEXT,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE people_aliases (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  alias TEXT NOT NULL
);

CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  org_type TEXT NOT NULL CHECK (org_type IN ('agency','corp','ngo','party','thinktank','other')),
  country TEXT,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE evidence (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_type TEXT NOT NULL CHECK (source_type IN ('registry','filing','watchdog_db','news','report','court','webpage','other')),
  publisher TEXT NOT NULL,
  title TEXT,
  url TEXT NOT NULL,
  accessed_at TIMESTAMPTZ NOT NULL,
  content_hash TEXT NOT NULL,
  raw_storage_path TEXT NOT NULL,
  extracted_text_path TEXT NOT NULL,
  trust_tier INT NOT NULL CHECK (trust_tier BETWEEN 1 AND 4),
  license_notes TEXT
);

CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  start_date DATE,
  end_date DATE,
  evidence_id UUID REFERENCES evidence(id),
  confidence NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1)
);

CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title TEXT NOT NULL,
  category TEXT NOT NULL CHECK (category IN ('policy','vote','reg_action','corp_action','advisory','forecast','public_statement','other')),
  start_date DATE,
  end_date DATE,
  jurisdiction TEXT,
  summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE event_participants (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  role_in_event TEXT NOT NULL,
  org_id UUID REFERENCES organizations(id),
  confidence NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1)
);

CREATE TABLE event_outcomes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  outcome_type TEXT NOT NULL CHECK (outcome_type IN ('financial','legal','social','operational')),
  magnitude_value NUMERIC,
  magnitude_currency TEXT,
  magnitude_text TEXT,
  affected_party TEXT CHECK (affected_party IN ('taxpayers','shareholders','customers','public','other')),
  evidence_id UUID REFERENCES evidence(id),
  confidence NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1)
);

CREATE TABLE extractions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
  extractor_version TEXT NOT NULL,
  model_name TEXT,
  schema_version TEXT NOT NULL,
  json_output JSONB NOT NULL,
  confidence NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE signals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  subject_type TEXT NOT NULL CHECK (subject_type IN ('person','event','org')),
  subject_id UUID NOT NULL,
  signal_type TEXT NOT NULL,
  value_numeric NUMERIC,
  value_text TEXT,
  evidence_id UUID REFERENCES evidence(id),
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE scores (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  subject_type TEXT NOT NULL CHECK (subject_type IN ('person','event','org')),
  subject_id UUID NOT NULL,
  score_type TEXT NOT NULL CHECK (score_type IN ('SITG','ELI','FCS','II','FS')),
  score_value INT NOT NULL CHECK (score_value BETWEEN 0 AND 100),
  score_version TEXT NOT NULL,
  explanation_json JSONB NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE discoveries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  subject_type TEXT NOT NULL CHECK (subject_type IN ('person','event','org')),
  subject_id UUID NOT NULL,
  pattern_type TEXT NOT NULL CHECK (pattern_type IN ('BOB_RUBIN_TRADE','REVOLVING_DOOR','BAILOUT_TO_BOARDROOM','COMPLEXITY_ARBITRAGE','POSTDICTING_STIGLITZ','IATROGENIC_INTERVENTION')),
  pattern_label TEXT NOT NULL,
  severity_score INT NOT NULL CHECK (severity_score BETWEEN 0 AND 100),
  confidence NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  explanation_json JSONB NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('suggested','captured','dismissed','flagged_for_review'))
);

CREATE TABLE discovery_evidence (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  discovery_id UUID NOT NULL REFERENCES discoveries(id) ON DELETE CASCADE,
  evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE
);

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE captures (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  discovery_id UUID NOT NULL REFERENCES discoveries(id) ON DELETE CASCADE,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  note TEXT,
  verification_level TEXT CHECK (verification_level IN ('viewed_evidence','verified_sources','expert_review')),
  share_token TEXT UNIQUE
);

CREATE TABLE user_actions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  action_type TEXT NOT NULL CHECK (action_type IN ('viewed_evidence','captured','shared','flagged')),
  entity_type TEXT NOT NULL,
  entity_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_discoveries_subject ON discoveries(subject_type, subject_id);
CREATE INDEX idx_scores_subject ON scores(subject_type, subject_id);
CREATE INDEX idx_events_title_fts ON events USING gin(to_tsvector('english', title));
CREATE INDEX idx_people_name_fts ON people USING gin(to_tsvector('english', full_name));
CREATE INDEX idx_orgs_name_fts ON organizations USING gin(to_tsvector('english', name));
