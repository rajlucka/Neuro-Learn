"""
dashboard/app.py

Student-facing Streamlit dashboard for Neuro Learn Phase 1.

Two-page flow:
    Page 1 -- Exam: student enters their name, selects grade, answers all
              20 questions, and submits. Answers are appended to
              student_answers.csv with an auto-generated Student_ID.

    Page 2 -- Results: full diagnostic report showing mastery bars,
              weakness summary, adaptive diagnostic exam, AI feedback,
              and a personalized study plan.

Run with:
    streamlit run dashboard/app.py
"""

import sys
import os
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import plotly.express as px

from data_loader               import load_student_answers, load_question_metadata, load_question_bank
from answer_evaluator          import evaluate_answers
from concept_mapper            import map_scores_to_concepts, calculate_mastery
from weakness_detector         import classify_mastery, build_summary_report
from diagnostic_exam_generator import generate_diagnostic_exam, format_exam_report
from ai_feedback               import generate_feedback, generate_study_plan
from config                    import TIER_COLORS, GRADE_RANGE

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Neuro Learn", layout="centered")

DATA_DIR         = os.path.join(os.path.dirname(__file__), "..", "data")
ANSWERS_CSV_PATH = os.path.join(DATA_DIR, "student_answers.csv")

# ---------------------------------------------------------------------------
# Session state initialisation
# Streamlit reruns the entire script on every interaction, so all state
# that needs to persist across interactions is stored in st.session_state.
# ---------------------------------------------------------------------------

if "page"         not in st.session_state:
    st.session_state.page = "exam"       # "exam" | "results"

if "answers"      not in st.session_state:
    st.session_state.answers = {}        # {question_id: selected_option}

if "student_sid"  not in st.session_state:
    st.session_state.student_sid = None  # assigned on submission

if "student_name" not in st.session_state:
    st.session_state.student_name = ""

if "student_grade" not in st.session_state:
    st.session_state.student_grade = GRADE_RANGE[0]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_data
def load_questions() -> pd.DataFrame:
    return load_question_metadata()

@st.cache_data
def load_bank() -> pd.DataFrame:
    return load_question_bank()


def generate_student_id() -> str:
    """
    Read the existing student_answers.csv and return the next Student_ID
    in the sequence (e.g. if the last is S10, return S11).
    """
    try:
        existing = pd.read_csv(ANSWERS_CSV_PATH)
        ids = existing["Student_ID"].dropna().tolist()
        # Extract numeric suffixes and find the highest
        nums = []
        for sid in ids:
            try:
                nums.append(int(str(sid).replace("S", "")))
            except ValueError:
                pass
        next_num = max(nums) + 1 if nums else 1
        return f"S{next_num:02d}"
    except FileNotFoundError:
        return "S01"


def append_student_answers(sid: str, name: str, grade: int, answers: dict) -> None:
    """
    Append a new student row to student_answers.csv.
    The answers dict maps Question_ID to the selected option letter.
    """
    existing   = pd.read_csv(ANSWERS_CSV_PATH)
    q_cols     = [c for c in existing.columns if c.startswith("Q")]
    new_row    = {"Student_ID": sid, "Name": name, "Grade": grade}

    for q in q_cols:
        new_row[q] = answers.get(q, "")

    new_df   = pd.DataFrame([new_row])
    updated  = pd.concat([existing, new_df], ignore_index=True)
    updated.to_csv(ANSWERS_CSV_PATH, index=False)


def run_pipeline_for_student(sid: str) -> tuple:
    """
    Run the full diagnostic pipeline for a single student and return
    their mastery scores, labels, weak concepts, and the question bank.
    Results are not cached because a new student may have just been added.
    """
    student_df  = load_student_answers()
    question_df = load_questions()
    qbank_df    = load_bank()

    answer_mat    = evaluate_answers(student_df, question_df)
    concept_sc    = map_scores_to_concepts(answer_mat, question_df)
    mastery_df    = calculate_mastery(concept_sc, question_df)
    classified_df = classify_mastery(mastery_df)
    report        = build_summary_report(mastery_df, classified_df)

    data = report.get(sid, {})
    return data.get("scores", {}), data.get("labels", {}), data.get("weak_concepts", []), qbank_df


# ---------------------------------------------------------------------------
# PAGE 1 -- EXAM
# ---------------------------------------------------------------------------

def render_exam_page():
    st.title("Neuro Learn")
    st.caption("Adaptive Learning Diagnostic System")
    st.divider()

    # Student info
    st.subheader("Your Information")
    name  = st.text_input("Full name", placeholder="Enter your name")
    grade = st.selectbox("Grade", GRADE_RANGE, format_func=lambda g: f"Grade {g}")

    st.divider()
    st.subheader("Exam")
    st.caption("Answer every question. Select the best answer for each one.")

    question_df = load_questions()
    answers     = {}
    all_answered = True

    # Group questions by grade so they appear in order 3 -> 4 -> 5
    for g in GRADE_RANGE:
        grade_qs = question_df[question_df["Grade"] == g]
        if grade_qs.empty:
            continue

        st.markdown(f"**Grade {g} Questions**")

        for q_id, row in grade_qs.iterrows():
            options = {
                "A": row.get("Option_A", ""),
                "B": row.get("Option_B", ""),
                "C": row.get("Option_C", ""),
                "D": row.get("Option_D", ""),
            }
            # Build display labels as "A) option text"
            option_labels = [f"{k}) {v}" for k, v in options.items()]

            chosen = st.radio(
                label=f"{q_id}: {row['Question_Text']}",
                options=option_labels,
                index=None,
                key=f"q_{q_id}",
            )

            if chosen is None:
                all_answered = False
            else:
                # Store only the letter (A/B/C/D)
                answers[q_id] = chosen[0]

        st.divider()

    # Submit button
    if st.button("Submit Exam", type="primary", use_container_width=True):
        if not name.strip():
            st.error("Please enter your name before submitting.")
        elif not all_answered:
            st.error("Please answer all questions before submitting.")
        else:
            sid = generate_student_id()
            append_student_answers(sid, name.strip(), grade, answers)

            st.session_state.student_sid   = sid
            st.session_state.student_name  = name.strip()
            st.session_state.student_grade = grade
            st.session_state.answers       = answers
            st.session_state.page          = "results"
            st.rerun()


# ---------------------------------------------------------------------------
# PAGE 2 -- RESULTS
# ---------------------------------------------------------------------------

def render_results_page():
    sid   = st.session_state.student_sid
    name  = st.session_state.student_name
    grade = st.session_state.student_grade

    st.title(f"Your Results, {name}")
    st.caption(f"Student ID: {sid}  |  Grade {grade}")
    st.divider()

    with st.spinner("Analysing your results..."):
        scores, labels, weak, qbank_df = run_pipeline_for_student(sid)

    if not scores:
        st.error("Could not load results. Please try again.")
        return

    overall    = sum(scores.values()) / len(scores)
    n_mastered = sum(1 for l in labels.values() if l == "Mastered")

    # Header metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Overall Score",     f"{overall:.0%}")
    col2.metric("Concepts Mastered", f"{n_mastered} / {len(scores)}")
    col3.metric("Needs Work",        f"{len(weak)} concept(s)")

    st.divider()

    # Mastery bar chart
    st.subheader("Concept Mastery")
    chart_df = (
        pd.DataFrame({
            "Concept": list(scores.keys()),
            "Mastery": list(scores.values()),
            "Status":  list(labels.values()),
        })
        .sort_values("Mastery", ascending=True)
    )

    fig = px.bar(
        chart_df,
        x="Mastery",
        y="Concept",
        orientation="h",
        color="Status",
        color_discrete_map=TIER_COLORS,
        range_x=[0, 1],
        height=max(320, len(scores) * 50),
        text="Mastery",
    )
    fig.update_traces(texttemplate="%{text:.0%}", textposition="outside")
    fig.add_vline(x=0.75, line_dash="dash", line_color="#2ecc71",
                  annotation_text="Mastered", annotation_position="top right")
    fig.add_vline(x=0.40, line_dash="dash", line_color="#e74c3c",
                  annotation_text="Weak threshold", annotation_position="bottom right")
    fig.update_layout(xaxis_title="Mastery Score", yaxis_title="", showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

    # Weakness table
    st.divider()
    st.subheader("Concepts Needing Attention")
    if weak:
        rows = [
            {"Concept": c, "Score": f"{scores[c]:.0%}", "Status": labels[c]}
            for c in weak
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.success(f"You have mastered every concept. Outstanding work, {name}!")

    # Feedback
    st.divider()
    st.subheader("Personalized Feedback")
    use_llm = st.sidebar.toggle("AI-powered feedback", value=True)

    if st.button("Get Feedback"):
        with st.spinner("Generating feedback..."):
            feedback = generate_feedback(
                student_name=name,
                weak_concepts=weak,
                mastery_scores=scores,
                use_llm=use_llm,
            )
        st.text_area("", feedback, height=160, label_visibility="collapsed")

    # Diagnostic exam
    st.divider()
    st.subheader("Adaptive Diagnostic Exam")
    if weak:
        exam = generate_diagnostic_exam(
            weak_concepts=weak,
            mastery_scores=scores,
            question_bank=qbank_df,
        )
        with st.expander("View your diagnostic exam"):
            st.text(format_exam_report(exam, qbank_df))
    else:
        st.info("No diagnostic exam needed -- all concepts mastered.")

    # Study plan
    st.divider()
    st.subheader("Study Plan")
    if st.button("Generate My Study Plan"):
        with st.spinner("Building your study plan..."):
            plan = generate_study_plan(
                student_name=name,
                weak_concepts=weak,
                mastery_scores=scores,
                use_llm=use_llm,
            )
        st.text_area("", plan, height=400, label_visibility="collapsed")

    # Allow student to retake
    st.divider()
    if st.button("Take Another Exam", use_container_width=True):
        for key in ["page", "answers", "student_sid", "student_name", "student_grade"]:
            del st.session_state[key]
        st.rerun()


# ---------------------------------------------------------------------------
# Router -- decides which page to render based on session state
# ---------------------------------------------------------------------------

if st.session_state.page == "exam":
    render_exam_page()
else:
    render_results_page()