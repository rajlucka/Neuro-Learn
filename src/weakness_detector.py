"""
weakness_detector.py

Classifies each student-concept mastery score into one of three tiers.
Thresholds and labels are imported from config.py so they never need to
be changed in more than one place.

Tiers:
    Mastered      mastery > THRESHOLD_MASTERED  (default 0.75)
    Needs Review  THRESHOLD_WEAK <= mastery <= THRESHOLD_MASTERED
    Weak          mastery < THRESHOLD_WEAK       (default 0.40)
"""

import logging
import pandas as pd

from config import (
    THRESHOLD_MASTERED, THRESHOLD_WEAK,
    LABEL_MASTERED, LABEL_REVIEW, LABEL_WEAK
)

logger = logging.getLogger(__name__)


def classify_mastery(mastery_df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply tier labels to every (student, concept) cell in the mastery matrix.

    Returns a same-shaped DataFrame of string labels.
    """
    return mastery_df.map(_label)


def get_weak_concepts(mastery_df: pd.DataFrame, student_id: str) -> list:
    """
    Return all concepts for a student that are not yet Mastered.

    Both Weak and Needs Review concepts are included so the diagnostic
    exam and study plan cover the full range of gaps.

    Args:
        mastery_df:  Mastery score DataFrame (students x concepts).
        student_id:  Target student index value.

    Returns:
        Sorted list of concept names below the Mastered threshold.
    """
    if student_id not in mastery_df.index:
        raise ValueError(f"Student '{student_id}' not found in mastery data.")

    row = mastery_df.loc[student_id]
    return sorted(c for c, score in row.items() if score <= THRESHOLD_MASTERED)


def build_summary_report(
    mastery_df: pd.DataFrame,
    classified_df: pd.DataFrame
) -> dict:
    """
    Produce a structured per-student summary used by the dashboard and pipeline.

    Returns:
        {student_id: {"scores": {...}, "labels": {...}, "weak_concepts": [...]}}
    """
    report = {}
    for sid in mastery_df.index:
        scores = mastery_df.loc[sid].to_dict()
        labels = classified_df.loc[sid].to_dict()
        weak   = sorted(c for c, lbl in labels.items() if lbl != LABEL_MASTERED)
        report[sid] = {"scores": scores, "labels": labels, "weak_concepts": weak}
    return report


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _label(v: float) -> str:
    """Map a single mastery float to its tier label string."""
    if v > THRESHOLD_MASTERED:
        return LABEL_MASTERED
    if v >= THRESHOLD_WEAK:
        return LABEL_REVIEW
    return LABEL_WEAK