"""
dashboard/app.py

Student-facing Streamlit dashboard for Neuro Learn.

Page 1 -- Exam
Page 2 -- Results (four tabs)
    Overview        : mastery bar chart, BKT, root cause, cluster, AI feedback
    Diagnostic Exam : adaptive exam questions
    Study Plan      : misconception analysis, personalized study plan
    Review Schedule : SM-2 spaced repetition review session

Run with:
    streamlit run dashboard/app.py
"""

import sys
import os
import html
from typing import Optional
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

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
import sr_service

# ---------------------------------------------------------------------------
# Page config and global styles
# ---------------------------------------------------------------------------

st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background-color: #f8f9fb;
        color: #1a1a2e;
    }
    .card {
        background: #ffffff;
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 16px;
        border: 1px solid #e8eaed;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
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
    .badge-mastered { background:#dcfce7; color:#166534; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-review   { background:#fef9c3; color:#854d0e; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-weak     { background:#fee2e2; color:#991b1b; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 12px;
        padding-bottom: 6px;
        border-bottom: 2px solid #e8eaed;
    }
    .cluster-box {
        background: #eff6ff;
        border-left: 4px solid #3b82f6;
        border-radius: 0 8px 8px 0;
        padding: 14px 18px;
        font-size: 0.92rem;
        color: #1e3a5f;
    }
    .root-box {
        background: #fff7ed;
        border-left: 4px solid #f97316;
        border-radius: 0 8px 8px 0;
        padding: 14px 18px;
        font-size: 0.92rem;
        color: #7c2d12;
    }
    .due-box {
        background: #fef9c3;
        border-left: 4px solid #f59e0b;
        border-radius: 0 8px 8px 0;
        padding: 14px 18px;
        font-size: 0.92rem;
        color: #78350f;
    }
    .block-container { padding-top: 2rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialise the SQLite DB on startup (creates tables if missing)
sr_service.init_db()

DATA_DIR         = os.path.join(os.path.dirname(__file__), "..", "data")
ANSWERS_CSV_PATH = os.path.join(DATA_DIR, "student_answers.csv")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

defaults = {
    "page":          "exam",
    "answers":       {},
    "explanation":   "",
    "student_sid":   None,
    "student_name":  "",
    "student_grade": GRADE_RANGE[0],
    # SR review session state
    "sr_review_active":  False,
    "sr_due_concepts":   [],
    "sr_concept_idx":    0,
    "sr_questions":      [],
    "sr_q_idx":          0,
    "sr_answers":        [],
    "sr_concept_result": None,   # dict returned by record_review_session
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# Data helpers
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
    Run the complete Phase 2 pipeline for a single student.
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

    tracer  = BayesianKnowledgeTracer()
    obs     = build_concept_observations(answer_mat, question_df, sid)
    states  = tracer.trace_student(obs)
    bkt_est = tracer.get_mastery_estimates(states)

    graph       = build_concept_graph()
    root_causes = detect_root_causes(scores, graph)
    learn_order = get_learning_order(weak, graph)

    cluster_labels, cluster_summary = cluster_students(mastery_df)
    cluster_desc    = describe_clusters(cluster_summary)
    student_cluster = int(cluster_labels.get(sid, 0))

    exam = generate_diagnostic_exam(
        weak_concepts=weak,
        mastery_scores=scores,
        question_bank=qbank_df
    ) if weak else {}

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

def render_exam_page() -> None:
    st.markdown(f"<h1 style='font-size:2rem;font-weight:800;color:#1a1a2e;'>{APP_TITLE}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#6b7280;margin-top:-12px;margin-bottom:24px;'>{APP_SUBTITLE}</p>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Your Information</div>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    name      = col1.text_input("Full name", placeholder="Enter your name", label_visibility="visible")
    grade_raw = col2.selectbox("Grade", GRADE_RANGE, format_func=lambda g: f"Grade {g}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Exam Questions</div>", unsafe_allow_html=True)
    st.caption("Answer every question before submitting.")

    question_df   = load_questions()
    answers: dict = {}
    all_answered  = True

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
                answers[str(q_id)] = chosen[0]
        st.divider()

    st.markdown("<div class='section-title'>Optional: Explain Your Thinking</div>", unsafe_allow_html=True)
    st.caption("If you want more personalised feedback, describe how you approached the questions you found hardest.")
    explanation = st.text_area(
        label="Your explanation",
        placeholder="e.g. For the fractions questions I tried to find the biggest number...",
        height=100,
        label_visibility="collapsed"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Submit Exam", type="primary", use_container_width=True):
        if not name.strip():
            st.error("Please enter your name.")
        elif not all_answered:
            st.error("Please answer all questions before submitting.")
        else:
            sid   = generate_student_id()
            grade = int(grade_raw) if grade_raw is not None else GRADE_RANGE[0]
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

def render_results_page() -> None:
    sid         = st.session_state.student_sid
    name        = str(st.session_state.student_name)
    grade       = st.session_state.student_grade
    explanation = str(st.session_state.explanation)
    use_llm     = bool(st.sidebar.toggle("AI-powered content", value=True))

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
    n_mastered = sum(1 for lbl in labels.values() if lbl == "Mastered")
    n_weak     = sum(1 for lbl in labels.values() if lbl == "Weak")

    cols = st.columns(4)
    metrics = [
        ("Overall Score",     f"{overall:.0%}"),
        ("Concepts Mastered", f"{n_mastered} / {len(scores)}"),
        ("Weak Concepts",     str(n_weak)),
        ("Cluster Group",     str(cluster_id)),
    ]
    for col, (metric_label, value) in zip(cols, metrics):
        col.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-value'>{value}</div>"
            f"<div class='metric-label'>{metric_label}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    tab_overview, tab_exam, tab_plan, tab_review = st.tabs([
        "Overview", "Diagnostic Exam", "Study Plan", "Review Schedule"
    ])

    # -----------------------------------------------------------------------
    # TAB 1 -- OVERVIEW
    # -----------------------------------------------------------------------
    with tab_overview:
        col_left, col_right = st.columns([3, 2])

        with col_left:
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

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Root Cause Analysis</div>", unsafe_allow_html=True)
            if root_causes:
                path = " -> ".join(learn_order) if learn_order else "None"
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
            st.code(format_exam_report(exam, qbank_df), language=None)
        else:
            st.success(f"No diagnostic exam needed -- {name} has mastered all concepts.")
        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # TAB 3 -- STUDY PLAN
    # -----------------------------------------------------------------------
    with tab_plan:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Misconception Analysis</div>", unsafe_allow_html=True)
        if explanation:
            if st.button("Analyse My Explanation", key="btn_misconception"):
                with st.spinner("Analysing your reasoning..."):
                    api_key: Optional[str] = None if use_llm else ""
                    analysis = detect_misconceptions(
                        student_name=name,
                        explanation=explanation,
                        weak_concepts=weak,
                        api_key=api_key,
                    )
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
            safe_plan = html.escape(plan)
            st.markdown(
                f"<div style='background:#f8f9fb;border-radius:8px;padding:16px 20px;"
                f"font-size:0.92rem;line-height:1.8;white-space:pre-wrap;color:#1a1a2e;'>"
                f"{safe_plan}</div>",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # TAB 4 -- REVIEW SCHEDULE
    # -----------------------------------------------------------------------
    with tab_review:
        _render_review_tab(sid, name, scores, qbank_df)

    st.divider()
    if st.button("Take Another Exam", use_container_width=True):
        for key in list(defaults.keys()):
            del st.session_state[key]
        st.rerun()


# ---------------------------------------------------------------------------
# REVIEW TAB -- extracted for readability
# ---------------------------------------------------------------------------

def _render_review_tab(sid: str, name: str, scores: dict, qbank_df) -> None:
    """
    Renders the spaced repetition review tab.

    Three states:
        1. No schedule yet         -- show Init button
        2. Schedule exists, idle   -- show schedule table + Start Review
        3. Review active           -- show question or concept result
    """

    # Auto-initialise schedule on first visit to this tab
    if not sr_service.schedule_exists(sid):
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Review Schedule</div>", unsafe_allow_html=True)
        st.caption("Your spaced repetition schedule has not been set up yet.")
        if st.button("Set Up Review Schedule", key="btn_init_sr"):
            sr_service.initialise_schedule(sid, scores)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # ---- Active review session ------------------------------------------
    if st.session_state.sr_review_active:
        _render_review_session(sid, qbank_df)
        return

    # ---- Idle: show schedule table + start button ----------------------
    schedule  = sr_service.get_schedule(sid)
    due       = sr_service.get_due_concepts(sid)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Your Review Schedule</div>", unsafe_allow_html=True)

    table_data = pd.DataFrame(schedule)[
        ["concept", "status", "due_date", "interval_days", "ease_factor", "last_score"]
    ].rename(columns={
        "concept":      "Concept",
        "status":       "Status",
        "due_date":     "Due Date",
        "interval_days":"Interval (days)",
        "ease_factor":  "Ease Factor",
        "last_score":   "Last Score",
    })
    table_data["Last Score"] = table_data["Last Score"].apply(
        lambda v: f"{v:.0%}" if v is not None else "--"
    )
    st.dataframe(table_data, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Due today box
    if due:
        st.markdown(
            f"<div class='due-box'>"
            f"<strong>{len(due)} concept(s) due for review today:</strong> {', '.join(due)}"
            f"</div><br>",
            unsafe_allow_html=True
        )
        if st.button("Start Review Session", key="btn_start_review", type="primary"):
            # Load questions for the first due concept and activate session
            concept    = due[0]
            status_row = sr_service.get_concept_status(sid, concept)
            status     = status_row["status"] if status_row else "New"
            questions  = sr_service.select_review_questions(concept, status, qbank_df)
            st.session_state.update({
                "sr_review_active":  True,
                "sr_due_concepts":   due,
                "sr_concept_idx":    0,
                "sr_questions":      questions,
                "sr_q_idx":          0,
                "sr_answers":        [],
                "sr_concept_result": None,
            })
            st.rerun()
    else:
        st.info("No concepts are due for review today. Check back tomorrow.")


def _render_review_session(sid: str, qbank_df) -> None:
    """
    Renders the active review session: one question at a time per concept.

    Flow:
        question -> answer submitted -> next question
        -> all questions done -> show concept result
        -> next concept or finish
    """
    due_concepts = st.session_state.sr_due_concepts
    concept_idx  = st.session_state.sr_concept_idx
    questions    = st.session_state.sr_questions
    q_idx        = st.session_state.sr_q_idx
    result       = st.session_state.sr_concept_result

    # All concepts done
    if concept_idx >= len(due_concepts):
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Review Session Complete</div>", unsafe_allow_html=True)
        st.success("You have reviewed all due concepts for today.")
        if st.button("Back to Schedule", key="btn_review_done"):
            st.session_state.sr_review_active = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    concept = due_concepts[concept_idx]

    # Show concept result before moving on
    if result is not None:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='section-title'>Result: {concept}</div>", unsafe_allow_html=True)
        score_pct = f"{result['score']:.0%}"
        st.metric("Session Score", score_pct)
        col1, col2, col3 = st.columns(3)
        col1.metric("New Status",   result["status"])
        col2.metric("Next Review",  result["due_date"])
        col3.metric("Interval",     f"{result['interval_days']} days")

        remaining = len(due_concepts) - concept_idx - 1
        if remaining > 0:
            if st.button(f"Next Concept ({remaining} remaining)", key="btn_next_concept", type="primary"):
                next_concept = due_concepts[concept_idx + 1]
                next_row     = sr_service.get_concept_status(sid, next_concept)
                next_status  = next_row["status"] if next_row else "New"
                next_qs      = sr_service.select_review_questions(next_concept, next_status, qbank_df)
                st.session_state.update({
                    "sr_concept_idx":    concept_idx + 1,
                    "sr_questions":      next_qs,
                    "sr_q_idx":          0,
                    "sr_answers":        [],
                    "sr_concept_result": None,
                })
                st.rerun()
        else:
            if st.button("Finish Review", key="btn_finish_review", type="primary"):
                st.session_state.sr_review_active = False
                st.session_state.sr_concept_result = None
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # No questions available for this concept
    if not questions:
        st.warning(f"No review questions found for {concept}. Skipping.")
        st.session_state.sr_concept_idx += 1
        st.rerun()
        return

    # All questions for this concept answered — score and update schedule
    if q_idx >= len(questions):
        result = sr_service.record_review_session(
            sid, concept, st.session_state.sr_answers
        )
        st.session_state.sr_concept_result = result
        st.rerun()
        return

    # Show current question
    q = questions[q_idx]
    progress = q_idx / len(questions)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='section-title'>"
        f"Reviewing: {concept} &nbsp; ({q_idx + 1} / {len(questions)})"
        f"</div>",
        unsafe_allow_html=True
    )
    st.progress(progress)
    st.markdown(f"**[{q['difficulty']}]** {q['text']}")

    option_labels = [f"{k}) {v}" for k, v in q["options"].items()]
    chosen = st.radio(
        label="Select your answer",
        options=option_labels,
        index=None,
        key=f"sr_q_{concept_idx}_{q_idx}",
        label_visibility="collapsed",
    )

    if st.button("Submit Answer", key=f"sr_submit_{concept_idx}_{q_idx}", type="primary"):
        if chosen is None:
            st.warning("Please select an answer before submitting.")
        else:
            is_correct = chosen[0] == q["correct"]
            st.session_state.sr_answers.append(is_correct)
            st.session_state.sr_q_idx += 1
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

if st.session_state.page == "exam":
    render_exam_page()
else:
    render_results_page()