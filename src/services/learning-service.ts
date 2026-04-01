import { eq, and, desc } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import * as schema from '../db/schema';
import { computeSM2, computeStatus } from '../lib/sm2-logic';

const MASTERY_WINDOW        = 5;
const LOW_MASTERY_THRESHOLD = 0.6;

export interface AttemptParams {
  studentId:   string;
  conceptId:   string;
  questionId:  string;
  answerGiven: string;
  isCorrect:   boolean;
}

export interface AttemptResult {
  attemptId:            string;
  masteryScore:         number;
  newInterval:          number;
  newEase:              number;
  nextReviewDate:       string;
  status:               string;
  prerequisitesFlagged: string[];
}

export class LearningService {
  constructor(private readonly db: BetterSQLite3Database<typeof schema>) {}

  /**
   * Record one student attempt and update all derived state atomically.
   * SELECTs run before the transaction (requires .all() to execute).
   * All INSERTs/UPSERTs run inside the transaction (requires .run() to execute).
   *
   * @param params - The attempt details.
   * @returns        Computed mastery, new SR schedule state, and any flagged prerequisites.
   * @throws         Re-throws any DB error after Drizzle auto-rolls back the transaction.
   */
  recordAttempt(params: AttemptParams): AttemptResult {
    const now   = new Date().toISOString();
    const today = now.split('T')[0];

    // ── Reads (.all() required — Drizzle is lazy by default) ─────────────

    const recentAttempts = this.db
      .select({ isCorrect: schema.attempts.isCorrect })
      .from(schema.attempts)
      .where(and(
        eq(schema.attempts.studentId, params.studentId),
        eq(schema.attempts.conceptId, params.conceptId),
      ))
      .orderBy(desc(schema.attempts.attemptedAt))
      .limit(MASTERY_WINDOW - 1)
      .all();

    // Include the incoming attempt in the mastery window manually
    const windowAttempts = [...recentAttempts, { isCorrect: params.isCorrect }];
    const masteryScore   = windowAttempts.reduce((sum, a) => sum + (a.isCorrect ? 1 : 0), 0)
                           / windowAttempts.length;

    const existingSchedule = this.db
      .select()
      .from(schema.reviewSchedule)
      .where(and(
        eq(schema.reviewSchedule.studentId, params.studentId),
        eq(schema.reviewSchedule.conceptId, params.conceptId),
      ))
      .limit(1)
      .all();

    const prev = existingSchedule[0];

    const sm2 = computeSM2({
      previousInterval: prev?.intervalDays ?? 1,
      previousEase:     prev?.easeFactor   ?? 2.5,
      repetitions:      prev?.repetitions  ?? 0,
      score:            masteryScore,
    });

    const newStatus = computeStatus(sm2.newRepetitions, sm2.newInterval, masteryScore);

    const prereqs = masteryScore < LOW_MASTERY_THRESHOLD
      ? this.db
          .select({ prerequisiteId: schema.conceptDependencies.prerequisiteId })
          .from(schema.conceptDependencies)
          .where(eq(schema.conceptDependencies.dependentId, params.conceptId))
          .all()
      : [];

    // ── Writes (.run() required on every mutation inside the transaction) ─

    const attemptId  = crypto.randomUUID();
    const flaggedIds: string[] = [];

    this.db.transaction((tx) => {
      // 1. Insert attempt (append-only)
      tx.insert(schema.attempts)
        .values({ id: attemptId, ...params, attemptedAt: now })
        .run();

      // 2. Upsert mastery score
      tx.insert(schema.mastery)
        .values({
          studentId: params.studentId, conceptId: params.conceptId,
          score: masteryScore, updatedAt: now,
        })
        .onConflictDoUpdate({
          target: [schema.mastery.studentId, schema.mastery.conceptId],
          set:    { score: masteryScore, updatedAt: now },
        })
        .run();

      // 3. Upsert review schedule with new SM-2 state
      tx.insert(schema.reviewSchedule)
        .values({
          studentId: params.studentId, conceptId: params.conceptId,
          status: newStatus, intervalDays: sm2.newInterval, easeFactor: sm2.newEase,
          repetitions: sm2.newRepetitions, dueDate: sm2.nextReviewDate,
          lastScore: masteryScore, lastReviewed: today,
        })
        .onConflictDoUpdate({
          target: [schema.reviewSchedule.studentId, schema.reviewSchedule.conceptId],
          set: {
            status: newStatus, intervalDays: sm2.newInterval, easeFactor: sm2.newEase,
            repetitions: sm2.newRepetitions, dueDate: sm2.nextReviewDate,
            lastScore: masteryScore, lastReviewed: today,
          },
        })
        .run();

      // 4. Flag prerequisite concepts if mastery is below threshold
      for (const { prerequisiteId } of prereqs) {
        tx.insert(schema.diagnostics)
          .values({
            id:        crypto.randomUUID(),
            studentId: params.studentId,
            conceptId: prerequisiteId,
            flagged:   true,
            reason:    `Auto-flagged: student scored ${(masteryScore * 100).toFixed(0)}% on a dependent concept`,
            createdAt: now,
          })
          .run();
        flaggedIds.push(prerequisiteId);
      }
    });

    return {
      attemptId, masteryScore,
      newInterval:          sm2.newInterval,
      newEase:              sm2.newEase,
      nextReviewDate:       sm2.nextReviewDate,
      status:               newStatus,
      prerequisitesFlagged: flaggedIds,
    };
  }
}