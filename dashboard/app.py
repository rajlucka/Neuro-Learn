"""
dashboard/app.py

Student-facing Streamlit dashboard for Phase 1.

Displays concept mastery, weakness summary, a generated diagnostic exam,
and a personalized study plan for each student.

Run with:
    streamlit run dashboard/app.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import streamlit as st
import pandas as pd
import plotly.express as px

from data_loader               import load_student_answers, load_question_metadata, load_question_bank
from answer_evaluator          import evaluate_answers
from concept_mapper            import map_scores_to_concepts, calculate_mastery
from weakness_detector         import classify_mastery, build_summary_report
from diagnostic_exam_generator import generate_diagnostic_exam, format_exam_report
from ai_feedback               import generate_feedback, generate_study_plan


# Page configuration


st.set_page_config(page_title="Learning Diagnostics", layout="centered")

TIER_COLORS = {
    "Mastered":     "#2ecc71",
    "Needs Review": "#f0a500",
    "Weak":         "#e74c3c",
}


# Data pipeline
# Cached so the CSV reads and calculations only run once per session.


@st.cache_data
def run_pipeline():
    student_df  = load_student_answers()
    question_df = load_question_metadata()
    qbank_df    = load_question_bank()

    answer_mat    = evaluate_answers(student_df, question_df)
    concept_sc    = map_scores_to_concepts(answer_mat, question_df)
    mastery_df    = calculate_mastery(concept_sc, question_df)
    classified_df = classify_mastery(mastery_df)
    summary       = build_summary_report(mastery_df, classified_df)
    meta          = student_df[["Name", "Grade"]]

    return qbank_df, summary, meta


qbank_df, summary, meta = run_pipeline()


# Sidebar -- student selection


st.sidebar.title("Student Login")
student_ids = list(summary.keys())
sid = st.sidebar.selectbox("Select your name", student_ids,
                           format_func=lambda s: meta.loc[s, "Name"] if s in meta.index else s)

use_llm = st.sidebar.toggle("AI-powered feedback", value=True)


# Pull this student's data


data         = summary[sid]
scores       = data["scores"]
labels       = data["labels"]
weak         = data["weak_concepts"]
name         = meta.loc[sid, "Name"]  if sid in meta.index else sid
grade        = meta.loc[sid, "Grade"] if sid in meta.index else "?"
overall      = sum(scores.values()) / len(scores) if scores else 0.0
n_mastered   = sum(1 for l in labels.values() if l == "Mastered")


# Header


st.title("Your Learning Report")
st.caption(f"Student: {name}   |   Grade {grade}")

col1, col2, col3 = st.columns(3)
col1.metric("Overall Score",      f"{overall:.0%}")
col2.metric("Concepts Mastered",  f"{n_mastered} / {len(scores)}")
col3.metric("Needs Work",         f"{len(weak)} concept(s)")

st.divider()


# Concept mastery bar chart


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


# Weakness summary


st.divider()
st.subheader("Concepts Needing Attention")

if weak:
    rows = [
        {"Concept": c, "Score": f"{scores[c]:.0%}", "Status": labels[c]}
        for c in weak
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.success(f"You have mastered every concept on this exam. Excellent work, {name}!")


# Personalized feedback


st.divider()
st.subheader("Personalized Feedback")

if st.button("Get Feedback"):
    with st.spinner("Generating feedback..."):
        feedback = generate_feedback(
            student_name=name,
            weak_concepts=weak,
            mastery_scores=scores,
            use_llm=use_llm,
        )
    st.text_area("", feedback, height=200, label_visibility="collapsed")


# Adaptive diagnostic exam


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
    st.info("No diagnostic exam needed -- you have mastered all concepts.")


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
    st.text_area("", plan, height=320, label_visibility="collapsed")