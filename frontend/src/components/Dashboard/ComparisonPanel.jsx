import { useEffect, useState } from "react";
import { api } from "../../api/client";

export default function ComparisonPanel() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/dashboard/comparison").then(r => setData(r.data));
  }, []);

  if (!data) return null;

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-3">RAAHI vs. Naive Baseline</h3>
      <div className="grid grid-cols-2 gap-4">
        {["raahi", "naive"].map((key) => (
          <div key={key} className="bg-black/20 rounded-lg p-3">
            <div className="text-raahi-text font-semibold mb-2">
              {key === "raahi" ? "RAAHI (Intelligent)" : "Naive Baseline"}
            </div>
            <div className="text-xs text-raahi-muted">Total Records</div>
            <div className="text-raahi-text mb-2">{data[key].total_records}</div>
            <div className="text-xs text-raahi-muted">Exceptions Caught</div>
            <div className={key === "raahi" ? "text-raahi-accent font-bold" : "text-raahi-danger font-bold"}>
              {data[key].exceptions_caught}
            </div>
          </div>
        ))}
      </div>
      <p className="text-raahi-muted text-xs mt-3">
        Naive's low exception count isn't better performance — it has no mechanism to detect
        opted-out customers or exhausted retries, meaning it would keep contacting people it
        shouldn't. RAAHI's exceptions represent real protection.
      </p>
    </div>
  );
}