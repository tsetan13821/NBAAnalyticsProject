from fastapi import Request
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    """A requested resource (player, team, season...) does not exist. Rendered as HTTP 404."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class BadRequestError(Exception):
    """The request is well-formed but asks for something impossible. Rendered as HTTP 400."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.detail})


async def bad_request_handler(_: Request, exc: BadRequestError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": exc.detail})
