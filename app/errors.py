from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class InputError(ValueError):
    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code = code
        self.status = status


async def input_error_handler(_request: Request, error: InputError):
    return JSONResponse({"code": error.code, "message": str(error)}, status_code=error.status)


async def validation_error_handler(_request: Request, error: RequestValidationError):
    paths = [".".join(map(str, item["loc"])) for item in error.errors()]
    return JSONResponse({"code": "INVALID_REQUEST", "message": "请求格式有误", "fields": paths}, status_code=422)
