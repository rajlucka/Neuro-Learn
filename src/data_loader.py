"""
data_loader.py

Responsible for loading and validating all CSV datasets used by the pipeline.
Each function returns a clean, validated DataFrame ready for downstream use.
All file paths default to the data/ directory relative to this file.
"""

import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_student_answers(filepath: str = None) -> pd.DataFrame:
    """
    Load student exam responses from CSV.

    Expected columns: Student_ID, Name, Grade, Q01..Qn
    Returns a DataFrame indexed by Student_ID.
    """
    path = filepath or os.path.join(DATA_DIR, "student_answers.csv")
    df   = pd.read_csv(path)

    _validate_columns(df, {"Student_ID", "Name", "Grade"}, "student_answers.csv")

    df = df.dropna(subset=["Student_ID"]).set_index("Student_ID")
    logger.info("Loaded %d student records.", len(df))
    return df


def load_question_metadata(filepath: str = None) -> pd.DataFrame:
    """
    Load question definitions including the answer key, topics, and difficulty.

    Topics are stored as pipe-separated strings (e.g. 'Fractions|Geometry')
    and are parsed into Python lists on load so downstream modules never
    need to handle raw strings.
    """
    path = filepath or os.path.join(DATA_DIR, "questions.csv")
    df   = pd.read_csv(path)

    _validate_columns(
        df,
        {"Question_ID", "Correct_Answer", "Topics", "Difficulty", "Grade", "Subject"},
        "questions.csv"
    )

    df = df.set_index("Question_ID")
    df["Topics"] = df["Topics"].fillna("").apply(_parse_topics)
    logger.info("Loaded metadata for %d questions.", len(df))
    return df


def load_question_bank(filepath: str = None) -> pd.DataFrame:
    """
    Load the question bank used when generating adaptive diagnostic exams.

    The bank is intentionally separate from the main exam so students
    never see repeated questions in their diagnostic.
    """
    path = filepath or os.path.join(DATA_DIR, "question_bank.csv")
    df   = pd.read_csv(path)

    _validate_columns(
        df,
        {"Question_ID", "Topic", "Difficulty", "Grade", "Subject"},
        "question_bank.csv"
    )

    df = df.set_index("Question_ID")
    logger.info("Loaded %d question bank entries.", len(df))
    return df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_topics(raw: str) -> list:
    """Split a pipe-separated topic string into a cleaned list."""
    return [t.strip() for t in raw.split("|") if t.strip()]


def _validate_columns(df: pd.DataFrame, required: set, filename: str) -> None:
    """Raise a clear error if any required columns are missing."""
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{filename} is missing required columns: {missing}")