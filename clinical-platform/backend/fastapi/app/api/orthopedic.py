# app/api/orthopedic.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from datetime import date
from pydantic import BaseModel
from ..models.database import get_db
from ..services.auth_context import get_user_context, UserContext

router = APIRouter(prefix="/api/patients/{patient_id}/skeleton", tags=["orthopedic"])


# Standard body regions seeded for every new patient chart
STANDARD_BODY_REGIONS = [
    {"region_name": "Head", "region_code": "head", "side": "midline", "svg_path": "M150,20 a40,40 0 1,0 0.001,0"},
    {"region_name": "Neck (Cervical Spine)", "region_code": "cervical", "side": "midline", "svg_path": "M140,60 h20 v20 h-20 z"},
    {"region_name": "Shoulder (Left)", "region_code": "shoulder", "side": "left", "svg_path": "M110,90 a15,10 0 1,0 0.001,0"},
    {"region_name": "Shoulder (Right)", "region_code": "shoulder", "side": "right", "svg_path": "M190,90 a15,10 0 1,0 0.001,0"},
    {"region_name": "Upper Arm (Left)", "region_code": "upper_arm", "side": "left", "svg_path": "M105,110 h15 v50 h-15 z"},
    {"region_name": "Upper Arm (Right)", "region_code": "upper_arm", "side": "right", "svg_path": "M180,110 h15 v50 h-15 z"},
    {"region_name": "Elbow (Left)", "region_code": "elbow", "side": "left", "svg_path": "M105,160 a10,10 0 1,0 0.001,0"},
    {"region_name": "Elbow (Right)", "region_code": "elbow", "side": "right", "svg_path": "M185,160 a10,10 0 1,0 0.001,0"},
    {"region_name": "Lower Arm (Left)", "region_code": "lower_arm", "side": "left", "svg_path": "M105,170 h15 v50 h-15 z"},
    {"region_name": "Lower Arm (Right)", "region_code": "lower_arm", "side": "right", "svg_path": "M180,170 h15 v50 h-15 z"},
    {"region_name": "Hand (Left)", "region_code": "hand", "side": "left", "svg_path": "M100,225 h20 v30 h-20 z"},
    {"region_name": "Hand (Right)", "region_code": "hand", "side": "right", "svg_path": "M180,225 h20 v30 h-20 z"},
    {"region_name": "Thoracic Spine", "region_code": "thoracic", "side": "midline", "svg_path": "M145,85 h10 v50 h-10 z"},
    {"region_name": "Lumbar Spine", "region_code": "lumbar", "side": "midline", "svg_path": "M145,140 h10 v50 h-10 z"},
    {"region_name": "Sacrum", "region_code": "sacrum", "side": "midline", "svg_path": "M140,195 h20 v25 h-20 z"},
    {"region_name": "Ribs", "region_code": "ribs", "side": "bilateral", "svg_path": "M125,90 a40,30 0 1,0 0.001,0"},
    {"region_name": "Pelvis", "region_code": "pelvis", "side": "midline", "svg_path": "M120,225 h60 v25 h-60 z"},
    {"region_name": "Hip (Left)", "region_code": "hip", "side": "left", "svg_path": "M125,250 a12,10 0 1,0 0.001,0"},
    {"region_name": "Hip (Right)", "region_code": "hip", "side": "right", "svg_path": "M163,250 a12,10 0 1,0 0.001,0"},
    {"region_name": "Upper Leg (Left)", "region_code": "upper_leg", "side": "left", "svg_path": "M125,265 h20 v70 h-20 z"},
    {"region_name": "Upper Leg (Right)", "region_code": "upper_leg", "side": "right", "svg_path": "M155,265 h20 v70 h-20 z"},
    {"region_name": "Knee (Left)", "region_code": "knee", "side": "left", "svg_path": "M130,335 a10,10 0 1,0 0.001,0"},
    {"region_name": "Knee (Right)", "region_code": "knee", "side": "right", "svg_path": "M160,335 a10,10 0 1,0 0.001,0"},
    {"region_name": "Lower Leg (Left)", "region_code": "lower_leg", "side": "left", "svg_path": "M130,345 h15 v70 h-15 z"},
    {"region_name": "Lower Leg (Right)", "region_code": "lower_leg", "side": "right", "svg_path": "M155,345 h15 v70 h-15 z"},
    {"region_name": "Foot (Left)", "region_code": "foot", "side": "left", "svg_path": "M125,420 h25 v20 h-25 z"},
    {"region_name": "Foot (Right)", "region_code": "foot", "side": "right", "svg_path": "M150,420 h25 v20 h-25 z"},
]

BONES_PER_REGION = {
    "head": [{"bone_name": "Skull", "bone_code": "skull"}],
    "cervical": [{"bone_name": "C1-C7 Vertebrae", "bone_code": "cervical_vertebrae"}],
    "thoracic": [{"bone_name": "T1-T12 Vertebrae", "bone_code": "thoracic_vertebrae"}],
    "lumbar": [{"bone_name": "L1-L5 Vertebrae", "bone_code": "lumbar_vertebrae"}],
    "sacrum": [{"bone_name": "Sacrum", "bone_code": "sacrum_bone"}],
    "ribs": [{"bone_name": "Ribs 1-12", "bone_code": "ribs"}],
    "pelvis": [{"bone_name": "Pelvic Bone", "bone_code": "pelvis_bone"}],
    "shoulder": [{"bone_name": "Clavicle + Scapula", "bone_code": "shoulder_girdle"}],
    "upper_arm": [{"bone_name": "Humerus", "bone_code": "humerus"}],
    "elbow": [{"bone_name": "Elbow Joint", "bone_code": "elbow_joint"}],
    "lower_arm": [{"bone_name": "Radius + Ulna", "bone_code": "radius_ulna"}],
    "hand": [{"bone_name": "Carpals + Metacarpals", "bone_code": "hand_bones"}],
    "hip": [{"bone_name": "Femoral Head", "bone_code": "femoral_head"}],
    "upper_leg": [{"bone_name": "Femur", "bone_code": "femur"}],
    "knee": [{"bone_name": "Patella + Knee Joint", "bone_code": "knee_joint"}],
    "lower_leg": [{"bone_name": "Tibia + Fibula", "bone_code": "tibia_fibula"}],
    "foot": [{"bone_name": "Tarsals + Metatarsals", "bone_code": "foot_bones"}],
}


class BoneEventOut(BaseModel):
    id: UUID
    bone_id: UUID
    event_type: str
    diagnosis: Optional[str]
    event_date: date
    status: str
    treatment: Optional[str]
    healing_status: Optional[str]
    side: Optional[str]
    notes: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class BoneOut(BaseModel):
    id: UUID
    bone_name: str
    bone_code: str
    side: Optional[str]
    svg_path: Optional[str]
    latest_event: Optional[BoneEventOut] = None
    state: str = "normal"  # derived from latest_event


class BodyRegionOut(BaseModel):
    id: UUID
    region_name: str
    region_code: str
    side: Optional[str]
    svg_path: Optional[str]
    bones: List[BoneOut]


class SkeletonOut(BaseModel):
    id: UUID
    patient_id: UUID
    body_regions: List[BodyRegionOut]


def _derive_bone_state(event_type: Optional[str]) -> str:
    if not event_type:
        return "normal"
    mapping = {
        "fracture": "fracture",
        "sprain": "under_treatment",
        "dislocation": "under_treatment",
        "surgery": "surgical",
        "implant": "surgical",
        "arthritis": "chronic",
        "healing": "healing",
        "follow_up": "follow_up",
    }
    return mapping.get(event_type, "treated")


def _ensure_skeleton(db: Session, patient_id: UUID) -> UUID:
    row = db.execute(
        text("SELECT id FROM orthopedic_charts WHERE patient_id = :pid"),
        {"pid": str(patient_id)},
    ).mappings().first()
    if row:
        return row["id"]
    chart_row = db.execute(
        text("INSERT INTO orthopedic_charts (patient_id) VALUES (:pid) RETURNING id"),
        {"pid": str(patient_id)},
    ).mappings().first()
    chart_id = chart_row["id"]
    for region in STANDARD_BODY_REGIONS:
        region_row = db.execute(
            text("""INSERT INTO body_regions (orthopedic_chart_id, region_name, region_code, side, svg_path)
                    VALUES (:cid, :rn, :rc, :side, :svg) RETURNING id"""),
            {
                "cid": str(chart_id),
                "rn": region["region_name"],
                "rc": region["region_code"],
                "side": region["side"],
                "svg": region["svg_path"],
            },
        ).mappings().first()
        region_id = region_row["id"]
        for bone in BONES_PER_REGION.get(region["region_code"], []):
            db.execute(
                text("""INSERT INTO bones (body_region_id, bone_name, bone_code, side)
                        VALUES (:rid, :bn, :bc, :side)"""),
                {
                    "rid": str(region_id),
                    "bn": bone["bone_name"],
                    "bc": bone["bone_code"],
                    "side": region["side"] if region["side"] in ("left","right","midline") else None,
                },
            )
    db.commit()
    return chart_id


@router.get("", response_model=SkeletonOut)
def get_skeleton(
    patient_id: UUID,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    p = db.execute(
        text("SELECT clinic_id FROM patients WHERE id = :pid AND deleted_at IS NULL"),
        {"pid": str(patient_id)},
    ).mappings().first()
    if not p:
        raise HTTPException(status_code=404, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient not found"})
    if user.clinic_id and p["clinic_id"] != user.clinic_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Patient not in your clinic"})

    chart_id = _ensure_skeleton(db, patient_id)

    regions = db.execute(
        text("SELECT id, region_name, region_code, side, svg_path FROM body_regions WHERE orthopedic_chart_id = :cid ORDER BY region_name"),
        {"cid": str(chart_id)},
    ).mappings().all()

    bones = db.execute(
        text("""SELECT b.id, b.bone_name, b.bone_code, b.side, b.body_region_id
                FROM bones b JOIN body_regions r ON b.body_region_id = r.id
                WHERE r.orthopedic_chart_id = :cid"""),
        {"cid": str(chart_id)},
    ).mappings().all()

    events = db.execute(
        text("""SELECT DISTINCT ON (bone_id) bone_id, id, event_type, diagnosis, event_date, status, treatment, healing_status, side, notes, created_at
                FROM bone_events
                WHERE patient_id = :pid AND status = 'active'
                ORDER BY bone_id, event_date DESC, created_at DESC"""),
        {"pid": str(patient_id)},
    ).mappings().all()

    events_by_bone = {e["bone_id"]: e for e in events}
    bones_by_region = {}
    for b in bones:
        bones_by_region.setdefault(b["body_region_id"], []).append(b)

    regions_out = []
    for r in regions:
        bones_out = []
        for b in bones_by_region.get(r["id"], []):
            latest = events_by_bone.get(b["id"])
            bones_out.append(BoneOut(
                id=b["id"], bone_name=b["bone_name"], bone_code=b["bone_code"], side=b["side"],
                svg_path=None,
                latest_event=BoneEventOut(
                    id=latest["id"], bone_id=latest["bone_id"], event_type=latest["event_type"],
                    diagnosis=latest["diagnosis"], event_date=latest["event_date"], status=latest["status"],
                    treatment=latest["treatment"], healing_status=latest["healing_status"],
                    side=latest["side"], notes=latest["notes"],
                    created_at=latest["created_at"].isoformat(),
                ) if latest else None,
                state=_derive_bone_state(latest["event_type"] if latest else None),
            ))
        regions_out.append(BodyRegionOut(
            id=r["id"], region_name=r["region_name"], region_code=r["region_code"], side=r["side"],
            svg_path=r["svg_path"], bones=bones_out,
        ))

    return SkeletonOut(id=chart_id, patient_id=patient_id, body_regions=regions_out)


@router.get("/bones/{bone_id}/events", response_model=List[BoneEventOut])
def list_bone_events(
    patient_id: UUID,
    bone_id: UUID,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    rows = db.execute(
        text("""SELECT id, bone_id, event_type, diagnosis, event_date, status, treatment, healing_status, side, notes, created_at
                FROM bone_events WHERE patient_id = :pid AND bone_id = :bid
                ORDER BY event_date DESC, created_at DESC"""),
        {"pid": str(patient_id), "bid": str(bone_id)},
    ).mappings().all()
    return [
        BoneEventOut(
            id=r["id"], bone_id=r["bone_id"], event_type=r["event_type"],
            diagnosis=r["diagnosis"], event_date=r["event_date"], status=r["status"],
            treatment=r["treatment"], healing_status=r["healing_status"], side=r["side"],
            notes=r["notes"], created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


class BoneEventCreate(BaseModel):
    event_type: str
    diagnosis: Optional[str] = None
    event_date: Optional[date] = None
    treatment: Optional[str] = None
    healing_status: Optional[str] = None
    side: Optional[str] = None
    notes: Optional[str] = None


@router.post("/bones/{bone_id}/events", response_model=BoneEventOut, status_code=status.HTTP_201_CREATED)
def create_bone_event(
    patient_id: UUID,
    bone_id: UUID,
    event: BoneEventCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    b = db.execute(
        text("SELECT id FROM bones WHERE id = :bid AND body_region_id IN (SELECT id FROM body_regions WHERE orthopedic_chart_id IN (SELECT id FROM orthopedic_charts WHERE patient_id = :pid))"),
        {"bid": str(bone_id), "pid": str(patient_id)},
    ).mappings().first()
    if not b:
        raise HTTPException(status_code=404, detail={"code": "BONE_NOT_FOUND", "message": "Bone not found"})

    valid_types = ("exam","fracture","sprain","dislocation","surgery","implant","arthritis","healing","follow_up","other")
    if event.event_type not in valid_types:
        raise HTTPException(status_code=400, detail={"code": "INVALID_EVENT_TYPE", "message": f"event_type must be one of {valid_types}"})

    params = {
        "bid": str(bone_id),
        "pid": str(patient_id),
        "etype": event.event_type,
        "diag": event.diagnosis,
        "edate": event.event_date or date.today(),
        "treat": event.treatment,
        "heal": event.healing_status,
        "side": event.side,
        "notes": event.notes,
        "creator": str(user.user_id),
    }
    row = db.execute(
        text("""INSERT INTO bone_events (bone_id, patient_id, event_type, diagnosis, event_date, treatment, healing_status, side, notes, created_by)
                VALUES (:bid, :pid, :etype, :diag, :edate, :treat, :heal, :side, :notes, :creator)
                RETURNING id, bone_id, event_type, diagnosis, event_date, status, treatment, healing_status, side, notes, created_at"""),
        params,
    ).mappings().first()
    db.commit()
    return BoneEventOut(
        id=row["id"], bone_id=row["bone_id"], event_type=row["event_type"],
        diagnosis=row["diagnosis"], event_date=row["event_date"], status=row["status"],
        treatment=row["treatment"], healing_status=row["healing_status"], side=row["side"],
        notes=row["notes"], created_at=row["created_at"].isoformat(),
    )


@router.put("/bones/{bone_id}/events/{event_id}", response_model=BoneEventOut)
def update_bone_event(
    patient_id: UUID,
    bone_id: UUID,
    event_id: UUID,
    event: BoneEventCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
):
    params = {
        "eid": str(event_id),
        "bid": str(bone_id),
        "pid": str(patient_id),
        "etype": event.event_type,
        "diag": event.diagnosis,
        "edate": event.event_date,
        "treat": event.treatment,
        "heal": event.healing_status,
        "side": event.side,
        "notes": event.notes,
    }
    row = db.execute(
        text("""UPDATE bone_events SET event_type=:etype, diagnosis=:diag,
                                          event_date=COALESCE(:edate, event_date),
                                          treatment=:treat, healing_status=:heal,
                                          side=:side, notes=:notes, updated_at=NOW()
                WHERE id=:eid AND bone_id=:bid AND patient_id=:pid
                RETURNING id, bone_id, event_type, diagnosis, event_date, status, treatment, healing_status, side, notes, created_at"""),
        params,
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "EVENT_NOT_FOUND", "message": "Event not found"})
    return BoneEventOut(
        id=row["id"], bone_id=row["bone_id"], event_type=row["event_type"],
        diagnosis=row["diagnosis"], event_date=row["event_date"], status=row["status"],
        treatment=row["treatment"], healing_status=row["healing_status"], side=row["side"],
        notes=row["notes"], created_at=row["created_at"].isoformat(),
    )