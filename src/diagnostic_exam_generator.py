"""
diagnostic_exam_generator.py

Builds a targeted diagnostic exam from the question bank based on a
student's weak and needs-review concepts.

Difficulty selection follows an IRT-inspired heuristic:
    Weak concepts        -> Easy questions first, then Medium
    Needs Review         -> Medium questions first, then Hard

Questions are ordered Easy -> Hard within each concept so students
encounter manageable problems before harder ones.
"""

import logging
import random
from collections import defaultdict

import pandas as pd

from config import THRESHOLD_WEAK, EXAM_TEMPLATE_WEAK, EXAM_TEMPLATE_REVIEW

logger = logging.getLogger(__name__)

DIFFICULTY_ORDER = {"Easy": 1, "Medium": 2, "Hard": 3}


def generate_diagnostic_exam(
    weak_concepts: list,
    mastery_scores: dict,
    question_bank: pd.DataFrame,
    seed: int = 42
) -> dict:
    """
    Sample questions from the bank for each weak concept.

    Args:
        weak_concepts:  Concepts below the Mastered threshold.
        mastery_scores: {concept: float} mastery values for this student.
        question_bank:  DataFrame indexed by Question_ID.
        seed:           Random seed for reproducibility.

    Returns:
        {concept: [question_id, ...]} ordered Easy -> Hard per concept.
        Concepts with no matching bank questions are excluded from the output.
    """
    random.seed(seed)
    exam = defaultdict(list)

    # Pre-group bank entries by (topic, difficulty) for fast lookup
    bank_index = defaultdict(list)
    for q_id, row in question_bank.iterrows():
        bank_index[(row["Topic"], row["Difficulty"])].append(q_id)

    for concept in weak_concepts:
        score    = mastery_scores.get(concept, 0.0)
        template = EXAM_TEMPLATE_WEAK if score < THRESHOLD_WEAK else EXAM_TEMPLATE_REVIEW

        for difficulty, n in template.items():
            pool = bank_index.get((concept, difficulty), [])
            random.shuffle(pool)
            exam[concept].extend(pool[:n])

        if not exam[concept]:
            del exam[concept]
            continue

        exam[concept] = sorted(
            exam[concept],
            key=lambda qid: DIFFICULTY_ORDER.get(
                question_bank.at[qid, "Difficulty"] if qid in question_bank.index else "Medium", 2
            )
        )

    n_total = sum(len(v) for v in exam.values())
    logger.info("Diagnostic exam: %d questions across %d concepts.", n_total, len(exam))
    return dict(exam)


def format_exam_report(exam: dict, question_bank: pd.DataFrame) -> str:
    """Render the diagnostic exam as a plain-text string for CLI output."""
    lines = []
    for concept, q_ids in exam.items():
        lines.append(f"\n  {concept}")
        lines.append("  " + "-" * 30)
        for qid in q_ids:
            if qid not in question_bank.index:
                continue
            row  = question_bank.loc[qid]
            diff = row.get("Difficulty", "?")
            text = row.get("Question_Text", "")
            lines.append(f"  [{diff}] {text}")
            for opt in ["A", "B", "C", "D"]:
                col = f"Option_{opt}"
                if col in question_bank.columns:
                    lines.append(f"    {opt}) {row.get(col, '')}")
            lines.append(f"    Answer: {row.get('Correct_Answer', '?')}")
    return "\n".join(lines)