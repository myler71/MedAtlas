-- 006_rag.sql
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    source VARCHAR(255),
    document_type VARCHAR(50) CHECK (document_type IN ('drug_info','clinical_guideline','patient_record','web_article','other')),
    content_hash VARCHAR(64) UNIQUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE rag_citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID NOT NULL,
    chunk_id UUID REFERENCES knowledge_chunks(id),
    claim_text TEXT,
    evidence_text TEXT,
    source VARCHAR(500),
    validated BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE rag_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    patient_id UUID REFERENCES patients(id),
    query_text TEXT NOT NULL,
    response_text TEXT,
    retrieval_mode VARCHAR(50) DEFAULT 'hybrid' CHECK (retrieval_mode IN ('local','tavily','hybrid')),
    citations_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_knowledge_chunks_doc ON knowledge_chunks(document_id);
CREATE INDEX idx_rag_citations_query ON rag_citations(query_id);
CREATE INDEX idx_rag_queries_patient ON rag_queries(patient_id, created_at DESC);
