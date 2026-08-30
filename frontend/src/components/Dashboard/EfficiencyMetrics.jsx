import { useEffect, useState } from "react";
import { api } from "../../api/client";

export default function EfficiencyMetrics() {
  const [cacheMetrics, setCacheMetrics] = useState(null);

  useEffect(() => {
    api.get("/dashboard/llm-cache-metrics").then(r => setCacheMetrics(r.data));
  }, []);

  if (!cacheMetrics) return null;

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-3">LLM Efficiency — Redis Caching</h3>
      <div className="grid grid-cols-4 gap-3">
        <div>
          <div className="text-raahi-muted text-xs">Cache Hit Rate</div>
          <div className="text-raahi-accent text-xl font-bold">{cacheMetrics.hit_rate_pct}%</div>
        </div>
        <div>
          <div className="text-raahi-muted text-xs">LLM Calls Saved</div>
          <div className="text-raahi-text text-xl font-bold">{cacheMetrics.llm_calls_saved}</div>
        </div>
        <div>
          <div className="text-raahi-muted text-xs">Cache Hits</div>
          <div className="text-raahi-text text-xl font-bold">{cacheMetrics.cache_hits}</div>
        </div>
        <div>
          <div className="text-raahi-muted text-xs">Cache Misses (real calls)</div>
          <div className="text-raahi-text text-xl font-bold">{cacheMetrics.cache_misses}</div>
        </div>
      </div>
    </div>
  );
}