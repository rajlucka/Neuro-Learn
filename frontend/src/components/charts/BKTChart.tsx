import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { ConceptData } from "@/lib/api";

interface BKTChartProps {
  conceptData: ConceptData[];
}

export function BKTChart({ conceptData }: BKTChartProps) {
  const chartData = conceptData.map((c) => ({
    name:        c.concept.length > 8 ? c.concept.slice(0, 8) + "…" : c.concept,
    probability: Math.round(c.bktProb * 100),
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
        <defs>
          <linearGradient id="bktGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#6366F1" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#A855F7" stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="#94A3B8" />
        <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="#94A3B8" />
        <Tooltip
          contentStyle={{
            borderRadius: "0.75rem",
            border: "1px solid #E2E8F0",
            boxShadow: "0 4px 15px rgba(0,0,0,0.04)",
          }}
        />
        <Area
          type="monotone"
          dataKey="probability"
          stroke="#6366F1"
          fill="url(#bktGrad)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}