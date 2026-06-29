import apiClient from '../../../shared/api/apiClient'

export async function login({ username, password }) {
  const response = await apiClient.post('/auth/login', {
    username,
    password,
    remember_me: false,
  })
  return response.data
}
