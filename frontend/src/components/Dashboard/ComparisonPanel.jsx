import { useEffect, useState } from "react";
import { api } from "../../api/client";

export default function ComparisonPanel() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/dashboard/comparison").then(r => setData(r.data));
  }, []);

  if (!data) return null;

  const raahi = data.raahi;
  const naive = data.naive;

  const rows = [
    { label: "Total Records", raahi: raahi.total_records, naive: naive.total_records, neutral: true },
    { label: "Total At-Risk", raahi: `₹${raahi.total_at_risk.toLocaleString("en-IN")}`, naive: `₹${naive.total_at_risk.toLocaleString("en-IN")}`, neutral: true },
    { label: "Exceptions Caught", raahi: raahi.exceptions_caught, naive: naive.exceptions_caught, better: "raahi" },
    { label: "Opted-Out Customers Protected", raahi: raahi.opted_out_protected, naive: naive.opted_out_protected, better: "raahi" },
    { label: "Exhausted Retries Stopped", raahi: raahi.exhausted_retries_stopped, naive: naive.exhausted_retries_stopped, better: "raahi" },
    { label: "Channels Used (diversity)", raahi: raahi.channel_diversity, naive: naive.channel_diversity, better: "raahi" },
    { label: "Records in Active Recovery", raahi: raahi.records_in_active_recovery, naive: naive.records_in_active_recovery, neutral: true },
  ];

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-3">RAAHI vs. Naive Baseline</h3>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-raahi-muted text-xs text-left border-b border-white/10">
            <th className="pb-2">Metric</th>
            <th className="pb-2 text-right">RAAHI (Intelligent)</th>
            <th className="pb-2 text-right">Naive Baseline</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-white/5">
              <td className="py-2 text-raahi-text">{row.label}</td>
              <td className={`py-2 text-right font-semibold ${row.better === "raahi" ? "text-raahi-accent" : "text-raahi-text"}`}>
                {row.raahi}
              </td>
              <td className={`py-2 text-right font-semibold ${row.better === "naive" ? "text-raahi-accent" : "text-raahi-muted"}`}>
                {row.naive}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-3 bg-black/20 rounded-lg p-3">
        <div className="text-raahi-muted text-xs mb-1">Naive channel usage:</div>
        <div className="text-raahi-text text-xs">
          {Object.entries(naive.channel_breakdown).map(([ch, c]) => `${ch}: ${c}`).join(", ") || "None"}
        </div>
      </div>

      <p className="text-raahi-muted text-xs mt-3">
        Naive's low exception count isn't better performance — it has no mechanism to detect
        opted-out customers or exhausted retries, meaning it would keep contacting people it
        shouldn't. RAAHI's exceptions represent real protection, not failure.
      </p>
    </div>
  );
}