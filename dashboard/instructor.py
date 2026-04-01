"""
dashboard/instructor.py

Instructor-facing Streamlit dashboard for Neuro Learn Phase 3.

Panels:
    1. Class-wide mastery heatmap     -- students x concepts
    2. Cluster breakdown              -- archetype distribution
    3. At-risk students               -- lowest overall mastery
    4. Flagged prerequisite gaps      -- auto-flagged from SR service
    5. Review schedule progress       -- who is due for review today

Run with:
    streamlit run dashboard/instructor.py
"""

import sys
import os
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from data_loader      import load_student_answers, load_question_metadata
from answer_evaluator import evaluate_answers
from concept_mapper   import map_scores_to_concepts, calculate_mastery
from weakness_detector import classify_mastery
from clustering       import cluster_students, describe_clusters
from config           import APP_TITLE, ALL_CONCEPTS

from datetime import date

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "neuro_learn.db")

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title=f"{APP_TITLE} -- Instructor View",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 12px;
        padding-bottom: 6px;
        border-bottom: 2px solid #e8eaed;
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
    .risk-box {
        background: #fee2e2;
        border-left: 4px solid #e74c3c;
        border-radius: 0 8px 8px 0;
        padding: 14px 18px;
        font-size: 0.92rem;
        color: #7f1d1d;
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
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

@st.cache_data
def load_mastery_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load and compute mastery scores for all students.
    Returns (mastery_df, student_df) -- mastery indexed by Student_ID.
    """
    student_df  = load_student_answers()
    question_df = load_question_metadata()
    answer_mat  = evaluate_answers(student_df, question_df)
    concept_sc  = map_scores_to_concepts(answer_mat, question_df)
    mastery_df  = calculate_mastery(concept_sc, question_df)
    return mastery_df, student_df


@st.cache_data
def load_cluster_data(mastery_key: str) -> tuple[pd.Series, dict]:
    """
    Run K-Means clustering. mastery_key is a cache-busting hash of the data.
    Returns (cluster_labels, cluster_descriptions).
    """
    mastery_df, _ = load_mastery_data()
    labels, summary = cluster_students(mastery_df)
    desc = describe_clusters(summary)
    return labels, desc


def load_sr_flags() -> pd.DataFrame:
    """
    Load all flagged prerequisite gaps from the SR diagnostics table.
    Returns empty DataFrame if the table does not exist yet.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        df   = pd.read_sql_query(
            "SELECT student_id, concept, reason, created_at FROM sr_history "
            "ORDER BY created_at DESC",
            conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["student_id", "concept", "reason", "created_at"])


def load_sr_schedule() -> pd.DataFrame:
    """
    Load the full sr_schedule table.
    Returns empty DataFrame if the table does not exist yet.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        df   = pd.read_sql_query("SELECT * FROM sr_schedule", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def load_diagnostics_flags() -> pd.DataFrame:
    """Load auto-flagged prerequisite gaps from the sr_history diagnostics."""
    try:
        conn = sqlite3.connect(DB_PATH)
        # sr_history stores every session; join to get student names from CSV
        df = pd.read_sql_query(
            "SELECT student_id, concept, review_date, score FROM sr_history "
            "WHERE score < 0.6 ORDER BY review_date DESC",
            conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["student_id", "concept", "review_date", "score"])

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    "<h1 style='font-size:2rem;font-weight:800;color:#1a1a2e;'>"
    "Neuro Learn -- Instructor Dashboard</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='color:#6b7280;margin-top:-12px;margin-bottom:24px;'>"
    "Class-wide performance overview</p>",
    unsafe_allow_html=True
)

if st.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

mastery_df, student_df = load_mastery_data()
n_students  = len(mastery_df)
n_concepts  = len(mastery_df.columns)
class_mean  = mastery_df.values.mean()

# Attach names for display
display_df = mastery_df.copy()
if "Name" in student_df.columns:
    display_df.index = [
        f"{student_df.loc[sid, 'Name']} ({sid})"
        if sid in student_df.index else sid
        for sid in display_df.index
    ]

# Cluster
mastery_hash    = str(mastery_df.values.sum())
cluster_labels, cluster_desc = load_cluster_data(mastery_hash)

# SR data
sr_schedule  = load_sr_schedule()
diag_flags   = load_diagnostics_flags()
today        = date.today().isoformat()

# ---------------------------------------------------------------------------
# Summary metric row
# ---------------------------------------------------------------------------

at_risk_threshold = 0.40
n_at_risk = sum(
    1 for sid in mastery_df.index
    if mastery_df.loc[sid].mean() < at_risk_threshold
)

due_today = (
    sr_schedule[sr_schedule["due_date"] <= today]["student_id"].nunique()
    if not sr_schedule.empty else 0
)

cols = st.columns(4)
summary_metrics = [
    ("Students",        str(n_students)),
    ("Concepts",        str(n_concepts)),
    ("Class Mean",      f"{class_mean:.0%}"),
    ("At Risk",         str(n_at_risk)),
]
for col, (lbl, val) in zip(cols, summary_metrics):
    col.markdown(
        f"<div class='metric-card'>"
        f"<div class='metric-value'>{val}</div>"
        f"<div class='metric-label'>{lbl}</div>"
        f"</div>",
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Panel 1 -- Class-wide mastery heatmap
# ---------------------------------------------------------------------------

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>Class Mastery Heatmap</div>", unsafe_allow_html=True)
st.caption("Each cell shows a student's mastery score for one concept. Red = Weak, Green = Mastered.")

fig_heat = go.Figure(data=go.Heatmap(
    z=display_df.values.tolist(),
    x=list(display_df.columns),
    y=list(display_df.index),
    colorscale="RdYlGn",
    zmin=0, zmax=1,
    text=[[f"{v:.0%}" for v in row] for row in display_df.values.tolist()],
    texttemplate="%{text}",
    hovertemplate="Student: %{y}<br>Concept: %{x}<br>Mastery: %{text}<extra></extra>",
))
fig_heat.update_layout(
    height=max(300, n_students * 36),
    margin=dict(l=0, r=0, t=10, b=10),
    xaxis=dict(tickangle=-35, tickfont=dict(size=11)),
    yaxis=dict(tickfont=dict(size=11)),
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    font=dict(family="Inter, Segoe UI, sans-serif", size=11),
)
st.plotly_chart(fig_heat, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Panel 2 -- Cluster breakdown
# ---------------------------------------------------------------------------

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>Student Cluster Breakdown</div>", unsafe_allow_html=True)

cluster_counts = (
    cluster_labels
    .value_counts()
    .reset_index()
    .rename(columns={"index": "Cluster", "Cluster": "Count", 0: "Count"})
)
cluster_counts.columns = ["Cluster", "Count"]
cluster_counts["Description"] = cluster_counts["Cluster"].apply(
    lambda c: cluster_desc.get(int(c), "")
)
cluster_counts["Label"] = cluster_counts.apply(
    lambda r: f"Group {r['Cluster']}: {r['Description']}", axis=1
)

col_chart, col_table = st.columns([2, 3])

with col_chart:
    fig_pie = px.pie(
        cluster_counts, values="Count", names="Label",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        height=300,
    )
    fig_pie.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="#ffffff",
        font=dict(family="Inter, Segoe UI, sans-serif", size=11),
        showlegend=False,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_table:
    # Show which students are in each cluster
    cluster_member_rows = []
    for sid in mastery_df.index:
        cid = int(cluster_labels.get(sid, 0))
        name = str(student_df.loc[sid, "Name"]) if "Name" in student_df.columns and sid in student_df.index else sid
        cluster_member_rows.append({
            "Student":     name,
            "Student ID":  sid,
            "Cluster":     cid,
            "Description": cluster_desc.get(cid, ""),
        })
    st.dataframe(
        pd.DataFrame(cluster_member_rows).sort_values("Cluster"),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Panel 3 -- At-risk students
# ---------------------------------------------------------------------------

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>At-Risk Students</div>", unsafe_allow_html=True)
st.caption(f"Students with overall mastery below {at_risk_threshold:.0%}.")

at_risk_rows = []
for sid in mastery_df.index:
    overall = mastery_df.loc[sid].mean()
    if overall < at_risk_threshold:
        name = str(student_df.loc[sid, "Name"]) if "Name" in student_df.columns and sid in student_df.index else sid
        weak_concepts = [
            c for c in mastery_df.columns
            if float(mastery_df[c].loc[sid]) < 0.40
        ]
        at_risk_rows.append({
            "Student":        name,
            "Student ID":     sid,
            "Overall Mastery": f"{overall:.0%}",
            "Weak Concepts":  ", ".join(weak_concepts),
        })

if at_risk_rows:
    st.dataframe(
        pd.DataFrame(at_risk_rows).sort_values("Overall Mastery"),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.success("No students below the at-risk threshold.")

st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Panel 4 -- Flagged prerequisite gaps
# ---------------------------------------------------------------------------

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>Flagged Prerequisite Gaps</div>", unsafe_allow_html=True)
st.caption("Concepts auto-flagged because a student scored below 60% on a dependent concept during review.")

if not diag_flags.empty:
    # Attach student names
    def _name(sid: str) -> str:
        if "Name" in student_df.columns and sid in student_df.index:
            return f"{student_df.loc[sid, 'Name']} ({sid})"
        return sid

    diag_flags["Student"]      = diag_flags["student_id"].apply(_name)
    diag_flags["Score"]        = diag_flags["score"].apply(lambda v: f"{v:.0%}")
    diag_flags["Review Date"]  = diag_flags["review_date"]
    diag_flags["Concept"]      = diag_flags["concept"]

    st.dataframe(
        diag_flags[["Student", "Concept", "Score", "Review Date"]]
        .sort_values("Review Date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No prerequisite gaps flagged yet. Gaps appear here after students complete review sessions.")

st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Panel 5 -- Review schedule progress
# ---------------------------------------------------------------------------

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>Review Schedule Progress</div>", unsafe_allow_html=True)
st.caption("Current spaced repetition state for all students who have set up a schedule.")

if not sr_schedule.empty:
    def _name_short(sid: str) -> str:
        if "Name" in student_df.columns and sid in student_df.index:
            return str(student_df.loc[sid, "Name"])
        return sid

    sr_display = sr_schedule.copy()
    sr_display["Student"]        = sr_display["student_id"].apply(_name_short)
    sr_display["Due Today"]      = sr_display["due_date"].apply(lambda d: "Yes" if d <= today else "No")
    sr_display["Last Score"]     = sr_display["last_score"].apply(
        lambda v: f"{v:.0%}" if v is not None else "--"
    )

    # Summary: due counts per student
    due_summary = (
        sr_display[sr_display["Due Today"] == "Yes"]
        .groupby("Student")["concept"]
        .count()
        .reset_index()
        .rename(columns={"concept": "Concepts Due Today"})
        .sort_values("Concepts Due Today", ascending=False)
    )

    col_due, col_full = st.columns([1, 2])

    with col_due:
        st.markdown("**Due today**")
        if not due_summary.empty:
            st.dataframe(due_summary, use_container_width=True, hide_index=True)
        else:
            st.info("No reviews due today.")

    with col_full:
        st.markdown("**Full schedule**")
        st.dataframe(
            sr_display[["Student", "concept", "status", "due_date", "interval_days", "ease_factor", "Last Score"]]
            .rename(columns={
                "concept":       "Concept",
                "status":        "Status",
                "due_date":      "Due Date",
                "interval_days": "Interval (days)",
                "ease_factor":   "Ease Factor",
            })
            .sort_values(["Student", "Due Date"]),
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("No review schedules found. Students must set up their schedule from the student dashboard first.")

st.markdown("</div>", unsafe_allow_html=True)