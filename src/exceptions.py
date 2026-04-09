from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from utilities.exceptions import DatabaseValidationError


async def database_validation_exception_handler(request: Request, exc: DatabaseValidationError) -> JSONResponse:
    # Create validation error in Pydantic v2 format
    error_dict = {
        "type": "value_error",
        "loc": (exc.field or "__root__",),
        "msg": exc.message,
        "input": exc.message,
    }
    # Create a RequestValidationError with the error dict
    validation_error = RequestValidationError.from_exception_data("database_validation", [error_dict])
    return await request_validation_exception_handler(
        request,
        validation_error,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Custom validation exception handler with better error messages"""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_type = error.get("type", "validation_error")
        
        # Customize error messages for common validation errors
        if error_type == "type_error.str":
            message = f"Expected string value for field '{field}', got {error.get('input', 'invalid type')}"
        elif error_type == "type_error.list":
            message = f"Expected list value for field '{field}', got {error.get('input', 'invalid type')}"
        elif error_type == "value_error.missing":
            message = f"Field '{field}' is required"
            
        errors.append({
            "field": field,
            "message": message,
            "type": error_type
        })
    
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": {
                "message": "Validation failed",
                "errors": errors
            }
        }
    )


class ObjectDoesNotExist(Exception):
    pass
