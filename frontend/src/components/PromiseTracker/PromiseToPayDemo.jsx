import { useState } from "react";
import { api } from "../../api/client";

export default function PromiseToPayDemo() {
  const [transactionId, setTransactionId] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleTest = async () => {
    setLoading(true);
    try {
      const res = await api.post(`/records/${transactionId}/customer-reply`, { message });
      setResult(res.data);
    } catch (e) {
      setResult({ error: e.response?.data?.detail || "Failed" });
    }
    setLoading(false);
  };

  const samplePrompts = [
    "Haan bhai, kal tak kar dunga. Thoda busy hoon aaj.",
    "I will pay by this Friday for sure.",
    "Maybe next week, not sure yet.",
    "I already paid this, please check.",
    "Not interested, stop messaging me.",
  ];

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-2">Promise-to-Pay — NLP Intent Extraction</h3>
      <p className="text-raahi-muted text-xs mb-4">
        Paste any transaction ID and a real customer reply (English or Hinglish) — RAAHI's LLM
        genuinely parses intent and extracts a structured commitment date, or correctly rejects
        vague/negative replies.
      </p>

      <input
        placeholder="Transaction ID (e.g. from exceptions list)"
        value={transactionId}
        onChange={(e) => setTransactionId(e.target.value)}
        className="w-full bg-raahi-bg text-raahi-text text-sm p-2 rounded mb-2"
      />
      <textarea
        placeholder="Customer reply text..."
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        className="w-full bg-raahi-bg text-raahi-text text-sm p-2 rounded mb-2"
        rows={2}
      />

      <div className="flex flex-wrap gap-1 mb-3">
        {samplePrompts.map((p, i) => (
          <button
            key={i}
            onClick={() => setMessage(p)}
            className="text-xs bg-black/30 text-raahi-muted px-2 py-1 rounded hover:text-raahi-text"
          >
            "{p.slice(0, 25)}..."
          </button>
        ))}
      </div>

      <button
        onClick={handleTest}
        disabled={loading || !transactionId || !message}
        className="bg-raahi-accent text-black text-sm font-semibold px-4 py-2 rounded-lg disabled:opacity-50"
      >
        {loading ? "Extracting..." : "Extract Intent"}
      </button>

      {result && (
        <div className="mt-3 bg-black/20 rounded-lg p-3 text-sm">
          {result.error ? (
            <span className="text-raahi-danger">❌ {result.error}</span>
          ) : result.status === "promise_logged" ? (
            <div className="text-raahi-accent">
              ✅ Promise detected — pay by {result.promised_date} (confidence {(result.confidence * 100).toFixed(0)}%)
            </div>
          ) : (
            <div className="text-raahi-muted">
              ℹ️ No commitment detected: {result.reasoning}
            </div>
          )}
        </div>
      )}
    </div>
  );
}