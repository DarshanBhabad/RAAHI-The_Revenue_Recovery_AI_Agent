import { useEffect, useState } from "react";
import { api } from "../../api/client";

export default function RetrainStatusPanel() {
  const [status, setStatus] = useState(null);
  useEffect(() => {
    const poll = () => api.get("/dashboard/retrain-status").then(r => setStatus(r.data));
    poll();
    const interval = setInterval(poll, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!status) return null;
  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-2">Automatic Model Retraining</h3>
      <p className="text-raahi-muted text-xs mb-2">
        Confidence model + meta-blend retrain automaticall At weekend's against live data.
      </p>
      <div className="text-sm text-raahi-text">
        Last run: {status.timestamp || "pending"} — 
        Confidence: <span className={status.confidence_model === "success" ? "text-raahi-accent" : "text-raahi-danger"}>{status.confidence_model || "-"}</span>,
        Meta-blend: <span className={status.meta_blend === "success" ? "text-raahi-accent" : "text-raahi-danger"}>{status.meta_blend || "-"}</span>
      </div>
    </div>
  );
}
