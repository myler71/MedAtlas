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
