import apiClient from '../../../shared/api/apiClient'

export async function login({ username, password }) {
  const response = await apiClient.post('/auth/login', {
    username: username.trim(),
    password: password.trim(),
    remember_me: false,
  })
  return response.data
}
