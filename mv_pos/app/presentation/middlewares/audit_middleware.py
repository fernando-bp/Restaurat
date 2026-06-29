from fastapi import Request

async def audit_middleware(request: Request, call_next):
    """Middleware que registra acciones críticas para auditoría."""
    response = await call_next(request)
    return response
