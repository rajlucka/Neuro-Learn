import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { AlertTriangle } from "lucide-react";
import { useClass, useClassGaps } from "@/hooks/useApi";
import { useStudentConcepts } from "@/hooks/useApi";
import { useUserType } from "@/contexts/UserTypeContext";

const ARCHETYPE_COLORS: Record<string, string> = {
  Rapid:   "#22C55E",
  Steady:  "#6366F1",
  "At-Risk": "#EF4444",
};

function getHeatColor(score: number) {
  if (score >= 80) return "bg-success/80 text-primary-foreground";
  if (score >= 60) return "bg-warning/70 text-foreground";
  return "bg-destructive/80 text-primary-foreground";
}

export function InstructorView() {
  const { data: classData, isLoading: loadingClass } = useClass();
  const { data: gapData,   isLoading: loadingGaps  } = useClassGaps();

  // Derive concept names from first student's score count
  const firstStudent   = classData?.[0];
  const conceptCount   = firstStudent?.scores.length ?? 12;
  const conceptLabels  = Array.from({ length: conceptCount }, (_, i) => `C${i + 1}`);

  // Fetch concept names from first student to get real labels
  const { data: firstConcepts } = useStudentConcepts(firstStudent?.id ?? "");
  const conceptNames = firstConcepts?.map(c =>
    c.concept.length > 6 ? c.concept.slice(0, 6) : c.concept
  ) ?? conceptLabels;

  if (loadingClass || loadingGaps) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-muted-foreground text-sm animate-pulse">Loading instructor dashboard...</div>
      </div>
    );
  }

  const students = classData ?? [];
  const gaps     = gapData   ?? [];

  const archetypeCounts = ["Rapid", "Steady", "At-Risk"].map(name => ({
    name,
    value: students.filter(s => s.archetype === name).length,
    color: ARCHETYPE_COLORS[name],
  }));

  return (
    <div className="space-y-6">
      <h1 className="font-heading font-bold text-2xl">Instructor Dashboard</h1>

      {/* Heatmap */}
      <div className="glass-card p-6 overflow-x-auto">
        <h3 className="font-heading font-semibold text-lg mb-4">Class Mastery Heatmap</h3>
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="text-left p-2 font-medium text-muted-foreground">Student</th>
              {conceptNames.map((c, i) => (
                <th
                  key={i}
                  className="p-1 font-medium text-muted-foreground text-center"
                  style={{ writingMode: "vertical-lr", minWidth: 32 }}
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {students.map(student => (
              <tr key={student.id} className="border-t border-border">
                <td className="p-2 font-medium whitespace-nowrap">{student.name}</td>
                {student.scores.map((score, i) => (
                  <td key={i} className="p-1 text-center">
                    <div className={`w-8 h-8 rounded-md flex items-center justify-center text-[10px] font-bold ${getHeatColor(score)}`}>
                      {score}
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cluster Analytics */}
        <div className="glass-card p-6">
          <h3 className="font-heading font-semibold text-lg mb-4">Student Archetypes</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={archetypeCounts}
                cx="50%" cy="50%"
                innerRadius={55} outerRadius={85}
                dataKey="value"
                paddingAngle={4}
              >
                {archetypeCounts.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-6 mt-2">
            {archetypeCounts.map(a => (
              <div key={a.name} className="flex items-center gap-2 text-sm">
                <div className="w-3 h-3 rounded-full" style={{ background: a.color }} />
                <span>{a.name} ({a.value})</span>
              </div>
            ))}
          </div>
        </div>

        {/* Gap Analysis */}
        <div className="glass-card p-6">
          <h3 className="font-heading font-semibold text-lg mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" /> Prerequisite Gap Analysis
          </h3>
          {gaps.length === 0 ? (
            <p className="text-sm text-muted-foreground">No prerequisite gaps detected.</p>
          ) : (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {gaps.map((g, i) => (
                <div key={i} className="p-4 rounded-lg bg-destructive/5 border border-destructive/20">
                  <p className="font-medium text-sm">{g.student}</p>
                  <p className="text-sm text-muted-foreground mt-1">{g.issue}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}