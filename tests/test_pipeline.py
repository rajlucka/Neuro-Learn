"""
test_pipeline.py

Developer and demo script for the Neuro Learn diagnostic pipeline.
Runs a chosen mock student from student_answers.csv through every module
and prints the full output without requiring any user interaction.

This script is intentionally separate from main.py so that the production
entry point stays clean. Use this for testing, demos, and CI verification.

Usage:
    python test_pipeline.py               # runs S01 by default
    python test_pipeline.py --student S06 # runs a specific student
    python test_pipeline.py --all         # runs all mock students
    python test_pipeline.py --no-llm      # skips Gemini API
"""

import sys
import argparse
import logging
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, "src/python")

from data_loader               import load_student_answers, load_question_metadata, load_question_bank
from answer_evaluator          import evaluate_answers
from concept_mapper            import map_scores_to_concepts, calculate_mastery
from weakness_detector         import classify_mastery, build_summary_report
from diagnostic_exam_generator import generate_diagnostic_exam, format_exam_report
from ai_feedback               import generate_feedback, generate_study_plan

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

DIVIDER      = "=" * 55
THIN_DIVIDER = "-" * 40


def run_mock_student(sid: str, report: dict, student_df, qbank_df, use_llm: bool) -> None:
    """Run and print the full diagnostic output for a single mock student."""

    if sid not in report:
        print(f"Student '{sid}' not found in mock data.")
        return

    data    = report[sid]
    scores  = data["scores"]
    labels  = data["labels"]
    weak    = data["weak_concepts"]
    name    = student_df.loc[sid, "Name"]  if "Name"  in student_df.columns else sid
    grade   = student_df.loc[sid, "Grade"] if "Grade" in student_df.columns else "?"
    overall = sum(scores.values()) / len(scores)

    print(f"\n{DIVIDER}")
    print(f"  MOCK STUDENT: {name} ({sid})  |  Grade {grade}  |  Overall: {overall:.0%}")
    print(DIVIDER)

    # Mastery profile
    for concept, score in sorted(scores.items()):
        bar   = "#" * int(score * 10) + "." * (10 - int(score * 10))
        label = labels.get(concept, "?")
        print(f"  {concept:<25} [{bar}] {score:.0%}  ({label})")

    # Diagnostic exam
    print(f"\n  Diagnostic Exam")
    print(THIN_DIVIDER)
    if weak:
        exam = generate_diagnostic_exam(
            weak_concepts=weak,
            mastery_scores=scores,
            question_bank=qbank_df,
        )
        print(format_exam_report(exam, qbank_df))
    else:
        print(f"  No diagnostic needed -- {name} has mastered all concepts.")

    # AI feedback
    print(f"\n  Feedback")
    print(THIN_DIVIDER)
    feedback = generate_feedback(
        student_name=name,
        weak_concepts=weak,
        mastery_scores=scores,
        use_llm=use_llm,
    )
    print(feedback)

    # Study plan
    print(f"\n  Study Plan")
    print(THIN_DIVIDER)
    plan = generate_study_plan(
        student_name=name,
        weak_concepts=weak,
        mastery_scores=scores,
        use_llm=use_llm,
    )
    print(plan)


def main():
    parser = argparse.ArgumentParser(description="Neuro Learn -- Mock Pipeline Tester")
    parser.add_argument("--student", type=str, default="S01", help="Student_ID to test (default: S01)")
    parser.add_argument("--all",     action="store_true",     help="Run all mock students")
    parser.add_argument("--no-llm",  action="store_true",     help="Skip Gemini API")
    args = parser.parse_args()

    print(f"\n{DIVIDER}")
    print("  NEURO LEARN -- PIPELINE TEST")
    print(DIVIDER)

    # Load and process all data once
    student_df  = load_student_answers()
    question_df = load_question_metadata()
    qbank_df    = load_question_bank()

    answer_matrix  = evaluate_answers(student_df, question_df)
    concept_scores = map_scores_to_concepts(answer_matrix, question_df)
    mastery_df     = calculate_mastery(concept_scores, question_df)
    classified_df  = classify_mastery(mastery_df)
    report         = build_summary_report(mastery_df, classified_df)

    use_llm = not args.no_llm

    if args.all:
        for sid in report:
            run_mock_student(sid, report, student_df, qbank_df, use_llm)
    else:
        run_mock_student(args.student, report, student_df, qbank_df, use_llm)

    print(f"\n{DIVIDER}")
    print("  Test complete.")
    print(DIVIDER)


if __name__ == "__main__":
    main()