import { useEffect, useState } from "react";
import { api } from "../../api/client";

export default function EventFeed() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const poll = () => api.get("/dashboard/recent-events").then(r => setEvents(r.data));
    poll();
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-3">Live Activity Feed</h3>
      <div className="space-y-1 max-h-64 overflow-y-auto font-mono text-xs">
        {events.map((e, i) => (
          <div key={i} className="text-raahi-muted">
            <span className="text-raahi-accent">[{e.stage}]</span> {e.summary}
          </div>
        ))}
      </div>
    </div>
  );
}