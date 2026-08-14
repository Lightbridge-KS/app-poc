"""Error plumbing that keeps the declared type and the real payload identical.

FastAPI's stock `HTTPException` serialises to `{"detail": ...}`, which would *not*
match the `ErrorOut` model declared in each route's `responses=`. Declaring one
shape and shipping another is exactly the drift this PoC argues against, so the
demo raises `ApiError` and renders it through `ErrorOut`.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.models import ErrorOut


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = ErrorOut(code=code, message=message)


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.payload.model_dump())
