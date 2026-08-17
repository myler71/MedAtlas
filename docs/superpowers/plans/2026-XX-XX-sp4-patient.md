# SP-4: Patient Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the patient enrichment data — medical history, allergies, medications, appointments — and the patient overview UI that aggregates all clinical data per patient.

**Architecture:** SQL migrations + FastAPI CRUD endpoints + frontend overview page that pulls dental, skeleton, medications, allergies, history, and appointments into one patient summary view.

**Tech Stack:** Python/SQLAlchemy, Pydantic, FastAPI, vanilla JS

**Spec:** `docs/superpowers/specs/2026-XX-XX-clinical-platform-design.md` (especially §6.4, §7.2)

**Depends on:** SP-1 (schema, auth). Can run in parallel with SP-2/SP-3 since SP-2/SP-3 modules only need dental/skeleton tables.

## Global Constraints

- All clinical entities enforce patient isolation via `patient_id` filter
- Soft delete via `status` field for medications (active/discontinued)
- Appointments enforce user_id + clinic_id from auth context
- Overview endpoint aggregates multiple sources but never exposes other patients' data

---

## Task 1: Database Migration — Patient Enrichment Tables

**Files:**
- Create: `clinical-platform/database/migrations/004_patient_enrichment.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- 004_patient_enrichment.sql
CREATE TABLE medical_histories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    condition_name VARCHAR(255) NOT NULL,
    diagnosed_date DATE,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active','resolved','chronic','in_remission')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE allergies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    allergen VARCHAR(255) NOT NULL,
    severity VARCHAR(50) DEFAULT 'mild' CHECK (severity IN ('mild','moderate','severe','life_threatening')),
    reaction TEXT,
    noted_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

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
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active','discontinued','completed','on_hold')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_medical_histories_patient ON medical_histories(patient_id);
CREATE INDEX idx_allergies_patient ON allergies(patient_id);
CREATE INDEX idx_medications_patient ON medications(patient_id);
CREATE INDEX idx_medications_status ON medications(patient_id) WHERE status = 'active';
```

- [ ] **Step 2: Apply migration**

```bash
docker compose exec -T postgres psql -U clinical -d clinical_platform < database/migrations/004_patient_enrichment.sql
```

- [ ] **Step 3: Commit**

```bash
git add database/migrations/
git commit -m "feat(db): medical history, allergies, medications tables"
```

---

## Task 2: Patient Enrichment API — Medical History, Allergies, Medications

**Files:**
- Create: `clinical-platform/backend/fastapi/app/api/patient_history.py`
- Modify: `clinical-platform/backend/fastapi/app/main.py` (include the router)

- [ ] **Step 1: Write patient_history.py**

```python
# app/api/patient_history.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from datetime import date
from pydantic import BaseModel
from ..models.database import get_db
from ..services.auth_context import get_user_context, UserContext

router = APIRouter(prefix="/api/patients/{patient_id}", tags=["patient-history"])


# ---------- Medical History ----------

class MedicalHistoryCreate(BaseModel):
    condition_name: str
    diagnosed_date: Optional[date] = None
    status: Optional[str] = "active"
    notes: Optional[str] = None


class MedicalHistoryOut(BaseModel):
    id: UUID
    condition_name: str
    diagnosed_date: Optional[date]
    status: str
    notes: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.get("/medical-history", response_model=List[MedicalHistoryOut])
def list_medical_history(patient_id: UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    rows = db.execute(
        text("SELECT id, condition_name, diagnosed_date, status, notes, created_at FROM medical_histories WHERE patient_id = :pid ORDER BY created_at DESC"),
        {"pid": str(patient_id)},
    ).mappings().all()
    return [
        MedicalHistoryOut(
            id=r["id"], condition_name=r["condition_name"], diagnosed_date=r["diagnosed_date"],
            status=r["status"], notes=r["notes"], created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.post("/medical-history", response_model=MedicalHistoryOut, status_code=status.HTTP_201_CREATED)
def create_medical_history(patient_id: UUID, item: MedicalHistoryCreate, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    row = db.execute(
        text("""INSERT INTO medical_histories (patient_id, condition_name, diagnosed_date, status, notes)
                VALUES (:pid, :cn, :dd, :st, :nt) RETURNING id, condition_name, diagnosed_date, status, notes, created_at"""),
        {"pid": str(patient_id), "cn": item.condition_name, "dd": item.diagnosed_date, "st": item.status, "nt": item.notes},
    ).mappings().first()
    db.commit()
    return MedicalHistoryOut(
        id=row["id"], condition_name=row["condition_name"], diagnosed_date=row["diagnosed_date"],
        status=row["status"], notes=row["notes"], created_at=row["created_at"].isoformat(),
    )


@router.delete("/medical-history/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_medical_history(patient_id: UUID, item_id: UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    db.execute(text("DELETE FROM medical_histories WHERE id = :id AND patient_id = :pid"), {"id": str(item_id), "pid": str(patient_id)})
    db.commit()
    return None


# ---------- Allergies ----------

class AllergyCreate(BaseModel):
    allergen: str
    severity: Optional[str] = "mild"
    reaction: Optional[str] = None
    noted_date: Optional[date] = None


class AllergyOut(BaseModel):
    id: UUID
    allergen: str
    severity: str
    reaction: Optional[str]
    noted_date: Optional[date]
    created_at: str

    class Config:
        from_attributes = True


@router.get("/allergies", response_model=List[AllergyOut])
def list_allergies(patient_id: UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    rows = db.execute(
        text("SELECT id, allergen, severity, reaction, noted_date, created_at FROM allergies WHERE patient_id = :pid ORDER BY severity DESC"),
        {"pid": str(patient_id)},
    ).mappings().all()
    return [
        AllergyOut(
            id=r["id"], allergen=r["allergen"], severity=r["severity"], reaction=r["reaction"],
            noted_date=r["noted_date"], created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.post("/allergies", response_model=AllergyOut, status_code=status.HTTP_201_CREATED)
def create_allergy(patient_id: UUID, item: AllergyCreate, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    row = db.execute(
        text("""INSERT INTO allergies (patient_id, allergen, severity, reaction, noted_date)
                VALUES (:pid, :al, :sv, :rx, :nd) RETURNING id, allergen, severity, reaction, noted_date, created_at"""),
        {"pid": str(patient_id), "al": item.allergen, "sv": item.severity, "rx": item.reaction, "nd": item.noted_date or date.today()},
    ).mappings().first()
    db.commit()
    return AllergyOut(
        id=row["id"], allergen=row["allergen"], severity=row["severity"], reaction=row["reaction"],
        noted_date=row["noted_date"], created_at=row["created_at"].isoformat(),
    )


@router.delete("/allergies/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allergy(patient_id: UUID, item_id: UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    db.execute(text("DELETE FROM allergies WHERE id = :id AND patient_id = :pid"), {"id": str(item_id), "pid": str(patient_id)})
    db.commit()
    return None


# ---------- Medications ----------

class MedicationCreate(BaseModel):
    drug_name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    prescriber: Optional[str] = None
    status: Optional[str] = "active"


class MedicationOut(BaseModel):
    id: UUID
    drug_name: str
    dosage: Optional[str]
    frequency: Optional[str]
    route: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    prescriber: Optional[str]
    status: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("/medications", response_model=List[MedicationOut])
def list_medications(patient_id: UUID, status: Optional[str] = None, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    where = ["patient_id = :pid"]
    params = {"pid": str(patient_id)}
    if status:
        where.append("status = :st")
        params["st"] = status
    rows = db.execute(
        text(f"SELECT id, drug_name, dosage, frequency, route, start_date, end_date, prescriber, status, created_at FROM medications WHERE {' AND '.join(where)} ORDER BY start_date DESC"),
        params,
    ).mappings().all()
    return [
        MedicationOut(
            id=r["id"], drug_name=r["drug_name"], dosage=r["dosage"], frequency=r["frequency"], route=r["route"],
            start_date=r["start_date"], end_date=r["end_date"], prescriber=r["prescriber"], status=r["status"],
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.post("/medications", response_model=MedicationOut, status_code=status.HTTP_201_CREATED)
def create_medication(patient_id: UUID, item: MedicationCreate, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    row = db.execute(
        text("""INSERT INTO medications (patient_id, drug_name, dosage, frequency, route, start_date, end_date, prescriber, status)
                VALUES (:pid, :dn, :do, :fr, :rt, :sd, :ed, :pr, :st)
                RETURNING id, drug_name, dosage, frequency, route, start_date, end_date, prescriber, status, created_at"""),
        {
            "pid": str(patient_id), "dn": item.drug_name, "do": item.dosage, "fr": item.frequency, "rt": item.route,
            "sd": item.start_date or date.today(), "ed": item.end_date, "pr": item.prescriber, "st": item.status,
        },
    ).mappings().first()
    db.commit()
    return MedicationOut(
        id=row["id"], drug_name=row["drug_name"], dosage=row["dosage"], frequency=row["frequency"], route=row["route"],
        start_date=row["start_date"], end_date=row["end_date"], prescriber=row["prescriber"], status=row["status"],
        created_at=row["created_at"].isoformat(),
    )


@router.put("/medications/{item_id}", response_model=MedicationOut)
def update_medication(patient_id: UUID, item_id: UUID, item: MedicationCreate, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    row = db.execute(
        text("""UPDATE medications SET drug_name=:dn, dosage=:do, frequency=:fr, route=:rt,
                                          start_date=COALESCE(:sd, start_date), end_date=:ed,
                                          prescriber=:pr, status=COALESCE(:st, status), updated_at=NOW()
                WHERE id=:id AND patient_id=:pid
                RETURNING id, drug_name, dosage, frequency, route, start_date, end_date, prescriber, status, created_at"""),
        {
            "id": str(item_id), "pid": str(patient_id), "dn": item.drug_name, "do": item.dosage, "fr": item.frequency, "rt": item.route,
            "sd": item.start_date, "ed": item.end_date, "pr": item.prescriber, "st": item.status,
        },
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "MEDICATION_NOT_FOUND", "message": "Medication not found"})
    return MedicationOut(
        id=row["id"], drug_name=row["drug_name"], dosage=row["dosage"], frequency=row["frequency"], route=row["route"],
        start_date=row["start_date"], end_date=row["end_date"], prescriber=row["prescriber"], status=row["status"],
        created_at=row["created_at"].isoformat(),
    )


@router.delete("/medications/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_medication(patient_id: UUID, item_id: UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    db.execute(text("DELETE FROM medications WHERE id = :id AND patient_id = :pid"), {"id": str(item_id), "pid": str(patient_id)})
    db.commit()
    return None
```

- [ ] **Step 2: Modify main.py**

Append inside `app/main.py`:

```python
from .api import patient_history
app.include_router(patient_history.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/fastapi/app/api/patient_history.py backend/fastapi/app/main.py
git commit -m "feat(patient): medical history, allergies, medications APIs"
```

---

## Task 3: Appointments API

**Files:**
- Create: `clinical-platform/backend/fastapi/app/api/appointments.py`
- Modify: `clinical-platform/backend/fastapi/app/main.py`

- [ ] **Step 1: Write appointments.py**

```python
# app/api/appointments.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from ..models.database import get_db
from ..services.auth_context import get_user_context, UserContext

router = APIRouter(prefix="/api/patients/{patient_id}/appointments", tags=["appointments"])


class AppointmentCreate(BaseModel):
    scheduled_at: datetime
    duration_minutes: Optional[int] = 30
    status: Optional[str] = "scheduled"
    type: Optional[str] = None
    notes: Optional[str] = None


class AppointmentOut(BaseModel):
    id: UUID
    patient_id: UUID
    user_id: UUID
    scheduled_at: datetime
    duration_minutes: int
    status: str
    type: Optional[str]
    notes: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[AppointmentOut])
def list_appointments(patient_id: UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    rows = db.execute(
        text("""SELECT id, patient_id, user_id, scheduled_at, duration_minutes, status, type, notes, created_at
                FROM appointments WHERE patient_id = :pid ORDER BY scheduled_at DESC"""),
        {"pid": str(patient_id)},
    ).mappings().all()
    return [
        AppointmentOut(
            id=r["id"], patient_id=r["patient_id"], user_id=r["user_id"],
            scheduled_at=r["scheduled_at"], duration_minutes=r["duration_minutes"],
            status=r["status"], type=r["type"], notes=r["notes"], created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(patient_id: UUID, item: AppointmentCreate, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    if not user.clinic_id:
        raise HTTPException(status_code=400, detail={"code": "NO_CLINIC", "message": "User is not associated with a clinic"})
    row = db.execute(
        text("""INSERT INTO appointments (patient_id, user_id, clinic_id, scheduled_at, duration_minutes, status, type, notes)
                VALUES (:pid, :uid, :cid, :sa, :dm, :st, :ty, :nt)
                RETURNING id, patient_id, user_id, scheduled_at, duration_minutes, status, type, notes, created_at"""),
        {
            "pid": str(patient_id), "uid": str(user.user_id), "cid": str(user.clinic_id),
            "sa": item.scheduled_at, "dm": item.duration_minutes, "st": item.status,
            "ty": item.type, "nt": item.notes,
        },
    ).mappings().first()
    db.commit()
    return AppointmentOut(
        id=row["id"], patient_id=row["patient_id"], user_id=row["user_id"],
        scheduled_at=row["scheduled_at"], duration_minutes=row["duration_minutes"],
        status=row["status"], type=row["type"], notes=row["notes"], created_at=row["created_at"].isoformat(),
    )


@router.put("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(patient_id: UUID, appointment_id: UUID, item: AppointmentCreate, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    row = db.execute(
        text("""UPDATE appointments SET scheduled_at=:sa, duration_minutes=:dm, status=:st, type=:ty, notes=:nt, updated_at=NOW()
                WHERE id=:aid AND patient_id=:pid
                RETURNING id, patient_id, user_id, scheduled_at, duration_minutes, status, type, notes, created_at"""),
        {"aid": str(appointment_id), "pid": str(patient_id), "sa": item.scheduled_at, "dm": item.duration_minutes,
         "st": item.status, "ty": item.type, "nt": item.notes},
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "APPOINTMENT_NOT_FOUND", "message": "Appointment not found"})
    return AppointmentOut(
        id=row["id"], patient_id=row["patient_id"], user_id=row["user_id"],
        scheduled_at=row["scheduled_at"], duration_minutes=row["duration_minutes"],
        status=row["status"], type=row["type"], notes=row["notes"], created_at=row["created_at"].isoformat(),
    )


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(patient_id: UUID, appointment_id: UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    db.execute(text("DELETE FROM appointments WHERE id = :id AND patient_id = :pid"), {"id": str(appointment_id), "pid": str(patient_id)})
    db.commit()
    return None
```

- [ ] **Step 2: Modify main.py**

Append inside `app/main.py`:

```python
from .api import appointments
app.include_router(appointments.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/fastapi/app/api/appointments.py backend/fastapi/app/main.py
git commit -m "feat(patient): appointments CRUD API"
```

---

## Task 4: Patient Overview Aggregator Endpoint

**Files:**
- Create: `clinical-platform/backend/fastapi/app/api/patient_overview.py`
- Modify: `clinical-platform/backend/fastapi/app/main.py`

- [ ] **Step 1: Write patient_overview.py**

```python
# app/api/patient_overview.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID
from pydantic import BaseModel
from datetime import date
from ..models.database import get_db
from ..services.auth_context import get_user_context, UserContext

router = APIRouter(prefix="/api/patients/{patient_id}", tags=["patient-overview"])


class PatientOverviewItem(BaseModel):
    id: UUID
    label: str
    type: str
    date: str
    severity: str = "normal"
    notes: str = None


class PatientOverview(BaseModel):
    patient_id: UUID
    patient_name: str
    summary: str
    active_medications: int
    active_allergies: int
    chronic_conditions: int
    dental_state_breakdown: dict
    skeleton_state_breakdown: dict
    recent_events: List[PatientOverviewItem]


@router.get("/overview", response_model=PatientOverview)
def patient_overview(patient_id: UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    # Patient + access check
    p = db.execute(
        text("SELECT first_name, last_name, clinic_id FROM patients WHERE id = :pid AND deleted_at IS NULL"),
        {"pid": str(patient_id)},
    ).mappings().first()
    if not p:
        raise HTTPException(status_code=404, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient not found"})
    if user.clinic_id and p["clinic_id"] != user.clinic_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Patient not in your clinic"})

    # Counts
    active_meds = db.execute(
        text("SELECT COUNT(*) AS c FROM medications WHERE patient_id = :pid AND status = 'active'"),
        {"pid": str(patient_id)},
    ).scalar()
    allergies = db.execute(
        text("SELECT COUNT(*) AS c FROM allergies WHERE patient_id = :pid"),
        {"pid": str(patient_id)},
    ).scalar()
    chronic = db.execute(
        text("SELECT COUNT(*) AS c FROM medical_histories WHERE patient_id = :pid AND status IN ('active','chronic')"),
        {"pid": str(patient_id)},
    ).scalar()

    # Dental states from latest tooth events
    dental_rows = db.execute(
        text("""SELECT event_type, COUNT(*) AS c FROM (
                    SELECT DISTINCT ON (tooth_id) tooth_id, event_type
                    FROM tooth_events WHERE patient_id = :pid AND status='active'
                    ORDER BY tooth_id, event_date DESC
                ) t GROUP BY event_type"""),
        {"pid": str(patient_id)},
    ).fetchall()
    dental_states = {r[0] or "healthy": r[1] for r in dental_rows}
    dental_states.setdefault("healthy", 32 - sum(dental_states.values()))

    # Skeleton states from latest bone events
    skel_rows = db.execute(
        text("""SELECT event_type, COUNT(*) AS c FROM (
                    SELECT DISTINCT ON (bone_id) bone_id, event_type
                    FROM bone_events WHERE patient_id = :pid AND status='active'
                    ORDER BY bone_id, event_date DESC
                ) b GROUP BY event_type"""),
        {"pid": str(patient_id)},
    ).fetchall()
    skel_states = {r[0] or "normal": r[1] for r in skel_rows}

    # Recent events (combined timeline)
    recent = db.execute(
        text("""(SELECT 'tooth' AS kind, event_date AS d, event_type, diagnosis AS notes, id FROM tooth_events WHERE patient_id = :pid)
                UNION ALL
                (SELECT 'bone' AS kind, event_date AS d, event_type, diagnosis AS notes, id FROM bone_events WHERE patient_id = :pid)
                UNION ALL
                (SELECT 'medication' AS kind, COALESCE(start_date, CURRENT_DATE) AS d, drug_name AS event_type, dosage AS notes, id FROM medications WHERE patient_id = :pid)
                ORDER BY d DESC LIMIT 10"""),
        {"pid": str(patient_id)},
    ).mappings().all()
    items = [
        PatientOverviewItem(
            id=r["id"], label=r["event_type"], type=r["kind"], date=str(r["d"]),
            notes=r["notes"],
        )
        for r in recent
    ]

    summary = f"{p['first_name']} {p['last_name']} • {active_meds} active medications • {chronic} chronic conditions"
    return PatientOverview(
        patient_id=patient_id, patient_name=f"{p['first_name']} {p['last_name']}",
        summary=summary, active_medications=active_meds or 0, active_allergies=allergies or 0,
        chronic_conditions=chronic or 0, dental_state_breakdown=dental_states,
        skeleton_state_breakdown=skel_states, recent_events=items,
    )
```

- [ ] **Step 2: Modify main.py**

Append inside `app/main.py`:

```python
from .api import patient_overview
app.include_router(patient_overview.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/fastapi/app/api/patient_overview.py backend/fastapi/app/main.py
git commit -m "feat(patient): overview aggregator endpoint"
```

---

## Task 5: Patient Overview Frontend Page

**Files:**
- Create: `clinical-platform/frontend/js/pages/patient-overview.js`

- [ ] **Step 1: Write patient-overview.js**

```javascript
// js/pages/patient-overview.js
import { apiCall } from '../api.js';
import { DentalChartPage } from './dental-chart.js';
import { SkeletonPage } from './skeleton.js';

export class PatientOverviewPage {
  constructor(container, patientId, role, onBack) {
    this.container = container;
    this.patientId = patientId;
    this.role = role;
    this.onBack = onBack;
    this.render();
  }

  async render() {
    this.container.innerHTML = `
      <div>
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--color-border);margin-bottom:24px">
          <div style="display:flex;gap:24px;align-items:center">
            <button class="btn btn-secondary" id="btn-back">← Back</button>
            <strong>Patient Overview</strong>
          </div>
          <div style="display:flex;gap:8px">
            ${this.role === 'dentist' || this.role === 'admin' ? '<button class="btn btn-primary" id="btn-dental">🦷 Dental Chart</button>' : ''}
            ${this.role === 'orthopedist' || this.role === 'admin' ? '<button class="btn btn-primary" id="btn-skeleton">🦴 Skeleton</button>' : ''}
          </div>
        </nav>
        <div id="overview-body" class="flex flex-col gap-lg"></div>
      </div>
    `;
    this.container.querySelector('#btn-back').onclick = this.onBack;
    if (this.role === 'dentist' || this.role === 'admin') {
      this.container.querySelector('#btn-dental').onclick = () => {
        new DentalChartPage(this.container, this.patientId, this.role, () => this.render());
      };
    }
    if (this.role === 'orthopedist' || this.role === 'admin') {
      this.container.querySelector('#btn-skeleton').onclick = () => {
        new SkeletonPage(this.container, this.patientId, this.role, () => this.render());
      };
    }

    const body = this.container.querySelector('#overview-body');
    body.innerHTML = '<p class="text-secondary">Loading...</p>';

    let overview;
    try {
      overview = await apiCall(`/api/patients/${this.patientId}/overview`);
    } catch (e) {
      body.innerHTML = `<p style="color:var(--color-danger)">Failed to load: ${e.message}</p>`;
      return;
    }

    let allergies = [], meds = [], history = [];
    try { allergies = await apiCall(`/api/patients/${this.patientId}/allergies`); } catch {}
    try { meds = await apiCall(`/api/patients/${this.patientId}/medications?status=active`); } catch {}
    try { history = await apiCall(`/api/patients/${this.patientId}/medical-history`); } catch {}

    body.innerHTML = `
      <div class="card">
        <h2>${overview.patient_name}</h2>
        <p class="text-secondary">${overview.summary}</p>
      </div>

      <div class="grid-3">
        <div class="card">
          <h4>Active Medications</h4>
          <p style="font-size:32px;font-weight:700;color:var(--color-primary)">${overview.active_medications}</p>
          <ul style="margin-top:8px;list-style:none">
            ${meds.slice(0, 5).map(m => `<li>• ${m.drug_name} ${m.dosage || ''} ${m.frequency || ''}</li>`).join('') || '<li class="text-secondary">None</li>'}
          </ul>
        </div>
        <div class="card">
          <h4>Allergies</h4>
          <p style="font-size:32px;font-weight:700;color:var(--color-warning)">${overview.active_allergies}</p>
          <ul style="margin-top:8px;list-style:none">
            ${allergies.slice(0, 5).map(a => `<li>• ${a.allergen} <span class="text-secondary">(${a.severity})</span></li>`).join('') || '<li class="text-secondary">None</li>'}
          </ul>
        </div>
        <div class="card">
          <h4>Chronic Conditions</h4>
          <p style="font-size:32px;font-weight:700;color:var(--color-danger)">${overview.chronic_conditions}</p>
          <ul style="margin-top:8px;list-style:none">
            ${history.slice(0, 5).map(h => `<li>• ${h.condition_name} <span class="text-secondary">(${h.status})</span></li>`).join('') || '<li class="text-secondary">None</li>'}
          </ul>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <h4>Dental States</h4>
          <ul style="list-style:none">
            ${Object.entries(overview.dental_state_breakdown).map(([k, v]) => `<li>${k}: ${v}</li>`).join('')}
          </ul>
        </div>
        <div class="card">
          <h4>Skeleton States</h4>
          <ul style="list-style:none">
            ${Object.entries(overview.skeleton_state_breakdown).map(([k, v]) => `<li>${k}: ${v}</li>`).join('') || '<li class="text-secondary">No events recorded</li>'}
          </ul>
        </div>
      </div>

      <div class="card">
        <h4>Recent Events</h4>
        ${overview.recent_events.length === 0 ? '<p class="text-secondary">No recent events</p>' : `
          <table style="width:100%;margin-top:8px">
            <thead><tr><th style="text-align:left">Date</th><th style="text-align:left">Type</th><th style="text-align:left">Detail</th></tr></thead>
            <tbody>
              ${overview.recent_events.map(e => `
                <tr><td>${e.date}</td><td>${e.type}</td><td>${e.label} ${e.notes ? `— ${e.notes}` : ''}</td></tr>
              `).join('')}
            </tbody>
          </table>
        `}
      </div>
    `;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/
git commit -m "feat(patient): overview page aggregating all patient data"
```

---

## Summary

| Task | Deliverable | Status |
|------|------------|--------|
| 1 | Patient enrichment tables migration | |
| 2 | Medical history / allergies / medications API | |
| 3 | Appointments API | |
| 4 | Patient overview aggregator endpoint | |
| 5 | Patient overview frontend page | |

**Total tasks:** 5
