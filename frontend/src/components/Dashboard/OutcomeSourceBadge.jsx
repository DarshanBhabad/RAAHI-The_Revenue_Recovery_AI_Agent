import { useEffect, useState } from "react";
import { api } from "../../api/client";

const LABELS = {
  real_verified: { label: "Real, webhook-verified", color: "text-raahi-accent" },
  modeled: { label: "Modeled (awaiting real payment)", color: "text-raahi-warn" },
  training_simulation: { label: "ML training simulation only", color: "text-raahi-muted" },
};

export default function OutcomeSourceBadge({ merchantId }) {
  const [data, setData] = useState({});

  useEffect(() => {
    const params = merchantId ? { merchant_id: merchantId } : {};
    api.get("/dashboard/outcome-source-breakdown", { params }).then(r => setData(r.data));
  }, [merchantId]);

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-3">Outcome Source — Honest Breakdown</h3>
      <div className="space-y-2">
        {Object.entries(data).map(([source, count]) => (
          <div key={source} className="flex justify-between text-sm">
            <span className={LABELS[source]?.color || "text-raahi-text"}>
              {LABELS[source]?.label || source}
            </span>
            <span className="text-raahi-text font-semibold">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}