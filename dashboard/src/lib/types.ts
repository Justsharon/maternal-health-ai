// Types mirroring api/main.py response shapes. Hand-written for now;
// could be auto-generated from FastAPI's OpenAPI spec later if it's worth it.

export interface DemoPatientSummary {
  patient_id: string;
  age: number;
  ethnicity: string;
  current_gestational_week: number;
  bmi_at_booking: number;
  expected_routing: string;
}

export interface ShapContribution {
  feature: string;
  label: string;
  shap_value: number;
  direction: string;       // "increases risk" | "decreases risk"
  abs_value: number;
}

export interface Guideline {
  summary: string;
  source: string;
  issuing_body: string;
}

export interface Explanation {
  probability: number;
  base_probability: number;
  top_contributions: ShapContribution[];
  narrative: string;
}

export interface AssessmentResult {
  validated_record: Record<string, unknown>;
  privacy_passed: boolean;
  privacy_notes?: string;
  fields_stripped?: string[];
  risk_probability?: number;
  confidence?: number;
  reliability_flag?: 'reliable' | 'reduced_reliability';
  reliability_reason?: string;
  routing_decision?: 'in_scope' | 'escalate' | 'out_of_scope';
  explanation?: Explanation;
  relevant_guidelines?: Guideline[];
  guideline_sources?: string[];
  review_status?: 'approved' | 'needs_review' | 'no_explanation';
  review_notes?: string;
  audit_logged: boolean;
  audit_id?: string;
}

export interface AuditEntry {
  entry_id: number;
  timestamp_utc: string;
  patient_id: string | null;
  event_type: string;
  risk_probability: number | null;
  confidence: number | null;
  routing_decision: string | null;
  review_status: string | null;
}

export interface FairnessGroup {
  group: string;
  recall: number;
  false_positive_rate: number;
  n_total: number;
}

export interface FairnessReport {
  computed_at: string;
  protected_attribute: string;
  operating_threshold: number;
  gap_threshold: number;
  named_groups: FairnessGroup[];
  residual_groups: FairnessGroup[];
  named_group_gap: number;
  full_equalized_odds_difference: number;
  demographic_parity_difference: number;
  verdict: 'PASS' | 'FAIL';
  overall_flag: string;
  audit_notes: string[];
}