"""
concept_graph.py

Builds a directed prerequisite graph of concepts using NetworkX.
An edge A -> B means concept A must be understood before concept B.

The graph enables two key Phase 2 features:
    1. Root cause detection  -- if a student is weak in Algebra, the graph
       reveals they likely also need Fractions and Division first.
    2. Learning order        -- topological sort ensures the study plan
       addresses foundational concepts before advanced ones.

Prerequisites are defined centrally in config.py as CONCEPT_PREREQUISITES
so the graph structure can be updated without touching this module.
"""

import logging
import networkx as nx

from config import CONCEPT_PREREQUISITES

logger = logging.getLogger(__name__)


def build_concept_graph() -> nx.DiGraph:
    """
    Construct a directed concept dependency graph from the prerequisites
    defined in config.CONCEPT_PREREQUISITES.

    Returns:
        nx.DiGraph where edge A -> B means A is a prerequisite for B.
    """
    G = nx.DiGraph()
    G.add_edges_from(CONCEPT_PREREQUISITES)
    logger.info(
        "Concept graph built: %d nodes, %d edges.",
        G.number_of_nodes(), G.number_of_edges()
    )
    return G


def detect_root_causes(
    concept_scores: dict,
    graph: nx.DiGraph,
    weak_threshold: float = 0.40
) -> list:
    """
    Identify root-cause weak concepts -- the foundational gaps that should
    be addressed first before tackling more advanced weak concepts.

    A concept is a root cause if it is weak AND none of its prerequisites
    are also weak. These are the concepts with no deeper dependency to fix.

    Args:
        concept_scores: {concept: mastery_float} for one student.
        graph:          The concept dependency graph.
        weak_threshold: Mastery score below which a concept is considered weak.

    Returns:
        Sorted list of root-cause concept names.
    """
    weak_set    = {c for c, s in concept_scores.items() if s < weak_threshold}
    root_causes = []

    for concept in weak_set:
        if concept not in graph:
            # Concept has no prerequisites in the graph -- treat as a root
            root_causes.append(concept)
            continue

        weak_prerequisites = set(graph.predecessors(concept)) & weak_set
        if not weak_prerequisites:
            root_causes.append(concept)

    return sorted(root_causes)


def get_learning_order(
    weak_concepts: list,
    graph: nx.DiGraph
) -> list:
    """
    Return a topologically sorted learning order for a set of weak concepts.
    Prerequisites appear before the concepts that depend on them.

    Concepts not present in the graph are appended at the end in their
    original order since no dependency information is available for them.

    Args:
        weak_concepts: Concepts to order.
        graph:         Full concept dependency graph.

    Returns:
        Ordered list of concepts, prerequisite-first.
    """
    in_graph  = [c for c in weak_concepts if c in graph]
    not_graph = [c for c in weak_concepts if c not in graph]

    subgraph = graph.subgraph(in_graph)
    try:
        ordered = list(nx.topological_sort(subgraph))
    except nx.NetworkXUnfeasible:
        logger.warning("Cycle detected in concept subgraph -- using original order.")
        ordered = in_graph

    return ordered + not_graph