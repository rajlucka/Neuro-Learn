/**
 * Seed 5 concepts in a chain, 10 questions, simulate a student failing
 * concept 5, and assert that concept 4 (prerequisite) was auto-flagged.
 *
 * Run with: npx tsx scripts/seed-and-test.ts
 */

import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';

import * as schema from '../src/db/schema';
import { LearningService } from '../src/services/learning-service';

const sqlite = new Database(':memory:');
const db     = drizzle(sqlite, { schema });

sqlite.exec(`
  CREATE TABLE students             (id TEXT PRIMARY KEY, name TEXT NOT NULL, grade INTEGER NOT NULL, created_at TEXT NOT NULL);
  CREATE TABLE concepts             (id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, subject TEXT NOT NULL, created_at TEXT NOT NULL);
  CREATE TABLE concept_dependencies (id TEXT PRIMARY KEY, prerequisite_id TEXT NOT NULL REFERENCES concepts(id), dependent_id TEXT NOT NULL REFERENCES concepts(id));
  CREATE TABLE questions            (id TEXT PRIMARY KEY, text TEXT NOT NULL, difficulty TEXT NOT NULL, grade INTEGER NOT NULL, subject TEXT NOT NULL, option_a TEXT NOT NULL, option_b TEXT NOT NULL, option_c TEXT NOT NULL, option_d TEXT NOT NULL, correct_answer TEXT NOT NULL);
  CREATE TABLE question_concepts    (id TEXT PRIMARY KEY, question_id TEXT NOT NULL REFERENCES questions(id), concept_id TEXT NOT NULL REFERENCES concepts(id));
  CREATE TABLE attempts             (id TEXT PRIMARY KEY, student_id TEXT NOT NULL, concept_id TEXT NOT NULL, question_id TEXT NOT NULL, answer_given TEXT NOT NULL, is_correct INTEGER NOT NULL, attempted_at TEXT NOT NULL);
  CREATE TABLE mastery              (id TEXT PRIMARY KEY, student_id TEXT NOT NULL, concept_id TEXT NOT NULL, score REAL NOT NULL DEFAULT 0.0, updated_at TEXT NOT NULL);
  CREATE UNIQUE INDEX mastery_student_concept_uniq  ON mastery(student_id, concept_id);
  CREATE TABLE review_schedule      (id TEXT PRIMARY KEY, student_id TEXT NOT NULL, concept_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'New', interval_days INTEGER NOT NULL DEFAULT 1, ease_factor REAL NOT NULL DEFAULT 2.5, repetitions INTEGER NOT NULL DEFAULT 0, due_date TEXT NOT NULL, last_score REAL, last_reviewed TEXT);
  CREATE UNIQUE INDEX schedule_student_concept_uniq ON review_schedule(student_id, concept_id);
  CREATE TABLE diagnostics          (id TEXT PRIMARY KEY, student_id TEXT NOT NULL, concept_id TEXT NOT NULL, flagged INTEGER NOT NULL DEFAULT 1, reason TEXT NOT NULL, created_at TEXT NOT NULL);
  CREATE TABLE ai_feedback          (id TEXT PRIMARY KEY, student_id TEXT NOT NULL, feedback_text TEXT NOT NULL, generated_at TEXT NOT NULL);
  CREATE TABLE study_plans          (id TEXT PRIMARY KEY, student_id TEXT NOT NULL, plan_text TEXT NOT NULL, generated_at TEXT NOT NULL);
`);

const service = new LearningService(db);

// ── Seed ──────────────────────────────────────────────────────────────────

const studentId = crypto.randomUUID();
db.insert(schema.students)
  .values({ id: studentId, name: 'Test Student', grade: 5 })
  .run();

const chain      = ['Multiplication', 'Division', 'Fractions', 'Algebra', 'Pre-Algebra'];
const conceptIds = chain.map(() => crypto.randomUUID());

chain.forEach((name, i) =>
  db.insert(schema.concepts)
    .values({ id: conceptIds[i], name, subject: 'Math' })
    .run()
);

// Build chain edges: each concept depends on the one before it
for (let i = 0; i < conceptIds.length - 1; i++) {
  db.insert(schema.conceptDependencies)
    .values({
      id:             crypto.randomUUID(),
      prerequisiteId: conceptIds[i],
      dependentId:    conceptIds[i + 1],
    })
    .run();
}

// 2 questions per concept, correct answer is always 'A'
const questionIds = chain.flatMap((_, ci) =>
  [0, 1].map(() => {
    const qid = crypto.randomUUID();
    db.insert(schema.questions)
      .values({
        id: qid, text: `Question for ${chain[ci]}`, difficulty: 'Medium',
        grade: 5, subject: 'Math',
        optionA: 'A', optionB: 'B', optionC: 'C', optionD: 'D',
        correctAnswer: 'A',
      })
      .run();
    db.insert(schema.questionConcepts)
      .values({ id: crypto.randomUUID(), questionId: qid, conceptId: conceptIds[ci] })
      .run();
    return qid;
  })
);

// ── Simulate: student fails both Pre-Algebra questions ────────────────────

console.log('\nSimulating 2 failed attempts on Pre-Algebra...\n');

const preAlgebraQIds = questionIds.slice(8);
const results = preAlgebraQIds.map((qid) =>
  service.recordAttempt({
    studentId,
    conceptId:   conceptIds[4],
    questionId:  qid,
    answerGiven: 'B', // wrong — correct is 'A'
    isCorrect:   false,
  })
);

// ── Verify ────────────────────────────────────────────────────────────────

// Use raw better-sqlite3 for verification reads — bypasses Drizzle builder inconsistencies
const flagged  = sqlite.prepare(`SELECT * FROM diagnostics    WHERE student_id = ?`).all(studentId) as any[];
const schedule = sqlite.prepare(`SELECT * FROM review_schedule WHERE student_id = ?`).all(studentId) as any[];

console.log('─── Review Schedule ───────────────────────────────────');
schedule.forEach((row) => {
  const name = chain[conceptIds.indexOf(row.concept_id)] ?? row.concept_id;
  console.log(`  ${name.padEnd(16)} status=${row.status.padEnd(8)} interval=${row.interval_days}d  ease=${row.ease_factor}  due=${row.due_date}`);
});

console.log('\n─── Diagnostics Flagged ───────────────────────────────');
flagged.forEach((row) => {
  const name = chain[conceptIds.indexOf(row.concept_id)] ?? row.concept_id;
  console.log(`  [FLAGGED] ${name}: ${row.reason}`);
});

const algebraFlagged = flagged.some((d) => d.concept_id === conceptIds[3]);

console.log('\n─── Result ────────────────────────────────────────────');
console.log(`  Mastery after 2 fails : ${(results[1].masteryScore * 100).toFixed(0)}%`);
console.log(`  SR status             : ${results[1].status}`);
console.log(`  Next review due       : ${results[1].nextReviewDate}`);
console.log(`  Prerequisites flagged : ${results[1].prerequisitesFlagged.length}`);
console.log(`\n  ${algebraFlagged ? 'PASS' : 'FAIL'} -- Algebra was ${algebraFlagged ? '' : 'NOT '}auto-flagged as a prerequisite gap`);