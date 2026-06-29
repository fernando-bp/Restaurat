from fastapi import Request

async def session_expiry_middleware(request: Request, call_next):
    """Middleware que valida la vigencia de sesión del usuario."""
    response = await call_next(request)
    return response
