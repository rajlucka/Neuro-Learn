"""
concept_mapper.py

Translates per-question binary scores into per-concept mastery scores.

When a question spans multiple concepts (e.g. "Fractions|Geometry"), the
student's score is split equally across all listed concepts.  This weighted
accumulation is then normalised against the maximum achievable weight for
each concept to produce mastery values in [0.0, 1.0].
"""

import logging
from collections import defaultdict

import pandas as pd

logger = logging.getLogger(__name__)


def map_scores_to_concepts(
    answer_matrix: pd.DataFrame,
    question_metadata: pd.DataFrame
) -> pd.DataFrame:
    """
    Convert a binary question-score matrix into a concept-score matrix.

    For a question with N concepts, a correct answer contributes 1/N to each
    concept's accumulated score, and an incorrect answer contributes 0.

    Args:
        answer_matrix:     Binary DataFrame (students x questions).
        question_metadata: DataFrame with a parsed 'Topics' list column.

    Returns:
        Raw (un-normalised) accumulated concept scores, shape (students x concepts).
    """
    # Build {question_id: {concept: weight}} for every question in the metadata
    concept_weights = {}
    for q_id, row in question_metadata.iterrows():
        topics = row["Topics"]
        if not topics:
            continue
        weight = 1.0 / len(topics)
        concept_weights[q_id] = {topic: weight for topic in topics}

    all_concepts = sorted({c for cw in concept_weights.values() for c in cw})
    accumulated = defaultdict(lambda: pd.Series(0.0, index=answer_matrix.index))

    for q_id, cw_map in concept_weights.items():
        if q_id not in answer_matrix.columns:
            continue
        q_scores = answer_matrix[q_id].astype(float)
        for concept, weight in cw_map.items():
            accumulated[concept] = accumulated[concept] + q_scores * weight

    df = pd.DataFrame(dict(accumulated), index=answer_matrix.index)[all_concepts]
    logger.info("Mapped scores to %d concepts.", len(all_concepts))
    return df


def calculate_mastery(
    concept_scores: pd.DataFrame,
    question_metadata: pd.DataFrame
) -> pd.DataFrame:
    """
    Normalise raw concept scores into [0.0, 1.0] mastery values.

    mastery = accumulated_correct_weight / maximum_possible_weight

    The maximum possible weight for a concept is the sum of 1/N contributions
    across all questions that include that concept.
    """
    max_weights = _compute_max_weights(question_metadata)

    mastery = concept_scores.copy()
    for concept in mastery.columns:
        divisor = max_weights.get(concept, 1.0)
        mastery[concept] = (mastery[concept] / divisor).clip(0.0, 1.0).round(2)

    return mastery


def _compute_max_weights(question_metadata: pd.DataFrame) -> dict:
    """Return the maximum achievable weight per concept given the question set."""
    max_weights = defaultdict(float)
    for _, row in question_metadata.iterrows():
        topics = row["Topics"]
        if not topics:
            continue
        weight = 1.0 / len(topics)
        for topic in topics:
            max_weights[topic] += weight
    return dict(max_weights)