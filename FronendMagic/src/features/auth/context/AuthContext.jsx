import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useState } from 'react'
import { login as loginRequest } from '../services/authService'
import apiClient from '../../../shared/api/apiClient'

const AuthContext = createContext(null)

const initialState = {
  user: null,
  token: null,
  tenantSlug: null,
}

function isTokenExpired(token) {
  if (!token) return true
  try {
    const [, payloadBase64] = token.split('.')
    const payload = JSON.parse(
      decodeURIComponent(
        atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/'))
          .split('')
          .map((c) => `%${(`00${c.charCodeAt(0).toString(16)}`).slice(-2)}`)
          .join('')
      )
    )
    return Boolean(payload.exp && payload.exp * 1000 <= Date.now())
  } catch {
    return true
  }
}

function authReducer(state, action) {
  switch (action.type) {
    case 'LOGIN':
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        tenantSlug: action.payload.tenantSlug,
      }
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
    /*
     * CONCEPTO: Rehidratar la sesión desde localStorage.
     *
     * Al recargar la página, el estado de React se pierde pero localStorage persiste.
     * Leemos el token y el usuario guardados, verificamos que el token no esté vencido,
     * y restauramos el estado de la sesión.
     *
     * También recuperamos el tenantSlug para que el próximo login (si es necesario)
     * pre-rellene el campo del restaurante.
     */
    const token = localStorage.getItem('mvpos_token')
    const userRaw = localStorage.getItem('mvpos_user')
    const tenantSlug = localStorage.getItem('mvpos_tenant_slug')

    try {
      if (!token || isTokenExpired(token)) {
        localStorage.removeItem('mvpos_token')
        localStorage.removeItem('mvpos_user')
        delete apiClient.defaults.headers.common.Authorization
        return
      }

      apiClient.defaults.headers.common.Authorization = `Bearer ${token}`

      if (userRaw) {
        const parsedUser = JSON.parse(userRaw)
        dispatch({ type: 'LOGIN', payload: { token, user: parsedUser, tenantSlug } })
      }
    } catch (error) {
      console.error('AuthContext initialization failed:', error)
      localStorage.removeItem('mvpos_token')
      localStorage.removeItem('mvpos_user')
      localStorage.removeItem('mvpos_tenant_slug')
      delete apiClient.defaults.headers.common.Authorization
    } finally {
      setInitialized(true)
    }
  }, [])

  const login = useCallback(async (username, password, tenantSlug) => {
    /*
     * CONCEPTO: Login con tenant_slug.
     *
     * Enviamos tenant_slug al backend para que sepa a qué restaurante
     * pertenece este usuario. El backend:
     *   1. Busca el restaurante en el control DB por slug
     *   2. Se conecta al DB privado del restaurante
     *   3. Verifica username + password
     *   4. Retorna JWT con restaurante_id incrustado
     *
     * Guardamos en localStorage:
     *   - mvpos_token: el JWT (lo usa apiClient en cada request)
     *   - mvpos_user: datos del usuario para mostrar en UI
     *   - mvpos_tenant_slug: el slug para rehidratación y display
     */
    localStorage.removeItem('mvpos_token')
    localStorage.removeItem('mvpos_user')
    localStorage.removeItem('mvpos_tenant_slug')
    delete apiClient.defaults.headers.common.Authorization

    const response = await loginRequest({ username, password, tenant_slug: tenantSlug })

    localStorage.setItem('mvpos_token', response.access_token)
    localStorage.setItem('mvpos_user', JSON.stringify(response.user))
    localStorage.setItem('mvpos_tenant_slug', response.restaurante_slug || tenantSlug)

    apiClient.defaults.headers.common.Authorization = `Bearer ${response.access_token}`

    dispatch({
      type: 'LOGIN',
      payload: {
        token: response.access_token,
        user: response.user,
        tenantSlug: response.restaurante_slug || tenantSlug,
      },
    })

    return response
  }, [])

  const logout = useCallback((options = { redirect: true }) => {
    localStorage.removeItem('mvpos_token')
    localStorage.removeItem('mvpos_user')
    localStorage.removeItem('mvpos_tenant_slug')
    delete apiClient.defaults.headers.common.Authorization
    dispatch({ type: 'LOGOUT' })
    if (options.redirect && window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  }, [])

  const value = useMemo(() => ({
    user: state.user,
    token: state.token,
    tenantSlug: state.tenantSlug,
    isAuthenticated: Boolean(state.token),
    initialized,
    login,
    logout,
  }), [state.user, state.token, state.tenantSlug, initialized, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuthContext() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used within AuthProvider')
  }
  return context
}
