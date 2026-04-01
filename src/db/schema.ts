import {
  sqliteTable, text, integer, real, uniqueIndex
} from 'drizzle-orm/sqlite-core';
import { relations } from 'drizzle-orm';

const uuid  = () => crypto.randomUUID();
const now   = () => new Date().toISOString();
const today = () => new Date().toISOString().split('T')[0];

export const students = sqliteTable('students', {
  id:        text('id').primaryKey().$defaultFn(uuid),
  name:      text('name').notNull(),
  grade:     integer('grade').notNull(),
  createdAt: text('created_at').notNull().$defaultFn(now),
});

export const concepts = sqliteTable('concepts', {
  id:        text('id').primaryKey().$defaultFn(uuid),
  name:      text('name').notNull().unique(),
  subject:   text('subject').notNull(),
  createdAt: text('created_at').notNull().$defaultFn(now),
});

/**
 * Two FK columns both pointing to concepts.id.
 * Edge direction: prerequisiteId → dependentId (A must be known before B).
 * This lets the service crawl upward with WHERE dependent_id = ? to find root gaps.
 */
export const conceptDependencies = sqliteTable('concept_dependencies', {
  id:             text('id').primaryKey().$defaultFn(uuid),
  prerequisiteId: text('prerequisite_id').notNull().references(() => concepts.id),
  dependentId:    text('dependent_id').notNull().references(() => concepts.id),
});

export const questions = sqliteTable('questions', {
  id:            text('id').primaryKey().$defaultFn(uuid),
  text:          text('text').notNull(),
  difficulty:    text('difficulty').notNull(),
  grade:         integer('grade').notNull(),
  subject:       text('subject').notNull(),
  optionA:       text('option_a').notNull(),
  optionB:       text('option_b').notNull(),
  optionC:       text('option_c').notNull(),
  optionD:       text('option_d').notNull(),
  correctAnswer: text('correct_answer').notNull(),
});

export const questionConcepts = sqliteTable('question_concepts', {
  id:         text('id').primaryKey().$defaultFn(uuid),
  questionId: text('question_id').notNull().references(() => questions.id),
  conceptId:  text('concept_id').notNull().references(() => concepts.id),
});

export const attempts = sqliteTable('attempts', {
  id:          text('id').primaryKey().$defaultFn(uuid),
  studentId:   text('student_id').notNull().references(() => students.id),
  conceptId:   text('concept_id').notNull().references(() => concepts.id),
  questionId:  text('question_id').notNull().references(() => questions.id),
  answerGiven: text('answer_given').notNull(),
  isCorrect:   integer('is_correct', { mode: 'boolean' }).notNull(),
  attemptedAt: text('attempted_at').notNull().$defaultFn(now),
});

/**
 * Unique index enables onConflictDoUpdate (true upsert) without a
 * separate SELECT first. Same pattern applied to review_schedule below.
 */
export const mastery = sqliteTable('mastery', {
  id:        text('id').primaryKey().$defaultFn(uuid),
  studentId: text('student_id').notNull().references(() => students.id),
  conceptId: text('concept_id').notNull().references(() => concepts.id),
  score:     real('score').notNull().default(0.0),
  updatedAt: text('updated_at').notNull().$defaultFn(now),
}, (t) => ({
  uniq: uniqueIndex('mastery_student_concept_uniq').on(t.studentId, t.conceptId),
}));

export const reviewSchedule = sqliteTable('review_schedule', {
  id:           text('id').primaryKey().$defaultFn(uuid),
  studentId:    text('student_id').notNull().references(() => students.id),
  conceptId:    text('concept_id').notNull().references(() => concepts.id),
  status:       text('status').notNull().default('New'),
  intervalDays: integer('interval_days').notNull().default(1),
  easeFactor:   real('ease_factor').notNull().default(2.5),
  repetitions:  integer('repetitions').notNull().default(0),
  dueDate:      text('due_date').notNull().$defaultFn(today),
  lastScore:    real('last_score'),
  lastReviewed: text('last_reviewed'),
}, (t) => ({
  uniq: uniqueIndex('schedule_student_concept_uniq').on(t.studentId, t.conceptId),
}));

export const diagnostics = sqliteTable('diagnostics', {
  id:        text('id').primaryKey().$defaultFn(uuid),
  studentId: text('student_id').notNull().references(() => students.id),
  conceptId: text('concept_id').notNull().references(() => concepts.id),
  flagged:   integer('flagged', { mode: 'boolean' }).notNull().default(true),
  reason:    text('reason').notNull(),
  createdAt: text('created_at').notNull().$defaultFn(now),
});

export const aiFeedback = sqliteTable('ai_feedback', {
  id:           text('id').primaryKey().$defaultFn(uuid),
  studentId:    text('student_id').notNull().references(() => students.id),
  feedbackText: text('feedback_text').notNull(),
  generatedAt:  text('generated_at').notNull().$defaultFn(now),
});

export const studyPlans = sqliteTable('study_plans', {
  id:          text('id').primaryKey().$defaultFn(uuid),
  studentId:   text('student_id').notNull().references(() => students.id),
  planText:    text('plan_text').notNull(),
  generatedAt: text('generated_at').notNull().$defaultFn(now),
});

export const conceptsRelations = relations(concepts, ({ many }) => ({
  prerequisites: many(conceptDependencies, { relationName: 'dependent' }),
  dependents:    many(conceptDependencies, { relationName: 'prerequisite' }),
}));

export const conceptDependenciesRelations = relations(conceptDependencies, ({ one }) => ({
  prerequisite: one(concepts, {
    fields:       [conceptDependencies.prerequisiteId],
    references:   [concepts.id],
    relationName: 'prerequisite',
  }),
  dependent: one(concepts, {
    fields:       [conceptDependencies.dependentId],
    references:   [concepts.id],
    relationName: 'dependent',
  }),
}));