"""
main.py

Entry point for Phase 1 of the Adaptive Learning Diagnostic System.
Runs the full analysis pipeline and prints a structured report to stdout.

Usage:
    python main.py                   # report for all students
    python main.py --student S01     # report for one student
    python main.py --no-llm          # skip Claude API, use rule-based outputs
"""

import sys
import argparse
import logging

sys.path.insert(0, "src")

from data_loader               import load_student_answers, load_question_metadata, load_question_bank
from answer_evaluator          import evaluate_answers
from concept_mapper            import map_scores_to_concepts, calculate_mastery
from weakness_detector         import classify_mastery, build_summary_report
from diagnostic_exam_generator import generate_diagnostic_exam, format_exam_report
from ai_feedback               import generate_feedback, generate_study_plan

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DIVIDER      = "=" * 60
THIN_DIVIDER = "-" * 60


def run(target_student: str = None, use_llm: bool = True) -> None:
    print(f"\n{DIVIDER}")
    print("  ADAPTIVE LEARNING DIAGNOSTIC SYSTEM -- PHASE 1")
    print(DIVIDER)

    
    # Step 1: Load data
    
    print("\n[1/6] Loading data...")
    student_df  = load_student_answers()
    question_df = load_question_metadata()
    qbank_df    = load_question_bank()

    
    # Step 2: Evaluate answers
    
    print("[2/6] Evaluating answers...")
    answer_matrix = evaluate_answers(student_df, question_df)

    
    # Step 3: Map to concepts and compute mastery
    
    print("[3/6] Computing concept mastery...")
    concept_scores = map_scores_to_concepts(answer_matrix, question_df)
    mastery_df     = calculate_mastery(concept_scores, question_df)

    print("\nMastery Matrix:")
    print(mastery_df.to_string())

    
    # Step 4: Detect weaknesses
    
    print("\n[4/6] Detecting weaknesses...")
    classified_df = classify_mastery(mastery_df)
    report        = build_summary_report(mastery_df, classified_df)

    
    # Steps 5 and 6: Per-student diagnostic + feedback
    
    students = [target_student] if target_student else list(report.keys())

    for sid in students:
        if sid not in report:
            print(f"\nStudent '{sid}' not found.")
            continue

        data    = report[sid]
        scores  = data["scores"]
        labels  = data["labels"]
        weak    = data["weak_concepts"]
        name    = student_df.loc[sid, "Name"] if "Name" in student_df.columns else sid
        grade   = student_df.loc[sid, "Grade"] if "Grade" in student_df.columns else "?"
        overall = sum(scores.values()) / len(scores)

        print(f"\n{DIVIDER}")
        print(f"  Student: {name} ({sid})  |  Grade {grade}  |  Overall: {overall:.0%}")
        print(THIN_DIVIDER)

        for concept, score in sorted(scores.items()):
            bar   = "#" * int(score * 10) + "." * (10 - int(score * 10))
            label = labels.get(concept, "?")
            print(f"  {concept:<25} [{bar}] {score:.0%}  ({label})")

        # -- Step 5: Diagnostic exam for students with weak concepts
        print(f"\n[5/6] Diagnostic exam for {name}...")
        if weak:
            exam = generate_diagnostic_exam(
                weak_concepts=weak,
                mastery_scores=scores,
                question_bank=qbank_df,
            )
            print(format_exam_report(exam, qbank_df))
        else:
            print(f"  No diagnostic needed -- {name} has mastered all concepts.")

        # -- Step 6: AI feedback and study plan
        print(f"\n[6/6] Feedback and study plan for {name}...")
        feedback = generate_feedback(
            student_name=name,
            weak_concepts=weak,
            mastery_scores=scores,
            use_llm=use_llm,
        )
        print(feedback)

        plan = generate_study_plan(
            student_name=name,
            weak_concepts=weak,
            mastery_scores=scores,
            use_llm=use_llm,
        )
        print(plan)

    print(f"\n{DIVIDER}")
    print("Pipeline complete.")
    print("Launch the dashboard with:  streamlit run dashboard/app.py")
    print(DIVIDER)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adaptive Learning Diagnostic System")
    parser.add_argument("--student", type=str, default=None, help="Run for a single Student_ID")
    parser.add_argument("--no-llm", action="store_true",    help="Use rule-based outputs only")
    args = parser.parse_args()

    run(target_student=args.student, use_llm=not args.no_llm)