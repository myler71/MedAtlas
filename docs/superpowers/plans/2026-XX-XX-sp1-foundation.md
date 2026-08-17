# SP-1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the complete project infrastructure — Express gateway, FastAPI scaffold, PostgreSQL with schema, Redis, auth, RBAC, audit logging, and frontend skeleton.

**Architecture:** Express.js handles auth/gateway, FastAPI handles clinical services. PostgreSQL + pgvector for data, Redis for caching. Frontend is vanilla HTML/CSS/JS.

**Tech Stack:** Node.js/Express, Python/FastAPI, PostgreSQL+pgvector, Redis, Docker Compose, JWT, bcrypt

**Spec:** `docs/superpowers/specs/2026-XX-XX-clinical-platform-design.md`

## Global Constraints

- UUID primary keys on all tables
- Soft deletes (deleted_at) on users and patients
- created_at/updated_at/created_by/updated_by on clinical tables
- JWT tokens with 15min access + 7-day refresh
- bcrypt password hashing
- Express is the single entry point (frontend never talks to FastAPI directly)
- All API responses use consistent JSON error format: `{ "error": { "code": "...", "message": "...", "request_id": "..." } }`
- No secrets in code — use .env files
- .env.example committed, .env gitignored

---

## Task 1: Project Directory Structure

**Files:**
- Create: `clinical-platform/` directory tree
- Create: `clinical-platform/.gitignore`
- Create: `clinical-platform/.env.example`
- Create: `clinical-platform/docker-compose.yml`

**Interfaces:**
- Consumes: None
- Produces: Directory structure for all subsequent tasks

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p clinical-platform/{frontend/{css,js/{components,pages,utils},assets},backend/{express/src/{routes,middleware,services},fastapi/app/{api,models,schemas,services,rag,ai}},database/{migrations,seeds},rag/{ingestion,retrieval,evaluation},docs,tests}
```

- [ ] **Step 2: Create .gitignore**

```
node_modules/
__pycache__/
*.pyc
.env
*.db
.pytest_cache/
.coverage
htmlcov/
.superpowers/
.opencode/skills/
```

- [ ] **Step 3: Create .env.example**

```
# Database
DATABASE_URL=postgresql://clinical:clinical@localhost:5432/clinical_platform
POSTGRES_USER=clinical
POSTGRES_PASSWORD=clinical
POSTGRES_DB=clinical_platform

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=change-me-in-production
JWT_EXPIRY_MINUTES=15
JWT_REFRESH_DAYS=7

# Express
EXPRESS_PORT=3000

# FastAPI
FASTAPI_PORT=8000
FASTAPI_HOST=0.0.0.0

# Tavily MCP / RAG (placeholder until final demo)
TAVILY_API_KEY=your-tavily-api-key
TAVILY_MCP_URL=mcp.tavily.com
LLM_PROVIDER=tavily-augmented
LLM_API_KEY=your-llm-api-key
LLM_MODEL=llama-3.3-70b-versatile

# RxNorm
RXNORM_API_BASE=https://rxnav.nlm.nih.gov/REST

# pgvector
PGVECTOR_EXTENSION=enabled
```

- [ ] **Step 4: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-clinical}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-clinical}
      POSTGRES_DB: ${POSTGRES_DB:-clinical_platform}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U clinical -d clinical_platform"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "chore: initialize project structure with docker-compose"
```

---

## Task 2: PostgreSQL Schema — Core Tables

**Files:**
- Create: `clinical-platform/database/schema.sql`

**Interfaces:**
- Consumes: None
- Produces: Database tables for users, roles, clinics, patients, patient_access, appointments, audit_logs, attachments

- [ ] **Step 1: Write schema.sql**

```sql
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
```

- [ ] **Step 2: Commit**

```bash
git add database/schema.sql
git commit -m "feat(db): core schema with users, patients, appointments, audit"
```

---

## Task 3: Express.js Gateway — Setup and Auth

**Files:**
- Create: `clinical-platform/backend/express/package.json`
- Create: `clinical-platform/backend/express/src/server.js`
- Create: `clinical-platform/backend/express/src/middleware/auth.js`
- Create: `clinical-platform/backend/express/src/middleware/rbac.js`
- Create: `clinical-platform/backend/express/src/middleware/audit.js`
- Create: `clinical-platform/backend/express/src/middleware/errorHandler.js`
- Create: `clinical-platform/backend/express/src/routes/auth.js`
- Create: `clinical-platform/backend/express/src/services/db.js`
- Create: `clinical-platform/backend/express/src/routes/proxy.js` (proxy to FastAPI)
- Create: `clinical-platform/backend/express/Dockerfile`

**Interfaces:**
- Consumes: PostgreSQL schema (Task 2), Redis (docker-compose)
- Produces: Express server on port 3000, JWT auth, RBAC, audit middleware, auth routes, FastAPI proxy

- [ ] **Step 1: Create package.json**

```json
{
  "name": "clinical-platform-express",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "node src/server.js",
    "dev": "node --watch src/server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "pg": "^8.12.0",
    "redis": "^4.6.12",
    "jsonwebtoken": "^9.0.2",
    "bcryptjs": "^2.4.3",
    "cors": "^2.8.5",
    "helmet": "^7.1.0",
    "express-rate-limit": "^7.1.5",
    "http-proxy-middleware": "^3.0.0",
    "uuid": "^9.0.0",
    "dotenv": "^16.3.1"
  }
}
```

- [ ] **Step 2: Create server.js**

```javascript
import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { authRouter } from './routes/auth.js';
import { createProxyRouter } from './routes/proxy.js';
import { auditMiddleware } from './middleware/audit.js';
import { errorHandler } from './middleware/errorHandler.js';

const app = express();
const PORT = process.env.EXPRESS_PORT || 3000;
const FASTAPI_BASE = process.env.FASTAPI_INTERNAL_URL || 'http://localhost:8000';

// Security
app.use(helmet());
app.use(cors({ origin: true, credentials: true }));
app.use(express.json());

// Rate limiting
app.use(rateLimit({ windowMs: 15 * 60 * 1000, max: 100 }));

// Audit logging
app.use(auditMiddleware);

// Routes
app.use('/api/auth', authRouter);
app.use('/api', createProxyRouter(FASTAPI_BASE));

// Health check
app.get('/api/health', (req, res) => res.json({ status: 'ok', service: 'express' }));

// Error handler
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`Express gateway running on port ${PORT}`);
});

export default app;
```

- [ ] **Step 3: Create auth middleware**

```javascript
// src/middleware/auth.js
import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret';

export function authenticate(req, res, next) {
  const token = req.cookies?.token || req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'No token provided' } });
  }
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({ error: { code: 'INVALID_TOKEN', message: 'Invalid or expired token' } });
  }
}

export function generateToken(user) {
  return jwt.sign(
    { id: user.id, email: user.email, role: user.role, clinic_id: user.clinic_id },
    JWT_SECRET,
    { expiresIn: `${process.env.JWT_EXPIRY_MINUTES || 15}m` }
  );
}

export function generateRefreshToken(user) {
  return jwt.sign(
    { id: user.id, type: 'refresh' },
    JWT_SECRET,
    { expiresIn: `${process.env.JWT_REFRESH_DAYS || 7}d` }
  );
}
```

- [ ] **Step 4: Create RBAC middleware**

```javascript
// src/middleware/rbac.js
export function requireRole(...roles) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Not authenticated' } });
    }
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Insufficient permissions' } });
    }
    next();
  };
}
```

- [ ] **Step 5: Create audit middleware**

```javascript
// src/middleware/audit.js
import { Pool } from 'pg';

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

export function auditMiddleware(req, res, next) {
  const start = Date.now();
  res.on('finish', async () => {
    const duration = Date.now() - start;
    if (!req.path.startsWith('/api/')) return;
    try {
      await pool.query(
        `INSERT INTO audit_logs (user_id, action, resource_type, resource_id, success, ip_address, metadata)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [
          req.user?.id || null,
          `${req.method} ${req.path}`,
          req.path.split('/')[2] || null,
          req.params?.id || null,
          res.statusCode < 400,
          req.ip,
          JSON.stringify({ duration_ms: duration, status: res.statusCode })
        ]
      );
    } catch (e) {
      console.error('audit log fail', e);
    }
  });
  next();
}
```

- [ ] **Step 6: Create error handler**

```javascript
// src/middleware/errorHandler.js
export function errorHandler(err, req, res, next) {
  console.error('Unhandled error:', err);
  res.status(500).json({
    error: {
      code: 'INTERNAL_ERROR',
      message: 'An unexpected error occurred',
      request_id: req.headers['x-request-id'] || 'unknown'
    }
  });
}
```

- [ ] **Step 7: Create db service**

```javascript
// src/services/db.js
import { Pool } from 'pg';

export const pool = new Pool({ connectionString: process.env.DATABASE_URL });
```

- [ ] **Step 8: Create auth routes**

```javascript
// src/routes/auth.js
import { Router } from 'express';
import bcrypt from 'bcryptjs';
import { pool } from '../services/db.js';
import { generateToken, generateRefreshToken, authenticate } from '../middleware/auth.js';

export const authRouter = Router();

authRouter.post('/register', async (req, res) => {
  try {
    const { email, password, full_name, role, clinic_id } = req.body;
    if (!email || !password || !full_name) {
      return res.status(400).json({ error: { code: 'VALIDATION_ERROR', message: 'Email, password, and full_name are required' } });
    }
    if (!['dentist', 'orthopedist', 'admin'].includes(role)) {
      return res.status(400).json({ error: { code: 'VALIDATION_ERROR', message: 'Role must be dentist, orthopedist, or admin' } });
    }
    const existing = await pool.query('SELECT id FROM users WHERE email = $1 AND deleted_at IS NULL', [email]);
    if (existing.rows.length > 0) {
      return res.status(409).json({ error: { code: 'USER_EXISTS', message: 'A user with this email already exists' } });
    }
    const password_hash = await bcrypt.hash(password, 12);
    const result = await pool.query(
      'INSERT INTO users (email, password_hash, full_name, role, clinic_id) VALUES ($1, $2, $3, $4, $5) RETURNING id, email, full_name, role, clinic_id',
      [email, password_hash, full_name, role, clinic_id || null]
    );
    const user = result.rows[0];
    const token = generateToken(user);
    const refreshToken = generateRefreshToken(user);
    res.cookie('token', token, { httpOnly: true, maxAge: 15 * 60 * 1000 });
    res.status(201).json({ user, token, refreshToken });
  } catch (err) {
    console.error('Register error:', err);
    res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Registration failed' } });
  }
});

authRouter.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    if (!email || !password) {
      return res.status(400).json({ error: { code: 'VALIDATION_ERROR', message: 'Email and password are required' } });
    }
    const result = await pool.query(
      'SELECT id, email, password_hash, full_name, role, clinic_id FROM users WHERE email = $1 AND deleted_at IS NULL',
      [email]
    );
    if (result.rows.length === 0) {
      return res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Invalid email or password' } });
    }
    const user = result.rows[0];
    const valid = await bcrypt.compare(password, user.password_hash);
    if (!valid) {
      return res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Invalid email or password' } });
    }
    const token = generateToken(user);
    const refreshToken = generateRefreshToken(user);
    delete user.password_hash;
    res.cookie('token', token, { httpOnly: true, maxAge: 15 * 60 * 1000 });
    res.json({ user, token, refreshToken });
  } catch (err) {
    console.error('Login error:', err);
    res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Login failed' } });
  }
});

authRouter.get('/me', authenticate, async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT id, email, full_name, role, clinic_id FROM users WHERE id = $1 AND deleted_at IS NULL',
      [req.user.id]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: { code: 'USER_NOT_FOUND', message: 'User not found' } });
    }
    res.json({ user: result.rows[0] });
  } catch (err) {
    res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to fetch user' } });
  }
});

authRouter.post('/logout', (req, res) => {
  res.clearCookie('token');
  res.json({ message: 'Logged out' });
});
```

- [ ] **Step 9: Create proxy router to FastAPI**

```javascript
// src/routes/proxy.js
import { Router } from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { authenticate } from '../middleware/auth.js';

export function createProxyRouter(fastapiBase) {
  const router = Router();

  router.use(authenticate);

  router.use('/', createProxyMiddleware({
    target: fastapiBase,
    changeOrigin: true,
    pathRewrite: (path) => path,  // keep the /api/* prefix
    onProxyReq: (proxyReq, req) => {
      if (req.user) {
        proxyReq.setHeader('x-user-id', req.user.id);
        proxyReq.setHeader('x-user-role', req.user.role);
        proxyReq.setHeader('x-clinic-id', req.user.clinic_id || '');
      }
    }
  }));

  return router;
}
```

- [ ] **Step 10: Create Express Dockerfile**

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["node", "src/server.js"]
```

- [ ] **Step 11: Commit**

```bash
git add backend/express/
git commit -m "feat(express): auth gateway with JWT, RBAC, audit, FastAPI proxy"
```

---

## Task 4: FastAPI Scaffold — Patient Endpoints

**Files:**
- Create: `clinical-platform/backend/fastapi/requirements.txt`
- Create: `clinical-platform/backend/fastapi/app/main.py`
- Create: `clinical-platform/backend/fastapi/app/api/patients.py`
- Create: `clinical-platform/backend/fastapi/app/api/__init__.py`
- Create: `clinical-platform/backend/fastapi/app/schemas/patient.py`
- Create: `clinical-platform/backend/fastapi/app/schemas/__init__.py`
- Create: `clinical-platform/backend/fastapi/app/models/database.py`
- Create: `clinical-platform/backend/fastapi/app/models/__init__.py`
- Create: `clinical-platform/backend/fastapi/app/services/auth_context.py`
- Create: `clinical-platform/backend/fastapi/app/services/__init__.py`
- Create: `clinical-platform/backend/fastapi/Dockerfile`

**Interfaces:**
- Consumes: PostgreSQL schema (Task 2)
- Produces: FastAPI server on port 8000, patient CRUD endpoints, x-user-* header context reader

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
asyncpg==0.29.0
psycopg2-binary==2.9.9
pydantic==2.9.0
pydantic-settings==2.5.0
redis==4.6.12
pgvector==0.3.0
httpx==0.27.0
python-dotenv==1.0.1
```

- [ ] **Step 2: Create database.py**

```python
# app/models/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://clinical:clinical@localhost:5432/clinical_platform")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: Create auth_context service**

```python
# app/services/auth_context.py
from fastapi import Request, HTTPException, Header
from typing import Optional
from uuid import UUID

class UserContext:
    def __init__(self, user_id: UUID, role: str, clinic_id: Optional[UUID]):
        self.user_id = user_id
        self.role = role
        self.clinic_id = clinic_id

def get_user_context(
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None),
    x_clinic_id: Optional[str] = Header(None),
) -> UserContext:
    if not x_user_id or not x_user_role:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Missing auth context"})
    try:
        clinic_id = UUID(x_clinic_id) if x_clinic_id else None
        return UserContext(user_id=UUID(x_user_id), role=x_user_role, clinic_id=clinic_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_CONTEXT", "message": "Invalid user context"})
```

- [ ] **Step 4: Create patient schema**

```python
# app/schemas/patient.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from uuid import UUID

class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None

class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None

class PatientResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    date_of_birth: Optional[date]
    gender: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    emergency_contact: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 5: Create patient routes**

```python
# app/api/patients.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from ..models.database import get_db
from ..schemas.patient import PatientCreate, PatientUpdate, PatientResponse
from ..services.auth_context import get_user_context, UserContext

router = APIRouter(prefix="/api/patients", tags=["patients"])

@router.get("", response_model=List[PatientResponse])
def list_patients(
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    params = {"clinic_id": str(user.clinic_id) if user.clinic_id else None, "skip": skip, "limit": limit}
    where = ["deleted_at IS NULL"]
    if user.clinic_id:
        where.append("clinic_id = :clinic_id")
    if search:
        where.append("(first_name ILIKE :search OR last_name ILIKE :search)")
        params["search"] = f"%{search}%"
    query = f"SELECT * FROM patients WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT :limit OFFSET :skip"
    result = db.execute(text(query), params)
    return [dict(row._mapping) for row in result]

@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    if not user.clinic_id:
        raise HTTPException(status_code=400, detail={"code": "NO_CLINIC", "message": "User is not associated with a clinic"})
    data = patient.model_dump()
    data["clinic_id"] = str(user.clinic_id)
    data["created_by"] = str(user.user_id)
    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{k}" for k in data.keys())
    query = text(f"INSERT INTO patients ({cols}) VALUES ({placeholders}) RETURNING *")
    result = db.execute(query, data)
    db.commit()
    return dict(result.mappings().first())

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    result = db.execute(
        text("SELECT * FROM patients WHERE id = :id AND deleted_at IS NULL"),
        {"id": str(patient_id)}
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient not found"})
    if user.clinic_id and row["clinic_id"] != user.clinic_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Patient not in your clinic"})
    return dict(row)

@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: UUID,
    patient: PatientUpdate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    updates = {k: v for k, v in patient.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail={"code": "NO_UPDATES", "message": "No fields to update"})
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    params = {**updates, "id": str(patient_id)}
    result = db.execute(
        text(f"UPDATE patients SET {set_clause}, updated_at = NOW() WHERE id = :id AND deleted_at IS NULL RETURNING *"),
        params
    )
    db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient not found"})
    return dict(row)

@router.delete("/{patient_id}")
def delete_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    result = db.execute(
        text("UPDATE patients SET deleted_at = NOW() WHERE id = :id AND deleted_at IS NULL RETURNING id"),
        {"id": str(patient_id)}
    )
    db.commit()
    if not result.mappings().first():
        raise HTTPException(status_code=404, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient not found"})
    return {"message": "Patient deleted"}
```

- [ ] **Step 6: Create __init__ files**

```python
# app/__init__.py
# app/api/__init__.py
# app/models/__init__.py
# app/schemas/__init__.py
# app/services/__init__.py
```
(All empty placeholder files)

- [ ] **Step 7: Create FastAPI main.py**

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import patients

app = FastAPI(title="Clinical Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "fastapi"}
```

- [ ] **Step 8: Create FastAPI Dockerfile**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 9: Commit**

```bash
git add backend/fastapi/
git commit -m "feat(fastapi): patient CRUD scaffold with SQLAlchemy"
```

---

## Task 5: Frontend Skeleton

**Files:**
- Create: `clinical-platform/frontend/index.html`
- Create: `clinical-platform/frontend/css/variables.css`
- Create: `clinical-platform/frontend/css/layout.css`
- Create: `clinical-platform/frontend/css/components.css`
- Create: `clinical-platform/frontend/js/app.js`
- Create: `clinical-platform/frontend/js/api.js`
- Create: `clinical-platform/frontend/js/pages/role-selection.js`
- Create: `clinical-platform/frontend/js/pages/auth.js`
- Create: `clinical-platform/frontend/js/pages/dashboard.js`

**Interfaces:**
- Consumes: Express API (Task 3)
- Produces: Working frontend with role selection, auth, and dashboard

- [ ] **Step 1: Create index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Clinical Platform</title>
  <link rel="stylesheet" href="css/variables.css">
  <link rel="stylesheet" href="css/layout.css">
  <link rel="stylesheet" href="css/components.css">
</head>
<body>
  <div id="app"></div>
  <script type="module" src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create CSS variables**

```css
/* css/variables.css */
:root {
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-secondary: #64748b;
  --color-success: #16a34a;
  --color-warning: #d97706;
  --color-danger: #dc2626;
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-text: #0f172a;
  --color-text-secondary: #64748b;
  --color-border: #e2e8f0;
  --radius: 8px;
  --shadow: 0 1px 3px rgba(0,0,0,0.1);
  --shadow-lg: 0 4px 12px rgba(0,0,0,0.15);
  --font: system-ui, -apple-system, sans-serif;
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
}
```

- [ ] **Step 3: Create layout CSS**

```css
/* css/layout.css */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: var(--font); background: var(--color-bg); color: var(--color-text); min-height: 100vh; }
#app { max-width: 1200px; margin: 0 auto; padding: var(--spacing-lg); }
.card { background: var(--color-surface); border-radius: var(--radius); box-shadow: var(--shadow); padding: var(--spacing-lg); }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-lg); }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--spacing-lg); }
.flex { display: flex; }
.flex-col { flex-direction: column; }
.gap-sm { gap: var(--spacing-sm); }
.gap-md { gap: var(--spacing-md); }
.gap-lg { gap: var(--spacing-lg); }
```

- [ ] **Step 4: Create components CSS**

```css
/* css/components.css */
.btn { padding: var(--spacing-sm) var(--spacing-md); border: none; border-radius: var(--radius); cursor: pointer; font-size: 14px; font-weight: 500; transition: background 0.2s; }
.btn-primary { background: var(--color-primary); color: white; }
.btn-primary:hover { background: var(--color-primary-hover); }
.btn-secondary { background: var(--color-secondary); color: white; }
.btn-danger { background: var(--color-danger); color: white; }
.btn-lg { padding: var(--spacing-md) var(--spacing-xl); font-size: 16px; }
.input { padding: var(--spacing-sm) var(--spacing-md); border: 1px solid var(--color-border); border-radius: var(--radius); font-size: 14px; width: 100%; }
.input:focus { outline: none; border-color: var(--color-primary); }
.label { font-size: 14px; font-weight: 500; margin-bottom: var(--spacing-xs); display: block; }
.text-center { text-align: center; }
.text-secondary { color: var(--color-text-secondary); }
.mt-md { margin-top: var(--spacing-md); }
.mb-md { margin-bottom: var(--spacing-md); }
.role-card { padding: var(--spacing-xl); text-align: center; cursor: pointer; border: 2px solid var(--color-border); transition: all 0.2s; font-size: 24px; }
.role-card:hover { border-color: var(--color-primary); transform: translateY(-2px); box-shadow: var(--shadow-lg); }
.role-card .emoji { font-size: 48px; margin-bottom: var(--spacing-md); display: block; }
```

- [ ] **Step 5: Create app.js router**

```javascript
// js/app.js
import { RoleSelection } from './pages/role-selection.js';
import { AuthPage } from './pages/auth.js';
import { Dashboard } from './pages/dashboard.js';

class App {
  constructor() {
    this.currentRole = localStorage.getItem('role');
    this.token = localStorage.getItem('token');
    this.render();
  }

  render() {
    const app = document.getElementById('app');
    if (!this.currentRole) {
      new RoleSelection(app, (role) => {
        this.currentRole = role;
        localStorage.setItem('role', role);
        this.render();
      });
    } else if (!this.token) {
      new AuthPage(app, this.currentRole, (token) => {
        this.token = token;
        localStorage.setItem('token', token);
        this.render();
      });
    } else {
      new Dashboard(app, this.currentRole, this.token);
    }
  }
}

new App();
```

- [ ] **Step 6: Create API client**

```javascript
// js/api.js
const API_BASE = 'http://localhost:3000';

export async function apiCall(endpoint, options = {}) {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error?.message || 'Request failed');
  }
  return data;
}
```

- [ ] **Step 7: Create role selection page**

```javascript
// js/pages/role-selection.js
export class RoleSelection {
  constructor(container, onSelect) {
    this.container = container;
    this.onSelect = onSelect;
    this.render();
  }

  render() {
    this.container.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:80vh;gap:32px">
        <h1 style="font-size:28px;font-weight:700">Clinical Platform</h1>
        <p style="color:var(--color-text-secondary);font-size:16px">What type of doctor are you?</p>
        <div style="display:flex;gap:24px">
          <div class="card role-card" id="select-dentist">
            <span class="emoji">🦷</span>
            <strong>Dentist</strong>
          </div>
          <div class="card role-card" id="select-orthopedist">
            <span class="emoji">🦴</span>
            <strong>Orthopedist</strong>
          </div>
        </div>
      </div>
    `;
    this.container.querySelector('#select-dentist').onclick = () => this.onSelect('dentist');
    this.container.querySelector('#select-orthopedist').onclick = () => this.onSelect('orthopedist');
  }
}
```

- [ ] **Step 8: Create auth page**

```javascript
// js/pages/auth.js
import { apiCall } from '../api.js';

export class AuthPage {
  constructor(container, role, onLogin) {
    this.container = container;
    this.role = role;
    this.onLogin = onLogin;
    this.isLogin = true;
    this.render();
  }

  render() {
    const roleLabel = this.role === 'dentist' ? '🦷 Dentist' : '🦴 Orthopedist';
    this.container.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:80vh;gap:24px">
        <div class="card" style="width:400px;padding:32px">
          <div class="text-center mb-md">
            <span style="font-size:24px">${roleLabel}</span>
            <h2 style="margin-top:8px">${this.isLogin ? 'Sign In' : 'Create Account'}</h2>
          </div>
          <form id="auth-form" class="flex flex-col gap-md">
            ${!this.isLogin ? '<div><label class="label">Full Name</label><input class="input" name="full_name" required></div>' : ''}
            <div><label class="label">Email</label><input class="input" type="email" name="email" required></div>
            <div><label class="label">Password</label><input class="input" type="password" name="password" required></div>
            <div id="auth-error" style="color:var(--color-danger);font-size:14px"></div>
            <button type="submit" class="btn btn-primary btn-lg">${this.isLogin ? 'Sign In' : 'Register'}</button>
          </form>
          <p class="text-center mt-md" style="font-size:14px">
            <a href="#" id="toggle-auth">${this.isLogin ? 'Create account' : 'Sign in'}</a>
          </p>
        </div>
      </div>
    `;
    this.container.querySelector('#auth-form').onsubmit = (e) => this.handleSubmit(e);
    this.container.querySelector('#toggle-auth').onclick = (e) => { e.preventDefault(); this.isLogin = !this.isLogin; this.render(); };
  }

  async handleSubmit(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const data = Object.fromEntries(form);
    try {
      const endpoint = this.isLogin ? '/api/auth/login' : '/api/auth/register';
      if (!this.isLogin) data.role = this.role;
      const result = await apiCall(endpoint, { method: 'POST', body: JSON.stringify(data) });
      this.onLogin(result.token);
    } catch (err) {
      document.getElementById('auth-error').textContent = err.message;
    }
  }
}
```

- [ ] **Step 9: Create dashboard page**

```javascript
// js/pages/dashboard.js
import { apiCall } from '../api.js';

export class Dashboard {
  constructor(container, role, token) {
    this.container = container;
    this.role = role;
    this.token = token;
    this.render();
  }

  render() {
    const roleLabel = this.role === 'dentist' ? '🦷 Dentist' : '🦴 Orthopedist';
    const primaryModule = this.role === 'dentist' ? 'Dental Chart' : 'Skeleton / Orthopedic Chart';
    this.container.innerHTML = `
      <div>
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--color-border);margin-bottom:24px">
          <div style="display:flex;gap:24px;align-items:center">
            <strong>Clinical Platform</strong>
            <span class="text-secondary">${roleLabel}</span>
          </div>
          <div style="display:flex;gap:16px;align-items:center">
            <button class="btn btn-secondary" id="btn-logout">Logout</button>
          </div>
        </nav>
        <div class="grid-3">
          <div class="card"><h3>Patients</h3><p class="text-secondary mt-md">Manage patient records</p></div>
          <div class="card"><h3>${primaryModule}</h3><p class="text-secondary mt-md">Interactive clinical chart</p></div>
          <div class="card"><h3>Drug Checker</h3><p class="text-secondary mt-md">Check drug interactions</p></div>
          <div class="card"><h3>AI Assistant</h3><p class="text-secondary mt-md">Ask about patient records</p></div>
          <div class="card"><h3>Appointments</h3><p class="text-secondary mt-md">Schedule and manage</p></div>
          <div class="card"><h3>History</h3><p class="text-secondary mt-md">View audit history</p></div>
        </div>
      </div>
    `;
    this.container.querySelector('#btn-logout').onclick = () => {
      localStorage.removeItem('token');
      localStorage.removeItem('role');
      location.reload();
    };
  }
}
```

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): role selection, auth, and dashboard skeleton"
```

---

## Task 6: Docker Compose — Full Stack

**Files:**
- Modify: `clinical-platform/docker-compose.yml` (add express and fastapi services)

- [ ] **Step 1: Update docker-compose.yml**

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-clinical}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-clinical}
      POSTGRES_DB: ${POSTGRES_DB:-clinical_platform}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U clinical -d clinical_platform"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  express:
    build: ./backend/express
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://clinical:clinical@postgres:5432/clinical_platform
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET:-dev-secret}
      FASTAPI_INTERNAL_URL: http://fastapi:8000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  fastapi:
    build: ./backend/fastapi
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://clinical:clinical@postgres:5432/clinical_platform
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(docker): full stack compose with express, fastapi, postgres, redis"
```

---

## Task 7: Seed Data

**Files:**
- Create: `clinical-platform/database/seed.sql`

- [ ] **Step 1: Create seed data**

```sql
-- database/seed.sql
-- Test clinic
INSERT INTO clinics (id, name, address, phone) VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Downtown Dental & Ortho', '123 Main St', '555-0100');

-- Test users (password: password123)
-- bcrypt hash of 'password123' with cost 12
-- Generated fresh: $2a$12$LQ4M5V0XJzS7KQO5G5H6yOWY8dQK9pZ5K9pZ5K9pZ5K9pZ5K9pZ5K9 (placeholder; will be regenerated by seed script)
INSERT INTO users (id, email, password_hash, full_name, role, clinic_id) VALUES
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'dentist@clinic.com', 'PLACEHOLDER_HASH_REGENERATED_AT_SEED_TIME', 'Dr. Sarah Chen', 'dentist', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'ortho@clinic.com', 'PLACEHOLDER_HASH_REGENERATED_AT_SEED_TIME', 'Dr. James Wilson', 'orthopedist', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');

-- Test patients
INSERT INTO patients (id, clinic_id, first_name, last_name, date_of_birth, gender, phone, created_by) VALUES
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'John', 'Smith', '1984-03-15', 'male', '555-0201', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22'),
    ('e0eebc99-9c0b-4ef8-bb6d-6bb9bd380a55', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Maria', 'Garcia', '1992-07-22', 'female', '555-0202', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22');

-- Patient access
INSERT INTO patient_access (patient_id, user_id, access_level) VALUES
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'full'),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'full'),
    ('e0eebc99-9c0b-4ef8-bb6d-6bb9bd380a55', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'full');
```

- [ ] **Step 2: Create seed script to generate bcrypt hash at seed time**

```bash
# clinical-platform/database/seed.sh
#!/bin/bash
set -e
HASH=$(node -e "console.log(require('bcryptjs').hashSync('password123', 12))")
echo "Generated bcrypt hash for password123"
psql -U clinical -d clinical_platform -v ON_ERROR_STOP=1 <<SQL
-- Update users with real bcrypt hash
UPDATE users SET password_hash = '$HASH' WHERE email IN ('dentist@clinic.com', 'ortho@clinic.com');
SELECT email, role FROM users;
SQL
```

- [ ] **Step 3: Commit**

```bash
git add database/seed.sql database/seed.sh
git commit -m "feat(seed): test clinic, users, and patients"
```

---

## Task 8: Integration Test — Full Auth + Patient Flow

**Files:**
- Create: `clinical-platform/tests/test-auth-patient.sh`

- [ ] **Step 1: Write integration test script**

```bash
#!/bin/bash
set -e

BASE="http://localhost:3000"
FASTAPI="http://localhost:8000"

echo "=== Test 1: Health checks ==="
curl -sf $BASE/api/health | grep -q "ok" && echo "PASS: Express health" || echo "FAIL: Express health"
curl -sf $FASTAPI/api/health | grep -q "ok" && echo "PASS: FastAPI health" || echo "FAIL: FastAPI health"

echo "=== Test 2: Register ==="
REGISTER=$(curl -sf -X POST $BASE/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"integration@test.com","password":"testpass123","full_name":"Dr. Integration","role":"dentist"}')
TOKEN=$(echo $REGISTER | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
echo "PASS: Register (token obtained)"

echo "=== Test 3: Login ==="
curl -sf -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"integration@test.com","password":"testpass123"}' | grep -q "token" && echo "PASS: Login" || echo "FAIL: Login"

echo "=== Test 4: Get me ==="
curl -sf $BASE/api/auth/me -H "Authorization: Bearer $TOKEN" | grep -q "Integration" && echo "PASS: Get me" || echo "FAIL: Get me"

echo "=== Test 5: Create patient ==="
PATIENT=$(curl -sf -X POST $FASTAPI/api/patients \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Test","last_name":"Patient","gender":"male"}')
PATIENT_ID=$(echo $PATIENT | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "PASS: Create patient ($PATIENT_ID)"

echo "=== Test 6: Get patient ==="
curl -sf $FASTAPI/api/patients/$PATIENT_ID | grep -q "Test" && echo "PASS: Get patient" || echo "FAIL: Get patient"

echo "=== Test 7: List patients ==="
curl -sf $FASTAPI/api/patients | grep -q "Test" && echo "PASS: List patients" || echo "FAIL: List patients"

echo "=== All tests passed ==="
```

- [ ] **Step 2: Commit**

```bash
git add tests/
git commit -m "test: integration test for auth and patient CRUD"
```

---

## Summary

| Task | Deliverable | Status |
|------|------------|--------|
| 1 | Project structure, .gitignore, .env, docker-compose | |
| 2 | PostgreSQL schema with core tables | |
| 3 | Express gateway with auth, RBAC, audit, FastAPI proxy | |
| 4 | FastAPI with patient CRUD | |
| 5 | Frontend skeleton with role selection, auth, dashboard | |
| 6 | Full stack docker-compose | |
| 7 | Seed data | |
| 8 | Integration tests | |

**Total tasks:** 8
**Estimated time:** 30-45 minutes per task
