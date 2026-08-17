-- 005_drugs.sql
CREATE TABLE drug_concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rxnorm_cui VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255),
    drug_class VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE drug_aliases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_concept_id UUID NOT NULL REFERENCES drug_concepts(id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL,
    alias_type VARCHAR(50) DEFAULT 'brand' CHECK (alias_type IN ('brand','synonym','abbreviation','other')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(drug_concept_id, alias)
);

CREATE TABLE drug_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_a_id UUID NOT NULL REFERENCES drug_concepts(id) ON DELETE CASCADE,
    drug_b_id UUID NOT NULL REFERENCES drug_concepts(id) ON DELETE CASCADE,
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('minor','moderate','major','contraindicated')),
    mechanism TEXT,
    clinical_significance TEXT,
    evidence_source VARCHAR(255),
    evidence_strength VARCHAR(50) CHECK (evidence_strength IN ('theoretical','case_reports','established','unknown')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (drug_a_id < drug_b_id),
    UNIQUE(drug_a_id, drug_b_id)
);

CREATE TABLE drug_cache (
    rxnorm_cui VARCHAR(20) PRIMARY KEY,
    payload JSONB NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_drug_concepts_rxnorm ON drug_concepts(rxnorm_cui);
CREATE INDEX idx_drug_concepts_name ON drug_concepts USING gin(to_tsvector('english', name));
CREATE INDEX idx_drug_aliases_alias ON drug_aliases USING gin(to_tsvector('english', alias));
CREATE INDEX idx_drug_interactions_drugs ON drug_interactions(drug_a_id, drug_b_id);