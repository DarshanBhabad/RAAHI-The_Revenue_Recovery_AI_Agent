import { useEffect, useState } from "react";
import SummaryCards from "../components/Dashboard/SummaryCards";
import RootCauseBreakdown from "../components/Dashboard/RootCauseBreakdown";
import ExceptionList from "../components/Dashboard/ExceptionList";
import ReasoningTrace from "../components/RecordTrace/ReasoningTrace";
import { getDashboardSummary, getExceptions, getRecordTrace, getRecord, runPipelineNow } from "../api/client";
import RealCheckoutForm from "../components/Dashboard/RealCheckoutForm";
import PromiseChatDemo from "../components/PromiseTracker/PromiseChatDemo";
import EfficiencyMetrics from "../components/Dashboard/EfficiencyMetrics";
import VoiceMessagesPanel from "../components/Dashboard/VoiceMessagesPanel";
import ChannelDistributionChart from "../components/Dashboard/ChannelDistributionChart";
import OutcomeSourceBadge from "../components/Dashboard/OutcomeSourceBadge";
import MLModelMetrics from "../components/Dashboard/MLModelMetrics";
import ComparisonPanel from "../components/Dashboard/ComparisonPanel";
import EventFeed from "../components/LiveFeed/EventFeed";
import RetryTimingPanel from "../components/Dashboard/RetryTimingPanel";
import GuardrailActivityPanel from "../components/Dashboard/GuardrailActivityPanel";
import MerchantSelector from "../components/Dashboard/MerchantSelector";

const TABS = [
  { id: "overview",   label: "Overview",   icon: "📊" },
  { id: "exceptions", label: "Exceptions", icon: "🚨" },
  { id: "analytics",  label: "Analytics",  icon: "🧠" },
  { id: "tools",      label: "Tools",      icon: "🛠️" },
];

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [exceptions, setExceptions] = useState([]);
  const [selectedTrace, setSelectedTrace] = useState(null);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [selectedMerchant, setSelectedMerchant] = useState(null);

 const loadData = async () => {
  const [s, e] = await Promise.all([
    getDashboardSummary(selectedMerchant),
    getExceptions(selectedMerchant),
  ]);
  setSummary(s);
  setExceptions(e);
  setLastUpdated(new Date());
};

useEffect(() => {
  loadData();
  const interval = setInterval(loadData, 30000);
  return () => clearInterval(interval);
}, [selectedMerchant]);

  const handleSelectException = async (id) => {
    setSelectedId(id);
    setActiveTab("exceptions");
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
    <div className="min-h-screen bg-raahi-bg">
      {/* Header */}
      <div className="border-b border-white/5 bg-raahi-card/50 backdrop-blur-sm sticky top-0 z-10">
        {/* Top row: branding + actions */}
        <div className="max-w-7xl mx-auto px-6 py-3 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-raahi-accent flex items-center justify-center text-black font-bold text-sm">R</div>
            <div>
              <h1 className="text-base font-bold text-raahi-text leading-tight">RAAHI</h1>
              <p className="text-raahi-muted text-xs">Revenue Recovery AI Agent</p>
            </div>
            <div className="ml-2 flex items-center gap-1.5 bg-raahi-accent/10 border border-raahi-accent/20 rounded-full px-2.5 py-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-raahi-accent animate-pulse"></span>
              <span className="text-raahi-accent text-xs font-medium">Live</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {lastUpdated && (
              <span className="text-raahi-muted text-xs hidden md:block">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={handleRunNow}
              disabled={running}
              className="bg-raahi-accent text-black font-semibold px-4 py-1.5 rounded-lg hover:opacity-90 disabled:opacity-50 text-sm flex items-center gap-2 transition-all"
            >
              {running ? (
                <>
                  <span className="w-3 h-3 border-2 border-black/30 border-t-black rounded-full animate-spin"></span>
                  Running...
                </>
              ) : (
                <>⚡ Run Batch Now</>
              )}
            </button>
          </div>
        </div>

        {/* Tabs row */}
        <div className="max-w-7xl mx-auto px-6 flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all ${
                activeTab === tab.id
                  ? "border-raahi-accent text-raahi-accent"
                  : "border-transparent text-raahi-muted hover:text-raahi-text"
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
              {tab.id === "exceptions" && exceptions.length > 0 && (
                <span className="bg-raahi-danger text-white text-xs rounded-full px-1.5 py-0.5 leading-none">
                  {exceptions.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Merchant filter bar */}
        <div className="max-w-7xl mx-auto px-6 py-2 border-t border-white/5">
          <MerchantSelector selected={selectedMerchant} onChange={setSelectedMerchant} />
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">

        {/* OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <SummaryCards summary={summary} />
            <RootCauseBreakdown summary={summary} />
            <div className="grid md:grid-cols-2 gap-6">
              <EventFeed />
              <PromiseChatDemo />
            </div>
          </div>
        )}

        {/* EXCEPTIONS TAB */}
        {activeTab === "exceptions" && (
          <div className="space-y-6">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-raahi-danger text-lg">🚨</span>
              <h2 className="text-raahi-text font-semibold">Exceptions — Needs Human Review</h2>
              <span className="bg-raahi-danger/20 text-raahi-danger text-xs px-2 py-0.5 rounded-full">
                {exceptions.length} active
              </span>
            </div>
            <div className="grid md:grid-cols-2 gap-6">
              <ExceptionList exceptions={exceptions} onSelect={handleSelectException} />
              <div className="bg-raahi-card rounded-xl p-4 shadow-lg border border-white/5">
                <h3 className="text-raahi-text font-semibold mb-4">
                  {selectedId ? `🔍 Audit Trail — ${selectedId}` : "Select a record to see its full audit trail"}
                </h3>
                {!selectedId && (
                  <div className="flex flex-col items-center justify-center h-48 text-raahi-muted text-sm gap-2">
                    <span className="text-3xl">👈</span>
                    Click any exception to inspect its reasoning trace
                  </div>
                )}
                {selectedRecord?.voice_message_url && (
                  <div className="mb-4 bg-black/20 rounded-lg p-3 border border-white/5">
                    <div className="text-raahi-muted text-xs mb-2">🔊 Generated Hinglish Voice Message</div>
                    <audio controls src={selectedRecord.voice_message_url} className="w-full" />
                    <div className="text-raahi-text text-sm mt-2 italic">
                      "{selectedRecord.voice_message_text}"
                    </div>
                  </div>
                )}
                {selectedTrace && <ReasoningTrace trace={selectedTrace} />}
              </div>
            </div>
            <VoiceMessagesPanel />
          </div>
        )}

        {/* ANALYTICS TAB */}
        {activeTab === "analytics" && (
          <div className="space-y-6">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🧠</span>
              <h2 className="text-raahi-text font-semibold">Analytics & Model Performance</h2>
            </div>
            <div className="grid md:grid-cols-2 gap-6">
              <ChannelDistributionChart />
              <ComparisonPanel />
              <EfficiencyMetrics />
              <MLModelMetrics />
              <OutcomeSourceBadge />
              <RetryTimingPanel />
              <GuardrailActivityPanel merchantId={selectedMerchant} />
            </div>
          </div>
        )}

        {/* TOOLS TAB */}
        {activeTab === "tools" && (
          <div className="space-y-6">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🛠️</span>
              <h2 className="text-raahi-text font-semibold">Interactive Tools</h2>
            </div>
            <RealCheckoutForm />
          </div>
        )}

      </div>
    </div>
  );
}
