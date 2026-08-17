import apiClient from '../../../shared/api/apiClient'

export async function login({ username, password, tenant_slug, remember_me = false }) {
  /*
   * CONCEPTO: El tenant_slug viaja en el body del POST /auth/login.
   *
   * El backend lo usa para:
   * 1. Buscar el restaurante en el control DB
   * 2. Conectarse al DB privado del restaurante
   * 3. Verificar username + password en ese DB
   * 4. Generar el JWT con restaurante_id incrustado
   *
   * A partir de ahí, el JWT lleva toda la información necesaria
   * y no se necesita ningún header extra en requests posteriores.
   */
  const response = await apiClient.post('/auth/login', {
    username: username.trim(),
    password: password.trim(),
    tenant_slug: (tenant_slug || '').trim().toLowerCase(),
    remember_me,
  })
  return response.data
}
