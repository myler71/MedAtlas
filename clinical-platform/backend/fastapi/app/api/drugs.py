# app/api/drugs.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from ..models.database import get_db
from ..services.auth_context import get_user_context, UserContext
from ..services.drugs import RxNormProvider
from ..services.drugs.interactions import DrugInteractionService

router = APIRouter(prefix="/api", tags=["drugs"])

provider = RxNormProvider()
interaction_service = DrugInteractionService(provider)


class ResolveRequest(BaseModel):
    name: str


class ResolveResponse(BaseModel):
    rxnorm_cui: str
    name: str
    generic_name: Optional[str]
    drug_class: Optional[str]
    aliases: List[str]


@router.post("/drugs/resolve", response_model=ResolveResponse)
async def resolve_drug(req: ResolveRequest, user: UserContext = Depends(get_user_context)):
    concept = await provider.resolve(req.name)
    if not concept:
        raise HTTPException(status_code=422, detail={"code": "DRUG_NOT_FOUND", "message": f"Could not resolve drug: {req.name}"})
    return ResolveResponse(
        rxnorm_cui=concept.rxnorm_cui, name=concept.name,
        generic_name=concept.generic_name, drug_class=concept.drug_class,
        aliases=concept.aliases,
    )


@router.get("/drugs/search", response_model=List[ResolveResponse])
async def search_drugs(q: str = Query(..., min_length=2), limit: int = 10, user: UserContext = Depends(get_user_context)):
    concepts = await provider.search(q, limit=limit)
    return [
        ResolveResponse(
            rxnorm_cui=c.rxnorm_cui, name=c.name,
            generic_name=c.generic_name, drug_class=c.drug_class,
            aliases=c.aliases,
        )
        for c in concepts
    ]


class InteractionCheckRequest(BaseModel):
    drugs: List[str]


@router.post("/drug-interactions/check")
async def check_interactions(req: InteractionCheckRequest, db: Session = Depends(get_db), user: UserContext = Depends(get_user_context)):
    if len(req.drugs) < 2:
        raise HTTPException(status_code=400, detail={"code": "NEED_2_DRUGS", "message": "Need at least 2 drugs to check interactions"})
    result = await interaction_service.check(db, req.drugs)
    return result.model_dump()
