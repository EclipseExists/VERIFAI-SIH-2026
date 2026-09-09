import axios from "axios";

const API_BASE = "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 600000, // 10 min timeout for first-time AI model downloads
});

export default api;