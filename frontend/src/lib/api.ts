/**
 * src/lib/api.ts
 *
 * Typed API client for the Neuro Learn FastAPI backend.
 * All components and hooks import from here — never call fetch() directly.
 *
 * Base URL is read from VITE_API_BASE_URL in .env.
 * All functions throw on non-2xx responses so React Query catches them.
 */

const BASE = import.meta.env.VITE_API_BASE_URL as string;

// ---------------------------------------------------------------------------
// Shared types -- mirror the Pydantic models in api/main.py
// and the TypeScript interfaces in src/data/mockData.ts
// ---------------------------------------------------------------------------

export interface StudentInfo {
  id: string;
  name: string;
  grade: string;
  overallMastery: number;
}

export interface ConceptData {
  concept: string;
  masteryScore: number;
  bktProb: number;
  status: "mastered" | "learning" | "struggling";
}

export interface SM2Item {
  concept: string;
  nextDate: string;
  easeFactor: number;
}

export interface ExamHistory {
  id: string;
  title: string;
  date: string;
  score: number;
  aiFeedback: string;
  studyPlan: string[];
}

export interface ClassStudent {
  id: string;
  name: string;
  scores: number[];
  archetype: "Rapid" | "Steady" | "At-Risk";
}

export interface GapItem {
  student: string;
  issue: string;
}

export interface DiagnosticQuestion {
  id: string;
  question: string;
  options: string[];
  concept: string;
}

export interface SubmitRequest {
  student_id: string;
  answers: Record<string, string>; // question_id -> selected option letter
}

export interface SubmitResult {
  student_id: string;
  concepts: ConceptData[];
  feedback: string;
  studyPlan: string[];
}

// ---------------------------------------------------------------------------
// Internal helper
// ---------------------------------------------------------------------------

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Student endpoints
// ---------------------------------------------------------------------------

export const getStudent = (studentId: string) =>
  request<StudentInfo>(`/students/${studentId}`);

export const getStudentConcepts = (studentId: string) =>
  request<ConceptData[]>(`/students/${studentId}/concepts`);

export const getStudentSchedule = (studentId: string) =>
  request<SM2Item[]>(`/students/${studentId}/schedule`);

export const getStudentHistory = (studentId: string) =>
  request<ExamHistory[]>(`/students/${studentId}/history`);

// ---------------------------------------------------------------------------
// Class endpoints
// ---------------------------------------------------------------------------

export const getClass = () =>
  request<ClassStudent[]>("/class");

export const getClassGaps = () =>
  request<GapItem[]>("/class/gaps");

// ---------------------------------------------------------------------------
// Diagnostic endpoints
// ---------------------------------------------------------------------------

export const getDiagnosticQuestions = () =>
  request<DiagnosticQuestion[]>("/diagnostic/questions");

export const submitDiagnostic = (body: SubmitRequest) =>
  request<SubmitResult>("/diagnostic/submit", {
    method: "POST",
    body: JSON.stringify(body),
  });