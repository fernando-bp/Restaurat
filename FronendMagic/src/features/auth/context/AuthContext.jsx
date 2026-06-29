import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useState } from 'react'
import { login as loginRequest } from '../services/authService'
import apiClient from '../../../shared/api/apiClient'

const AuthContext = createContext(null)

const initialState = {
  user: null,
  token: null,
}

function isTokenExpired(token) {
  if (!token) return true

  try {
    const [, payloadBase64] = token.split('.')
    const payload = JSON.parse(decodeURIComponent(atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/')).split('').map((c) => `%${(`00${c.charCodeAt(0).toString(16)}`).slice(-2)}`).join('')))
    return Boolean(payload.exp && payload.exp * 1000 <= Date.now())
  } catch {
    return true
  }
}

function authReducer(state, action) {
  switch (action.type) {
    case 'LOGIN':
      return { ...state, user: action.payload.user, token: action.payload.token }
    case 'LOGOUT':
      return { ...initialState }
    default:
      return state
  }
}

export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState)
  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('mvpos_token')
    const user = localStorage.getItem('mvpos_user')

    try {
      if (!token || isTokenExpired(token)) {
        localStorage.removeItem('mvpos_token')
        localStorage.removeItem('mvpos_user')
        delete apiClient.defaults.headers.common.Authorization
        return
      }

      apiClient.defaults.headers.common.Authorization = `Bearer ${token}`
      if (user) {
        try {
          const parsedUser = JSON.parse(user)
          dispatch({ type: 'LOGIN', payload: { token, user: parsedUser } })
        } catch (parseError) {
          console.warn('AuthContext: failed to parse stored user, clearing auth data.', parseError)
          localStorage.removeItem('mvpos_token')
          localStorage.removeItem('mvpos_user')
          delete apiClient.defaults.headers.common.Authorization
        }
      }
    } catch (error) {
      console.error('AuthContext initialization failed:', error)
      localStorage.removeItem('mvpos_token')
      localStorage.removeItem('mvpos_user')
      delete apiClient.defaults.headers.common.Authorization
    } finally {
      setInitialized(true)
    }
  }, [])

  const login = useCallback(async (username, password) => {
    const response = await loginRequest({ username, password })
    localStorage.setItem('mvpos_token', response.access_token)
    localStorage.setItem('mvpos_user', JSON.stringify(response.user))
    apiClient.defaults.headers.common.Authorization = `Bearer ${response.access_token}`
    dispatch({ type: 'LOGIN', payload: { token: response.access_token, user: response.user } })
    return response
  }, [])

  const logout = useCallback((options = { redirect: true }) => {
    localStorage.removeItem('mvpos_token')
    localStorage.removeItem('mvpos_user')
    delete apiClient.defaults.headers.common.Authorization
    dispatch({ type: 'LOGOUT' })
    if (options.redirect && window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  }, [])

  const value = useMemo(() => ({
    user: state.user,
    token: state.token,
    isAuthenticated: Boolean(state.token),
    initialized,
    login,
    logout,
  }), [state.user, state.token, initialized, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuthContext() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used within AuthProvider')
  }
  return context
}
