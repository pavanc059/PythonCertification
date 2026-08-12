import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',  // Vite proxy rewrites /api → http://localhost:8000
  withCredentials: true,  // send cookies for refresh token
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: attach JWT from localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('stockiq-token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor: 401 → redirect to login
apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('stockiq-token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
