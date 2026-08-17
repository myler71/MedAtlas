-- 003_orthopedic.sql
CREATE TABLE orthopedic_charts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL UNIQUE REFERENCES patients(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE body_regions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    orthopedic_chart_id UUID NOT NULL REFERENCES orthopedic_charts(id) ON DELETE CASCADE,
    region_name VARCHAR(100) NOT NULL,
    region_code VARCHAR(50) NOT NULL,
    side VARCHAR(10) CHECK (side IN ('left','right','midline','bilateral')),
    svg_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(orthopedic_chart_id, region_code, side)
);

CREATE TABLE bones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    body_region_id UUID NOT NULL REFERENCES body_regions(id) ON DELETE CASCADE,
    bone_name VARCHAR(100) NOT NULL,
    bone_code VARCHAR(50) NOT NULL,
    side VARCHAR(10) CHECK (side IN ('left','right','midline')),
    svg_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(body_region_id, bone_code)
);

CREATE TABLE bone_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bone_id UUID NOT NULL REFERENCES bones(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('exam','fracture','sprain','dislocation','surgery','implant','arthritis','healing','follow_up','other')),
    diagnosis TEXT,
    event_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active','archived')),
    treatment TEXT,
    healing_status VARCHAR(50) CHECK (healing_status IN ('acute','recovering','healed','chronic','unknown')),
    side VARCHAR(10) CHECK (side IN ('left','right','midline')),
    notes TEXT,
    attachments JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_body_regions_chart ON body_regions(orthopedic_chart_id);
CREATE INDEX idx_bones_region ON bones(body_region_id);
CREATE INDEX idx_bone_events_bone ON bone_events(bone_id, event_date DESC);
CREATE INDEX idx_bone_events_patient ON bone_events(patient_id, event_date DESC);
CREATE INDEX idx_bone_events_status ON bone_events(status) WHERE status = 'active';
