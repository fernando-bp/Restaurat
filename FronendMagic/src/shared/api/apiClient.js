import axios from 'axios'
import { API_URL } from '../../config/env'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('mvpos_token')
  config.headers = config.headers || {}
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status
    if (status === 401) {
      localStorage.removeItem('mvpos_token')
      localStorage.removeItem('mvpos_user')
      delete apiClient.defaults.headers.common.Authorization
      if (window.location.pathname !== '/login') {
        window.location.replace('/login')
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
