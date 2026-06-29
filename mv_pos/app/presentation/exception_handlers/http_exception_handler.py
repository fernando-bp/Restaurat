from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.exceptions import HTTPException as StarletteHTTPException


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "details": None,
                },
                "timestamp": request.scope.get("time") or "",
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        def _make_json_safe(obj):
            if isinstance(obj, bytes):
                try:
                    return obj.decode("utf-8")
                except Exception:
                    return str(obj)
            if isinstance(obj, dict):
                return {k: _make_json_safe(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_make_json_safe(v) for v in obj]
            return obj

        safe_details = _make_json_safe(exc.errors())

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Datos inválidos",
                    "details": safe_details,
                },
                "timestamp": request.scope.get("time") or "",
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        import traceback

        tb = traceback.format_exc()
        # make sure the traceback is serializable
        try:
            tb = str(tb)
        except Exception:
            tb = "<traceback unavailable>"

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": 500,
                    "message": str(exc),
                    "details": tb,
                },
                "timestamp": request.scope.get("time") or "",
            },
        )
