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
