"""
config.py

Central configuration for the Neuro Learn system.

Every tuneable parameter lives here. When moving to Phase 3 or production
this is the only file that needs updating for most system-wide changes.
Modules import from here directly -- never define constants locally.
"""

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

GEMINI_MODEL    = "gemini-2.5-flash-lite"
LLM_MAX_TOKENS  = 1000
LLM_TIMEOUT_SEC = 30

# ---------------------------------------------------------------------------
# Mastery classification thresholds
# ---------------------------------------------------------------------------

THRESHOLD_MASTERED = 0.75
THRESHOLD_WEAK     = 0.40

LABEL_MASTERED = "Mastered"
LABEL_REVIEW   = "Needs Review"
LABEL_WEAK     = "Weak"

# ---------------------------------------------------------------------------
# Diagnostic exam -- questions sampled per difficulty tier per concept
# ---------------------------------------------------------------------------

EXAM_TEMPLATE_WEAK   = {"Easy": 2, "Medium": 1}
EXAM_TEMPLATE_REVIEW = {"Medium": 2, "Hard": 1}

# ---------------------------------------------------------------------------
# Supported subjects, concepts, and grade range
# Phase 2 adds: Data and Graphs (Math), Life Science (Science)
# ---------------------------------------------------------------------------

SUPPORTED_SUBJECTS = ["Math", "Science"]

CONCEPTS_MATH    = [
    "Multiplication", "Division", "Fractions",
    "Geometry", "Algebra", "Data and Graphs"
]
CONCEPTS_SCIENCE = [
    "Photosynthesis", "States of Matter", "Earth Science",
    "Physical Science", "Forces and Motion", "Life Science"
]
ALL_CONCEPTS = CONCEPTS_MATH + CONCEPTS_SCIENCE

GRADE_RANGE = [3, 4, 5]

# ---------------------------------------------------------------------------
# Concept prerequisite graph edges
# Each tuple (A, B) means A must be understood before B.
# Used by concept_graph.py to build the NetworkX dependency graph.
# ---------------------------------------------------------------------------

CONCEPT_PREREQUISITES = [
    ("Multiplication", "Division"),
    ("Multiplication", "Fractions"),
    ("Fractions",      "Algebra"),
    ("Division",       "Algebra"),
    ("Geometry",       "Algebra"),
    ("Multiplication", "Data and Graphs"),
    ("Fractions",      "Data and Graphs"),
    ("Photosynthesis", "Life Science"),
    ("States of Matter", "Physical Science"),
    ("Physical Science", "Forces and Motion"),
    ("Earth Science",  "Life Science"),
]

# ---------------------------------------------------------------------------
# Bayesian Knowledge Tracing default parameters per concept
# p_init    : probability student knows concept before any evidence
# p_transit : probability of learning concept after each practice attempt
# p_slip    : probability of wrong answer despite knowing (careless error)
# p_guess   : probability of correct answer despite not knowing (lucky guess)
# ---------------------------------------------------------------------------

BKT_PARAMS = {
    "Multiplication":  {"p_init": 0.40, "p_transit": 0.15, "p_slip": 0.10, "p_guess": 0.20},
    "Division":        {"p_init": 0.35, "p_transit": 0.14, "p_slip": 0.10, "p_guess": 0.20},
    "Fractions":       {"p_init": 0.30, "p_transit": 0.12, "p_slip": 0.10, "p_guess": 0.20},
    "Geometry":        {"p_init": 0.35, "p_transit": 0.13, "p_slip": 0.10, "p_guess": 0.20},
    "Algebra":         {"p_init": 0.25, "p_transit": 0.10, "p_slip": 0.10, "p_guess": 0.15},
    "Data and Graphs": {"p_init": 0.30, "p_transit": 0.12, "p_slip": 0.10, "p_guess": 0.20},
    "Photosynthesis":  {"p_init": 0.35, "p_transit": 0.13, "p_slip": 0.10, "p_guess": 0.20},
    "States of Matter":{"p_init": 0.40, "p_transit": 0.15, "p_slip": 0.10, "p_guess": 0.20},
    "Earth Science":   {"p_init": 0.35, "p_transit": 0.13, "p_slip": 0.10, "p_guess": 0.20},
    "Physical Science":{"p_init": 0.30, "p_transit": 0.12, "p_slip": 0.10, "p_guess": 0.20},
    "Forces and Motion":{"p_init": 0.25,"p_transit": 0.11, "p_slip": 0.10, "p_guess": 0.20},
    "Life Science":    {"p_init": 0.30, "p_transit": 0.12, "p_slip": 0.10, "p_guess": 0.20},
}

BKT_PARAMS_DEFAULT = {"p_init": 0.30, "p_transit": 0.12, "p_slip": 0.10, "p_guess": 0.20}

# ---------------------------------------------------------------------------
# Student clustering
# ---------------------------------------------------------------------------

N_CLUSTERS = 3

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

TIER_COLORS = {
    LABEL_MASTERED: "#2ecc71",
    LABEL_REVIEW:   "#f0a500",
    LABEL_WEAK:     "#e74c3c",
}

APP_TITLE       = "Neuro Learn"
APP_SUBTITLE    = "Adaptive Learning Diagnostic System"