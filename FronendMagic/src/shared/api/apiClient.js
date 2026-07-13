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
    if (error?.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('mvpos_token')
      localStorage.removeItem('mvpos_user')
      delete apiClient.defaults.headers.common.Authorization
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
