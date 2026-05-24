"""
Sentinel — LLM Helper

Provider cascade with recording/replay, adapted from Aria (Phase 3).
Supports: Groq (primary) → Mock (replay recorded responses).

For the OBGYN demo, USE_MOCK_LLM=true replays recorded responses so the
demo is deterministic and never depends on a live API or rate limits.
"""

import os
import json
import hashlib
from pathlib import Path

RECORDINGS_PATH = "agents/recordings.json"


def _load_recordings() -> dict:
    if Path(RECORDINGS_PATH).exists():
        with open(RECORDINGS_PATH) as f:
            return json.load(f)
    return {}


def _save_recording(key: str, response: str):
    recordings = _load_recordings()
    recordings[key] = response
    with open(RECORDINGS_PATH, "w") as f:
        json.dump(recordings, f, indent=2)


def _make_key(system_prompt: str, user_prompt: str) -> str:
    """Deterministic key from prompts for replay matching."""
    combined = f"{system_prompt}|||{user_prompt}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 500,
) -> str:
    """
    Call the LLM with provider cascade.
    
    Modes (via env vars):
      USE_MOCK_LLM=true  → replay recorded response (demo-safe)
      RECORD_LLM=true    → call real API and save the response
      (neither)          → call real API normally
    """
    key = _make_key(system_prompt, user_prompt)
    use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
    record = os.getenv("RECORD_LLM", "false").lower() == "true"
    
    # --- Mock/replay mode (demo-safe) ---
    if use_mock:
        recordings = _load_recordings()
        if key in recordings:
            return recordings[key]
        # No recording found — return a safe placeholder
        return (
            "[Mock response unavailable for this input. "
            "Run once with RECORD_LLM=true to capture a real response.]"
        )
    
    # --- Real API call (Groq) ---
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        result = response.choices[0].message.content.strip()
        
        if record:
            _save_recording(key, result)
        
        return result
    
    except Exception as e:
        return f"[LLM error: {type(e).__name__}. Check GROQ_API_KEY or use USE_MOCK_LLM=true]"