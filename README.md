# Sentinel

A 9-agent clinical AI pipeline for pre-eclampsia risk prediction, with calibrated
probabilities, fairness auditing, and a Generator-Critic faithfulness pattern that
catches LLM fabrication in medical explanations.

**[Live demo ->](https://your-deploy-url.vercel.app)** | Built for portfolio review.

> Synthetic data only. Not for use with real patient information.

## What this is

Sentinel is a working capstone project demonstrating how to build a clinical AI
system with safety properties verifiable at every layer. It is not a product. It
is the architecture and engineering discipline you'd apply if you were starting
to build one.

The system takes a patient record, predicts pre-eclampsia risk using a calibrated
XGBoost model, generates a plain-language explanation grounded in SHAP feature
contributions, retrieves related clinical guidance, and routes through a separate
Clinical Reviewer agent that catches fabrication before any output reaches a
clinician. Every prediction is logged in an immutable audit trail.

## What you'll see in the demo

- **Pre-recorded demo patients** with instant assessments — one reliable, one early-pregnancy with reduced reliability flagged by the calibrator and escalated by the router
- **Custom patient form** that lets you input a synthetic record and run it through the full pipeline live
- **Audit log** of every prediction the deployed system has made, navigable and clickable
- **Fairness audit** showing per-group recall across ethnicities with the auditor's own interpretive notes surfaced verbatim
- **Calibration evidence** with the reliability diagram and Brier score history

### Deployed constraints (honest accounting)

- Backend is on Render's free tier with a 30-second cold start after inactivity. UptimeRobot pings `/healthz` every 10 minutes to keep it warm during business hours.
- Frontend on Vercel free tier.
- LLM provider: Groq's free tier (used for explanation generation and review).
- Mock LLM mode runs for the pre-recorded demo patients (deterministic, zero API calls). Live LLM mode runs for custom form-submitted patients.

## Architecture

Nine agents, orchestrated by LangGraph:

1. **Privacy Gate** — Pydantic schema strips unauthorized fields, enforces synthetic-only
2. **Risk Predictor** — Calibrated XGBoost on 36 engineered features (BP trajectory dominant)
3. **Confidence Calibrator** — Identifies reduced-reliability predictions (gestational window, OOD)
4. **Router** — Two-signal escalation: reliability first, confidence threshold second
5. **Risk Explainer** — LLM generates contribution prose; reliability caveats appended deterministically by code
6. **Literature Retriever** — Tag-based filtering returns related guidance with explicit anti-validation framing
7. **Fairness Auditor** — Offline batch agent; computes equalized odds, distinguishes named clinical groups from residual buckets
8. **Clinical Reviewer** — Generator-Critic faithfulness check; flags fabricated causation, fail-safe on unparseable output
9. **Audit Logger** — Append-only SQLite, captures every safety decision

## Stack

- **ML:** XGBoost, scikit-learn (isotonic CalibratedClassifierCV), SHAP, NumPy
- **Pipeline:** LangGraph, Pydantic v2, Groq (LLM)
- **Backend:** FastAPI, Uvicorn
- **Frontend:** SvelteKit 5, Tailwind v4, TypeScript
- **Deploy:** Render (backend), Vercel (frontend)
- **Storage:** SQLite WAL mode for audit log, ChromaDB at build-time only

## Engineering decisions worth reviewing

- **Calibration is separate from ranking.** `scale_pos_weight` improves AUC but distorts probabilities. Isotonic calibration was applied on a held-out set. Brier 0.148 → 0.023.
- **Determinism for structured data, LLM for prose.** The reliability caveat is appended in code, not authored by the LLM, after a three-iteration prompt loop didn't converge.
- **Move expensive runtime computation to build time.** The literature retriever's query space is bounded (36 unique queries from 5000 patients); precomputing eliminated the sentence-transformer embedder from the runtime image. Resident memory ~480MB → ~250MB.
- **Test our code, not the LLM's behavior.** The regression suite monkeypatches the LLM call at the reviewer agent boundary, keeping safety checks deterministic and CI-ready.

## Running locally

Requires Python 3.11+ and Node 18+.

### Backend

```bash
cd sentinel
pip install -r requirements.txt
python3 -m build.precompute_embeddings   # ~30s, generates data/retriever_cache.json
python3 -m build.precompute_fairness     # ~10s, generates data/fairness_report.json
PYTHONPATH=. uvicorn api.main:app --reload --port 8000
```

### Frontend

```bash
cd sentinel/dashboard
npm install
npm run dev
```

Open `http://localhost:5173`.

### Live LLM mode (optional, for the form path)

```bash
export USE_MOCK_LLM=false
export GROQ_API_KEY=<your key>
# restart uvicorn
```

Without these, the form path shows a graceful "live mode not available" message. Pre-recorded demo patients work in mock mode without any API key.

## Verification

Run the 9-test regression suite to confirm every safety property holds:

```bash
PYTHONPATH=. pytest -v evals/regression_suite.py
# 9 passed in ~25s — schema integrity, gold-set recall, fairness gap,
# all three routing paths, reviewer in both directions
```

## License

