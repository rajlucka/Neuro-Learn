"""
misconception_detector.py

Uses the Gemini API to analyze a student's optional free-text explanation
and identify specific conceptual misunderstandings.

This module addresses a fundamental limitation of multiple choice exams:
a correct answer does not guarantee correct understanding, and a wrong
answer does not always reveal why the student is struggling. By asking
students to explain their thinking, the LLM can surface misconceptions
that the score alone would never expose.

Example:
    Student explanation: "Fractions are just two numbers with a line between them"
    Detected misconception: Student lacks understanding that fractions
    represent a part-whole relationship, not just a notation.

The detector returns a structured result containing:
    - A plain-language summary of detected misconceptions
    - The specific concept(s) affected
    - A targeted correction the student can act on immediately

Falls back to a generic message if no API key is available.
"""

import os
import logging

import google.generativeai as genai
from dotenv import load_dotenv

from config import GEMINI_MODEL

load_dotenv()
logger = logging.getLogger(__name__)


from typing import Optional
def detect_misconceptions(student_name:
                           str, explanation: 
                           str, weak_concepts: 
                           list, api_key: 
                           Optional[str] = None) -> str:
    """
    Analyse a student's free-text explanation for conceptual misunderstandings.

    Args:
        student_name:   Used to personalise the response.
        explanation:    The student's own words explaining their thinking.
        weak_concepts:  The concepts identified as weak from their exam score.
                        Provided as context so the LLM focuses its analysis.
        api_key:        Gemini API key. Reads GEMINI_API_KEY env var if None.

    Returns:
        Plain-text misconception analysis written at a 3rd-5th grade level.
        Returns a generic fallback message if the API is unavailable or the
        explanation is empty.
    """
    if not explanation or not explanation.strip():
        return ""

    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        logger.warning("No Gemini API key found -- skipping misconception detection.")
        return _fallback_response(student_name)

    prompt = _build_prompt(student_name, explanation, weak_concepts)

    try:
        genai.configure(api_key=key)
        model    = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        return response.text
    except Exception as exc:
        logger.warning("Misconception detection API call failed (%s).", exc)
        return _fallback_response(student_name)


def _build_prompt(name: str, explanation: str, weak_concepts: list) -> str:
    concepts_str = ", ".join(weak_concepts) if weak_concepts else "general topics"
    return (
        f"You are an expert educator analysing a 3rd-5th grade student's reasoning.\n"
        f"Student name: {name}\n"
        f"Concepts the student struggled with on their exam: {concepts_str}\n\n"
        f"The student wrote this explanation of their thinking:\n"
        f"\"{explanation}\"\n\n"
        f"Analyse the explanation and respond with exactly three short paragraphs:\n"
        f"1. What the student understands correctly (be specific and encouraging).\n"
        f"2. The specific misconception or gap in their reasoning (be precise).\n"
        f"3. One clear, simple correction they can apply immediately.\n\n"
        f"Write at a level a 3rd-5th grader can understand. "
        f"Be encouraging and constructive. Plain text only, no markdown."
    )


def _fallback_response(name: str) -> str:
    return (
        f"Thank you for sharing your thinking, {name}. "
        f"Your explanation shows effort and curiosity. "
        f"Review the feedback and diagnostic questions above to strengthen your understanding."
    )