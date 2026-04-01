"""
sr_service.py

Python-native spaced repetition service.

Writes to the same data/neuro_learn.db SQLite file as the TypeScript schema
but uses its own tables (sr_schedule, sr_history) with concept name strings
as keys to avoid UUID bridging overhead at runtime.

SM-2 algorithm is ported directly from src/lib/sm2-logic.ts.
"""

import os
import sqlite3
import uuid
from datetime import date, timedelta
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "neuro_learn.db")

MIN_EASE          = 1.3
SUCCESS_THRESHOLD = 0.6

# Questions served per difficulty tier depending on SR status
QUESTIONS_BY_STATUS = {
    "New":      {"Easy": 2, "Medium": 1},
    "Learning": {"Easy": 2, "Medium": 1},
    "Review":   {"Medium": 2, "Hard": 1},
    "Mastered": {"Hard": 1},
}


# ---------------------------------------------------------------------------
# DB initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create SR tables if they do not already exist."""
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS sr_schedule (
                student_id    TEXT NOT NULL,
                concept       TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'New',
                interval_days INTEGER NOT NULL DEFAULT 1,
                ease_factor   REAL NOT NULL DEFAULT 2.5,
                repetitions   INTEGER NOT NULL DEFAULT 0,
                due_date      TEXT NOT NULL,
                last_score    REAL,
                last_reviewed TEXT,
                PRIMARY KEY (student_id, concept)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS sr_history (
                id              TEXT PRIMARY KEY,
                student_id      TEXT NOT NULL,
                concept         TEXT NOT NULL,
                review_date     TEXT NOT NULL,
                score           REAL NOT NULL,
                interval_before INTEGER,
                interval_after  INTEGER,
                ease_before     REAL,
                ease_after      REAL
            )
        """)
        c.commit()


# ---------------------------------------------------------------------------
# Schedule management
# ---------------------------------------------------------------------------

def schedule_exists(student_id: str) -> bool:
    """Return True if the student already has SR rows in sr_schedule."""
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM sr_schedule WHERE student_id = ? LIMIT 1",
            (student_id,)
        ).fetchone()
    return row is not None


def initialise_schedule(student_id: str, mastery_scores: dict) -> None:
    """
    Seed one sr_schedule row per concept for a student who has just
    completed the exam. Initial due_date is today so all concepts are
    immediately available for their first review.

    Uses the Phase 2 mastery score as last_score so students who already
    performed well are not penalised on their first SR session.
    """
    today = date.today().isoformat()
    with _conn() as c:
        for concept, score in mastery_scores.items():
            c.execute("""
                INSERT OR IGNORE INTO sr_schedule
                    (student_id, concept, status, interval_days, ease_factor,
                     repetitions, due_date, last_score, last_reviewed)
                VALUES (?, ?, 'New', 1, 2.5, 0, ?, ?, NULL)
            """, (student_id, concept, today, score))
        c.commit()


def get_schedule(student_id: str) -> list[dict]:
    """Return all sr_schedule rows for a student as a list of dicts."""
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM sr_schedule WHERE student_id = ? ORDER BY due_date ASC",
            (student_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_due_concepts(student_id: str) -> list[str]:
    """Return concept names where due_date <= today, ordered soonest first."""
    today = date.today().isoformat()
    with _conn() as c:
        rows = c.execute("""
            SELECT concept FROM sr_schedule
            WHERE student_id = ? AND due_date <= ?
            ORDER BY due_date ASC, ease_factor ASC
        """, (student_id, today)).fetchall()
    return [r["concept"] for r in rows]


def get_concept_status(student_id: str, concept: str) -> Optional[dict]:
    """Return the sr_schedule row for one (student, concept) pair."""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM sr_schedule WHERE student_id = ? AND concept = ?",
            (student_id, concept)
        ).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Attempt recording and SM-2 update
# ---------------------------------------------------------------------------

def record_review_session(
    student_id: str,
    concept: str,
    answers: list[bool],
) -> dict:
    """
    Score a completed review session for one concept and apply SM-2.

    Args:
        student_id : Student identifier.
        concept    : Concept name that was reviewed.
        answers    : List of booleans (True = correct) for each question answered.

    Returns:
        Dict with new SR state: status, interval_days, ease_factor, due_date, score.
    """
    score = sum(answers) / len(answers) if answers else 0.0
    today = date.today().isoformat()

    prev = get_concept_status(student_id, concept) or {}
    prev_interval = prev.get("interval_days", 1)
    prev_ease     = prev.get("ease_factor",   2.5)
    prev_reps     = prev.get("repetitions",   0)

    new_interval, new_ease, new_reps, due_date = _compute_sm2(
        prev_interval, prev_ease, prev_reps, score
    )
    new_status = _compute_status(new_reps, new_interval, score)

    with _conn() as c:
        c.execute("""
            UPDATE sr_schedule
            SET status        = ?,
                interval_days = ?,
                ease_factor   = ?,
                repetitions   = ?,
                due_date      = ?,
                last_score    = ?,
                last_reviewed = ?
            WHERE student_id = ? AND concept = ?
        """, (new_status, new_interval, new_ease, new_reps,
              due_date, score, today, student_id, concept))

        c.execute("""
            INSERT INTO sr_history
                (id, student_id, concept, review_date, score,
                 interval_before, interval_after, ease_before, ease_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), student_id, concept, today, score,
              prev_interval, new_interval, prev_ease, new_ease))

        c.commit()

    return {
        "status":       new_status,
        "interval_days": new_interval,
        "ease_factor":  new_ease,
        "due_date":     due_date,
        "score":        score,
    }


# ---------------------------------------------------------------------------
# Question selection
# ---------------------------------------------------------------------------

def select_review_questions(
    concept: str,
    status: str,
    question_bank,   # pd.DataFrame
) -> list[dict]:
    """
    Pull questions from the question bank for a review session.
    Difficulty mix is determined by the concept's current SR status.

    Returns a list of question dicts ordered Easy -> Hard.
    """
    import random
    template     = QUESTIONS_BY_STATUS.get(status, QUESTIONS_BY_STATUS["Review"])
    difficulty_order = {"Easy": 1, "Medium": 2, "Hard": 3}
    selected     = []

    for difficulty, n in template.items():
        pool = question_bank[
            (question_bank["Topic"] == concept) &
            (question_bank["Difficulty"] == difficulty)
        ]
        sample = pool.sample(min(n, len(pool)), random_state=42) if len(pool) > 0 else pool
        for qid, row in sample.iterrows():
            selected.append({
                "id":         qid,
                "text":       row.get("Question_Text", ""),
                "difficulty": difficulty,
                "options": {
                    "A": row.get("Option_A", ""),
                    "B": row.get("Option_B", ""),
                    "C": row.get("Option_C", ""),
                    "D": row.get("Option_D", ""),
                },
                "correct": row.get("Correct_Answer", ""),
            })

    return sorted(selected, key=lambda q: difficulty_order.get(q["difficulty"], 2))


# ---------------------------------------------------------------------------
# SM-2 pure functions (ported from src/lib/sm2-logic.ts)
# ---------------------------------------------------------------------------

def _compute_sm2(
    prev_interval: int,
    prev_ease: float,
    repetitions: int,
    score: float,
) -> tuple[int, float, int, str]:
    """
    Return (new_interval, new_ease, new_repetitions, due_date_iso).
    Mirrors the TypeScript computeSM2 function exactly.
    """
    if score >= SUCCESS_THRESHOLD:
        if repetitions == 0:   new_interval = 1
        elif repetitions == 1: new_interval = 6
        else:                  new_interval = round(prev_interval * prev_ease)
        new_repetitions = repetitions + 1
        new_ease = max(MIN_EASE, prev_ease + 0.1 - (0.8 - score) * 0.28)
    else:
        new_interval    = 1
        new_repetitions = 0
        new_ease        = max(MIN_EASE, prev_ease - 0.2)

    new_ease    = round(new_ease * 100) / 100
    due_date    = (date.today() + timedelta(days=new_interval)).isoformat()
    return new_interval, new_ease, new_repetitions, due_date


def _compute_status(repetitions: int, interval: int, score: float) -> str:
    """Mirrors the TypeScript computeStatus function exactly."""
    if score < SUCCESS_THRESHOLD:                      return "Learning"
    if interval >= 21 and score >= 0.8:                return "Mastered"
    if repetitions >= 2 and score >= SUCCESS_THRESHOLD: return "Review"
    if repetitions >= 1:                               return "Learning"
    return "New"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _conn() -> sqlite3.Connection:
    """Open a connection to the SQLite DB with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn