from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import (
    patients, dental, orthopedic,
    patient_history, appointments, patient_overview,
    drugs, chat,
)

app = FastAPI(title="Clinical Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(patients.router)
app.include_router(dental.router)
app.include_router(orthopedic.router)
app.include_router(patient_history.router)
app.include_router(appointments.router)
app.include_router(patient_overview.router)
app.include_router(drugs.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "fastapi"}
