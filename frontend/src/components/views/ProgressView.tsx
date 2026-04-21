import { useUserType } from "@/contexts/UserTypeContext";
import { useStudentConcepts } from "@/hooks/useApi";
import { BKTChart } from "@/components/charts/BKTChart";

export function ProgressView() {
  const { studentId } = useUserType();
  const { data: conceptData, isLoading } = useStudentConcepts(studentId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-muted-foreground text-sm animate-pulse">Loading progress...</div>
      </div>
    );
  }

  const concepts = conceptData ?? [];
  const mastered  = concepts.filter(c => c.status === "mastered").length;
  const learning  = concepts.filter(c => c.status === "learning").length;
  const struggling = concepts.filter(c => c.status === "struggling").length;
  const avgMastery = concepts.length > 0
    ? Math.round(concepts.reduce((a, c) => a + c.masteryScore, 0) / concepts.length * 100)
    : 0;

  return (
    <div className="space-y-6">
      <h1 className="font-heading font-bold text-2xl">Progress Overview</h1>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Mastered",    value: mastered,          color: "text-success" },
          { label: "Learning",    value: learning,          color: "gradient-ai-text" },
          { label: "Struggling",  value: struggling,        color: "text-destructive" },
          { label: "Avg Mastery", value: `${avgMastery}%`,  color: "text-foreground" },
        ].map(s => (
          <div key={s.label} className="glass-card p-5 text-center">
            <p className={`text-3xl font-heading font-bold ${s.color}`}>{s.value}</p>
            <p className="text-sm text-muted-foreground mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="glass-card p-6">
        <h3 className="font-heading font-semibold text-lg mb-4">BKT Knowledge Probability</h3>
        <BKTChart conceptData={concepts} />
      </div>

      <div className="glass-card p-6">
        <h3 className="font-heading font-semibold text-lg mb-4">All Concepts</h3>
        {concepts.length > 0 ? (
          <div className="space-y-3">
            {concepts.map(c => (
              <div key={c.concept} className="flex items-center gap-4">
                <span className="w-36 text-sm font-medium shrink-0">{c.concept}</span>
                <div className="flex-1 h-3 bg-secondary rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      c.status === "mastered"   ? "bg-success" :
                      c.status === "learning"   ? "gradient-ai" : "bg-destructive"
                    }`}
                    style={{ width: `${c.masteryScore * 100}%` }}
                  />
                </div>
                <span className="text-sm text-muted-foreground w-12 text-right">
                  {Math.round(c.bktProb * 100)}%
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No concept data available.</p>
        )}
      </div>
    </div>
  );
}