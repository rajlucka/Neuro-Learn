"""
answer_evaluator.py

Compares student responses against the answer key and produces a binary
correctness matrix:  1 = correct,  0 = incorrect.

This matrix is the single source of truth for all downstream scoring.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def evaluate_answers(
    student_df: pd.DataFrame,
    question_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Produce a binary correctness matrix aligned to the question metadata.

    Only questions present in both the student response file and the question
    metadata are evaluated. Non-question columns such as Name and Grade are
    silently ignored.

    Args:
        student_df:  DataFrame indexed by Student_ID with answer columns Q01..Qn.
        question_df: DataFrame indexed by Question_ID with a Correct_Answer column.

    Returns:
        Integer DataFrame (0 or 1) with the same student index and question columns.
    """
    question_cols = [c for c in student_df.columns if c in question_df.index]
    skipped       = set(student_df.columns) - set(question_cols) - {"Name", "Grade"}

    if skipped:
        logger.warning("Skipping columns with no matching question metadata: %s", skipped)

    answer_key = question_df.loc[question_cols, "Correct_Answer"]

    result = student_df[question_cols].apply(
        lambda col: (
            col.astype(str).str.strip().str.upper()
            == answer_key[col.name].strip().upper()
        ).astype(int)
    )

    logger.info(
        "Evaluated %d students across %d questions. Class mean accuracy: %.1f%%",
        len(result), len(question_cols), result.values.mean() * 100
    )
    return result