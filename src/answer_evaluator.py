"""
answer_evaluator.py

Compares student responses against the answer key and produces a binary
correctness matrix:  1 = correct,  0 = incorrect.

This matrix is the single source of truth for all downstream scoring modules.
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

    Only questions that appear in both the student response file and the
    question metadata are evaluated. Any extra columns in student_df (such
    as Name or Grade) are silently ignored.

    Args:
        student_df:   DataFrame indexed by Student_ID; question columns Q01..Qn.
        question_df:  DataFrame indexed by Question_ID with a Correct_Answer column.

    Returns:
        DataFrame of the same shape as the question-column subset of student_df,
        with integer values 0 or 1.
    """
    question_cols = [c for c in student_df.columns if c in question_df.index]
    skipped = set(student_df.columns) - set(question_cols) - {"Name", "Grade"}

    if skipped:
        logger.warning("Skipping columns with no matching question metadata: %s", skipped)

    answer_key = question_df.loc[question_cols, "Correct_Answer"]

    # Normalize both sides to uppercase stripped strings before comparing
    result = student_df[question_cols].apply(
        lambda col: (col.astype(str).str.strip().str.upper()
                     == answer_key[col.name].strip().upper()).astype(int)
    )

    mean_acc = result.values.mean()
    logger.info(
        "Evaluated %d students across %d questions. Class mean accuracy: %.1f%%",
        len(result), len(question_cols), mean_acc * 100
    )
    return result