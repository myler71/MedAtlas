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