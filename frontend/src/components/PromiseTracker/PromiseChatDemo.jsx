import { useState, useRef, useEffect } from "react";
import { api } from "../../api/client";

export default function PromiseChatDemo() {
  const [transactionId, setTransactionId] = useState("");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);

  const samplePrompts = [
    "Haan bhai, kal tak kar dunga. Thoda busy hoon aaj.",
    "I will pay by this Friday for sure.",
    "Maybe next week, not sure yet.",
    "I already paid this, please check.",
    "Not interested, stop messaging me.",
  ];

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!transactionId.trim() || !message.trim()) return;
    setSending(true);

    const userMsg = { from: "customer", text: message.trim(), time: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    const sentMessage = message.trim();
    setMessage("");

    try {
      const res = await api.post(`/records/${transactionId.trim()}/customer-reply`, {
        message: sentMessage,
      });

      let systemMsg;
      if (res.data.status === "promise_logged") {
        systemMsg = {
          from: "system",
          text: `✅ Promise-to-pay logged — pay by ${res.data.promised_date} (confidence ${(res.data.confidence * 100).toFixed(0)}%). Reminders paused until then.`,
        };
      } else {
        systemMsg = {
          from: "system",
          text: `ℹ️ No commitment detected — ${res.data.reasoning}`,
        };
      }
      setMessages((prev) => [...prev, systemMsg]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { from: "system", text: `❌ ${e.response?.data?.detail || "Failed to process"}` },
      ]);
    }

    setSending(false);
  };

  return (
    <div className="bg-raahi-card rounded-xl overflow-hidden border border-white/5">
      <div className="bg-green-700 px-4 py-3 flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center text-white font-semibold">
          R
        </div>
        <div>
          <div className="text-white font-medium text-sm">RAAHI Recovery Assistant</div>
          <div className="text-green-100 text-xs">
            Real NLP extraction — live, not scripted
          </div>
        </div>
      </div>

      <div className="p-3 border-b border-white/10">
        <input
          placeholder="Transaction ID (from exceptions list)"
          value={transactionId}
          onChange={(e) => setTransactionId(e.target.value)}
          className="w-full bg-raahi-bg text-raahi-text text-xs p-2 rounded"
        />
      </div>

      <div
        className="p-4 space-y-3 min-h-[300px] max-h-[400px] overflow-y-auto"
        style={{
          backgroundColor: "#0b141a",
          backgroundImage: "radial-gradient(circle at 20px 20px, rgba(255,255,255,0.02) 1px, transparent 0)",
          backgroundSize: "20px 20px",
        }}
      >
        {messages.length === 0 && (
          <div className="text-center text-raahi-muted text-xs mt-10">
            Enter a transaction ID above, then send a message below to test
            real intent extraction.
          </div>
        )}

        {messages.map((m, i) => {
          if (m.from === "system") {
            return (
              <div key={i} className="flex justify-center">
                <span className="bg-black/40 text-raahi-muted text-xs px-3 py-2 rounded-lg max-w-[90%] text-center">
                  {m.text}
                </span>
              </div>
            );
          }
          return (
            <div key={i} className="flex justify-end">
              <div className="max-w-[75%] rounded-lg px-3 py-2 text-sm bg-[#005c4b] text-white">
                <div>{m.text}</div>
                <div className="text-[10px] text-white/50 text-right mt-1">
                  {m.time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={scrollRef} />
      </div>

      <div className="p-3 border-t border-white/10">
        <div className="flex flex-wrap gap-1 mb-2">
          {samplePrompts.map((p, i) => (
            <button
              key={i}
              onClick={() => setMessage(p)}
              className="text-xs bg-black/30 text-raahi-muted px-2 py-1 rounded hover:text-raahi-text"
            >
              "{p.slice(0, 22)}..."
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            placeholder="Type a customer reply..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            className="flex-1 bg-raahi-bg text-raahi-text text-sm p-2 rounded"
          />
          <button
            onClick={handleSend}
            disabled={sending || !transactionId.trim() || !message.trim()}
            className="bg-raahi-accent text-black text-sm font-semibold px-4 py-2 rounded-lg disabled:opacity-50"
          >
            {sending ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}