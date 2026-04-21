export interface ConceptData {
  concept: string;
  masteryScore: number;
  bktProb: number;
  status: "mastered" | "learning" | "struggling";
}

export interface SM2Item {
  concept: string;
  nextDate: string;
  easeFactor: number;
}

export interface StudentInfo {
  id: string;
  name: string;
  grade: string;
  overallMastery: number;
}

export interface ClassStudent {
  id: string;
  name: string;
  scores: number[];
  archetype: "Rapid" | "Steady" | "At-Risk";
}

export interface ExamHistory {
  id: string;
  title: string;
  date: string;
  score: number;
  aiFeedback: string;
  studyPlan: string[];
}

export const concepts = [
  "Addition", "Subtraction", "Multiplication", "Division",
  "Fractions", "Decimals", "Percentages", "Ratios",
  "Algebra Basics", "Linear Equations", "Geometry", "Statistics"
];

export const studentInfo: StudentInfo = {
  id: "S01",
  name: "Jake",
  grade: "8th",
  overallMastery: 0.72,
};

export const conceptData: ConceptData[] = [
  { concept: "Addition", masteryScore: 0.95, bktProb: 0.97, status: "mastered" },
  { concept: "Subtraction", masteryScore: 0.92, bktProb: 0.94, status: "mastered" },
  { concept: "Multiplication", masteryScore: 0.88, bktProb: 0.90, status: "mastered" },
  { concept: "Division", masteryScore: 0.78, bktProb: 0.80, status: "learning" },
  { concept: "Fractions", masteryScore: 0.55, bktProb: 0.58, status: "struggling" },
  { concept: "Decimals", masteryScore: 0.72, bktProb: 0.75, status: "learning" },
  { concept: "Percentages", masteryScore: 0.68, bktProb: 0.70, status: "learning" },
  { concept: "Ratios", masteryScore: 0.60, bktProb: 0.63, status: "struggling" },
  { concept: "Algebra Basics", masteryScore: 0.85, bktProb: 0.87, status: "mastered" },
  { concept: "Linear Equations", masteryScore: 0.45, bktProb: 0.48, status: "struggling" },
  { concept: "Geometry", masteryScore: 0.70, bktProb: 0.73, status: "learning" },
  { concept: "Statistics", masteryScore: 0.62, bktProb: 0.65, status: "learning" },
];

export const sm2Schedule: SM2Item[] = [
  { concept: "Fractions", nextDate: "2026-04-11", easeFactor: 1.8 },
  { concept: "Linear Equations", nextDate: "2026-04-10", easeFactor: 1.5 },
  { concept: "Ratios", nextDate: "2026-04-12", easeFactor: 2.0 },
  { concept: "Division", nextDate: "2026-04-13", easeFactor: 2.2 },
  { concept: "Percentages", nextDate: "2026-04-14", easeFactor: 2.1 },
];

export const classData: ClassStudent[] = [
  { id: "S01", name: "Jake M.", scores: [95,92,88,78,55,72,68,60,85,45,70,62], archetype: "Steady" },
  { id: "S02", name: "Mia R.", scores: [90,85,80,40,30,65,55,50,70,35,60,45], archetype: "At-Risk" },
  { id: "S03", name: "Leo T.", scores: [98,97,95,92,88,90,85,82,95,80,88,85], archetype: "Rapid" },
  { id: "S04", name: "Ava K.", scores: [88,82,75,70,60,68,62,58,72,50,65,55], archetype: "Steady" },
  { id: "S05", name: "Noah P.", scores: [70,65,55,45,35,50,42,38,55,30,48,40], archetype: "At-Risk" },
  { id: "S06", name: "Emma S.", scores: [96,94,92,88,82,85,80,78,90,75,82,78], archetype: "Rapid" },
  { id: "S07", name: "Liam H.", scores: [85,80,78,72,58,65,60,55,75,48,62,58], archetype: "Steady" },
  { id: "S08", name: "Zoe W.", scores: [92,90,85,80,70,75,72,68,82,62,72,68], archetype: "Steady" },
  { id: "S09", name: "Eli C.", scores: [75,70,60,50,38,55,48,42,60,32,50,45], archetype: "At-Risk" },
  { id: "S10", name: "Ivy L.", scores: [97,95,93,90,85,88,82,80,92,78,85,80], archetype: "Rapid" },
];

export const examHistory: ExamHistory[] = [
  {
    id: "E1",
    title: "Mid-Term Assessment",
    date: "2026-03-15",
    score: 72,
    aiFeedback: "Jake demonstrated strong arithmetic skills but struggled with fraction-to-decimal conversions. The pattern suggests a conceptual gap in understanding place value relationships. Focused practice on number line representations would bridge this gap effectively.",
    studyPlan: ["Review fraction-decimal equivalence", "Practice 20 number line problems", "Complete mixed operations worksheet"],
  },
  {
    id: "E2",
    title: "Algebra Readiness Quiz",
    date: "2026-03-28",
    score: 65,
    aiFeedback: "Performance on variable isolation was below target. Jake correctly set up equations 80% of the time but made errors during the solving steps. This indicates procedural rather than conceptual difficulty. Repetitive drill with immediate feedback is recommended.",
    studyPlan: ["Solve 15 one-step equations daily", "Watch video on inverse operations", "Attempt 5 word problems for application"],
  },
  {
    id: "E3",
    title: "Weekly Practice Set #12",
    date: "2026-04-05",
    score: 81,
    aiFeedback: "Significant improvement in fractions after targeted practice. Geometry questions revealed a need for better spatial reasoning. Consider using manipulatives or visual aids to strengthen understanding of angle relationships.",
    studyPlan: ["Complete geometry visualization exercises", "Review angle theorems", "Take a timed mini-quiz on mixed topics"],
  },
];

export const diagnosticQuestions = Array.from({ length: 36 }, (_, i) => ({
  id: i + 1,
  question: `Question ${i + 1}: ${concepts[i % 12]} — Which of the following is correct?`,
  options: ["Option A", "Option B", "Option C", "Option D"],
  concept: concepts[i % 12],
}));
