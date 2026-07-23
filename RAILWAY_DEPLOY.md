# Despliegue en Railway

El repositorio se despliega como cuatro servicios: `frontend`, `api`, PostgreSQL y Redis. No subas archivos `.env` ni credenciales al repositorio.

## 1. Subir el proyecto a GitHub

1. Crea un repositorio privado en GitHub.
2. Confirma que `.env` no aparece entre los cambios.
3. Sube la rama que quieres desplegar.

## 2. Crear los servicios

En Railway crea un proyecto vacío y agrega:

1. **PostgreSQL** desde `+ New > Database > PostgreSQL`.
2. **Redis** desde `+ New > Database > Redis`.
3. **API** desde `+ New > GitHub Repo`, seleccionando este repositorio.
   - Root Directory: `/mv_pos`
   - Railway detecta `mv_pos/Dockerfile` y usa `/health` para validar el servicio.
4. **Frontend** desde `+ New > GitHub Repo`, usando el mismo repositorio.
   - Root Directory: `/FronendMagic`

Genera primero el dominio público de la API en `API > Settings > Networking > Generate Domain`. Luego genera el dominio del Frontend.

## 3. Variables de la API

En `API > Variables`, usa referencias de Railway para base de datos y Redis. Carga lo siguiente en el editor Raw, sustituyendo las variables marcadas:

```dotenv
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=crea_un_valor_largo_aleatorio_de_32_caracteres_o_mas
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
ENVIRONMENT=production
CORS_ORIGINS=["https://${{Frontend.RAILWAY_PUBLIC_DOMAIN}}"]
FACTUS_ENABLED=false
BOLD_TERMINAL_SANDBOX=true
BOLD_API_KEY_SANDBOX=
BOLD_SECRET_KEY_SANDBOX=
BOLD_API_KEY_PROD=
BOLD_SECRET_KEY_PROD=
BOLD_TERMINAL_WEBHOOK_URL=https://${{API.RAILWAY_PUBLIC_DOMAIN}}/api/v1/webhooks/bold
```

Los nombres `Postgres`, `Redis`, `API` y `Frontend` deben coincidir con los nombres que asignes a los servicios en Railway. Si eliges otros nombres, ajusta las referencias.

Cuando recibas las llaves de Bold, llena solo `BOLD_API_KEY_SANDBOX` para empezar. Para producción usa `BOLD_TERMINAL_SANDBOX=false`, `BOLD_API_KEY_PROD` y `BOLD_SECRET_KEY_PROD`.

## 4. Variable del Frontend

En `Frontend > Variables` agrega:

```dotenv
VITE_API_URL=https://${{API.RAILWAY_PUBLIC_DOMAIN}}/api/v1
```

Esta variable se usa durante la compilación; vuelve a desplegar el frontend después de crearla.

## 5. Verificación

1. Abre `https://<dominio-api>/health`; debe responder `{"status":"ok"}`.
2. Abre el dominio del frontend e inicia sesión.
3. Revisa los logs de API; no debe haber errores de conexión a PostgreSQL o Redis.
4. En Bold registra `BOLD_TERMINAL_WEBHOOK_URL` como webhook de Sandbox. Solo después de probarlo cambia a las llaves de producción y registra el webhook productivo.

Railway usa un servicio separado para cada componente del monorepo y sus variables deben configurarse en la pestaña **Variables** de cada servicio.
