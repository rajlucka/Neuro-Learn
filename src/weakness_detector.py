"""
weakness_detector.py

Classifies each student-concept pair into one of three mastery tiers:

    Mastered      mastery > 0.75
    Needs Review  0.40 <= mastery <= 0.75
    Weak          mastery < 0.40

These labels drive both the diagnostic exam generator and the study plan,
so the thresholds are defined as module-level constants to keep them easy
to adjust without touching other modules.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)

THRESHOLD_MASTERED = 0.75
THRESHOLD_WEAK     = 0.40

LABEL_MASTERED = "Mastered"
LABEL_REVIEW   = "Needs Review"
LABEL_WEAK     = "Weak"


def classify_mastery(mastery_df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply tier labels to every (student, concept) cell in the mastery matrix.

    Returns a same-shaped DataFrame of string labels.
    """
    def _label(v: float) -> str:
        if v > THRESHOLD_MASTERED:
            return LABEL_MASTERED
        if v >= THRESHOLD_WEAK:
            return LABEL_REVIEW
        return LABEL_WEAK

    return mastery_df.map(_label)


def get_weak_concepts(mastery_df: pd.DataFrame, student_id: str) -> list:
    """
    Return all concepts for a student that are not yet Mastered.

    Both Weak and Needs Review concepts are included so the diagnostic exam
    and study plan cover the full range of gaps.
    """
    if student_id not in mastery_df.index:
        raise ValueError(f"Student '{student_id}' not found in mastery data.")

    row = mastery_df.loc[student_id]
    return sorted(concept for concept, score in row.items() if score <= THRESHOLD_MASTERED)


def build_summary_report(
    mastery_df: pd.DataFrame,
    classified_df: pd.DataFrame
) -> dict:
    """
    Produce a structured per-student summary dict used by the profile builder
    and dashboard.

    Returns:
        {student_id: {"scores": {...}, "labels": {...}, "weak_concepts": [...]}}
    """
    report = {}
    for sid in mastery_df.index:
        scores = mastery_df.loc[sid].to_dict()
        labels = classified_df.loc[sid].to_dict()
        weak   = [c for c, lbl in labels.items() if lbl != LABEL_MASTERED]
        report[sid] = {
            "scores":        scores,
            "labels":        labels,
            "weak_concepts": sorted(weak),
        }
    return report