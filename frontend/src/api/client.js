import axios from "axios";

const API_BASE_URL = "https://raahi-the-revenue-recovery-ai-agent.onrender.com";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

export const getDashboardSummary = (merchantId) =>
  api.get("/dashboard/summary", { params: merchantId ? { merchant_id: merchantId } : {} }).then(r => r.data);
export const getMerchantBreakdown = () => api.get("/dashboard/merchants").then(r => r.data);
export const getRecords = (params = {}) => api.get("/records", { params }).then(r => r.data);
export const getExceptions = (merchantId) =>
  api.get("/records/exceptions/all", { params: merchantId ? { merchant_id: merchantId } : {} }).then(r => r.data);
export const getRecordTrace = (id) => api.get(`/records/${id}/trace`).then(r => r.data);
export const runPipelineNow = () => api.post("/pipeline/run").then(r => r.data);
export const getLastRun = () => api.get("/pipeline/last-run").then(r => r.data);
export const getRecord = (id) => api.get(`/records/${id}`).then(r => r.data);
export const getMerchantList = () => api.get("/dashboard/merchant-list").then(r => r.data);