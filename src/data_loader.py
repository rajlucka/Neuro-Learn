"""
data_loader.py

Handles loading and validation of all CSV datasets.
Each function returns a clean, validated DataFrame ready for downstream modules.
"""

import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

DIFFICULTY_ORDER = {"Easy": 1, "Medium": 2, "Hard": 3}


def _build_path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


def load_student_answers(filepath: str = None) -> pd.DataFrame:
    """
    Load student exam responses.

    Expects columns: Student_ID, Name, Grade, Q01..Q15
    Returns a DataFrame with Student_ID as the index.
    """
    path = filepath or _build_path("student_answers.csv")
    df = pd.read_csv(path)

    required = {"Student_ID", "Name", "Grade"}
    _assert_columns(df, required, "student_answers.csv")

    df = df.dropna(subset=["Student_ID"])
    df = df.set_index("Student_ID")

    logger.info("Loaded %d student records.", len(df))
    return df


def load_question_metadata(filepath: str = None) -> pd.DataFrame:
    """
    Load question definitions including the answer key, topics, and difficulty.

    Topics are stored as pipe-separated strings (e.g. 'Fractions|Geometry')
    and are parsed into Python lists on load.
    """
    path = filepath or _build_path("questions.csv")
    df = pd.read_csv(path)

    required = {"Question_ID", "Correct_Answer", "Topics", "Difficulty", "Grade", "Subject"}
    _assert_columns(df, required, "questions.csv")

    df = df.set_index("Question_ID")
    df["Topics"] = df["Topics"].fillna("").apply(_parse_topics)

    # Attach a numeric sort key so questions can be ordered by difficulty
    df["Difficulty_Rank"] = df["Difficulty"].map(DIFFICULTY_ORDER).fillna(2)

    logger.info("Loaded metadata for %d questions.", len(df))
    return df


def load_question_bank(filepath: str = None) -> pd.DataFrame:
    """
    Load the question bank used when generating adaptive diagnostic exams.

    The bank is separate from the original exam so diagnostic questions
    are fresh and not repeated from the assessment the student already took.
    """
    path = filepath or _build_path("question_bank.csv")
    df = pd.read_csv(path)

    required = {"Question_ID", "Topic", "Difficulty", "Grade", "Subject"}
    _assert_columns(df, required, "question_bank.csv")

    df = df.set_index("Question_ID")
    df["Difficulty_Rank"] = df["Difficulty"].map(DIFFICULTY_ORDER).fillna(2)

    logger.info("Loaded %d question bank entries.", len(df))
    return df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_topics(raw: str) -> list:
    """Split a pipe-separated topic string into a cleaned list."""
    return [t.strip() for t in raw.split("|") if t.strip()]


def _assert_columns(df: pd.DataFrame, required: set, filename: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{filename} is missing required columns: {missing}")