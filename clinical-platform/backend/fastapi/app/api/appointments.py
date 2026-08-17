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
