from functools import wraps

from torpedo import get_error_body_response, send_response
from torpedo.common_utils import call_anonymous_function
from torpedo.exceptions import *
from torpedo.handlers import get_error_body_response


class APIRequestDecorator:
    @classmethod
    def api_request_handler(cls, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await call_anonymous_function(func, *args, **kwargs)
            return send_response(result)

        return wrapper
