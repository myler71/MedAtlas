# Clinical Platform — Data Structures (数据结构详解)

## 1. Database Schema Entity-Relationship Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    roles     │     │   clinics    │     │    users     │
│──────────────│     │──────────────│     │──────────────│
│ id: UUID PK  │     │ id: UUID PK  │◄────│ clinic_id: FK│
│ name: VARCHAR│     │ name: VARCHAR│     │ id: UUID PK  │
│ permissions  │     │ address: TEXT│     │ email: UNIQUE│
│   : JSONB    │     │ phone: VARCHAR     │ password_hash│
└──────────────┘     └──────┬───────┘     │ full_name    │
                            │             │ role: VARCHAR│
                            │             │ deleted_at   │
                            ▼             └──────┬───────┘
                     ┌──────────────┐            │
                     │  patients    │◄───────────┘
                     │──────────────│  (created_by)
                     │ id: UUID PK  │
                     │ clinic_id: FK│
                     │ first_name   │
                     │ last_name    │
                     │ DOB, gender  │
                     │ deleted_at   │
                     └──────┬───────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ dental_charts│ │orthopedic_   │ │medical_      │
    │              │ │charts        │ │histories     │
    │ teeth        │ │body_regions  │ ├──────────────┤
    │ tooth_events │ │bones         │ │allergies     │
    └──────────────┘ │bone_events   │ │medications   │
                     └──────────────┘ └──────────────┘
           │                │                │
           ▼                ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │drug_concepts │ │knowledge_    │ │appointments  │
    │drug_aliases  │ │documents     │ ├──────────────┤
    │drug_         │ │knowledge_    │ │audit_logs    │
    │interactions  │ │chunks        │ │attachments   │
    │drug_cache    │ │rag_citations │ │patient_access│
    └──────────────┘ │rag_queries   │ └──────────────┘
                     └──────────────┘
```

---

## 2. Core Tables (核心表)

### 2.1 `roles`

[VERIFY: clinical-platform/database/schema.sql:6-11]

```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,       -- 'dentist', 'orthopedist', 'admin'
    permissions JSONB DEFAULT '[]'::jsonb,   -- e.g. ["patients.read","dental.write"]
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Default seed data** (schema.sql:121-124):
- `dentist`: patients.r/w, dental.r/w, drugs.r, chat.patient, appointments.r/w
- `orthopedist`: patients.r/w, ortho.r/w, drugs.r, chat.patient, appointments.r/w
- `admin`: all permissions + audit.read, users.r/w, admin.all

### 2.2 `clinics`

[VERIFY: clinical-platform/database/schema.sql:14-21]

```sql
CREATE TABLE clinics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    phone VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Tenant boundary**: All patient data is scoped to a clinic. The `clinic_id` is injected into every FastAPI request via proxy headers.

### 2.3 `users`

[VERIFY: clinical-platform/database/schema.sql:24-34]

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,     -- bcrypt cost 12
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'dentist',  -- FK to roles.name (logical, not enforced)
    clinic_id UUID REFERENCES clinics(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ                   -- soft delete
);
```

**Indexes** (schema.sql:108-109):
- `idx_users_email` — WHERE deleted_at IS NULL
- `idx_users_clinic` — WHERE deleted_at IS NULL

### 2.4 `patients`

[VERIFY: clinical-platform/database/schema.sql:37-52]

```sql
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(20),
    phone VARCHAR(50),
    email VARCHAR(255),
    address TEXT,
    emergency_contact TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    deleted_at TIMESTAMPTZ                   -- soft delete
);
```

**Pydantic schemas** (schemas/patient.py:6-40):
- `PatientCreate`: first_name, last_name, DOB, gender, phone, email, address, emergency_contact
- `PatientUpdate`: All fields Optional
- `PatientResponse`: All fields + id, created_at, updated_at

### 2.5 `patient_access`

[VERIFY: clinical-platform/database/schema.sql:55-63]

```sql
CREATE TABLE patient_access (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_level VARCHAR(50) DEFAULT 'read',  -- 'read' or 'full'
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by UUID REFERENCES users(id),
    UNIQUE(patient_id, user_id)
);
```

**Note**: This table exists in the schema but is **not enforced** in FastAPI routes. Clinic-level scoping is used instead (clinic_id check in each endpoint).

### 2.6 `appointments`

[VERIFY: clinical-platform/database/schema.sql:66-78]

```sql
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id),
    user_id UUID NOT NULL REFERENCES users(id),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    scheduled_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    status VARCHAR(50) DEFAULT 'scheduled',  -- 'scheduled', 'completed', 'cancelled'
    type VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.7 `audit_logs`

[VERIFY: clinical-platform/database/schema.sql:81-91]

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,            -- e.g. "GET /api/patients"
    resource_type VARCHAR(100),              -- extracted from path segment [2]
    resource_id UUID,                        -- from req.params.id
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN DEFAULT true,           -- res.statusCode < 400
    metadata JSONB DEFAULT '{}'::jsonb,      -- { duration_ms, status }
    ip_address VARCHAR(45)
);
```

**Written by**: `audit.js` middleware on every `/api/*` response finish.

### 2.8 `attachments`

[VERIFY: clinical-platform/database/schema.sql:94-105]

```sql
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id),
    entity_type VARCHAR(100) NOT NULL,       -- e.g. 'tooth_event', 'bone_event'
    entity_id UUID NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(100),
    file_size INTEGER,
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 3. Dental Domain Tables (牙科领域表)

### 3.1 `dental_charts`

[VERIFY: clinical-platform/database/migrations/002_dental.sql:2-7]

```sql
CREATE TABLE dental_charts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL UNIQUE REFERENCES patients(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Relationship**: One chart per patient (UNIQUE constraint). Created lazily on first access.

### 3.2 `teeth`

[VERIFY: clinical-platform/database/migrations/002_dental.sql:9-20]

```sql
CREATE TABLE teeth (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dental_chart_id UUID NOT NULL REFERENCES dental_charts(id) ON DELETE CASCADE,
    tooth_number_fdi SMALLINT NOT NULL,  -- FDI (ISO 3950): 11-18, 21-28, 31-38, 41-48
    tooth_name VARCHAR(100),
    dentition_type VARCHAR(20) NOT NULL CHECK (dentition_type IN ('permanent','primary')),
    position_in_quadrant SMALLINT NOT NULL CHECK (position_in_quadrant BETWEEN 1 AND 8),
    quadrant SMALLINT NOT NULL CHECK (quadrant BETWEEN 1 AND 4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(dental_chart_id, tooth_number_fdi)
);
```

**FDI Numbering System** (numbering.py:4-8):
- Permanent teeth: quadrants 1-4 (UR, UL, LL, LR), positions 1-8
  - FDI 11..18 (Upper Right), 21..28 (Upper Left), 31..38 (Lower Left), 41..48 (Lower Right)
- Primary teeth: quadrants 5-8, positions 1-5

**Numbering conversions** (numbering.py:35-124):
- `fdi_to_universal(fdi)`: FDI → ADA Universal (1-32, A-T)
- `universal_to_fdi(universal)`: ADA → FDI
- `fdi_to_palmer(fdi)`: FDI → Palmer (┌1, ┐2, └3, ┘4 + position)
- `palmer_to_fdi(palmer)`: Palmer → FDI

### 3.3 `tooth_events`

[VERIFY: clinical-platform/database/migrations/002_dental.sql:22-38]

```sql
CREATE TABLE tooth_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tooth_id UUID NOT NULL REFERENCES teeth(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL
        CHECK (event_type IN ('exam','caries','restoration','extraction',
               'root_canal','crown','implant','fracture','cleaning','other')),
    procedure_name VARCHAR(255),
    diagnosis TEXT,
    event_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(50) DEFAULT 'active'
        CHECK (status IN ('active','archived')),
    surfaces JSONB DEFAULT '[]'::jsonb,      -- tooth surface codes
    provider_id UUID REFERENCES users(id),
    notes TEXT,
    attachments JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);
```

**State derivation** (dental.py:56-68):
```python
def _derive_state(event_type):
    mapping = {
        "caries": "caries", "restoration": "restored",
        "extraction": "missing", "root_canal": "root_canal",
        "crown": "crown", "implant": "implant", "fracture": "fractured",
    }
    return mapping.get(event_type, "treated")
```

---

## 4. Orthopedic Domain Tables (骨科领域表)

### 4.1 `orthopedic_charts`

[VERIFY: clinical-platform/database/migrations/003_orthopedic.sql:2-7]

```sql
CREATE TABLE orthopedic_charts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL UNIQUE REFERENCES patients(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.2 `body_regions`

[VERIFY: clinical-platform/database/migrations/003_orthopedic.sql:9-19]

```sql
CREATE TABLE body_regions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    orthopedic_chart_id UUID NOT NULL REFERENCES orthopedic_charts(id) ON DELETE CASCADE,
    region_name VARCHAR(100) NOT NULL,
    region_code VARCHAR(50) NOT NULL,
    side VARCHAR(10) CHECK (side IN ('left','right','midline','bilateral')),
    svg_path TEXT,                           -- SVG path data for interactive rendering
    UNIQUE(orthopedic_chart_id, region_code, side)
);
```

**Standard body regions** (orthopedic.py:16-44): 26 regions with SVG paths including:
- Head, Neck (Cervical), Shoulders (L/R), Upper Arms (L/R), Elbows (L/R), Lower Arms (L/R), Hands (L/R)
- Thoracic Spine, Lumbar Spine, Sacrum, Ribs, Pelvis
- Hips (L/R), Upper Legs (L/R), Knees (L/R), Lower Legs (L/R), Feet (L/R)

### 4.3 `bones`

[VERIFY: clinical-platform/database/migrations/003_orthopedic.sql:21-31]

```sql
CREATE TABLE bones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    body_region_id UUID NOT NULL REFERENCES body_regions(id) ON DELETE CASCADE,
    bone_name VARCHAR(100) NOT NULL,
    bone_code VARCHAR(50) NOT NULL,
    side VARCHAR(10) CHECK (side IN ('left','right','midline')),
    svg_path TEXT,
    UNIQUE(body_region_id, bone_code)
);
```

**Bones per region** (orthopedic.py:46-64): Maps region_code → bone definitions:
- head → Skull
- cervical → C1-C7 Vertebrae
- shoulder → Clavicle + Scapula
- upper_arm → Humerus
- elbow → Elbow Joint
- lower_arm → Radius + Ulna
- hand → Carpals + Metacarpals
- hip → Femoral Head
- upper_leg → Femur
- knee → Patella + Knee Joint
- lower_leg → Tibia + Fibula
- foot → Tarsals + Metatarsals

### 4.4 `bone_events`

[VERIFY: clinical-platform/database/migrations/003_orthopedic.sql:33-49]

```sql
CREATE TABLE bone_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bone_id UUID NOT NULL REFERENCES bones(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL
        CHECK (event_type IN ('exam','fracture','sprain','dislocation','surgery',
               'implant','arthritis','healing','follow_up','other')),
    diagnosis TEXT,
    event_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active','archived')),
    treatment TEXT,
    healing_status VARCHAR(50)
        CHECK (healing_status IN ('acute','recovering','healed','chronic','unknown')),
    side VARCHAR(10) CHECK (side IN ('left','right','midline')),
    notes TEXT,
    attachments JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);
```

**State derivation** (orthopedic.py:109-122):
```python
def _derive_bone_state(event_type):
    mapping = {
        "fracture": "fracture", "sprain": "under_treatment",
        "dislocation": "under_treatment", "surgery": "surgical",
        "implant": "surgical", "arthritis": "chronic",
        "healing": "healing", "follow_up": "follow_up",
    }
    return mapping.get(event_type, "treated")
```

---

## 5. Patient Enrichment Tables (患者补充表)

### 5.1 `medical_histories`

[VERIFY: clinical-platform/database/migrations/004_patient_enrichment.sql:2-11]

```sql
CREATE TABLE medical_histories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    condition_name VARCHAR(255) NOT NULL,
    diagnosed_date DATE,
    status VARCHAR(50) DEFAULT 'active'
        CHECK (status IN ('active','resolved','chronic','in_remission')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.2 `allergies`

[VERIFY: clinical-platform/database/migrations/004_patient_enrichment.sql:13-22]

```sql
CREATE TABLE allergies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    allergen VARCHAR(255) NOT NULL,
    severity VARCHAR(50) DEFAULT 'mild'
        CHECK (severity IN ('mild','moderate','severe','life_threatening')),
    reaction TEXT,
    noted_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.3 `medications`

[VERIFY: clinical-platform/database/migrations/004_patient_enrichment.sql:24-37]

```sql
CREATE TABLE medications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    drug_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100),
    frequency VARCHAR(100),
    route VARCHAR(50) CHECK (route IN ('oral','iv','im','topical','subcutaneous','inhaled','other')),
    start_date DATE DEFAULT CURRENT_DATE,
    end_date DATE,
    prescriber VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active'
        CHECK (status IN ('active','discontinued','completed','on_hold')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. Drug Intelligence Tables (药物情报表)

### 6.1 `drug_concepts`

[VERIFY: clinical-platform/database/migrations/005_drugs.sql:2-10]

```sql
CREATE TABLE drug_concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rxnorm_cui VARCHAR(20) UNIQUE NOT NULL,   -- RxNorm Concept Unique Identifier
    name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255),
    drug_class VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Index**: GIN index on `to_tsvector('english', name)` for full-text search.

### 6.2 `drug_aliases`

[VERIFY: clinical-platform/database/migrations/005_drugs.sql:12-19]

```sql
CREATE TABLE drug_aliases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_concept_id UUID NOT NULL REFERENCES drug_concepts(id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL,
    alias_type VARCHAR(50) DEFAULT 'brand'
        CHECK (alias_type IN ('brand','synonym','abbreviation','other')),
    UNIQUE(drug_concept_id, alias)
);
```

### 6.3 `drug_interactions`

[VERIFY: clinical-platform/database/migrations/005_drugs.sql:21-33]

```sql
CREATE TABLE drug_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_a_id UUID NOT NULL REFERENCES drug_concepts(id) ON DELETE CASCADE,
    drug_b_id UUID NOT NULL REFERENCES drug_concepts(id) ON DELETE CASCADE,
    severity VARCHAR(50) NOT NULL
        CHECK (severity IN ('minor','moderate','major','contraindicated')),
    mechanism TEXT,
    clinical_significance TEXT,
    evidence_source VARCHAR(255),
    evidence_strength VARCHAR(50)
        CHECK (evidence_strength IN ('theoretical','case_reports','established','unknown')),
    CHECK (drug_a_id < drug_b_id),           -- canonical ordering
    UNIQUE(drug_a_id, drug_b_id)
);
```

### 6.4 `drug_cache`

[VERIFY: clinical-platform/database/migrations/005_drugs.sql:35-39]

```sql
CREATE TABLE drug_cache (
    rxnorm_cui VARCHAR(20) PRIMARY KEY,
    payload JSONB NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 7. RAG / AI Tables (RAG/AI 表)

### 7.1 `knowledge_documents`

[VERIFY: clinical-platform/database/migrations/006_rag.sql:2-10]

```sql
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    source VARCHAR(255),
    document_type VARCHAR(50)
        CHECK (document_type IN ('drug_info','clinical_guideline','patient_record','web_article','other')),
    content_hash VARCHAR(64) UNIQUE,          -- deduplication
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 7.2 `knowledge_chunks`

[VERIFY: clinical-platform/database/migrations/006_rag.sql:12-20]

```sql
CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),                   -- pgvector column
    metadata JSONB DEFAULT '{}'::jsonb,       -- e.g. {"patient_id": "...", "source": "..."}
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Index** (006_rag.sql:44):
```sql
CREATE INDEX idx_knowledge_chunks_embedding
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 7.3 `rag_citations`

[VERIFY: clinical-platform/database/migrations/006_rag.sql:22-31]

```sql
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
```

### 7.4 `rag_queries`

[VERIFY: clinical-platform/database/migrations/006_rag.sql:33-42]

```sql
CREATE TABLE rag_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    patient_id UUID REFERENCES patients(id),
    query_text TEXT NOT NULL,
    response_text TEXT,
    retrieval_mode VARCHAR(50) DEFAULT 'hybrid'
        CHECK (retrieval_mode IN ('local','tavily','hybrid')),
    citations_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 8. Python Data Models (Python 数据模型)

### 8.1 DrugConcept (Pydantic)

[VERIFY: clinical-platform/backend/fastapi/app/services/drugs/provider.py:8-13]

```python
class DrugConcept(BaseModel):
    rxnorm_cui: str
    name: str
    generic_name: Optional[str] = None
    drug_class: Optional[str] = None
    aliases: List[str] = []
```

### 8.2 DrugInteraction / InteractionCheckResult

[VERIFY: clinical-platform/backend/fastapi/app/services/drugs/interactions.py:15-31]

```python
class DrugInteraction(BaseModel):
    drug_a: str
    drug_a_cui: str
    drug_b: str
    drug_b_cui: str
    severity: str                        # minor|moderate|major|contraindicated
    mechanism: Optional[str]
    clinical_significance: Optional[str]
    evidence_source: Optional[str]
    evidence_strength: Optional[str]

class InteractionCheckResult(BaseModel):
    drugs_resolved: List[dict]
    interactions: List[DrugInteraction]
    warnings: List[str] = []
```

### 8.3 RetrievedChunk

[VERIFY: clinical-platform/backend/fastapi/app/rag/retrieval.py:11-16]

```python
class RetrievedChunk:
    def __init__(self, content: str, source: str, score: float, metadata: Dict[str, Any] = None):
        self.content = content
        self.source = source
        self.score = score
        self.metadata = metadata or {}
```

### 8.4 PatientChatResponse

[VERIFY: clinical-platform/backend/fastapi/app/ai/patient_assistant.py:27-40]

```python
class PatientChatResponse(BaseModel):
    patient_name: str
    patient_id: str
    summary: str
    dental_history: List[Dict[str, Any]] = []
    orthopedic_history: List[Dict[str, Any]] = []
    recent_procedures: List[Dict[str, Any]] = []
    current_medications: List[Dict[str, Any]] = []
    allergies: List[Dict[str, Any]] = []
    tooth_findings: List[Dict[str, Any]] = []
    bone_findings: List[Dict[str, Any]] = []
    important_notes: List[str] = []
    missing_information: List[str] = []
    citations: List[Citation] = []
```

### 8.5 Citation

[VERIFY: clinical-platform/backend/fastapi/app/ai/patient_assistant.py:19-25]

```python
class Citation(BaseModel):
    source: str
    title: Optional[str] = None
    url: Optional[str] = None
    claim: Optional[str] = None
    evidence_excerpt: Optional[str] = None
```

### 8.6 UserContext

[VERIFY: clinical-platform/backend/fastapi/app/services/auth_context.py:5-9]

```python
class UserContext:
    def __init__(self, user_id: UUID, role: str, clinic_id: Optional[UUID]):
        self.user_id = user_id
        self.role = role
        self.clinic_id = clinic_id
```

---

## 9. Table Relationship Summary

| Parent | Child | FK | Cascade |
|--------|-------|----|---------|
| clinics | users | clinic_id | RESTRICT |
| clinics | patients | clinic_id | RESTRICT |
| users | patients | created_by | SET NULL |
| patients | patient_access | patient_id | CASCADE |
| users | patient_access | user_id | CASCADE |
| patients | appointments | patient_id | RESTRICT |
| users | appointments | user_id | RESTRICT |
| clinics | appointments | clinic_id | RESTRICT |
| patients | dental_charts | patient_id | CASCADE |
| dental_charts | teeth | dental_chart_id | CASCADE |
| patients | tooth_events | patient_id | CASCADE |
| teeth | tooth_events | tooth_id | CASCADE |
| patients | orthopedic_charts | patient_id | CASCADE |
| orthopedic_charts | body_regions | orthopedic_chart_id | CASCADE |
| body_regions | bones | body_region_id | CASCADE |
| patients | bone_events | patient_id | CASCADE |
| bones | bone_events | bone_id | CASCADE |
| patients | medical_histories | patient_id | CASCADE |
| patients | allergies | patient_id | CASCADE |
| patients | medications | patient_id | CASCADE |
| drug_concepts | drug_aliases | drug_concept_id | CASCADE |
| drug_concepts | drug_interactions | drug_a_id, drug_b_id | CASCADE |
| knowledge_documents | knowledge_chunks | document_id | CASCADE |
| users | audit_logs | user_id | SET NULL |
| patients | attachments | patient_id | RESTRICT |

**Soft-delete pattern**: `users` and `patients` use `deleted_at` column instead of physical deletion. Queries filter `WHERE deleted_at IS NULL`.
