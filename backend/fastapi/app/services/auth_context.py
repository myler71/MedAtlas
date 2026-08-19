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
