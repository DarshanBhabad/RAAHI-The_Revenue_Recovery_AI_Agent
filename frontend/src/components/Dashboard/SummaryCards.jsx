export default function SummaryCards({ summary }) {
  if (!summary) return null;

  const cards = [
    { label: "Total At-Risk", value: `₹${summary.total_at_risk_amount.toLocaleString("en-IN")}`, color: "text-raahi-warn" },
    { label: "Total Recovered", value: `₹${summary.total_recovered_amount.toLocaleString("en-IN")}`, color: "text-raahi-accent" },
    { label: "Recovery Rate", value: `${summary.recovery_rate_pct}%`, color: "text-raahi-accent" },
    { label: "Total Records", value: summary.total_records, color: "text-raahi-text" },
    { label: "Exceptions", value: summary.exceptions_count, color: "text-raahi-danger" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
      {cards.map((c) => (
        <div key={c.label} className="bg-raahi-card rounded-xl p-4 shadow-lg border border-white/5">
          <div className="text-raahi-muted text-xs uppercase tracking-wide mb-1">{c.label}</div>
          <div className={`text-2xl font-bold ${c.color}`}>{c.value}</div>
        </div>
      ))}
    </div>
  );
}