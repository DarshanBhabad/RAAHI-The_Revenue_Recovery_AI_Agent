export default function ReasoningTrace({ trace }) {
  const stageColors = {
    detection: "border-blue-500",
    diagnosis: "border-teal-500",
    decision: "border-amber-500",
    guardrail: "border-purple-500",
    execution: "border-green-500",
  };

  return (
    <div className="space-y-3">
      {trace.map((log, i) => (
        <div key={i} className={`bg-raahi-card border-l-4 ${stageColors[log.stage] || "border-gray-500"} rounded-r-lg p-3`}>
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs uppercase tracking-wide text-raahi-muted font-semibold">{log.stage}</span>
            <span className="text-xs text-raahi-muted">{new Date(log.timestamp).toLocaleTimeString()}</span>
          </div>
          <div className="text-raahi-text font-medium mb-1">{log.summary}</div>
          {log.reasoning && <div className="text-raahi-muted text-sm">{log.reasoning}</div>}
        </div>
      ))}
    </div>
  );
}