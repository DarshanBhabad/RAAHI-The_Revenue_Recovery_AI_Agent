import { useEffect, useState } from "react";
import { api } from "../../api/client";

export default function VoiceMessagesPanel() {
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    api.get("/dashboard/voice-messages").then(r => setMessages(r.data));
  }, []);

  if (messages.length === 0) return null;

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-3">
        🔊 Real Hinglish Voice Messages ({messages.length})
      </h3>
      <div className="space-y-3 max-h-80 overflow-y-auto">
        {messages.map((m) => (
          <div key={m.id} className="bg-black/20 rounded-lg p-3">
            <div className="flex justify-between text-xs text-raahi-muted mb-1">
              <span>{m.id}</span>
              <span>₹{m.amount.toLocaleString("en-IN")} — {m.root_cause}</span>
            </div>
            <audio controls src={m.voice_message_url} className="w-full mb-1" />
            <div className="text-raahi-text text-sm italic">"{m.voice_message_text}"</div>
          </div>
        ))}
      </div>
    </div>
  );
}