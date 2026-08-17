# app/ai/patient_assistant.py
"""Patient-scoped AI assistant. Retrieves evidence + patient context, synthesizes a
structured response with citations. The synthesis step is pluggable via env.

Clinical safety: this is decision-support. Outputs use 'based on', 'evidence
indicates', 'no supporting record was found' language — never diagnosis or prescription.
"""
import os
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime
from ..rag import TavilyClient
from ..rag.retrieval import HybridRetriever


class Citation(BaseModel):
    source: str
    title: Optional[str] = None
    url: Optional[str] = None
    claim: Optional[str] = None
    evidence_excerpt: Optional[str] = None


class PatientChatResponse(BaseModel):
    patient_name: str
    patient_id: str
    summary: str
    dental_history: List[Dict[str, Any]] = []
    orthopedic_history: List[Dict[str, Any]] = []
    recent_procedures: List[Dict[str, Any]] = []
    current_medications: List[Dict[str, Any]] = []
    allergies: List[Dict[str, Any]] = []
    tooth_findings: List[Dict[str, Any]] = []
    bone_findings: List[Dict[str, Any]] = []
    important_notes: List[str] = []
    missing_information: List[str] = []
    citations: List[Citation] = []


class PatientAssistant:
    def __init__(self, retriever: Optional[HybridRetriever] = None):
        self.retriever = retriever or HybridRetriever(TavilyClient())

    async def _gather_patient_context(self, db: Session, patient_id: UUID) -> Dict[str, Any]:
        # Patient identity
        p = db.execute(
            text("SELECT first_name, last_name, date_of_birth, gender FROM patients WHERE id = :pid"),
            {"pid": str(patient_id)},
        ).mappings().first()
        if not p:
            return {}

        meds = db.execute(
            text("SELECT drug_name, dosage, frequency, status FROM medications WHERE patient_id = :pid"),
            {"pid": str(patient_id)},
        ).mappings().all()
        allergies = db.execute(
            text("SELECT allergen, severity, reaction FROM allergies WHERE patient_id = :pid"),
            {"pid": str(patient_id)},
        ).mappings().all()
        history = db.execute(
            text("SELECT condition_name, status FROM medical_histories WHERE patient_id = :pid"),
            {"pid": str(patient_id)},
        ).mappings().all()
        tooth_events = db.execute(
            text("""SELECT tooth_id, event_type, procedure_name, event_date, diagnosis
                    FROM tooth_events WHERE patient_id = :pid ORDER BY event_date DESC LIMIT 10"""),
            {"pid": str(patient_id)},
        ).mappings().all()
        bone_events = db.execute(
            text("""SELECT bone_id, event_type, diagnosis, event_date, treatment
                    FROM bone_events WHERE patient_id = :pid ORDER BY event_date DESC LIMIT 10"""),
            {"pid": str(patient_id)},
        ).mappings().all()

        return {
            "patient": dict(p),
            "medications": [dict(m) for m in meds],
            "allergies": [dict(a) for a in allergies],
            "medical_history": [dict(h) for h in history],
            "tooth_events": [dict(t) for t in tooth_events],
            "bone_events": [dict(b) for b in bone_events],
        }

    async def chat(self, db: Session, patient_id: UUID, message: str) -> PatientChatResponse:
        ctx = await self._gather_patient_context(db, patient_id)
        if not ctx:
            return PatientChatResponse(
                patient_name="(unknown)", patient_id=str(patient_id),
                summary="Patient not found.",
                important_notes=["No record exists for this patient ID."],
            )

        # Retrieve evidence (patient-scoped)
        chunks = await self.retriever.retrieve(db, message, patient_id=patient_id, top_k=5)
        citations = []
        for c in chunks:
            citations.append(Citation(
                source=c.source,
                title=c.metadata.get("title") if c.metadata else None,
                url=c.metadata.get("url") if c.metadata else None,
                evidence_excerpt=c.content[:280],
            ))

        p = ctx["patient"]
        meds = ctx["medications"]
        allergies = ctx["allergies"]
        history = ctx["medical_history"]
        tooth_events = ctx["tooth_events"]
        bone_events = ctx["bone_events"]

        # Synthesize summary (rule-based, no external LLM required for the demo)
        summary_parts = [
            f"Patient is {p.get('first_name', '')} {p.get('last_name', '')}".strip(),
        ]
        if p.get("date_of_birth"):
            summary_parts.append(f"DOB {p['date_of_birth']}")
        summary_parts.append(f"{len(meds)} medications on file")
        summary_parts.append(f"{len(allergies)} allergies on file")
        summary_parts.append(f"{len(history)} medical history entries")
        summary_parts.append(f"{len(tooth_events)} recent dental events")
        summary_parts.append(f"{len(bone_events)} recent orthopedic events")
        summary_parts.append(f"Retrieved {len(chunks)} evidence chunks for the query")

        summary = " • ".join(summary_parts)

        # Important notes (clinical safety language)
        important = [
            "This response is decision-support information based on retrieved records.",
            "It is NOT a diagnosis or prescription.",
        ]
        if not chunks:
            important.append("No supporting external evidence was retrieved. Local records only.")
            missing = ["External clinical evidence unavailable — Tavily API key may be missing"]
        else:
            missing = []

        return PatientChatResponse(
            patient_name=f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
            patient_id=str(patient_id),
            summary=summary,
            dental_history=[{"event_type": t["event_type"], "procedure": t["procedure_name"], "date": str(t["event_date"])} for t in tooth_events],
            orthopedic_history=[{"event_type": b["event_type"], "diagnosis": b["diagnosis"], "date": str(b["event_date"])} for b in bone_events],
            recent_procedures=[{"kind": "tooth", "detail": t["procedure_name"] or t["event_type"], "date": str(t["event_date"])} for t in tooth_events[:5]] +
                               [{"kind": "bone", "detail": b["event_type"], "date": str(b["event_date"])} for b in bone_events[:5]],
            current_medications=[{"drug": m["drug_name"], "dosage": m["dosage"], "frequency": m["frequency"], "status": m["status"]} for m in meds if m["status"] == "active"],
            allergies=[{"allergen": a["allergen"], "severity": a["severity"], "reaction": a["reaction"]} for a in allergies],
            tooth_findings=[],
            bone_findings=[],
            important_notes=important,
            missing_information=missing,
            citations=citations,
        )
