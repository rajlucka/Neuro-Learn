"""
diagnostic_exam_generator.py

Builds a targeted diagnostic exam from the question bank based on a
student's identified weak and needs-review concepts.

Question selection strategy (IRT-inspired difficulty targeting):
    Weak concepts        -> Easy first, then Medium
    Needs Review         -> Medium first, then Hard
    Mastered (optional)  -> one Hard stretch question

Questions are sorted Easy -> Medium -> Hard within each concept so the
student encounters manageable problems before harder ones.
"""

import logging
import random
from collections import defaultdict

import pandas as pd

from weakness_detector import THRESHOLD_MASTERED, THRESHOLD_WEAK

logger = logging.getLogger(__name__)

DIFFICULTY_ORDER = {"Easy": 1, "Medium": 2, "Hard": 3}

# How many questions to pull per difficulty tier, keyed by mastery tier
SELECTION_TEMPLATE = {
    "Weak":         {"Easy": 2, "Medium": 1},
    "Needs Review": {"Medium": 2, "Hard": 1},
}


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
        {concept: [question_id, ...]} ordered Easy -> Hard within each concept.
    """
    random.seed(seed)
    exam = defaultdict(list)

    # Pre-group bank rows by (topic, difficulty) for fast lookup
    bank_index = {}
    for q_id, row in question_bank.iterrows():
        key = (row["Topic"], row["Difficulty"])
        bank_index.setdefault(key, []).append(q_id)

    for concept in weak_concepts:
        score = mastery_scores.get(concept, 0.0)
        template = _select_template(score)

        for difficulty, n in template.items():
            pool = bank_index.get((concept, difficulty), [])
            random.shuffle(pool)
            exam[concept].extend(pool[:n])

        # Sort this concept's questions Easy -> Hard
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
    lines = [
        "=" * 55,
        "ADAPTIVE DIAGNOSTIC EXAM",
        "=" * 55,
    ]
    for concept, q_ids in exam.items():
        lines.append(f"\n{concept}")
        lines.append("-" * 30)
        for qid in q_ids:
            if qid not in question_bank.index:
                continue
            row  = question_bank.loc[qid]
            diff = row.get("Difficulty", "?")
            text = row.get("Question_Text", "")
            lines.append(f"  [{diff}] {qid}: {text}")
            for opt in ["A", "B", "C", "D"]:
                col = f"Option_{opt}"
                if col in question_bank.columns:
                    lines.append(f"         {opt}) {row.get(col, '')}")
            lines.append(f"         Answer: {row.get('Correct_Answer', '?')}")
    lines.append("\n" + "=" * 55)
    return "\n".join(lines)


def _select_template(score: float) -> dict:
    """Choose the difficulty distribution based on how weak the student is."""
    if score < THRESHOLD_WEAK:
        return SELECTION_TEMPLATE["Weak"]
    return SELECTION_TEMPLATE["Needs Review"]