"""
Sentinel — FastAPI Service

HTTP interface to the orchestrator. Wraps assess_patient() and the audit
logger as endpoints. Pydantic validation reuses the existing schemas
(no translation layer).

Endpoints:
  GET  /healthz            — liveness check (for Render's health probe)
  GET  /demo_patients      — list curated demo patients
  POST /assess             — run a patient through the orchestrator
  GET  /audit_log?limit=N  — read recent audit entries

Deployment notes:
  - CORS allows the Vercel frontend origin
  - USE_MOCK_LLM=true by default in production (deterministic demo)
  - Heavy resources (models, ChromaDB) load once at startup, not per-request
"""

import os
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data.schema import PatientRecord
from data.generator import load_dataset
from orchestrator import assess_patient, get_sentinel
from agents.audit_logger import read_audit_log


# --- Deployment configuration ---

# Default to mock mode in production: deterministic, no API key needed at runtime
os.environ.setdefault("USE_MOCK_LLM", "true")

# CORS origins: configured via env var so dev/prod can differ
# In dev: "http://localhost:5173" (SvelteKit default)
# In prod: "https://your-app.vercel.app"
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
).split(",")


# --- Demo patient curation ---
# Hand-picked illustrative cases. IDs from the synthetic dataset.
# These are the patients the dashboard's "demo path" exposes.

DEMO_PATIENT_IDS = [
    "SYN-00004",   # standard reliable patient (in_scope)
    "SYN-00000",   # early-pregnancy patient (escalate, reduced reliability)
    # Additional curated patients can be added here as we identify them.
]


# --- Lifespan: load heavy resources once at startup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm only what's needed for serving demo traffic.
    
    Demo patients are pre-loaded (6 records, ~negligible memory).
    The full 5000-patient dataset is NOT loaded; it's only accessed
    by offline scripts like the fairness auditor.
    """
    print("Sentinel API starting...")
    app.state.orchestrator = get_sentinel()
    
    # Lazy load: only the curated demo patients
    full_dataset = {p.patient_id: p for p in load_dataset("synthetic_data.json")}
    app.state.patients = {
        pid: full_dataset[pid] for pid in DEMO_PATIENT_IDS if pid in full_dataset
    }
    # Explicitly drop the full dict so Python can GC it
    del full_dataset
    
    print(f"  Loaded {len(app.state.patients)} demo patients (lazy mode).")
    print(f"  Mock LLM mode: {os.getenv('USE_MOCK_LLM', 'true')}")
    yield
    print("Sentinel API shutting down.")

app = FastAPI(
    title="Sentinel",
    description="Maternal health risk insight assistant — 9-agent clinical AI pipeline.",
    version="1.0.0",
    lifespan=lifespan,
)


# --- CORS: explicit, restricted to our frontends ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# --- Response shapes (Pydantic for OpenAPI autodocs + type safety) ---

class DemoPatientSummary(BaseModel):
    patient_id: str
    age: int
    ethnicity: str
    current_gestational_week: int
    bmi_at_booking: float
    expected_routing: str  # narrative for the dashboard tile


class AuditEntry(BaseModel):
    entry_id: int
    timestamp_utc: str
    patient_id: Optional[str]
    event_type: str
    risk_probability: Optional[float]
    confidence: Optional[float]
    routing_decision: Optional[str]
    review_status: Optional[str]


# --- Endpoints ---

@app.get("/healthz")
def healthz():
    """Liveness probe. Render and Vercel both ping this."""
    return {"status": "ok", "service": "sentinel"}


@app.get("/demo_patients", response_model=list[DemoPatientSummary])
def list_demo_patients():
    """Return the curated demo patients for the dashboard sidebar."""
    summaries = []
    for pid in DEMO_PATIENT_IDS:
        patient = app.state.patients.get(pid)
        if patient is None:
            continue  # skip if data file changed
        # Tag with the expected routing so the dashboard can preview without running
        if patient.current_gestational_week < 20:
            expected = "escalate (reduced reliability)"
        else:
            expected = "in_scope"
        summaries.append(DemoPatientSummary(
            patient_id=patient.patient_id,
            age=patient.age,
            ethnicity=patient.ethnicity.value,
            current_gestational_week=patient.current_gestational_week,
            bmi_at_booking=patient.bmi_at_booking,
            expected_routing=expected,
        ))
    return summaries


@app.post("/assess")
def assess(patient: PatientRecord):
    """
    Run a patient through the full 9-agent pipeline.
    
    The PatientRecord schema is the SAME one used by the privacy gate —
    validation happens once at this boundary. If the request is malformed
    or non-synthetic, FastAPI returns 422 before the orchestrator runs.
    """
    try:
        # The orchestrator already takes a raw dict, but we've validated
        # via Pydantic at the endpoint boundary, so dump it back cleanly
        result = assess_patient(patient.model_dump(mode="json"))
        return result
    except Exception as e:
        # Defensive: any unhandled error returns 500 with type, never silent
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error: {type(e).__name__}: {str(e)}"
        )


@app.post("/assess_demo/{patient_id}")
def assess_demo(patient_id: str):
    """
    Convenience endpoint: assess a pre-curated demo patient by ID.
    Avoids the dashboard having to POST the full record for known cases.
    """
    patient = app.state.patients.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    if patient_id not in DEMO_PATIENT_IDS:
        raise HTTPException(
            status_code=403,
            detail=f"Patient {patient_id} is not in the demo set"
        )
    result = assess_patient(patient.model_dump(mode="json"))
    return result


@app.get("/audit_log", response_model=list[AuditEntry])
def get_audit_log(limit: int = 20):
    """Read recent audit entries (read-only — for the dashboard viewer)."""
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    entries = read_audit_log(limit=limit)
    # Filter to the fields exposed by AuditEntry schema; drop fields we don't surface
    return [
        AuditEntry(
            entry_id=e["entry_id"],
            timestamp_utc=e["timestamp_utc"],
            patient_id=e.get("patient_id"),
            event_type=e["event_type"],
            risk_probability=e.get("risk_probability"),
            confidence=e.get("confidence"),
            routing_decision=e.get("routing_decision"),
            review_status=e.get("review_status"),
        )
        for e in entries
    ]
