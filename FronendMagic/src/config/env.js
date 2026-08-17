export const API_URL = import.meta.env.VITE_API_URL || '/api/v1'
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'MV-POS Frontend'

/**
 * CONCEPTO: Detección automática del tenant desde el subdominio.
 *
 * Arquitectura de URLs en producción:
 *   pizza-palace.mvpos.com   → tenant_slug = "pizza-palace"
 *   burger-king.mvpos.com    → tenant_slug = "burger-king"
 *   sushi-bar.mvpos.com      → tenant_slug = "sushi-bar"
 *
 * ¿Por qué subdominio y no ruta (/pizza-palace/mesas)?
 *   - Cada restaurante tiene su propio "espacio" — psicológicamente más limpio.
 *   - Nginx puede servir el mismo frontend para todos los subdominios con *.mvpos.com.
 *   - El tenant se resuelve en el cliente sin ningún request extra al servidor.
 *   - Los cookies y localStorage están separados por origen (subdominio distinto).
 *
 * En desarrollo (localhost):
 *   No hay subdominio → usamos VITE_TENANT_SLUG del .env local,
 *   o "default" como fallback para no romper el flujo de desarrollo.
 *
 * Cómo configurar en desarrollo:
 *   En FronendMagic/.env.local:  VITE_TENANT_SLUG=mi-restaurante-local
 *   O usar el campo en el login (ver LoginPage.jsx)
 */
function detectTenantSlug() {
  const hostname = window.location.hostname

  // En localhost o 127.0.0.1: usar variable de entorno o "default"
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname.startsWith('192.168.')) {
    return import.meta.env.VITE_TENANT_SLUG || ''
  }

  // En Railway con dominio personalizado: extraer primer segmento del subdominio
  // pizza-palace.mvpos.com → parts = ["pizza-palace", "mvpos", "com"]
  const parts = hostname.split('.')
  if (parts.length >= 3) {
    return parts[0]
  }

  // Dominio plano (sin subdominio): no hay forma de detectar el tenant
  return ''
}

export const TENANT_SLUG = detectTenantSlug()
