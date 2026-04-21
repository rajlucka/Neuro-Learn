/**
 * src/hooks/useApi.ts
 *
 * React Query hooks for all Neuro Learn API endpoints.
 * Components import from here — never call api.ts directly from components.
 *
 * All hooks accept an optional enabled flag so components can defer
 * fetching until a student ID is known.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getStudent,
  getStudentConcepts,
  getStudentSchedule,
  getStudentHistory,
  getClass,
  getClassGaps,
  getDiagnosticQuestions,
  submitDiagnostic,
  type SubmitRequest,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Query keys -- centralised so cache invalidation is consistent
// ---------------------------------------------------------------------------

export const queryKeys = {
  student:     (id: string) => ["student", id] as const,
  concepts:    (id: string) => ["concepts", id] as const,
  schedule:    (id: string) => ["schedule", id] as const,
  history:     (id: string) => ["history", id] as const,
  class:                      ["class"] as const,
  classGaps:                  ["classGaps"] as const,
  diagnostic:                 ["diagnostic"] as const,
};

// ---------------------------------------------------------------------------
// Student hooks
// ---------------------------------------------------------------------------

export function useStudent(studentId: string) {
  return useQuery({
    queryKey: queryKeys.student(studentId),
    queryFn:  () => getStudent(studentId),
    enabled:  !!studentId,
    staleTime: 30_000,
  });
}

export function useStudentConcepts(studentId: string) {
  return useQuery({
    queryKey: queryKeys.concepts(studentId),
    queryFn:  () => getStudentConcepts(studentId),
    enabled:  !!studentId,
    staleTime: 30_000,
  });
}

export function useStudentSchedule(studentId: string) {
  return useQuery({
    queryKey: queryKeys.schedule(studentId),
    queryFn:  () => getStudentSchedule(studentId),
    enabled:  !!studentId,
    staleTime: 30_000,
    retry: false,   // 404 when no schedule exists -- don't retry
  });
}

export function useStudentHistory(studentId: string) {
  return useQuery({
    queryKey: queryKeys.history(studentId),
    queryFn:  () => getStudentHistory(studentId),
    enabled:  !!studentId,
    staleTime: 60_000,
  });
}

// ---------------------------------------------------------------------------
// Class hooks
// ---------------------------------------------------------------------------

export function useClass() {
  return useQuery({
    queryKey: queryKeys.class,
    queryFn:  getClass,
    staleTime: 60_000,
  });
}

export function useClassGaps() {
  return useQuery({
    queryKey: queryKeys.classGaps,
    queryFn:  getClassGaps,
    staleTime: 60_000,
  });
}

// ---------------------------------------------------------------------------
// Diagnostic hooks
// ---------------------------------------------------------------------------

export function useDiagnosticQuestions() {
  return useQuery({
    queryKey: queryKeys.diagnostic,
    queryFn:  getDiagnosticQuestions,
    staleTime: Infinity,   // questions don't change during a session
  });
}

export function useSubmitDiagnostic() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: SubmitRequest) => submitDiagnostic(body),
    onSuccess: (data) => {
      // Invalidate all caches for this student so data refreshes immediately
      queryClient.invalidateQueries({ queryKey: queryKeys.student(data.student_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.concepts(data.student_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.history(data.student_id) });
    },
  });
}