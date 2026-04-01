"""
knowledge_tracing.py

Implements 4-parameter Bayesian Knowledge Tracing (BKT).

BKT models student knowledge as a Hidden Markov Model where:
    - Hidden state : does the student actually know this concept?
    - Observable   : did the student answer correctly or incorrectly?

The four parameters per concept are:
    p_init    : P(student knows concept before seeing any questions)
    p_transit : P(student learns concept after each practice opportunity)
    p_slip    : P(wrong answer despite knowing -- careless mistake)
    p_guess   : P(correct answer despite not knowing -- lucky guess)

After each observed answer the model updates P(know) using Bayes theorem,
then applies the transit probability to model the chance of learning.

BKT produces a richer mastery estimate than simple scoring because it
accounts for the reliability of each observation (slips and guesses),
and models knowledge as a probability that grows with practice.

All default parameters are defined in config.BKT_PARAMS so they can be
tuned per concept without touching this module.
"""

import logging
from dataclasses import dataclass, field

from config import BKT_PARAMS, BKT_PARAMS_DEFAULT

logger = logging.getLogger(__name__)


@dataclass
class BKTState:
    """Tracks the current BKT probability of knowledge for one student-concept pair."""
    concept:  str
    p_know:   float
    history:  list = field(default_factory=list)   # sequence of 1/0 observations

    def __str__(self) -> str:
        return f"BKT({self.concept}): P(know)={self.p_know:.3f}  history={self.history}"


class BayesianKnowledgeTracer:
    """
    Runs the standard BKT forward pass for one or more concepts.

    Usage:
        tracer = BayesianKnowledgeTracer()
        state  = tracer.initialise("Fractions")
        state  = tracer.update(state, observations=[1, 0, 1])
        print(state.p_know)
    """

    def __init__(self, params: dict = None):
        self.params = params or BKT_PARAMS

    def initialise(self, concept: str) -> BKTState:
        """Create an initial BKT state for a concept using its prior probability."""
        p = self._get_params(concept)
        return BKTState(concept=concept, p_know=p["p_init"])

    def update(self, state: BKTState, observations: list) -> BKTState:
        """
        Run the BKT forward pass over a sequence of binary observations.

        For each observation the update has two steps:
            1. Bayes update  -- revise P(know) given whether answer was correct.
            2. Transition    -- apply learning probability to model knowledge gain.

        Args:
            state:        Current BKTState for this concept.
            observations: List of 1 (correct) or 0 (incorrect) responses.

        Returns:
            New BKTState with updated p_know and appended history.
        """
        p      = self._get_params(state.concept)
        p_know = state.p_know

        for obs in observations:
            # Step 1 -- Bayes update
            # Likelihood of this observation given knowing vs not knowing
            if obs == 1:
                p_obs_given_know   = 1.0 - p["p_slip"]
                p_obs_given_unknow = p["p_guess"]
            else:
                p_obs_given_know   = p["p_slip"]
                p_obs_given_unknow = 1.0 - p["p_guess"]

            numerator   = p_obs_given_know * p_know
            denominator = numerator + p_obs_given_unknow * (1.0 - p_know)
            p_know_posterior = numerator / denominator if denominator > 0 else p_know

            # Step 2 -- Transition (learning opportunity)
            p_know = p_know_posterior + (1.0 - p_know_posterior) * p["p_transit"]

        return BKTState(
            concept=state.concept,
            p_know=round(p_know, 4),
            history=state.history + list(observations)
        )

    def trace_student(self, concept_observations: dict) -> dict:
        """
        Run BKT for all concepts for a single student.

        Args:
            concept_observations: {concept: [1, 0, 1, ...]} response sequences.

        Returns:
            {concept: BKTState} after tracing all observations.
        """
        states = {}
        for concept, obs in concept_observations.items():
            state          = self.initialise(concept)
            state          = self.update(state, obs)
            states[concept] = state
        return states

    def get_mastery_estimates(self, states: dict) -> dict:
        """
        Extract {concept: p_know} from a dict of traced BKTStates.
        This is the BKT-based mastery score used in place of simple scoring.
        """
        return {concept: s.p_know for concept, s in states.items()}

    def _get_params(self, concept: str) -> dict:
        return self.params.get(concept, BKT_PARAMS_DEFAULT)


def build_concept_observations(
    answer_matrix,
    question_metadata,
    student_id: str
) -> dict:
    """
    Extract per-concept observation sequences for a single student from
    the binary answer matrix and question metadata.

    For each concept, collects the 0/1 answer for every question that
    covers that concept, in question order.

    Args:
        answer_matrix:     Binary correctness DataFrame (students x questions).
        question_metadata: DataFrame with parsed Topics list column.
        student_id:        The student to extract observations for.

    Returns:
        {concept: [1, 0, 1, ...]} observation sequences.
    """
    if student_id not in answer_matrix.index:
        raise ValueError(f"Student '{student_id}' not found in answer matrix.")

    concept_obs = {}
    student_row = answer_matrix.loc[student_id]

    for q_id, row in question_metadata.iterrows():
        if q_id not in student_row.index:
            continue
        obs = int(student_row[q_id])
        for concept in row["Topics"]:
            concept_obs.setdefault(concept, []).append(obs)

    return concept_obs