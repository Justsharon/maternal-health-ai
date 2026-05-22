"""
Sentinel - Audit Logger (Agent 9)

Append-only audit trail for every prediction and clinician decision.
Built on SQLITE with WAL mode for crash safety.

Design principle: the only write operation is INSERT. There is no
update or delete. This enforces imutability at the API level.

Reference: WHO principle 4 (responsibilty and accountabilty).
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from state import SentinelState

DB_PATH = "audit_log.db"


def _init_db(db_path: str = DB_PATH):
    """Initialise the audit log database with WAL mode enabled."""
    conn = sqlite3.connect(db_path)
    # WAL mode: crash-safe, concurrent reads don't block writes

    conn.execute("PRAGMA journal_mode=WAL;")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            entry_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id        TEXT NOT NULL,
            timestamp_utc   TEXT NOT NULL,
            patient_id      TEXT,
            event_type      TEXT NOT NULL,
            risk_probability REAL,
            confidence      REAL,
            routing_decision TEXT,
            review_status   TEXT,
            clinician_decision TEXT,
            privacy_passed  INTEGER,
            fields_stripped TEXT,
            payload         TEXT
        );
    """)
    conn.commit()
    conn.close()


def log_event(
    state: SentinelState,
    event_type: str,
    db_path: str = DB_PATH,
) -> str:
    """
    Append one immutable entry to the audit log.
    
    Returns the generated audit_id.
    This is the ONLY write operation. No update or delete exists.
    """
    _init_db(db_path)
    
    audit_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Extract patient_id from validated record if present
    validated = state.get("validated_record") or {}
    patient_id = validated.get("patient_id")
    
    # Serialise the full state snapshot for completeness
    # (excluding any large/sensitive raw data)
    payload = {
        "privacy_notes": state.get("privacy_notes"),
        "reliability_flag": state.get("reliability_flag"),
        "reliability_reason": state.get("reliability_reason"),
        "review_notes": state.get("review_notes"),
        "final_recommendation": state.get("final_recommendation"),
    }
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        INSERT INTO audit_log (
            audit_id, timestamp_utc, patient_id, event_type,
            risk_probability, confidence, routing_decision,
            review_status, clinician_decision, privacy_passed,
            fields_stripped, payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        audit_id,
        timestamp,
        patient_id,
        event_type,
        state.get("risk_probability"),
        state.get("confidence"),
        state.get("routing_decision"),
        state.get("review_status"),
        state.get("clinician_decision"),
        1 if state.get("privacy_passed") else 0,
        json.dumps(state.get("fields_stripped") or []),
        json.dumps(payload),
    ))
    conn.commit()
    conn.close()
    
    return audit_id


def audit_logger(state: SentinelState) -> SentinelState:
    """
    Agent 9 — logs the complete pipeline run.
    
    Reads:  most state fields
    Writes: audit_logged, audit_id
    """
    audit_id = log_event(state, event_type="prediction_complete")
    state["audit_logged"] = True
    state["audit_id"] = audit_id
    return state


def read_audit_log(db_path: str = DB_PATH, limit: int = 20) -> list[dict]:
    """Read recent audit entries (read-only — for the dashboard viewer)."""
    if not Path(db_path).exists():
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM audit_log ORDER BY entry_id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            entry_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id        TEXT NOT NULL,
            timestamp_utc   TEXT NOT NULL,
            patient_id      TEXT,
            event_type      TEXT NOT NULL,
            risk_probability REAL,
            confidence      REAL,
            routing_decision TEXT,
            review_status   TEXT,
            clinician_decision TEXT,
            privacy_passed  INTEGER,
            fields_stripped TEXT,
            payload         TEXT
        );
    """)
    conn.commit()
    conn.close()

def log_events(
    state: SentinelState,
    event_type: str,
    db_path: str = DB_PATH,
) -> str:
    """
    Append one immutable entry to the audit log.
    
    Returns the generated audit_id.
    This is the ONLY write operation. No update or delete exists.
    """
    _init_db(db_path)

    audit_id = str(uuid.uuid4())
    timestamp = datetime.now(timestamp.utc).isoformat()

    # Extract patient_id from validated record if present
    validated = state.get("validated_record") or {}
    patient_id = validated.get("patient_id")

    # Serialise the full state snapshot for completeness
    # (excluding any large/sensitive raw data)

    payload = {
        "privacy_notes": state.get("privacy_notes"),
        "reliability_flag": state.get("reliability_flag"),
        "reliability_reason": state.get("reliability_reason"),
        "review_notes": state.get("review_notes"),
        "final_recommendation": state.get("final_recommendation"),
    }

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        INSERT INTO audit_log (
            audit_id, timestamp_utc, patient_id, event_type,
            risk_probability, confidence, routing_decision,
            review_status, clinician_decision, privacy_passed,
            fields_stripped, payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        audit_id,
        timestamp,
        patient_id,
        event_type,
        state.get("risk_probability"),
        state.get("confidence"),
        state.get("routing_decision"),
        state.get("review_status"),
        state.get("clinician_decision"),
        1 if state.get("privacy_passed") else 0,
        json.dumps(state.get("fields_stripped") or []),
        json.dumps(payload),
    ))
    conn.commit()
    conn.close()
    
    return audit_id

def audit_logger(state: SentinelState) -> SentinelState:
    """
    Agent 9 — logs the complete pipeline run.
    
    Reads:  most state fields
    Writes: audit_logged, audit_id
    """
    audit_id = log_event(state, event_type="prediction_complete")
    state["audit_logged"] = True
    state["audit_id"] = audit_id
    return state


def read_audit_log(db_path: str = DB_PATH, limit: int = 20) -> list[dict]:
    """Read recent audit entries (read-only — for the dashboard viewer)."""
    if not Path(db_path).exists():
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM audit_log ORDER BY entry_id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

# --- Standalone test ---
if __name__ == "__main__":
    # Use a test database so we don't pollute the real one
    TEST_DB = "test_audit_log.db"
    Path(TEST_DB).unlink(missing_ok=True)
    Path(f"{TEST_DB}-wal").unlink(missing_ok=True)
    Path(f"{TEST_DB}-shm").unlink(missing_ok=True)
    
    # Simulate a completed pipeline state
    state = {
        "validated_record": {"patient_id": "SYN-TEST-99"},
        "risk_probability": 0.78,
        "confidence": 0.85,
        "routing_decision": "in_scope",
        "review_status": "approved",
        "clinician_decision": None,
        "privacy_passed": True,
        "fields_stripped": ["patient_name"],
        "privacy_notes": "Record validated. Stripped 1 field.",
        "reliability_flag": "reliable",
        "reliability_reason": None,
        "review_notes": "Prediction consistent with BP trajectory.",
        "final_recommendation": "Recommend increased monitoring.",
    }
    
    # Test 1 — log an event
    audit_id = log_event(state, event_type="prediction_complete", db_path=TEST_DB)
    print("Test 1 — Logged event:")
    print(f"  Audit ID: {audit_id}")
    print()
    
    # Test 2 — log a second event (clinician decision)
    state["clinician_decision"] = "confirmed"
    audit_id_2 = log_event(state, event_type="clinician_confirmed", db_path=TEST_DB)
    print("Test 2 — Logged clinician decision:")
    print(f"  Audit ID: {audit_id_2}")
    print(f"  Different from first: {audit_id != audit_id_2}")
    print()
    
    # Test 3 — read back the log
    entries = read_audit_log(db_path=TEST_DB)
    print(f"Test 3 — Read back {len(entries)} entries:")
    for e in entries:
        print(f"  [{e['entry_id']}] {e['event_type']:22s} "
              f"patient={e['patient_id']} "
              f"risk={e['risk_probability']} "
              f"decision={e['clinician_decision']}")
    print()
    
    # Test 4 — verify append-only (both entries exist, original unchanged)
    assert len(entries) == 2, "Both entries should exist"
    # The first event (most recent in DESC order is entry 2) had no clinician decision
    confirmed_entry = [e for e in entries if e["event_type"] == "clinician_confirmed"][0]
    prediction_entry = [e for e in entries if e["event_type"] == "prediction_complete"][0]
    assert prediction_entry["clinician_decision"] is None, "Original entry preserved"
    assert confirmed_entry["clinician_decision"] == "confirmed", "New entry recorded"
    print("Test 4 — Append-only verified:")
    print("Original prediction entry unchanged (clinician_decision=None)")
    print("New confirmation entry added separately")
    print("The log appends — it never overwrites")
    
    # Cleanup
    Path(TEST_DB).unlink(missing_ok=True)
    Path(f"{TEST_DB}-wal").unlink(missing_ok=True)
    Path(f"{TEST_DB}-shm").unlink(missing_ok=True)