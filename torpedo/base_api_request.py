import aiotask_context as context

from .base_http_request import BaseHttpRequest
from .constants import GLOBAL_HEADERS, X_SERVICE_NAME, X_SERVICE_VERSION, CONTENT_TYPE
from .parser import BaseApiResponseParser


class BaseApiRequest(BaseHttpRequest):
    _parser = BaseApiResponseParser

    @classmethod
    def get_global_headers(
            cls,
    ):
        global_headers = context.get(GLOBAL_HEADERS) or dict()
        global_headers[X_SERVICE_NAME] = cls._config.get("NAME", "Unknown")
        global_headers[X_SERVICE_VERSION] = cls._config.get("HTTP_VERSION", "Unknown")
        global_headers[CONTENT_TYPE] = "application/json"
        return global_headers

    @classmethod
    def get_request_headers(cls, headers):
        global_headers = cls.get_global_headers()
        if headers:
            for key, value in global_headers.items():
                if key not in headers:
                    headers[key] = value

            return headers

        return global_headers
