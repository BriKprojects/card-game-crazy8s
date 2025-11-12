const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
const WS_BASE_URL = API_BASE_URL.replace('http', 'ws')

export { API_BASE_URL, WS_BASE_URL }
