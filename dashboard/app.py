"""
dashboard/app.py

Student-facing Streamlit dashboard for Neuro Learn Phase 2.

Page 1 -- Exam
    Student enters name and grade, answers all 36 questions grouped by
    grade level, and optionally provides a free-text explanation of their
    thinking. On submit, answers are appended to student_answers.csv with
    an auto-generated Student_ID.

Page 2 -- Results (three tabs)
    Overview   : mastery bar chart, BKT estimates, root cause path,
                 cluster group, AI feedback
    Exam       : adaptive diagnostic exam questions
    Study Plan : misconception analysis, personalized study plan

Run with:
    streamlit run dashboard/app.py
"""

import sys
import os
import html  # FIX 2: escape LLM output before unsafe_allow_html injection
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from data_loader               import load_student_answers, load_question_metadata, load_question_bank
from answer_evaluator          import evaluate_answers
from concept_mapper            import map_scores_to_concepts, calculate_mastery
from weakness_detector         import classify_mastery, build_summary_report
from diagnostic_exam_generator import generate_diagnostic_exam, format_exam_report
from ai_feedback               import generate_feedback, generate_study_plan
from knowledge_tracing         import BayesianKnowledgeTracer, build_concept_observations
from concept_graph             import build_concept_graph, detect_root_causes, get_learning_order
from clustering                import cluster_students, describe_clusters
from misconception_detector    import detect_misconceptions
from config                    import TIER_COLORS, GRADE_RANGE, APP_TITLE, APP_SUBTITLE

# ---------------------------------------------------------------------------
# Page configuration and global styles
# ---------------------------------------------------------------------------

st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Global font and background */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background-color: #f8f9fb;
        color: #1a1a2e;
    }

    /* Card component used throughout the dashboard */
    .card {
        background: #ffffff;
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 16px;
        border: 1px solid #e8eaed;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }

    /* Metric cards in the header row */
    .metric-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 20px 24px;
        border: 1px solid #e8eaed;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a2e;
        line-height: 1.1;
    }
    .metric-label {
        font-size: 0.82rem;
        color: #6b7280;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    /* Tier badge pills */
    .badge-mastered    { background:#dcfce7; color:#166534; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-review      { background:#fef9c3; color:#854d0e; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-weak        { background:#fee2e2; color:#991b1b; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }

    /* Section headings */
    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 12px;
        padding-bottom: 6px;
        border-bottom: 2px solid #e8eaed;
    }

    /* Cluster info box */
    .cluster-box {
        background: #eff6ff;
        border-left: 4px solid #3b82f6;
        border-radius: 0 8px 8px 0;
        padding: 14px 18px;
        font-size: 0.92rem;
        color: #1e3a5f;
    }

    /* Root cause path box */
    .root-box {
        background: #fff7ed;
        border-left: 4px solid #f97316;
        border-radius: 0 8px 8px 0;
        padding: 14px 18px;
        font-size: 0.92rem;
        color: #7c2d12;
    }

    /* Hide Streamlit default header padding */
    .block-container { padding-top: 2rem; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

DATA_DIR         = os.path.join(os.path.dirname(__file__), "..", "data")
ANSWERS_CSV_PATH = os.path.join(DATA_DIR, "student_answers.csv")

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

defaults = {
    "page":          "exam",
    "answers":       {},
    "explanation":   "",
    "student_sid":   None,
    "student_name":  "",
    "student_grade": GRADE_RANGE[0],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

@st.cache_data
def load_questions() -> pd.DataFrame:
    return load_question_metadata()

@st.cache_data
def load_bank() -> pd.DataFrame:
    return load_question_bank()


def generate_student_id() -> str:
    """Auto-generate the next Student_ID by reading the existing CSV."""
    try:
        existing = pd.read_csv(ANSWERS_CSV_PATH)
        nums = []
        for sid in existing["Student_ID"].dropna():
            try:
                nums.append(int(str(sid).replace("S", "")))
            except ValueError:
                pass
        return f"S{max(nums) + 1:02d}" if nums else "S01"
    except FileNotFoundError:
        return "S01"


def append_student_answers(sid: str, name: str, grade: int, answers: dict) -> None:
    """Append a new student row to student_answers.csv."""
    existing = pd.read_csv(ANSWERS_CSV_PATH)
    q_cols   = [c for c in existing.columns if c.startswith("Q")]
    new_row  = {"Student_ID": sid, "Name": name, "Grade": grade}
    for q in q_cols:
        new_row[q] = answers.get(q, "")
    updated = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
    updated.to_csv(ANSWERS_CSV_PATH, index=False)


def run_full_pipeline(sid: str) -> dict:
    """
    Run the complete Phase 2 pipeline for a single student and return
    all computed results in a single dict.
    Not cached because a new student row may have just been written.
    """
    student_df  = load_student_answers()
    question_df = load_questions()
    qbank_df    = load_bank()

    answer_mat    = evaluate_answers(student_df, question_df)
    concept_sc    = map_scores_to_concepts(answer_mat, question_df)
    mastery_df    = calculate_mastery(concept_sc, question_df)
    classified_df = classify_mastery(mastery_df)
    report        = build_summary_report(mastery_df, classified_df)

    data   = report.get(sid, {})
    scores = data.get("scores", {})
    labels = data.get("labels", {})
    weak   = data.get("weak_concepts", [])

    # BKT estimates
    tracer  = BayesianKnowledgeTracer()
    obs     = build_concept_observations(answer_mat, question_df, sid)
    states  = tracer.trace_student(obs)
    bkt_est = tracer.get_mastery_estimates(states)

    # Concept graph -- root causes and learning order
    graph       = build_concept_graph()
    root_causes = detect_root_causes(scores, graph)
    learn_order = get_learning_order(weak, graph)

    # Clustering
    cluster_labels, cluster_summary = cluster_students(mastery_df)
    cluster_desc    = describe_clusters(cluster_summary)
    student_cluster = int(cluster_labels.get(sid, 0))

    # Diagnostic exam
    exam = generate_diagnostic_exam(
        weak_concepts=weak,
        mastery_scores=scores,
        question_bank=qbank_df
    ) if weak else {}

    # FIX 1: removed duplicate "learn_order" key that was previously listed twice
    return {
        "scores":       scores,
        "labels":       labels,
        "weak":         weak,
        "bkt":          bkt_est,
        "root_causes":  root_causes,
        "learn_order":  learn_order,
        "cluster_id":   student_cluster,
        "cluster_desc": cluster_desc,
        "exam":         exam,
        "qbank":        qbank_df,
    }

# ---------------------------------------------------------------------------
# PAGE 1 -- EXAM
# ---------------------------------------------------------------------------

def render_exam_page():
    # Header
    st.markdown(f"<h1 style='font-size:2rem;font-weight:800;color:#1a1a2e;'>{APP_TITLE}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#6b7280;margin-top:-12px;margin-bottom:24px;'>{APP_SUBTITLE}</p>", unsafe_allow_html=True)

    # Student info
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Your Information</div>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    name  = col1.text_input("Full name", placeholder="Enter your name", label_visibility="visible")
    grade = col2.selectbox("Grade", GRADE_RANGE, format_func=lambda g: f"Grade {g}")
    st.markdown("</div>", unsafe_allow_html=True)

    # Questions
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Exam Questions</div>", unsafe_allow_html=True)
    st.caption("Answer every question before submitting.")

    question_df  = load_questions()
    answers      = {}
    all_answered = True

    for g in GRADE_RANGE:
        grade_qs = question_df[question_df["Grade"] == g]
        if grade_qs.empty:
            continue
        st.markdown(f"**Grade {g}**")
        for q_id, row in grade_qs.iterrows():
            option_labels = [
                f"{k}) {row.get(f'Option_{k}', '')}"
                for k in ["A", "B", "C", "D"]
            ]
            chosen = st.radio(
                label=f"{q_id}: {row['Question_Text']}",
                options=option_labels,
                index=None,
                key=f"q_{q_id}",
            )
            if chosen is None:
                all_answered = False
            else:
                answers[q_id] = chosen[0]
        st.divider()

    # Optional explanation
    st.markdown("<div class='section-title'>Optional: Explain Your Thinking</div>", unsafe_allow_html=True)
    st.caption("If you want more personalised feedback, describe how you approached the questions you found hardest.")
    explanation = st.text_area(
        label="Your explanation",
        placeholder="e.g. For the fractions questions I tried to find the biggest number...",
        height=100,
        label_visibility="collapsed"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Submit
    if st.button("Submit Exam", type="primary", use_container_width=True):
        if not name.strip():
            st.error("Please enter your name.")
        elif not all_answered:
            st.error("Please answer all questions before submitting.")
        else:
            sid = generate_student_id()
            append_student_answers(sid, name.strip(), grade, answers)
            st.session_state.update({
                "student_sid":   sid,
                "student_name":  name.strip(),
                "student_grade": grade,
                "answers":       answers,
                "explanation":   explanation.strip(),
                "page":          "results",
            })
            st.rerun()


# ---------------------------------------------------------------------------
# PAGE 2 -- RESULTS
# ---------------------------------------------------------------------------

def render_results_page():
    sid         = st.session_state.student_sid
    name        = st.session_state.student_name
    grade       = st.session_state.student_grade
    explanation = st.session_state.explanation
    use_llm     = st.sidebar.toggle("AI-powered content", value=True)

    # Page header
    st.markdown(f"<h1 style='font-size:1.8rem;font-weight:800;color:#1a1a2e;'>Results for {name}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#6b7280;margin-top:-10px;'>Student ID: {sid} &nbsp;|&nbsp; Grade {grade}</p>", unsafe_allow_html=True)

    with st.spinner("Running diagnostics..."):
        r = run_full_pipeline(sid)

    scores       = r["scores"]
    labels       = r["labels"]
    weak         = r["weak"]
    bkt          = r["bkt"]
    root_causes  = r["root_causes"]
    learn_order  = r["learn_order"]
    cluster_id   = r["cluster_id"]
    cluster_desc = r["cluster_desc"]
    exam         = r["exam"]
    qbank_df     = r["qbank"]

    overall    = sum(scores.values()) / len(scores) if scores else 0.0
    n_mastered = sum(1 for l in labels.values() if l == "Mastered")
    n_weak     = sum(1 for l in labels.values() if l == "Weak")

    # Metric row
    cols = st.columns(4)
    metrics = [
        ("Overall Score",     f"{overall:.0%}"),
        ("Concepts Mastered", f"{n_mastered} / {len(scores)}"),
        ("Weak Concepts",     str(n_weak)),
        ("Cluster Group",     str(cluster_id)),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-value'>{value}</div>"
            f"<div class='metric-label'>{label}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs
    tab_overview, tab_exam, tab_plan = st.tabs(["Overview", "Diagnostic Exam", "Study Plan"])

    # -----------------------------------------------------------------------
    # TAB 1 -- OVERVIEW
    # -----------------------------------------------------------------------
    with tab_overview:

        col_left, col_right = st.columns([3, 2])

        with col_left:
            # Mastery bar chart
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Concept Mastery</div>", unsafe_allow_html=True)
            chart_df = (
                pd.DataFrame({
                    "Concept": list(scores.keys()),
                    "Mastery": list(scores.values()),
                    "Status":  list(labels.values()),
                })
                .sort_values("Mastery", ascending=True)
            )
            fig = px.bar(
                chart_df, x="Mastery", y="Concept", orientation="h",
                color="Status", color_discrete_map=TIER_COLORS,
                range_x=[0, 1], height=420, text="Mastery",
            )
            fig.update_traces(texttemplate="%{text:.0%}", textposition="outside")
            fig.add_vline(x=0.75, line_dash="dash", line_color="#2ecc71", annotation_text="Mastered")
            fig.add_vline(x=0.40, line_dash="dash", line_color="#e74c3c", annotation_text="Weak")
            fig.update_layout(
                xaxis_title="", yaxis_title="", showlegend=True,
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                margin=dict(l=0, r=40, t=10, b=10),
                font=dict(family="Inter, Segoe UI, sans-serif", size=12)
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            # BKT probability chart
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Knowledge Probability (BKT)</div>", unsafe_allow_html=True)
            bkt_df = (
                pd.DataFrame({
                    "Concept": list(bkt.keys()),
                    "P(Know)": list(bkt.values()),
                })
                .sort_values("P(Know)", ascending=True)
            )
            fig2 = px.bar(
                bkt_df, x="P(Know)", y="Concept", orientation="h",
                range_x=[0, 1], height=420, text="P(Know)",
                color="P(Know)", color_continuous_scale="RdYlGn",
            )
            fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
            fig2.update_layout(
                xaxis_title="", yaxis_title="", coloraxis_showscale=False,
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                margin=dict(l=0, r=50, t=10, b=10),
                font=dict(family="Inter, Segoe UI, sans-serif", size=12)
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Root cause and cluster row
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Root Cause Analysis</div>", unsafe_allow_html=True)
            if root_causes:
                path = " → ".join(learn_order) if learn_order else "None"
                st.markdown(
                    f"<div class='root-box'>"
                    f"<strong>Start here:</strong> {', '.join(root_causes)}<br><br>"
                    f"<strong>Recommended learning path:</strong><br>{path}"
                    f"</div>",
                    unsafe_allow_html=True
                )
            else:
                st.success("No root cause gaps detected.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_b:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Student Cluster</div>", unsafe_allow_html=True)
            desc = cluster_desc.get(cluster_id, "")
            st.markdown(
                f"<div class='cluster-box'>"
                f"<strong>Group {cluster_id}</strong><br>{desc}"
                f"</div>",
                unsafe_allow_html=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # AI Feedback
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Personalized Feedback</div>", unsafe_allow_html=True)
        if st.button("Get Feedback", key="btn_feedback"):
            with st.spinner("Generating feedback..."):
                feedback = generate_feedback(
                    student_name=name,
                    weak_concepts=weak,
                    mastery_scores=scores,
                    use_llm=use_llm,
                )
            # FIX 2: escape LLM output to prevent stray HTML chars from breaking the card
            safe_feedback = html.escape(feedback)
            st.markdown(
                f"<div style='background:#f0fdf4;border-radius:8px;padding:16px 20px;"
                f"font-size:0.95rem;line-height:1.6;white-space:pre-wrap;color:#1a1a2e;'>"
                f"{safe_feedback}</div>",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # TAB 2 -- DIAGNOSTIC EXAM
    # -----------------------------------------------------------------------
    with tab_exam:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Adaptive Diagnostic Exam</div>", unsafe_allow_html=True)
        if exam:
            st.caption("Questions selected based on your weak and needs-review concepts, ordered Easy to Hard.")
            # FIX 4: st.code() preserves all whitespace and indentation from
            # format_exam_report(); st.text() collapses leading spaces.
            st.code(format_exam_report(exam, qbank_df), language=None)
        else:
            st.success(f"No diagnostic exam needed — {name} has mastered all concepts.")
        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # TAB 3 -- STUDY PLAN
    # -----------------------------------------------------------------------
    with tab_plan:

        # Misconception detector
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Misconception Analysis</div>", unsafe_allow_html=True)
        if explanation:
            if st.button("Analyse My Explanation", key="btn_misconception"):
                with st.spinner("Analysing your reasoning..."):
                    # FIX 3: pass api_key="" when use_llm is off so the
                    # misconception detector respects the sidebar toggle,
                    # matching the behaviour of the other two AI buttons.
                    analysis = detect_misconceptions(
                        student_name=name,
                        explanation=explanation,
                        weak_concepts=weak,
                        api_key=None if use_llm else "",
                    )
                # FIX 2: escape before HTML injection
                safe_analysis = html.escape(analysis)
                st.markdown(
                    f"<div style='background:#fffbeb;border-radius:8px;padding:16px 20px;"
                    f"font-size:0.95rem;line-height:1.6;white-space:pre-wrap;color:#1a1a2e;'>"
                    f"{safe_analysis}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.caption("You did not provide an explanation on the exam page. Retake the exam to include one.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Study plan
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Personalized Study Plan</div>", unsafe_allow_html=True)
        if st.button("Generate Study Plan", key="btn_plan"):
            with st.spinner("Building your study plan..."):
                plan = generate_study_plan(
                    student_name=name,
                    weak_concepts=weak,
                    mastery_scores=scores,
                    use_llm=use_llm,
                )
            # FIX 2: escape before HTML injection
            safe_plan = html.escape(plan)
            st.markdown(
                f"<div style='background:#f8f9fb;border-radius:8px;padding:16px 20px;"
                f"font-size:0.92rem;line-height:1.8;white-space:pre-wrap;color:#1a1a2e;'>"
                f"{safe_plan}</div>",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # Retake button
    st.divider()
    if st.button("Take Another Exam", use_container_width=True):
        # Wipe all session state keys defined in defaults to fully reset the app
        for key in list(defaults.keys()):
            del st.session_state[key]
        st.rerun()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

if st.session_state.page == "exam":
    render_exam_page()
else:
    render_results_page()