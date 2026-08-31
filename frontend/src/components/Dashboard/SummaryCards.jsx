export default function SummaryCards({ summary }) {
  if (!summary) return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="bg-raahi-card rounded-xl p-4 border border-white/5 animate-pulse">
          <div className="h-3 bg-white/5 rounded mb-3 w-2/3"></div>
          <div className="h-7 bg-white/5 rounded w-1/2"></div>
        </div>
      ))}
    </div>
  );

  const cards = [
    {
      label: "Total At-Risk",
      value: `₹${summary.total_at_risk_amount.toLocaleString("en-IN")}`,
      color: "text-raahi-warn",
      bg: "bg-raahi-warn/10",
      border: "border-raahi-warn/20",
      icon: "⚠️",
    },
    {
      label: "Total Recovered",
      value: `₹${summary.total_recovered_amount.toLocaleString("en-IN")}`,
      color: "text-raahi-accent",
      bg: "bg-raahi-accent/10",
      border: "border-raahi-accent/20",
      icon: "✅",
    },
    {
      label: "Recovery Rate",
      value: `${summary.recovery_rate_pct}%`,
      color: "text-raahi-accent",
      bg: "bg-raahi-accent/10",
      border: "border-raahi-accent/20",
      icon: "📈",
    },
    {
      label: "Total Records",
      value: summary.total_records,
      color: "text-raahi-text",
      bg: "bg-white/5",
      border: "border-white/10",
      icon: "🗂️",
    },
    {
      label: "Exceptions",
      value: summary.exceptions_count,
      color: "text-raahi-danger",
      bg: "bg-raahi-danger/10",
      border: "border-raahi-danger/20",
      icon: "🚨",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
      {cards.map((c) => (
        <div
          key={c.label}
          className={`${c.bg} border ${c.border} rounded-xl p-4 shadow-lg hover:scale-105 transition-transform cursor-default`}
        >
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">{c.icon}</span>
            <div className="text-raahi-muted text-xs uppercase tracking-wide">{c.label}</div>
          </div>
          <div className={`text-2xl font-bold ${c.color}`}>{c.value}</div>
        </div>
      ))}
    </div>
  );
}
