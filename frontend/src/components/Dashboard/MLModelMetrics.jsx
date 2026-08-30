import { useEffect, useState } from "react";
import { api } from "../../api/client";

export default function MLModelMetrics() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    api.get("/dashboard/ml-model-metrics").then(r => setMetrics(r.data));
  }, []);

  if (!metrics || metrics.message) return null;

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-3">Confidence Model Performance</h3>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-raahi-muted text-xs">5-fold CV ROC-AUC</div>
          <div className="text-raahi-text font-bold">
            {metrics.cv_roc_auc_mean?.toFixed(3)} (±{metrics.cv_roc_auc_std?.toFixed(3)})
          </div>
        </div>
        <div>
          <div className="text-raahi-muted text-xs">Held-out ROC-AUC</div>
          <div className="text-raahi-text font-bold">{metrics.held_out_roc_auc?.toFixed(3)}</div>
        </div>
        <div>
          <div className="text-raahi-muted text-xs">Training Samples</div>
          <div className="text-raahi-text font-bold">{metrics.training_samples}</div>
        </div>
        <div>
          <div className="text-raahi-muted text-xs">Accuracy</div>
          <div className="text-raahi-text font-bold">{(metrics.held_out_accuracy * 100).toFixed(1)}%</div>
        </div>
      </div>
    </div>
  );
}