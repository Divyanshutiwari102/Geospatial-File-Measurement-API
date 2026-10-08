from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY


def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom exception handler for HTTPException to return error in the format:
    {"detail": ..., "code": ...}
    where code is the status code as a string.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": str(exc.status_code),
        },
    )


def generic_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions to return a 500 error with code INTERNAL_ERROR.
    """
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "code": "INTERNAL_ERROR",
        },
    )


# Optional: Add handlers for other exceptions if needed
# For example, we can handle RequestValidationError to format it similarly


def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors to return in the same format.
    """
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "code": str(HTTP_422_UNPROCESSABLE_ENTITY),
        },
    )