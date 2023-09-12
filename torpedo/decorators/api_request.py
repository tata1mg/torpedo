from functools import wraps

from torpedo import send_response, get_error_body_response
from torpedo.exceptions import *
from torpedo.common_utils import call_anonymous_function

from torpedo.handlers import get_error_body_response

class APIRequestDecorator:
    
    @classmethod
    def api_request_handler(cls, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await call_anonymous_function(func, *args, **kwargs)
            return send_response(result)
        return wrapper
