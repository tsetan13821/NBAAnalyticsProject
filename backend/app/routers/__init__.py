from app.schemas.common import ErrorResponse

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Not found"}}
BAD_REQUEST = {400: {"model": ErrorResponse, "description": "Impossible request"}}
