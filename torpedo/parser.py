from sanic.log import error_logger

from .exceptions import HTTPInterServiceRequestException
from .task import AsyncTaskResponse


class BaseHttpResponseParser:

    def __init__(self, data, status_code, headers, response_headers_list):
        self._data = data
        self._status_code = status_code
        self._headers = headers
        self._response_headers_list = response_headers_list

    def parse(self) -> AsyncTaskResponse:
        headers = self._prepare_headers()
        return AsyncTaskResponse(
            self._data,
            meta=None,
            status_code=self._status_code,
            headers=headers,
        )

    def _prepare_headers(self):
        final_headers = {}
        if self._headers and self._response_headers_list:
            for key in self._response_headers_list:
                final_headers[key] = self._headers[key]
            return final_headers

        return final_headers


class BaseApiResponseParser(BaseHttpResponseParser):
    def __init__(self, data, status_code, headers, response_headers_list):
        self._data = data
        self._status_code = status_code
        self._headers = headers
        self._response_headers_list = response_headers_list

    def parse(self):
        if self._data["is_success"]:
            headers = self._prepare_headers()
            res = AsyncTaskResponse(
                self._data["data"],
                meta=self._data.get("meta", None),
                status_code=self._data["status_code"],
                headers=headers,
            )

            return res
        else:
            error_logger.debug(self._data["error"])
            raise HTTPInterServiceRequestException(
                error=self._data["error"],
                status_code=self._data["status_code"],
                meta=self._data.get("meta", None),
            )
