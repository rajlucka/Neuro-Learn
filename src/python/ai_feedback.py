"""
ai_feedback.py

Generates student-facing feedback and study plans using the Google Gemini API.
Falls back to rule-based messages when no API key is available.

All content targets 3rd-5th grade Math and Science concepts.
"""

import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from config import GEMINI_MODEL, LLM_TIMEOUT_SEC

load_dotenv()

logger = logging.getLogger(__name__)

MODEL = GEMINI_MODEL

CONCEPT_EXPLANATIONS = {
    # Math
    "Multiplication": (
        "Multiplication is a shortcut for adding the same number many times. "
        "For example, 6 x 7 means six groups of seven. "
        "Practice your times tables up to 12 using flashcards or skip-counting out loud."
    ),
    "Division": (
        "Division means splitting a number into equal groups. "
        "It is the opposite of multiplication, so knowing your times tables makes division easier. "
        "If 7 x 8 = 56, then 56 divided by 7 must be 8."
    ),
    "Fractions": (
        "A fraction shows part of a whole. "
        "The bottom number (denominator) tells you how many equal parts the whole is split into. "
        "The top number (numerator) tells you how many of those parts you have."
    ),
    "Geometry": (
        "Geometry is the study of shapes and their measurements. "
        "Area tells you how much space is inside a shape. "
        "For a rectangle, multiply the length by the width to find the area."
    ),
    "Algebra": (
        "In algebra, a letter like x stands for a number you need to find. "
        "To solve for x, do the same thing to both sides of the equals sign "
        "until x is by itself."
    ),
    "Data and Graphs": (
        "Data and graphs help us read and understand information visually. "
        "A bar graph uses bars to compare amounts, a line graph shows change over time, "
        "and a pictograph uses pictures to represent numbers. "
        "Practice by reading graphs carefully and answering questions about what they show."
    ),
    # Science
    "Photosynthesis": (
        "Photosynthesis is the process plants use to make their own food. "
        "Plants take in sunlight, water, and carbon dioxide, and turn them into sugar and oxygen. "
        "Leaves are where most photosynthesis happens because they catch the most sunlight."
    ),
    "States of Matter": (
        "Matter exists as a solid, liquid, or gas. "
        "Solids have a fixed shape and volume. "
        "Liquids have a fixed volume but take the shape of their container. "
        "Gases spread out to fill any space they are in."
    ),
    "Earth Science": (
        "Earth is made of layers: the crust, mantle, outer core, and inner core. "
        "We live on the thin outer layer called the crust. "
        "The mantle below it is the thickest layer and is made of hot, slow-moving rock."
    ),
    "Physical Science": (
        "Physical science covers how matter and energy behave. "
        "When most materials are heated, their particles move faster and spread apart, "
        "so the material expands. When cooled, particles slow down and the material contracts."
    ),
    "Forces and Motion": (
        "A force is a push or pull on an object. "
        "When two forces on an object are equal and opposite, the object does not move. "
        "Gravity pulls objects toward Earth, friction slows objects down, "
        "and applied forces start or change motion."
    ),
    "Life Science": (
        "Life science is the study of living things and how they grow, reproduce, and survive. "
        "All living things need food, water, and air. "
        "Animals and plants have life cycles, and species can change over many generations "
        "through a process called natural selection."
    ),
}

DEFAULT_EXPLANATION = (
    "Review your class notes and examples for this topic. "
    "Try a few practice problems slowly, checking each step before moving on."
)


def generate_feedback(
    student_name: str,
    weak_concepts: list,
    mastery_scores: dict,
    use_llm: bool = True,
    api_key: str = None
) -> str:
    """
    Generate personalized, encouraging feedback for a student.

    Args:
        student_name:   Used to personalize the message.
        weak_concepts:  Concepts below the Mastered threshold.
        mastery_scores: {concept: float} for score context.
        use_llm:        Whether to attempt the Gemini API call.
        api_key:        Gemini key; reads GEMINI_API_KEY env var if None.

    Returns:
        Plain-text feedback string.
    """
    if not weak_concepts:
        return f"Great work, {student_name}! You have mastered all concepts on this exam."

    if use_llm:
        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if key:
            return _llm_call(
                prompt=_feedback_prompt(student_name, weak_concepts, mastery_scores),
                api_key=key,
                fallback=_rule_based_feedback(student_name, weak_concepts, mastery_scores),
            )
        logger.warning("No Gemini API key found -- using rule-based feedback.")

    return _rule_based_feedback(student_name, weak_concepts, mastery_scores)


def generate_study_plan(
    student_name: str,
    weak_concepts: list,
    mastery_scores: dict,
    use_llm: bool = True,
    api_key: str = None
) -> str:
    """
    Generate a week-by-week study plan addressing the student's weak concepts.

    Args:
        student_name:   For personalization.
        weak_concepts:  Ordered list of concepts to address.
        mastery_scores: {concept: float} used to gauge depth needed.
        use_llm:        Whether to attempt the Gemini API call.
        api_key:        Gemini key; reads GEMINI_API_KEY env var if None.
    """
    if not weak_concepts:
        return f"{student_name} has mastered all concepts. No study plan needed."

    if use_llm:
        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if key:
            return _llm_call(
                prompt=_study_plan_prompt(student_name, weak_concepts, mastery_scores),
                api_key=key,
                fallback=_rule_based_study_plan(student_name, weak_concepts),
            )
        logger.warning("No Gemini API key found -- using rule-based study plan.")

    return _rule_based_study_plan(student_name, weak_concepts)


# ---------------------------------------------------------------------------
# Gemini API call
# ---------------------------------------------------------------------------

def _llm_call(prompt: str, api_key: str, fallback: str) -> str:
    """Configure the Gemini client and send a single prompt, return text response."""
    try:
        genai.configure(api_key=api_key)
        model    = genai.GenerativeModel(MODEL)
        response = model.generate_content(prompt)
        return response.text
    except Exception as exc:
        logger.warning("Gemini API call failed (%s). Using rule-based fallback.", exc)
        return fallback


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _feedback_prompt(name: str, weak_concepts: list, scores: dict) -> str:
    score_lines = "\n".join(
        f"  - {c}: {scores.get(c, 0):.0%}" for c in weak_concepts
    )
    return (
        f"You are a friendly, encouraging tutor helping a 3rd-5th grade student.\n"
        f"The student's name is {name}.\n"
        f"They need help with the following Math and Science concepts "
        f"(with their current mastery level):\n"
        f"{score_lines}\n\n"
        f"Write exactly 3 sentences that:\n"
        f"1. Acknowledge something they did well.\n"
        f"2. Tell them which concept to focus on first and why.\n"
        f"3. Give one concrete, simple tip they can try today.\n"
        f"Use simple language a 3rd-5th grader can understand. Plain text only, no markdown."
    )


def _study_plan_prompt(name: str, weak_concepts: list, scores: dict) -> str:
    score_lines = "\n".join(
        f"  - {c}: {scores.get(c, 0):.0%}" for c in weak_concepts
    )
    n_weeks = len(weak_concepts)
    return (
        f"You are a curriculum designer creating a study plan for a 3rd-5th grade student.\n"
        f"Student: {name}\n"
        f"Concepts to study (listed in recommended learning order):\n"
        f"{score_lines}\n\n"
        f"Create exactly {n_weeks} weeks, one week per concept above. Do not add extra weeks.\n"
        f"For each week provide:\n"
        f"  - The concept name as the week title\n"
        f"  - 3 specific, actionable daily tasks (Monday, Tuesday, Wednesday)\n"
        f"  - One suggested practice resource (worksheet, video, or hands-on activity)\n\n"
        f"Keep language simple and encouraging for a 3rd-5th grader. Plain text only, no markdown."
    )


# ---------------------------------------------------------------------------
# Rule-based fallbacks
# ---------------------------------------------------------------------------

def _rule_based_feedback(name: str, weak_concepts: list, scores: dict) -> str:
    lines = [f"Hi {name}, here is your personalized feedback:", ""]
    for concept in weak_concepts:
        score       = scores.get(concept, 0.0)
        tier_note   = "Keep practicing" if score >= 0.40 else "Focus here first"
        explanation = CONCEPT_EXPLANATIONS.get(concept, DEFAULT_EXPLANATION)
        lines.append(f"{concept} ({score:.0%}) -- {tier_note}")
        lines.append(f"  {explanation}")
        lines.append("")
    return "\n".join(lines)


def _rule_based_study_plan(name: str, weak_concepts: list) -> str:
    lines = [f"Study Plan for {name}", "=" * 40, ""]
    for week, concept in enumerate(weak_concepts, start=1):
        explanation = CONCEPT_EXPLANATIONS.get(concept, DEFAULT_EXPLANATION)
        lines.append(f"Week {week}: {concept}")
        lines.append(f"  {explanation}")
        lines.append(f"  Practice: Find 5 problems on this topic and check each answer carefully.")
        lines.append("")
    return "\n".join(lines)