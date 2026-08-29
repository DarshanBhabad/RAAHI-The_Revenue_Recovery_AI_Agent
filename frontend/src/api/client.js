import axios from "axios";

const API_BASE_URL =  "https://raahi-the-revenue-recovery-ai-agent.onrender.com" 
//  "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

export const getDashboardSummary = () => api.get("/dashboard/summary").then(r => r.data);
export const getMerchantBreakdown = () => api.get("/dashboard/merchants").then(r => r.data);
export const getRecords = (params = {}) => api.get("/records", { params }).then(r => r.data);
export const getExceptions = () => api.get("/records/exceptions/all").then(r => r.data);
export const getRecordTrace = (id) => api.get(`/records/${id}/trace`).then(r => r.data);
export const runPipelineNow = () => api.post("/pipeline/run").then(r => r.data);
export const getLastRun = () => api.get("/pipeline/last-run").then(r => r.data);
export const getRecord = (id) => api.get(`/records/${id}`).then(r => r.data);