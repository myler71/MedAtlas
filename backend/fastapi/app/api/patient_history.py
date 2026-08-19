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