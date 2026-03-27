"""
config.py

Central configuration for the Neuro Learn system.

All tuneable parameters live here so that changing thresholds, models,
or question counts never requires hunting through multiple modules.
When moving to Phase 2 or production, this file is the only place
that needs updating for most system-wide changes.
"""

# ---------------------------------------------------------------------------
# LLM settings
# ---------------------------------------------------------------------------

GEMINI_MODEL      = "gemini-2.5-flash-lite"
LLM_MAX_TOKENS    = 1000
LLM_TIMEOUT_SEC   = 30

# ---------------------------------------------------------------------------
# Mastery classification thresholds
# ---------------------------------------------------------------------------

THRESHOLD_MASTERED = 0.75   # above this -> Mastered
THRESHOLD_WEAK     = 0.40   # below this -> Weak, between -> Needs Review

LABEL_MASTERED = "Mastered"
LABEL_REVIEW   = "Needs Review"
LABEL_WEAK     = "Weak"

# ---------------------------------------------------------------------------
# Diagnostic exam question counts per mastery tier
# ---------------------------------------------------------------------------

# {difficulty: number of questions to sample}
EXAM_TEMPLATE_WEAK   = {"Easy": 2, "Medium": 1}
EXAM_TEMPLATE_REVIEW = {"Medium": 2, "Hard": 1}

# ---------------------------------------------------------------------------
# Supported subjects and grade range
# ---------------------------------------------------------------------------

SUPPORTED_SUBJECTS = ["Math", "Science"]
GRADE_RANGE        = [3, 4, 5]

# ---------------------------------------------------------------------------
# Dashboard settings
# ---------------------------------------------------------------------------

TIER_COLORS = {
    LABEL_MASTERED: "#2ecc71",
    LABEL_REVIEW:   "#f0a500",
    LABEL_WEAK:     "#e74c3c",
}