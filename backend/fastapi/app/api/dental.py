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
