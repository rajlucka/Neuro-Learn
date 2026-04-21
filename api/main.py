"""
api/main.py

FastAPI adapter layer for the Neuro Learn pipeline.

All business logic lives in src/python -- this file is a thin HTTP wrapper
only. No computation happens here; every endpoint delegates to the existing
Python modules and returns typed JSON responses.

Run locally:
    uvicorn api.main:app --reload --port 8000

Endpoints:
    GET  /students/{student_id}              -> StudentInfo
    GET  /students/{student_id}/concepts     -> ConceptData[]
    GET  /students/{student_id}/schedule     -> SM2Item[]
    GET  /students/{student_id}/history      -> ExamHistory[]
    GET  /class                              -> ClassStudent[]
    GET  /class/gaps                         -> GapItem[]
    GET  /diagnostic/questions               -> DiagnosticQuestion[]
    POST /diagnostic/submit                  -> SubmitResult
"""

import os
import sys
import logging
from typing import Literal, Optional
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from data_loader               import load_student_answers, load_question_metadata, load_question_bank
from answer_evaluator          import evaluate_answers
from concept_mapper            import map_scores_to_concepts, calculate_mastery
from weakness_detector         import classify_mastery, build_summary_report
from knowledge_tracing         import BayesianKnowledgeTracer, build_concept_observations
from clustering                import cluster_students
from concept_graph             import build_concept_graph, detect_root_causes
from diagnostic_exam_generator import generate_diagnostic_exam
from ai_feedback               import generate_feedback, generate_study_plan
from sr_service                import init_db, get_schedule

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = FastAPI(title="Neuro Learn API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# ---------------------------------------------------------------------------
# Response models -- mirror the TypeScript interfaces in frontend/src/data/mockData.ts
# ---------------------------------------------------------------------------

class StudentInfo(BaseModel):
    id: str
    name: str
    grade: str
    overallMastery: float


class ConceptData(BaseModel):
    concept: str
    masteryScore: float
    bktProb: float
    status: Literal["mastered", "learning", "struggling"]


class SM2Item(BaseModel):
    concept: str
    nextDate: str
    easeFactor: float


class ExamHistory(BaseModel):
    id: str
    title: str
    date: str
    score: int
    aiFeedback: str
    studyPlan: list[str]


class ClassStudent(BaseModel):
    id: str
    name: str
    scores: list[int]
    archetype: Literal["Rapid", "Steady", "At-Risk"]


class GapItem(BaseModel):
    student: str
    issue: str


class DiagnosticQuestion(BaseModel):
    id: str
    question: str
    options: list[str]
    concept: str


class SubmitRequest(BaseModel):
    student_id: str
    answers: dict[str, str]   # question_id -> selected option letter (A/B/C/D)


class SubmitResult(BaseModel):
    student_id: str
    concepts: list[ConceptData]
    feedback: str
    studyPlan: list[str]


# ---------------------------------------------------------------------------
# Pipeline helpers -- run once per request, not cached (append-only CSV)
# ---------------------------------------------------------------------------

def _run_pipeline():
    """Load data and run the full analysis pipeline. Returns all intermediate frames."""
    student_df  = load_student_answers()
    question_df = load_question_metadata()
    qbank_df    = load_question_bank()

    answer_matrix  = evaluate_answers(student_df, question_df)
    concept_scores = map_scores_to_concepts(answer_matrix, question_df)
    mastery_df     = calculate_mastery(concept_scores, question_df)
    classified_df  = classify_mastery(mastery_df)
    report         = build_summary_report(mastery_df, classified_df)

    return student_df, question_df, qbank_df, answer_matrix, mastery_df, classified_df, report


def _get_student_data(student_id: str):
    """Run pipeline and extract data for one student. Raises 404 if not found."""
    student_df, question_df, qbank_df, answer_matrix, mastery_df, classified_df, report = _run_pipeline()

    if student_id not in report:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found.")

    data    = report[student_id]
    name    = str(student_df.loc[student_id, "Name"])  if "Name"  in student_df.columns else student_id
    grade   = str(student_df.loc[student_id, "Grade"]) if "Grade" in student_df.columns else "?"
    overall = sum(data["scores"].values()) / len(data["scores"])

    return student_df, question_df, qbank_df, answer_matrix, mastery_df, classified_df, data, name, grade, overall


def _run_bkt(student_id: str, answer_matrix, question_df) -> dict:
    """Return {concept: p_know} for one student using the BKT tracer."""
    tracer      = BayesianKnowledgeTracer()
    concept_obs = build_concept_observations(answer_matrix, question_df, student_id)
    states      = tracer.trace_student(concept_obs)
    return tracer.get_mastery_estimates(states)


def _map_status(label: str) -> Literal["mastered", "learning", "struggling"]:
    """Convert internal tier label to frontend status string."""
    if label == "Mastered":     return "mastered"
    if label == "Needs Review": return "learning"
    return "struggling"


def _parse_study_plan(raw: str) -> list[str]:
    """
    Convert the plain-text study plan string from generate_study_plan()
    into a list of individual action strings for the frontend.
    Each non-empty line that isn't a header becomes one list item.
    """
    lines = []
    for line in raw.splitlines():
        line = line.strip().lstrip("-•1234567890. ")
        if line and not line.endswith(":"):
            lines.append(line)
    return lines[:6]   # cap at 6 items to match frontend card height


# ---------------------------------------------------------------------------
# GET /students/{student_id}
# ---------------------------------------------------------------------------

@app.get("/students/{student_id}", response_model=StudentInfo)
def get_student(student_id: str):
    _, _, _, _, _, _, _, name, grade, overall = _get_student_data(student_id)
    return StudentInfo(
        id=student_id,
        name=name,
        grade=grade,
        overallMastery=round(overall, 4),
    )


# ---------------------------------------------------------------------------
# GET /students/{student_id}/concepts
# ---------------------------------------------------------------------------

@app.get("/students/{student_id}/concepts", response_model=list[ConceptData])
def get_concepts(student_id: str):
    student_df, question_df, _, answer_matrix, mastery_df, classified_df, data, _, _, _ = _get_student_data(student_id)

    bkt_results = _run_bkt(student_id, answer_matrix, question_df)

    result = []
    for concept, score in data["scores"].items():
        label   = data["labels"].get(concept, "Weak")
        bkt_prob = bkt_results.get(concept, score)
        result.append(ConceptData(
            concept=concept,
            masteryScore=round(score, 4),
            bktProb=round(bkt_prob, 4),
            status=_map_status(label),
        ))
    return result


# ---------------------------------------------------------------------------
# GET /students/{student_id}/schedule
# ---------------------------------------------------------------------------

@app.get("/students/{student_id}/schedule", response_model=list[SM2Item])
def get_schedule_endpoint(student_id: str):
    rows = get_schedule(student_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No SR schedule found for '{student_id}'. Complete the diagnostic exam first.")

    return [
        SM2Item(
            concept=r["concept"],
            nextDate=r["due_date"],
            easeFactor=round(r["ease_factor"], 2),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# GET /students/{student_id}/history
# ---------------------------------------------------------------------------

@app.get("/students/{student_id}/history", response_model=list[ExamHistory])
def get_history(student_id: str):
    student_df, question_df, _, answer_matrix, mastery_df, classified_df, data, name, grade, overall = _get_student_data(student_id)

    weak    = data["weak_concepts"]
    scores  = data["scores"]

    feedback_raw = generate_feedback(
        student_name=name,
        weak_concepts=weak,
        mastery_scores=scores,
        use_llm=True,
    )
    plan_raw = generate_study_plan(
        student_name=name,
        weak_concepts=weak,
        mastery_scores=scores,
        use_llm=True,
    )

    # Build a single history entry representing the most recent exam result.
    # When the CSV grows to support multiple exam sessions this list expands.
    score_pct = int(round(overall * 100))
    today     = date.today().isoformat()

    return [
        ExamHistory(
            id="E1",
            title="Diagnostic Assessment",
            date=today,
            score=score_pct,
            aiFeedback=feedback_raw.strip(),
            studyPlan=_parse_study_plan(plan_raw),
        )
    ]


# ---------------------------------------------------------------------------
# GET /class
# ---------------------------------------------------------------------------

@app.get("/class", response_model=list[ClassStudent])
def get_class():
    student_df, question_df, _, answer_matrix, mastery_df, classified_df, report = _run_pipeline()

    cluster_labels, cluster_summary = cluster_students(mastery_df)

    # Map cluster integers to archetype labels by ranking clusters on mean mastery.
    # Highest mean -> Rapid, lowest mean -> At-Risk, middle -> Steady.
    cluster_means = cluster_summary.mean(axis=1).sort_values()
    archetype_map = {}
    labels_sorted = cluster_means.index.tolist()
    archetype_order = ["At-Risk", "Steady", "Rapid"]
    for i, cid in enumerate(labels_sorted):
        archetype_map[int(cid)] = archetype_order[min(i, 2)]

    result = []
    for sid, data in report.items():
        name      = str(student_df.loc[sid, "Name"]) if "Name" in student_df.columns else sid
        scores    = [int(round(v * 100)) for v in data["scores"].values()]
        archetype = archetype_map.get(int(cluster_labels.get(sid, 1)), "Steady")
        result.append(ClassStudent(
            id=sid,
            name=name,
            scores=scores,
            archetype=archetype,
        ))
    return result


# ---------------------------------------------------------------------------
# GET /class/gaps
# ---------------------------------------------------------------------------

@app.get("/class/gaps", response_model=list[GapItem])
def get_class_gaps():
    student_df, question_df, _, answer_matrix, mastery_df, classified_df, report = _run_pipeline()

    graph    = build_concept_graph()
    gap_list = []

    for sid, data in report.items():
        name   = str(student_df.loc[sid, "Name"]) if "Name" in student_df.columns else sid
        scores = data["scores"]

        root_causes = detect_root_causes(scores, graph)

        for root_concept in root_causes:
            root_pct = int(round(scores.get(root_concept, 0) * 100))
            gap_list.append(GapItem(
                student=f"{sid} ({name})",
                issue=f"Root cause gap: {root_concept} ({root_pct}%)",
            ))

    return gap_list


# ---------------------------------------------------------------------------
# GET /diagnostic/questions
# ---------------------------------------------------------------------------

@app.get("/diagnostic/questions", response_model=list[DiagnosticQuestion])
def get_diagnostic_questions():
    question_df = load_question_metadata()

    result = []
    for qid, row in question_df.iterrows():
        options = [
            str(row.get("Option_A", "")),
            str(row.get("Option_B", "")),
            str(row.get("Option_C", "")),
            str(row.get("Option_D", "")),
        ]
        # Topics is a list after data_loader parses it; take the first entry
        topics = row.get("Topics", "")
        concept = topics[0] if isinstance(topics, list) and topics else str(topics)
        result.append(DiagnosticQuestion(
            id=str(qid),
            question=str(row.get("Question_Text", f"Question {qid}")),
            options=options,
            concept=concept,
        ))
    return result


# ---------------------------------------------------------------------------
# POST /diagnostic/submit
# ---------------------------------------------------------------------------

@app.post("/diagnostic/submit", response_model=SubmitResult)
def submit_diagnostic(body: SubmitRequest):
    """
    Accepts a student's completed diagnostic answers, appends to student_answers.csv,
    reruns the pipeline, and returns updated concept scores with AI feedback.

    The CSV append uses the same append-only contract established in main.py.
    A new Student_ID is auto-incremented if the student_id is 'new'.
    """
    import pandas as pd

    student_df  = load_student_answers()
    question_df = load_question_metadata()

    # Resolve or assign student ID
    sid = body.student_id
    if sid == "new" or sid not in student_df.index:
        existing = [int(s[1:]) for s in student_df.index if s.startswith("S") and s[1:].isdigit()]
        next_num = max(existing) + 1 if existing else 1
        sid      = f"S{next_num:02d}"

    # Build answer row matching the CSV schema: one column per question ID
    row_data = {"Student_ID": sid}
    for qid, selected in body.answers.items():
        correct_answer = question_df.loc[qid, "Correct_Answer"] if qid in question_df.index else None
        row_data[qid]  = 1 if (correct_answer and selected == correct_answer) else 0

    answers_path = os.path.join(os.path.dirname(__file__), "..", "data", "student_answers.csv")
    new_row      = pd.DataFrame([row_data])
    new_row.to_csv(answers_path, mode="a", header=not os.path.exists(answers_path), index=False)

    # Rerun pipeline with updated CSV
    student_df2, question_df2, _, answer_matrix2, mastery_df2, classified_df2, report2 = _run_pipeline()

    if sid not in report2:
        raise HTTPException(status_code=500, detail="Pipeline failed to process submitted answers.")

    data2   = report2[sid]
    name    = str(student_df2.loc[sid, "Name"]) if "Name" in student_df2.columns else sid
    weak    = data2["weak_concepts"]
    scores  = data2["scores"]

    bkt_results = _run_bkt(sid, answer_matrix2, question_df2)

    concepts_out = []
    for concept, score in scores.items():
        label    = data2["labels"].get(concept, "Weak")
        bkt_prob = bkt_results.get(concept, score)
        concepts_out.append(ConceptData(
            concept=concept,
            masteryScore=round(score, 4),
            bktProb=round(bkt_prob, 4),
            status=_map_status(label),
        ))

    feedback_raw = generate_feedback(
        student_name=name,
        weak_concepts=weak,
        mastery_scores=scores,
        use_llm=True,
    )
    plan_raw = generate_study_plan(
        student_name=name,
        weak_concepts=weak,
        mastery_scores=scores,
        use_llm=True,
    )

    return SubmitResult(
        student_id=sid,
        concepts=concepts_out,
        feedback=feedback_raw.strip(),
        studyPlan=_parse_study_plan(plan_raw),
    )