# SP-2: Dental Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the interactive dental chart — tooth model with Universal/FDI/Palmer numbering adapters, odontogram API, tooth events CRUD, and the SVG-based interactive dental chart frontend.

**Architecture:** Three layers — Python data model + numbering adapters in FastAPI, REST endpoints under `/api/patients/{id}/dental-chart`, vanilla JS + SVG odontogram frontend.

**Tech Stack:** Python/SQLAlchemy, Pydantic, FastAPI, vanilla JS, SVG, CSS

**Spec:** `docs/superpowers/specs/2026-XX-XX-clinical-platform-design.md` (especially §6.2, §7.3, §10.2 Odontogram)

**Depends on:** SP-1 (schema, auth context, Express proxy)

## Global Constraints

- A patient's dental chart is auto-created the first time it's accessed (no separate POST endpoint needed)
- All tooth numbers use FDI canonical form internally; display adapters convert to Universal or Palmer on read
- Tooth event timestamps are immutable once created
- Soft delete (status='archived') for tooth events, never hard delete
- Express proxy adds `x-user-id` / `x-user-role` / `x-clinic-id` headers — FastAPI reads them via `get_user_context()`

---

## Task 1: Database Migration — Dental Tables

**Files:**
- Create: `clinical-platform/database/migrations/002_dental.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
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
```

- [ ] **Step 2: Apply migration to running DB (if postgres is up)**

```bash
docker compose exec -T postgres psql -U clinical -d clinical_platform < database/migrations/002_dental.sql
```

- [ ] **Step 3: Commit**

```bash
git add database/migrations/
git commit -m "feat(db): dental chart, teeth, tooth_events tables"
```

---

## Task 2: Numbering Adapters (FDI / Universal / Palmer)

**Files:**
- Create: `clinical-platform/backend/fastapi/app/services/dental/numbering.py`
- Create: `clinical-platform/backend/fastapi/app/services/dental/__init__.py`
- Create: `clinical-platform/backend/fastapi/app/services/__init__.py` (already exists, may need update)

- [ ] **Step 1: Write numbering.py**

```python
# app/services/dental/numbering.py
"""Tooth numbering adapters: canonical FDI <-> Universal <-> Palmer.

Canonical form stored in DB is FDI (ISO 3950).
- Permanent teeth: quadrants 1-4, positions 1-8
  - FDI 11..18 (UR), 21..28 (UL), 31..38 (LL), 41..48 (LR)
- Primary teeth: quadrants 5-8, positions 1-5
  - FDI 51..55 (UR), 61..65 (UL), 71..75 (LL), 81..85 (LR)

Universal (ADA) numbers:
- Permanent: 1..32 (UR starts at 1 going clockwise to 32 at LR third molar)
- Primary: A..T

Palmer notation: quadrant symbol + position 1-8 (e.g. UR1)
"""

from typing import Optional

# Quadrant boundaries for Universal numbering (permanent)
_UNIVERSAL_QUADRANT_BOUNDS = {  # (start_inclusive, end_inclusive, fdi_quadrant)
    "UR": (1, 8, 1),
    "UL": (9, 16, 2),
    "LL": (17, 24, 3),
    "LR": (25, 32, 4),
}

_UNIVERSAL_PRIMARY_QUADRANT_BOUNDS = {
    "UR": ("A", "E", 5),
    "UL": ("F", "J", 6),
    "LL": ("K", "O", 7),
    "LR": ("P", "T", 8),
}


def fdi_to_universal(fdi: int) -> Optional[str]:
    """Convert FDI tooth number to Universal notation.

    Returns integer as string for permanent teeth, single letter for primary.
    Returns None if FDI is invalid.
    """
    if fdi < 11 or fdi > 85:
        return None
    fdi_quadrant = fdi // 10
    position = fdi % 10
    if fdi_quadrant in (1, 2, 3, 4):
        if not (1 <= position <= 8):
            return None
        # Universal is sequential 1..32 across quadrants clockwise from UR
        base = (fdi_quadrant - 1) * 8
        universal_num = base + position
        return str(universal_num)
    elif fdi_quadrant in (5, 6, 7, 8):
        if not (1 <= position <= 5):
            return None
        # Primary: UR=A-E, UL=F-J, LL=K-O, LR=P-T
        idx = (fdi_quadrant - 5) * 5 + (position - 1)
        return chr(ord("A") + idx)
    return None


def universal_to_fdi(universal: str) -> Optional[int]:
    """Convert Universal notation to FDI.

    Accepts integer 1..32 (permanent) or letter A..T (primary).
    """
    s = universal.strip().upper()
    if s.isdigit():
        n = int(s)
        if not (1 <= n <= 32):
            return None
        fdi_quadrant = ((n - 1) // 8) + 1
        position = ((n - 1) % 8) + 1
        return fdi_quadrant * 10 + position
    elif len(s) == 1 and "A" <= s <= "T":
        idx = ord(s) - ord("A")
        fdi_quadrant = (idx // 5) + 5
        position = (idx % 5) + 1
        return fdi_quadrant * 10 + position
    return None


def fdi_to_palmer(fdi: int) -> Optional[str]:
    """Convert FDI tooth number to Palmer notation.

    Palmer: quadrant symbol (UR┌, UL┐, LL└, LR┘) + position number 1-8.
    Returns None if FDI is invalid.
    """
    if fdi < 11 or fdi > 85:
        return None
    fdi_quadrant = fdi // 10
    position = fdi % 10
    is_primary = fdi_quadrant in (5, 6, 7, 8)
    max_position = 5 if is_primary else 8
    if not (1 <= position <= max_position):
        return None
    # Quadrant symbols (use unicode)
    symbols = {1: "�", 2: "┐", 3: "└", 4: "┘",
               5: "┌ᵖ", 6: "┐ᵖ", 7: "└ᵖ", 8: "┘ᵖ"}
    return f"{symbols[fdi_quadrant]}{position}"


def palmer_to_fdi(palmer: str) -> Optional[int]:
    """Convert Palmer notation to FDI. Accepts ┌1..┘8 (and primary variants)."""
    s = palmer.strip()
    if len(s) < 2:
        return None
    sym = s[0]
    pos_str = s[1:].rstrip("�")
    if not pos_str.isdigit():
        return None
    position = int(pos_str)
    is_primary = "ᵖ" in s
    if is_primary:
        if not (1 <= position <= 5):
            return None
        sym_map = {"┌": 5, "�": 6, "└": 7, "┘": 8}
    else:
        if not (1 <= position <= 8):
            return None
        sym_map = {"┌": 1, "┐": 2, "└": 3, "┘": 4}
    fdi_quadrant = sym_map.get(sym)
    if fdi_quadrant is None:
        return None
    return fdi_quadrant * 10 + position


def all_permanent_fdi() -> list[int]:
    return [q * 10 + p for q in (1, 2, 3, 4) for p in range(1, 9)]


def all_primary_fdi() -> list[int]:
    return [q * 10 + p for q in (5, 6, 7, 8) for p in range(1, 6)]
```

- [ ] **Step 2: Add empty `__init__.py`**

```python
# app/services/dental/__init__.py
```

- [ ] **Step 3: Commit**

```bash
git add backend/fastapi/app/services/dental/
git commit -m "feat(dental): FDI/Universal/Palmer numbering adapters"
```

---

## Task 3: Dental Chart API — Read & Auto-create

**Files:**
- Create: `clinical-platform/backend/fastapi/app/api/dental.py`
- Modify: `clinical-platform/backend/fastapi/app/main.py` (include the new router)

- [ ] **Step 1: Write dental.py**

```python
# app/api/dental.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID
from datetime import date
from ..models.database import get_db
from ..services.auth_context import get_user_context, UserContext
from ..services.dental.numbering import (
    fdi_to_universal,
    fdi_to_palmer,
    all_permanent_fdi,
    all_primary_fdi,
)
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/patients/{patient_id}/dental-chart", tags=["dental"])


class ToothEventOut(BaseModel):
    id: UUID
    tooth_id: UUID
    event_type: str
    procedure_name: Optional[str]
    diagnosis: Optional[str]
    event_date: date
    status: str
    surfaces: list
    notes: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class ToothOut(BaseModel):
    id: UUID
    tooth_number_fdi: int
    tooth_number_universal: Optional[str]
    tooth_number_palmer: Optional[str]
    dentition_type: str
    quadrant: int
    position_in_quadrant: int
    latest_event: Optional[ToothEventOut] = None
    state: str = "healthy"  # derived from latest_event.event_type


class DentalChartOut(BaseModel):
    id: UUID
    patient_id: UUID
    teeth: List[ToothOut]


def _derive_state(event_type: Optional[str]) -> str:
    if not event_type:
        return "healthy"
    mapping = {
        "caries": "caries",
        "restoration": "restored",
        "extraction": "missing",
        "root_canal": "root_canal",
        "crown": "crown",
        "implant": "implant",
        "fracture": "fractured",
    }
    return mapping.get(event_type, "treated")


def _ensure_chart(db: Session, patient_id: UUID) -> UUID:
    """Return the dental_chart.id for patient, creating one (and all 32 permanent teeth) if needed."""
    row = db.execute(
        text("SELECT id FROM dental_charts WHERE patient_id = :pid"),
        {"pid": str(patient_id)},
    ).mappings().first()
    if row:
        return row["id"]
    chart_row = db.execute(
        text("INSERT INTO dental_charts (patient_id) VALUES (:pid) RETURNING id"),
        {"pid": str(patient_id)},
    ).mappings().first()
    chart_id = chart_row["id"]
    # Seed all 32 permanent teeth by default
    for fdi in all_permanent_fdi():
        db.execute(
            text("""INSERT INTO teeth (dental_chart_id, tooth_number_fdi, dentition_type, position_in_quadrant, quadrant, tooth_name)
                    VALUES (:cid, :fdi, 'permanent', :pos, :quad, :name)"""),
            {
                "cid": str(chart_id),
                "fdi": fdi,
                "pos": fdi % 10,
                "quad": fdi // 10,
                "name": f"Tooth {fdi}",
            },
        )
    db.commit()
    return chart_id


@router.get("", response_model=DentalChartOut)
def get_dental_chart(
    patient_id: UUID,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    # Patient access check
    p = db.execute(
        text("SELECT clinic_id FROM patients WHERE id = :pid AND deleted_at IS NULL"),
        {"pid": str(patient_id)},
    ).mappings().first()
    if not p:
        raise HTTPException(status_code=404, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient not found"})
    if user.clinic_id and p["clinic_id"] != user.clinic_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Patient not in your clinic"})

    chart_id = _ensure_chart(db, patient_id)

    teeth_rows = db.execute(
        text("""SELECT id, tooth_number_fdi, dentition_type, position_in_quadrant, quadrant
                FROM teeth WHERE dental_chart_id = :cid ORDER BY tooth_number_fdi"""),
        {"cid": str(chart_id)},
    ).mappings().all()

    # Latest event per tooth
    events = db.execute(
        text("""SELECT DISTINCT ON (tooth_id) tooth_id, id, event_type, procedure_name, diagnosis, event_date, status, surfaces, notes, created_at
                FROM tooth_events
                WHERE patient_id = :pid AND status = 'active'
                ORDER BY tooth_id, event_date DESC, created_at DESC"""),
        {"pid": str(patient_id)},
    ).mappings().all()

    events_by_tooth = {e["tooth_id"]: e for e in events}

    teeth_out = []
    for t in teeth_rows:
        latest = events_by_tooth.get(t["id"])
        teeth_out.append(ToothOut(
            id=t["id"],
            tooth_number_fdi=t["tooth_number_fdi"],
            tooth_number_universal=fdi_to_universal(t["tooth_number_fdi"]),
            tooth_number_palmer=fdi_to_palmer(t["tooth_number_fdi"]),
            dentition_type=t["dentition_type"],
            quadrant=t["quadrant"],
            position_in_quadrant=t["position_in_quadrant"],
            latest_event=ToothEventOut(
                id=latest["id"], tooth_id=latest["tooth_id"],
                event_type=latest["event_type"],
                procedure_name=latest["procedure_name"],
                diagnosis=latest["diagnosis"],
                event_date=latest["event_date"],
                status=latest["status"],
                surfaces=latest["surfaces"] or [],
                notes=latest["notes"],
                created_at=latest["created_at"].isoformat(),
            ) if latest else None,
            state=_derive_state(latest["event_type"] if latest else None),
        ))

    return DentalChartOut(id=chart_id, patient_id=patient_id, teeth=teeth_out)


@router.get("/teeth/{tooth_id}/events", response_model=List[ToothEventOut])
def list_tooth_events(
    patient_id: UUID,
    tooth_id: UUID,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    rows = db.execute(
        text("""SELECT id, tooth_id, event_type, procedure_name, diagnosis, event_date, status, surfaces, notes, created_at
                FROM tooth_events WHERE patient_id = :pid AND tooth_id = :tid
                ORDER BY event_date DESC, created_at DESC"""),
        {"pid": str(patient_id), "tid": str(tooth_id)},
    ).mappings().all()
    return [
        ToothEventOut(
            id=r["id"], tooth_id=r["tooth_id"], event_type=r["event_type"],
            procedure_name=r["procedure_name"], diagnosis=r["diagnosis"],
            event_date=r["event_date"], status=r["status"],
            surfaces=r["surfaces"] or [], notes=r["notes"],
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


class ToothEventCreate(BaseModel):
    event_type: str
    procedure_name: Optional[str] = None
    diagnosis: Optional[str] = None
    event_date: Optional[date] = None
    surfaces: list = []
    notes: Optional[str] = None


@router.post("/teeth/{tooth_id}/events", response_model=ToothEventOut, status_code=status.HTTP_201_CREATED)
def create_tooth_event(
    patient_id: UUID,
    tooth_id: UUID,
    event: ToothEventCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    # Verify tooth belongs to patient
    t = db.execute(
        text("SELECT id FROM teeth WHERE id = :tid AND dental_chart_id IN (SELECT id FROM dental_charts WHERE patient_id = :pid)"),
        {"tid": str(tooth_id), "pid": str(patient_id)},
    ).mappings().first()
    if not t:
        raise HTTPException(status_code=404, detail={"code": "TOOTH_NOT_FOUND", "message": "Tooth not found"})

    valid_types = ("exam","caries","restoration","extraction","root_canal","crown","implant","fracture","cleaning","other")
    if event.event_type not in valid_types:
        raise HTTPException(status_code=400, detail={"code": "INVALID_EVENT_TYPE", "message": f"event_type must be one of {valid_types}"})

    params = {
        "tid": str(tooth_id),
        "pid": str(patient_id),
        "etype": event.event_type,
        "pname": event.procedure_name,
        "diag": event.diagnosis,
        "edate": event.event_date or date.today(),
        "surfaces": event.surfaces,
        "notes": event.notes,
        "provider": str(user.user_id),
        "creator": str(user.user_id),
    }
    row = db.execute(
        text("""INSERT INTO tooth_events (tooth_id, patient_id, event_type, procedure_name, diagnosis, event_date, surfaces, provider_id, notes, created_by)
                VALUES (:tid, :pid, :etype, :pname, :diag, :edate, :surfaces, :provider, :notes, :creator)
                RETURNING id, tooth_id, event_type, procedure_name, diagnosis, event_date, status, surfaces, notes, created_at"""),
        params,
    ).mappings().first()
    db.commit()
    return ToothEventOut(
        id=row["id"], tooth_id=row["tooth_id"], event_type=row["event_type"],
        procedure_name=row["procedure_name"], diagnosis=row["diagnosis"],
        event_date=row["event_date"], status=row["status"],
        surfaces=row["surfaces"] or [], notes=row["notes"],
        created_at=row["created_at"].isoformat(),
    )


@router.put("/teeth/{tooth_id}/events/{event_id}", response_model=ToothEventOut)
def update_tooth_event(
    patient_id: UUID,
    tooth_id: UUID,
    event_id: UUID,
    event: ToothEventCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    params = {
        "eid": str(event_id),
        "tid": str(tooth_id),
        "pid": str(patient_id),
        "etype": event.event_type,
        "pname": event.procedure_name,
        "diag": event.diagnosis,
        "edate": event.event_date,
        "surfaces": event.surfaces,
        "notes": event.notes,
    }
    row = db.execute(
        text("""UPDATE tooth_events SET event_type=:etype, procedure_name=:pname, diagnosis=:diag,
                                          event_date=COALESCE(:edate, event_date),
                                          surfaces=:surfaces, notes=:notes, updated_at=NOW()
                WHERE id=:eid AND tooth_id=:tid AND patient_id=:pid
                RETURNING id, tooth_id, event_type, procedure_name, diagnosis, event_date, status, surfaces, notes, created_at"""),
        params,
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "EVENT_NOT_FOUND", "message": "Event not found"})
    return ToothEventOut(
        id=row["id"], tooth_id=row["tooth_id"], event_type=row["event_type"],
        procedure_name=row["procedure_name"], diagnosis=row["diagnosis"],
        event_date=row["event_date"], status=row["status"],
        surfaces=row["surfaces"] or [], notes=row["notes"],
        created_at=row["created_at"].isoformat(),
    )
```

- [ ] **Step 2: Modify main.py to include the dental router**

Append inside `app/main.py` (after `app.include_router(patients.router)`):

```python
from .api import dental
app.include_router(dental.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/fastapi/app/api/dental.py backend/fastapi/app/main.py
git commit -m "feat(dental): dental chart API with auto-seed and tooth event CRUD"
```

---

## Task 4: Interactive Odontogram Frontend

**Files:**
- Create: `clinical-platform/frontend/js/pages/dental-chart.js`
- Create: `clinical-platform/frontend/css/dental.css`
- Create: `clinical-platform/frontend/js/components/odontogram.js`

- [ ] **Step 1: Create dental.css**

```css
/* css/dental.css */
.odontogram-container {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-lg);
  padding: var(--spacing-md);
}

.odontogram-row {
  display: flex;
  justify-content: center;
  gap: var(--spacing-xs);
}

.tooth-svg {
  cursor: pointer;
  transition: transform 0.1s;
}

.tooth-svg:hover {
  transform: scale(1.1);
}

.tooth-state-healthy { fill: #ffffff; stroke: #0f172a; stroke-width: 1.5; }
.tooth-state-caries { fill: #fbbf24; stroke: #92400e; stroke-width: 1.5; }
.tooth-state-restored { fill: #93c5fd; stroke: #1e40af; stroke-width: 1.5; }
.tooth-state-missing { fill: #94a3b8; stroke: #475569; stroke-width: 1.5; opacity: 0.5; }
.tooth-state-extracted { fill: #1e293b; stroke: #0f172a; stroke-width: 1.5; }
.tooth-state-root_canal { fill: #fda4af; stroke: #be123c; stroke-width: 1.5; }
.tooth-state-crown { fill: #fde68a; stroke: #b45309; stroke-width: 1.5; }
.tooth-state-implant { fill: #c4b5fd; stroke: #5b21b6; stroke-width: 1.5; }
.tooth-state-fractured { fill: #fca5a5; stroke: #991b1b; stroke-width: 1.5; }

.tooth-label {
  font-size: 10px;
  text-anchor: middle;
  fill: var(--color-text-secondary);
}

.tooth-detail-panel {
  position: fixed;
  right: 0;
  top: 0;
  height: 100vh;
  width: 400px;
  background: var(--color-surface);
  box-shadow: var(--shadow-lg);
  padding: var(--spacing-lg);
  overflow-y: auto;
  transform: translateX(100%);
  transition: transform 0.2s;
}

.tooth-detail-panel.open { transform: translateX(0); }

.event-timeline {
  border-left: 2px solid var(--color-border);
  padding-left: var(--spacing-md);
  margin-top: var(--spacing-md);
}

.event-item {
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--color-border);
}
```

- [ ] **Step 2: Create odontogram.js (SVG renderer)**

```javascript
// js/components/odontogram.js
// Renders a simple anatomical tooth SVG. Quadrant and position determine shape.
import { apiCall } from '../api.js';

const TOOTH_STATE_CLASSES = {
  healthy: 'tooth-state-healthy',
  caries: 'tooth-state-caries',
  restored: 'tooth-state-restored',
  missing: 'tooth-state-missing',
  extracted: 'tooth-state-extracted',
  root_canal: 'tooth-state-root_canal',
  crown: 'tooth-state-crown',
  implant: 'tooth-state-implant',
  fractured: 'tooth-state-fractured',
};

export class Odontogram {
  constructor(container, patientId, onSelectTooth) {
    this.container = container;
    this.patientId = patientId;
    this.onSelectTooth = onSelectTooth;
    this.teeth = [];
  }

  async load() {
    const data = await apiCall(`/api/patients/${this.patientId}/dental-chart`);
    this.teeth = data.teeth;
    this.render();
  }

  render() {
    // Group teeth by quadrant
    const byQuad = { 1: [], 2: [], 3: [], 4: [] };
    for (const t of this.teeth) byQuad[t.quadrant].push(t);

    // Order rows: Q1+Q2 (upper), Q3+Q4 (lower). Quadrant numbers in FDI: UR=1, UL=2, LL=3, LR=4.
    const rows = [
      { label: 'Upper', quadA: byQuad[1], quadB: byQuad[2] },
      { label: 'Lower', quadA: byQuad[3], quadB: byQuad[4] },
    ];

    const html = rows.map((r, idx) => `
      <div class="odontogram-row" style="${idx === 0 ? 'margin-bottom:24px' : ''}">
        ${this.renderRow(r.quadA, true)}
        ${this.renderRow(r.quadB, false)}
      </div>
    `).join('');

    this.container.innerHTML = `<div class="odontogram-container">${html}</div>`;

    // Attach click handlers
    this.container.querySelectorAll('.tooth-svg').forEach(el => {
      el.onclick = () => {
        const toothId = el.dataset.toothId;
        const tooth = this.teeth.find(t => t.id === toothId);
        if (tooth) this.onSelectTooth(tooth);
      };
    });
  }

  renderRow(teeth, isRightSide) {
    // Right-side: position 8 (molar) leftmost, position 1 (central incisor) rightmost
    // For UL quadrant 2 (left side of mouth, but rendered on right): reverse
    const sorted = [...teeth].sort((a, b) => b.position_in_quadrant - a.position_in_quadrant);
    return sorted.map(t => {
      const stateClass = TOOTH_STATE_CLASSES[t.state] || TOOTH_STATE_CLASSES.healthy;
      const label = t.tooth_number_universal || t.tooth_number_fdi;
      return `
        <svg class="tooth-svg ${stateClass}" data-tooth-id="${t.id}" width="36" height="50" viewBox="0 0 36 50">
          <path d="M 8 8 Q 18 4 28 8 L 28 30 Q 28 42 22 46 Q 18 48 14 46 Q 8 42 8 30 Z" />
          <text class="tooth-label" x="18" y="56">${label}</text>
        </svg>
      `;
    }).join('');
  }
}
```

- [ ] **Step 3: Create dental-chart.js (page that loads odontogram + event panel)**

```javascript
// js/pages/dental-chart.js
import { apiCall } from '../api.js';
import { Odontogram } from '../components/odontogram.js';

export class DentalChartPage {
  constructor(container, patientId, role, onBack) {
    this.container = container;
    this.patientId = patientId;
    this.role = role;
    this.onBack = onBack;
    this.selectedTooth = null;
    this.render();
  }

  render() {
    this.container.innerHTML = `
      <div>
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--color-border);margin-bottom:24px">
          <div style="display:flex;gap:24px;align-items:center">
            <button class="btn btn-secondary" id="btn-back">← Back</button>
            <strong>Dental Chart — Patient ${this.patientId.substring(0, 8)}</strong>
          </div>
        </nav>
        <div id="odontogram-host" class="card"></div>
        <div id="tooth-detail" class="tooth-detail-panel"></div>
      </div>
    `;
    this.container.querySelector('#btn-back').onclick = this.onBack;

    const host = this.container.querySelector('#odontogram-host');
    this.odonto = new Odontogram(host, this.patientId, (tooth) => this.selectTooth(tooth));
    this.odonto.load();
  }

  async selectTooth(tooth) {
    this.selectedTooth = tooth;
    const panel = this.container.querySelector('#tooth-detail');
    panel.classList.add('open');

    // Load event history
    let events = [];
    try {
      events = await apiCall(`/api/patients/${this.patientId}/dental-chart/teeth/${tooth.id}/events`);
    } catch (e) { events = []; }

    const eventTypeOptions = ['exam','caries','restoration','extraction','root_canal','crown','implant','fracture','cleaning','other']
      .map(t => `<option value="${t}">${t}</option>`).join('');

    panel.innerHTML = `
      <h3>Tooth ${tooth.tooth_number_universal || tooth.tooth_number_fdi}</h3>
      <p class="text-secondary">FDI ${tooth.tooth_number_fdi} • ${tooth.dentition_type}</p>
      <p>Current state: <strong>${tooth.state}</strong></p>

      <h4 style="margin-top:24px">Add Event</h4>
      <form id="event-form" class="flex flex-col gap-md" style="margin-top:8px">
        <div>
          <label class="label">Event Type</label>
          <select class="input" name="event_type" required>${eventTypeOptions}</select>
        </div>
        <div>
          <label class="label">Procedure</label>
          <input class="input" name="procedure_name" />
        </div>
        <div>
          <label class="label">Notes</label>
          <textarea class="input" name="notes" rows="3"></textarea>
        </div>
        <button type="submit" class="btn btn-primary">Add Event</button>
      </form>

      <h4 style="margin-top:24px">Event History</h4>
      <div class="event-timeline">
        ${events.length === 0 ? '<p class="text-secondary">No events yet.</p>' : events.map(e => `
          <div class="event-item">
            <strong>${e.event_type}</strong>
            ${e.procedure_name ? `— ${e.procedure_name}` : ''}
            <div class="text-secondary" style="font-size:12px">${e.event_date}</div>
            ${e.notes ? `<div style="margin-top:4px">${e.notes}</div>` : ''}
          </div>
        `).join('')}
      </div>

      <button class="btn btn-secondary mt-md" id="btn-close-panel">Close</button>
    `;
    panel.querySelector('#btn-close-panel').onclick = () => panel.classList.remove('open');
    panel.querySelector('#event-form').onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const data = Object.fromEntries(fd);
      await apiCall(`/api/patients/${this.patientId}/dental-chart/teeth/${tooth.id}/events`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
      // Reload odontogram + panel
      await this.odonto.load();
      const fresh = this.odonto.teeth.find(t => t.id === tooth.id);
      if (fresh) this.selectTooth(fresh);
    };
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat(dental): interactive odontogram SVG and event panel"
```

---

## Summary

| Task | Deliverable | Status |
|------|------------|--------|
| 1 | Dental tables migration | |
| 2 | FDI/Universal/Palmer adapters | |
| 3 | Dental chart API (read, auto-seed, event CRUD) | |
| 4 | Interactive odontogram frontend | |

**Total tasks:** 4
