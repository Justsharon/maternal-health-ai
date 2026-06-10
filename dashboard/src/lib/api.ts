import type {
  DemoPatientSummary,
  AssessmentResult,
  AuditEntry,
  FairnessReport,
} from './types';

// API base URL: env var in production, localhost in dev
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API ${path}: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      if (err.detail) {
        // Pydantic returns a list of {loc, msg, type} or a string
        detail = typeof err.detail === 'string'
          ? err.detail
          : err.detail.map((e: { msg: string; loc?: string[] }) =>
              `${e.loc?.join('.') ?? ''}: ${e.msg}`).join('; ');
      }
    } catch {
      throw new Error(`API ${path}: ${res.status} ${res.statusText}`);
    }
    throw new Error(`API ${path}: ${res.status} — ${detail}`);
  }
  return res.json();
}

export const api = {
  health: () => get<{ status: string; service: string }>('/healthz'),
  listDemoPatients: () => get<DemoPatientSummary[]>('/demo_patients'),
  assessDemo: (patientId: string) =>
    post<AssessmentResult>(`/assess_demo/${patientId}`),
  // Submit a custom patient record. Backend validates against PatientRecord schema.
  assess: (patient: Record<string, unknown>) =>
    post<AssessmentResult>('/assess', patient),
  auditLog: (limit = 50) => get<AuditEntry[]>(`/audit_log?limit=${limit}`),
  fairnessReport: () => get<FairnessReport>('/fairness_report'),
};

