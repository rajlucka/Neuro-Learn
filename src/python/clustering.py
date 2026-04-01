"""
clustering.py

Groups students by learning patterns using K-Means clustering applied
to their concept mastery vectors.

Clustering surfaces student archetypes that are not visible from
individual profiles -- for example, a group that is consistently strong
in Science but weak in Math, or a group with broad foundational gaps.
This information is used in the dashboard to give instructors a
class-level view and to tailor study plan tone in Phase 3.

K-Means is appropriate here because:
    - Mastery vectors are continuous and numeric
    - We expect a small number of meaningful archetypes (3 by default)
    - The feature space is modest (12 concepts)

Features are standardised before clustering so no single high-variance
concept dominates the distance calculations.
"""

import logging
import pandas as pd
from sklearn.cluster        import KMeans
from sklearn.preprocessing  import StandardScaler

from config import N_CLUSTERS

logger = logging.getLogger(__name__)


def cluster_students(
    mastery_df: pd.DataFrame,
    n_clusters: int = None,
    seed: int = 42
) -> tuple:
    """
    Apply K-Means clustering to student mastery vectors.

    Args:
        mastery_df: DataFrame of mastery scores (students x concepts).
        n_clusters: Number of clusters. Defaults to config.N_CLUSTERS.
        seed:       Random seed for reproducibility.

    Returns:
        Tuple of:
            cluster_labels  -- pd.Series {student_id: cluster_int}
            cluster_summary -- DataFrame of mean mastery per cluster
    """
    k = n_clusters or N_CLUSTERS

    # Reduce cluster count if we have fewer students than requested clusters
    if len(mastery_df) < k:
        logger.warning(
            "Only %d students available for %d clusters. Reducing to %d.",
            len(mastery_df), k, len(mastery_df)
        )
        k = len(mastery_df)

    scaler = StandardScaler()
    X      = scaler.fit_transform(mastery_df.values)

    kmeans = KMeans(n_clusters=k, random_state=seed, n_init=10)
    labels = kmeans.fit_predict(X)

    cluster_series = pd.Series(labels, index=mastery_df.index, name="Cluster")

    mastery_with_cluster          = mastery_df.copy()
    mastery_with_cluster["Cluster"] = labels
    cluster_summary               = (
        mastery_with_cluster
        .groupby("Cluster")
        .mean()
        .round(2)
    )

    logger.info("Clustered %d students into %d groups.", len(mastery_df), k)
    return cluster_series, cluster_summary


def describe_clusters(cluster_summary: pd.DataFrame) -> dict:
    """
    Generate a human-readable description for each cluster based on
    which concepts have the lowest and highest average mastery.

    Returns:
        {cluster_id: description_string}
    """
    descriptions = {}
    for cluster_id, row in cluster_summary.iterrows():
        mean_score  = row.mean()
        weakest     = row.idxmin()
        strongest   = row.idxmax()

        if mean_score > 0.75:
            desc = f"Strong across all concepts (best: {strongest})"
        elif mean_score < 0.40:
            desc = f"Broadly weak -- biggest gap in {weakest}"
        else:
            desc = f"Mixed mastery -- primary gap in {weakest}, strongest in {strongest}"

        descriptions[int(cluster_id)] = desc

    return descriptions


def get_cluster_for_student(
    student_id: str,
    cluster_labels: pd.Series
) -> int:
    """Return the cluster ID assigned to a specific student."""
    if student_id not in cluster_labels.index:
        raise ValueError(f"Student '{student_id}' not found in cluster labels.")
    return int(cluster_labels[student_id])