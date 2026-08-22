import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function RootCauseBreakdown({ summary }) {
  if (!summary) return null;

  const data = Object.entries(summary.breakdown_by_root_cause).map(([cause, stats]) => ({
    cause: cause.replace(/_/g, " "),
    count: stats.count,
    recovered: stats.recovered_count,
  }));

  return (
    <div className="bg-raahi-card rounded-xl p-4 shadow-lg border border-white/5 mb-6">
      <h3 className="text-raahi-text font-semibold mb-4">Recovery by Root Cause</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="cause" tick={{ fill: "#9ca3af", fontSize: 11 }} angle={-20} textAnchor="end" height={70} />
          <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
          <Tooltip contentStyle={{ backgroundColor: "#131922", border: "1px solid #333" }} />
          <Bar dataKey="count" fill="#f59e0b" name="Total" radius={[4, 4, 0, 0]} />
          <Bar dataKey="recovered" fill="#22c55e" name="Recovered" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}