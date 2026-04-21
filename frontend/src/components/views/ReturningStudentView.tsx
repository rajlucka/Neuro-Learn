import { useState } from "react";
import { Sparkles, Zap, Brain, Target, Flame, CheckCircle2, HelpCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BKTChart } from "@/components/charts/BKTChart";
import { useUserType } from "@/contexts/UserTypeContext";
import { useStudent, useStudentConcepts, useStudentSchedule } from "@/hooks/useApi";

export function ReturningStudentView() {
  const { studentId } = useUserType();

  const { data: studentInfo, isLoading: loadingStudent } = useStudent(studentId);
  const { data: conceptData, isLoading: loadingConcepts } = useStudentConcepts(studentId);
  const { data: sm2Schedule } = useStudentSchedule(studentId);

  const [showReflection, setShowReflection] = useState(false);
  const [practiceMode,   setPracticeMode]   = useState(false);
  const [streak,         setStreak]         = useState(5);
  const [currentQ,       setCurrentQ]       = useState(0);
  const [feedback,       setFeedback]       = useState<"correct" | "incorrect" | null>(null);

  const isLoading = loadingStudent || loadingConcepts;

  const weakest = conceptData
    ? [...conceptData].sort((a, b) => a.masteryScore - b.masteryScore)[0]
    : null;

  const nextReview = sm2Schedule && sm2Schedule.length > 0
    ? [...sm2Schedule].sort((a, b) => new Date(a.nextDate).getTime() - new Date(b.nextDate).getTime())[0]
    : null;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-muted-foreground text-sm animate-pulse">Loading your dashboard...</div>
      </div>
    );
  }

  if (practiceMode) {
    const practiceQuestions = [
      "What is 3/4 + 1/2?", "Solve: 2x + 5 = 11", "Convert 0.75 to a fraction",
      "What is the ratio of 6 to 9?", "Simplify: 15/25"
    ];
    return (
      <div className="max-w-xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <Button variant="outline" onClick={() => { setPracticeMode(false); setFeedback(null); setCurrentQ(0); }}>
            Back to Dashboard
          </Button>
          <div className="flex items-center gap-2 glass-card px-4 py-2">
            <Flame className="h-5 w-5 text-warning" />
            <span className="font-heading font-bold text-lg">{streak}</span>
            <span className="text-sm text-muted-foreground">streak</span>
          </div>
        </div>

        <div className="glass-card p-8 text-center">
          <p className="text-sm text-muted-foreground mb-2">Question {currentQ + 1} of {practiceQuestions.length}</p>
          <h2 className="text-xl font-heading font-semibold mb-8">{practiceQuestions[currentQ]}</h2>

          {feedback && (
            <div className={`p-4 rounded-xl mb-6 ${feedback === "correct" ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"}`}>
              <p className="font-semibold">{feedback === "correct" ? "Correct!" : "Not quite — review the concept and try again."}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 mb-6">
            {["5/4", "1 1/4", "7/4", "1/4"].map((opt, i) => (
              <button
                key={i}
                onClick={() => {
                  setFeedback(i === 0 ? "correct" : "incorrect");
                  if (i === 0) setStreak(s => s + 1);
                  else setStreak(0);
                }}
                disabled={feedback !== null}
                className="p-3 rounded-lg border border-border hover:border-primary/40 transition-all text-sm font-medium disabled:opacity-60"
              >
                {opt}
              </button>
            ))}
          </div>

          {feedback && (
            <Button onClick={() => {
              setFeedback(null);
              setCurrentQ(q => (q + 1) % practiceQuestions.length);
              setShowReflection(currentQ > 0 && (currentQ + 1) % 3 === 0);
            }}>
              Next Question
            </Button>
          )}
        </div>

        {showReflection && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 backdrop-blur-sm" onClick={() => setShowReflection(false)}>
            <div className="ai-glow-card p-8 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
              <div className="relative z-10">
                <h3 className="font-heading font-bold text-lg mb-2 flex items-center gap-2">
                  <Brain className="h-5 w-5 text-accent" /> Reflection Check
                </h3>
                <p className="text-muted-foreground text-sm mb-5">How confident did you feel on those last questions?</p>
                <div className="space-y-2">
                  {[
                    { label: "Confident", icon: CheckCircle2, color: "text-success" },
                    { label: "Guessing",  icon: HelpCircle,   color: "text-warning" },
                    { label: "Confused",  icon: XCircle,      color: "text-destructive" },
                  ].map(({ label, icon: Icon, color }) => (
                    <button
                      key={label}
                      onClick={() => setShowReflection(false)}
                      className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:bg-secondary transition-colors"
                    >
                      <Icon className={`h-5 w-5 ${color}`} />
                      <span className="font-medium">{label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* AI Helper */}
      <div className="ai-glow-card p-6">
        <div className="relative z-10 flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl gradient-ai flex items-center justify-center shrink-0">
            <Sparkles className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <h2 className="font-heading font-bold text-lg">
              Hi {studentInfo?.name ?? "there"}, you're {Math.round((studentInfo?.overallMastery ?? 0) * 100)}% of the way to mastery.
            </h2>
            <p className="text-muted-foreground mt-1">
              {weakest
                ? <>Let's finish it today! Your weakest area is <strong>{weakest.concept}</strong> — a quick 10-minute session could boost your score.</>
                : "You've mastered all concepts. Keep up the great work!"}
            </p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <button onClick={() => setPracticeMode(true)} className="glass-card p-5 text-left hover:shadow-glass-hover transition-shadow group">
          <div className="flex items-center gap-3 mb-2">
            <Target className="h-5 w-5 text-destructive" />
            <span className="font-heading font-semibold">Weakest Concept</span>
          </div>
          <p className="text-sm text-muted-foreground">
            {weakest ? `${weakest.concept} — ${Math.round(weakest.masteryScore * 100)}%` : "All concepts mastered"}
          </p>
        </button>

        <button onClick={() => setPracticeMode(true)} className="glass-card p-5 text-left hover:shadow-glass-hover transition-shadow">
          <div className="flex items-center gap-3 mb-2">
            <Zap className="h-5 w-5 text-warning" />
            <span className="font-heading font-semibold">Next Review</span>
          </div>
          <p className="text-sm text-muted-foreground">
            {nextReview ? `${nextReview.concept} — Due ${nextReview.nextDate}` : "No reviews scheduled yet"}
          </p>
        </button>

        <button onClick={() => setPracticeMode(true)} className="glass-card p-5 text-left hover:shadow-glass-hover transition-shadow">
          <div className="flex items-center gap-3 mb-2">
            <Flame className="h-5 w-5 text-accent" />
            <span className="font-heading font-semibold">Practice Mode</span>
          </div>
          <p className="text-sm text-muted-foreground">SM-2 spaced repetition</p>
        </button>
      </div>

      {/* Progress Bars */}
      <div className="glass-card p-6">
        <h3 className="font-heading font-semibold text-lg mb-4">Concept Mastery</h3>
        {conceptData && conceptData.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
            {conceptData.map((c) => (
              <div key={c.concept}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{c.concept}</span>
                  <span className="text-muted-foreground">{Math.round(c.masteryScore * 100)}%</span>
                </div>
                <div className="h-2.5 bg-secondary rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ${
                      c.status === "mastered" ? "bg-success" :
                      c.status === "learning" ? "gradient-ai" : "bg-destructive"
                    }`}
                    style={{ width: `${c.masteryScore * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No concept data available.</p>
        )}
      </div>

      {/* BKT Chart */}
      <div className="glass-card p-6">
        <h3 className="font-heading font-semibold text-lg mb-4">Knowledge Probability (BKT)</h3>
        <BKTChart conceptData={conceptData ?? []} />
      </div>
    </div>
  );
}