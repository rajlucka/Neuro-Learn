import { useState } from "react";
import { FileText, ChevronRight, Sparkles, BookOpen } from "lucide-react";
import { useUserType } from "@/contexts/UserTypeContext";
import { useStudentHistory } from "@/hooks/useApi";

export function HistoryView() {
  const { studentId } = useUserType();
  const { data: examHistory, isLoading } = useStudentHistory(studentId);
  const [selectedExam, setSelectedExam] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-muted-foreground text-sm animate-pulse">Loading exam history...</div>
      </div>
    );
  }

  const history  = examHistory ?? [];
  const selected = history.find(e => e.id === selectedExam);

  return (
    <div className="space-y-6">
      <h1 className="font-heading font-bold text-2xl">Exam History</h1>

      {history.length === 0 ? (
        <div className="glass-card p-8 text-center text-muted-foreground text-sm">
          No exam history yet. Complete the diagnostic exam to see your results here.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-3">
            {history.map(exam => (
              <button
                key={exam.id}
                onClick={() => setSelectedExam(exam.id)}
                className={`glass-card p-5 w-full text-left hover:shadow-glass-hover transition-all flex items-center justify-between ${
                  selectedExam === exam.id ? "ring-2 ring-primary/30" : ""
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                    <FileText className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="font-heading font-semibold">{exam.title}</p>
                    <p className="text-sm text-muted-foreground">{exam.date}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`font-heading font-bold text-lg ${
                    exam.score >= 80 ? "text-success" :
                    exam.score >= 60 ? "text-warning" : "text-destructive"
                  }`}>
                    {exam.score}%
                  </span>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </div>
              </button>
            ))}
          </div>

          {selected && (
            <div className="space-y-4">
              <div className="ai-glow-card p-6">
                <div className="relative z-10">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="h-5 w-5 text-accent" />
                    <h3 className="font-heading font-semibold">AI Feedback</h3>
                  </div>
                  <p className="text-sm leading-relaxed text-muted-foreground">{selected.aiFeedback}</p>
                </div>
              </div>
              <div className="glass-card p-6">
                <div className="flex items-center gap-2 mb-3">
                  <BookOpen className="h-5 w-5 text-primary" />
                  <h3 className="font-heading font-semibold">Study Plan</h3>
                </div>
                <ul className="space-y-2">
                  {selected.studyPlan.map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm">
                      <span className="w-6 h-6 rounded-full gradient-ai flex items-center justify-center text-xs text-primary-foreground font-bold shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}