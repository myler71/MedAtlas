-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Roles
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    permissions JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Clinics
CREATE TABLE clinics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    phone VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'dentist',
    clinic_id UUID REFERENCES clinics(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Patients
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
    deleted_at TIMESTAMPTZ
);

-- Patient Access Control
CREATE TABLE patient_access (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_level VARCHAR(50) DEFAULT 'read',
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by UUID REFERENCES users(id),
    UNIQUE(patient_id, user_id)
);

-- Appointments
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id),
    user_id UUID NOT NULL REFERENCES users(id),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    scheduled_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    status VARCHAR(50) DEFAULT 'scheduled',
    type VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45)
);

-- Attachments
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id),
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(100),
    file_size INTEGER,
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_clinic ON users(clinic_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_patients_clinic ON patients(clinic_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_patients_name ON patients(last_name, first_name) WHERE deleted_at IS NULL;
CREATE INDEX idx_patient_access_patient ON patient_access(patient_id);
CREATE INDEX idx_patient_access_user ON patient_access(user_id);
CREATE INDEX idx_appointments_patient ON appointments(patient_id, scheduled_at);
CREATE INDEX idx_appointments_user ON appointments(user_id, scheduled_at);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, timestamp DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_attachments_entity ON attachments(entity_type, entity_id);

-- Insert default roles
INSERT INTO roles (name, permissions) VALUES
    ('dentist', '["patients.read","patients.write","dental.read","dental.write","drugs.read","chat.patient","appointments.read","appointments.write"]'::jsonb),
    ('orthopedist', '["patients.read","patients.write","ortho.read","ortho.write","drugs.read","chat.patient","appointments.read","appointments.write"]'::jsonb),
    ('admin', '["patients.read","patients.write","dental.read","dental.write","ortho.read","ortho.write","drugs.read","chat.patient","appointments.read","appointments.write","audit.read","users.read","users.write","admin.all"]'::jsonb);
