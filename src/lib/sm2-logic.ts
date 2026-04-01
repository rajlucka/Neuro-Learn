/**
 * Pure SM-2 implementation with zero database dependencies.
 * Kept isolated so it can be unit-tested without any DB setup.
 */

export interface SM2Input {
  previousInterval: number;
  previousEase:     number;
  repetitions:      number;
  score:            number; // 0.0 – 1.0
}

export interface SM2Result {
  newInterval:    number;
  newEase:        number;
  newRepetitions: number;
  nextReviewDate: string; // YYYY-MM-DD
}

const MIN_EASE          = 1.3;
const SUCCESS_THRESHOLD = 0.6;

/**
 * Compute the next SM-2 interval and ease factor from a single review session.
 *
 * @param input - Previous SM-2 state and current session score.
 * @returns       Updated state and ISO date of the next scheduled review.
 */
export function computeSM2(input: SM2Input): SM2Result {
  const { previousInterval, previousEase, repetitions, score } = input;

  let newInterval:    number;
  let newEase:        number;
  let newRepetitions: number;

  if (score >= SUCCESS_THRESHOLD) {
    // Standard SM-2 interval ladder: 1 → 6 → interval * ease
    if (repetitions === 0)      newInterval = 1;
    else if (repetitions === 1) newInterval = 6;
    else                        newInterval = Math.round(previousInterval * previousEase);

    newRepetitions = repetitions + 1;

    // Penalises scores below 0.8, rewards scores above — keeps ease self-correcting
    newEase = Math.max(MIN_EASE, previousEase + 0.1 - (0.8 - score) * 0.28);
  } else {
    // Failed review: full reset
    newInterval    = 1;
    newRepetitions = 0;
    newEase        = Math.max(MIN_EASE, previousEase - 0.2);
  }

  newEase = Math.round(newEase * 100) / 100; // prevent floating-point drift

  const nextDate = new Date();
  nextDate.setDate(nextDate.getDate() + newInterval);

  return {
    newInterval,
    newEase,
    newRepetitions,
    nextReviewDate: nextDate.toISOString().split('T')[0],
  };
}

/**
 * Derive a status label from the current SM-2 state.
 * Used to populate reviewSchedule.status after each update.
 *
 * @param repetitions - Consecutive successful reviews without a reset.
 * @param interval    - Current interval in days.
 * @param score       - Last session score (0.0 – 1.0).
 */
export function computeStatus(
  repetitions: number,
  interval:    number,
  score:       number,
): 'New' | 'Learning' | 'Review' | 'Mastered' {
  if (score < SUCCESS_THRESHOLD)                       return 'Learning';
  if (interval >= 21 && score >= 0.8)                  return 'Mastered';
  if (repetitions >= 2 && score >= SUCCESS_THRESHOLD)  return 'Review';
  if (repetitions >= 1)                                return 'Learning';
  return 'New';
}