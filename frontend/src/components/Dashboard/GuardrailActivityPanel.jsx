import { useEffect, useState } from "react";
import { api } from "../../api/client";

export default function GuardrailActivityPanel({ merchantId }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    const params = merchantId ? { merchant_id: merchantId } : {};
    api.get("/dashboard/guardrail-activity", { params }).then(r => setData(r.data));
  }, [merchantId]);

  if (!data || data.total_guardrail_checks === 0) return null;

  const { verdict_counts, deferral_reasons, total_guardrail_checks } = data;

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-1">Guardrail Activity</h3>
      <p className="text-raahi-muted text-xs mb-3">
        Deterministic safety checks — {total_guardrail_checks} total evaluations, zero LLM involvement.
      </p>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-black/20 rounded-lg p-3 text-center">
          <div className="text-raahi-accent text-xl font-bold">{verdict_counts.approved}</div>
          <div className="text-raahi-muted text-xs">Approved</div>
        </div>
        <div className="bg-black/20 rounded-lg p-3 text-center">
          <div className="text-raahi-warn text-xl font-bold">{verdict_counts.modified}</div>
          <div className="text-raahi-muted text-xs">Deferred</div>
        </div>
        <div className="bg-black/20 rounded-lg p-3 text-center">
          <div className="text-raahi-danger text-xl font-bold">{verdict_counts.blocked}</div>
          <div className="text-raahi-muted text-xs">Blocked</div>
        </div>
      </div>

      {Object.keys(deferral_reasons).length > 0 && (
        <div>
          <div className="text-raahi-muted text-xs mb-2">Why deferred/blocked:</div>
          <div className="space-y-1">
            {Object.entries(deferral_reasons).map(([reason, count]) => (
              <div key={reason} className="flex justify-between text-sm bg-black/10 rounded px-2 py-1">
                <span className="text-raahi-text">{reason}</span>
                <span className="text-raahi-muted">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}