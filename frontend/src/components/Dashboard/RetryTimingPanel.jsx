import { useEffect, useState } from "react";
import { api } from "../../api/client";

export default function RetryTimingPanel() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/dashboard/retry-timing-model").then(r => setData(r.data));
  }, []);

  if (!data || data.message) return null;

  const rows = Object.entries(data.comparison_vs_baseline)
    .filter(([, v]) => v.improvement_pct > 0)
    .sort((a, b) => b[1].improvement_pct - a[1].improvement_pct);

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-1">ML-Driven Retry Timing</h3>
      <p className="text-raahi-muted text-xs mb-3">
        Learned optimal retry windows per root cause vs. fixed-time baseline
        (CV-AUC: {data.cv_roc_auc})
      </p>
      <div className="space-y-2">
        {rows.map(([cause, stats]) => (
          <div key={cause} className="flex justify-between items-center bg-black/20 rounded-lg p-2">
            <span className="text-raahi-text text-sm">{cause.replace(/_/g, " ")}</span>
            <span className="text-raahi-accent text-sm font-semibold">
              +{stats.improvement_pct}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}