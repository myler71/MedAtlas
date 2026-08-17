-- 002_dental.sql
CREATE TABLE dental_charts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL UNIQUE REFERENCES patients(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE teeth (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dental_chart_id UUID NOT NULL REFERENCES dental_charts(id) ON DELETE CASCADE,
    tooth_number_fdi SMALLINT NOT NULL,  -- canonical FDI: 11-18, 21-28, 31-38, 41-48 (permanent) + 51-55, 61-65, 71-75, 81-85 (primary)
    tooth_name VARCHAR(100),
    dentition_type VARCHAR(20) NOT NULL CHECK (dentition_type IN ('permanent','primary')),
    position_in_quadrant SMALLINT NOT NULL CHECK (position_in_quadrant BETWEEN 1 AND 8),
    quadrant SMALLINT NOT NULL CHECK (quadrant BETWEEN 1 AND 4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(dental_chart_id, tooth_number_fdi)
);

CREATE TABLE tooth_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tooth_id UUID NOT NULL REFERENCES teeth(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('exam','caries','restoration','extraction','root_canal','crown','implant','fracture','cleaning','other')),
    procedure_name VARCHAR(255),
    diagnosis TEXT,
    event_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active','archived')),
    surfaces JSONB DEFAULT '[]'::jsonb,
    provider_id UUID REFERENCES users(id),
    notes TEXT,
    attachments JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_teeth_chart ON teeth(dental_chart_id);
CREATE INDEX idx_teeth_fdi ON teeth(tooth_number_fdi);
CREATE INDEX idx_tooth_events_tooth ON tooth_events(tooth_id, event_date DESC);
CREATE INDEX idx_tooth_events_patient ON tooth_events(patient_id, event_date DESC);
CREATE INDEX idx_tooth_events_status ON tooth_events(status) WHERE status = 'active';