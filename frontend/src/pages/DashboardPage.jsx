import { useEffect, useState } from "react";
import SummaryCards from "../components/Dashboard/SummaryCards";
import RootCauseBreakdown from "../components/Dashboard/RootCauseBreakdown";
import ExceptionList from "../components/Dashboard/ExceptionList";
import ReasoningTrace from "../components/RecordTrace/ReasoningTrace";
import { getDashboardSummary, getExceptions, getRecordTrace, getRecord, runPipelineNow } from "../api/client";
import RealCheckoutForm from "../components/Dashboard/RealCheckoutForm";

const API_BASE_URL = "https://raahi-the-revenue-recovery-ai-agent.onrender.com";

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [exceptions, setExceptions] = useState([]);
  const [selectedTrace, setSelectedTrace] = useState(null);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [running, setRunning] = useState(false);

  const loadData = async () => {
    const [s, e] = await Promise.all([getDashboardSummary(), getExceptions()]);
    setSummary(s);
    setExceptions(e);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectException = async (id) => {
    setSelectedId(id);
    const [trace, record] = await Promise.all([getRecordTrace(id), getRecord(id)]);
    setSelectedTrace(trace);
    setSelectedRecord(record);
  };

  const handleRunNow = async () => {
    setRunning(true);
    await runPipelineNow();
    await loadData();
    setRunning(false);
  };

  return (
    <div className="min-h-screen bg-raahi-bg p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-raahi-text">RAAHI — Revenue Recovery Dashboard</h1>
          <p className="text-raahi-muted text-sm">Detects, diagnoses, decides, and recovers — every action audited.</p>
        </div>
        <button
          onClick={handleRunNow}
          disabled={running}
          className="bg-raahi-accent text-black font-semibold px-4 py-2 rounded-lg hover:opacity-90 disabled:opacity-50"
        >
          {running ? "Running..." : "Run Batch Now"}
        </button>
      </div>

      <SummaryCards summary={summary} />
      <RootCauseBreakdown summary={summary} />

      <div className="grid md:grid-cols-2 gap-6">
        <ExceptionList exceptions={exceptions} onSelect={handleSelectException} />
        <div className="bg-raahi-card rounded-xl p-4 shadow-lg border border-white/5">
          <h3 className="text-raahi-text font-semibold mb-4">
            {selectedId ? `Audit Trail — ${selectedId}` : "Select a record to see its full audit trail"}
          </h3>

          {selectedRecord?.voice_message_url && (
            <div className="mb-4 bg-black/20 rounded-lg p-3 border border-white/5">
              <div className="text-raahi-muted text-xs mb-2">🔊 Generated Hinglish Voice Message</div>
              <audio
                controls
                src={selectedRecord.voice_message_url} 
                className="w-full"
              />
              <div className="text-raahi-text text-sm mt-2 italic">
                "{selectedRecord.voice_message_text}"
              </div>
            </div>
          )}

          {selectedTrace && <ReasoningTrace trace={selectedTrace} />}
        </div>
      </div>
      <div className="mt-6">
        <RealCheckoutForm />
      </div>
    </div>
  );
}