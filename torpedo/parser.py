from sanic.log import error_logger

from .constants import HTTPStatusCodes
from .exceptions import HTTPInterServiceRequestException
from .task import AsyncTaskResponse


class BaseApiResponseParser:
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
            error = self._data.get("error") or self._data.get("errors")
            error_logger.debug(error)
            raise HTTPInterServiceRequestException(
                error=error,
                status_code=self._data["status_code"],
                meta=self._data.get("meta", None),
            )

    def _prepare_headers(self):
        final_headers = {}
        if self._headers and self._response_headers_list:
            for key in self._response_headers_list:
                final_headers[key] = self._headers[key]
            return final_headers

        return final_headers


class TataApiResponseParser:
    def __init__(self, data, status_code, headers, response_headers_list):
        self._data = data
        self._status_code = status_code
        self._headers = headers
        self._response_headers_list = response_headers_list

    def parse(self):
        if self._status_code == HTTPStatusCodes.SUCCESS.value:
            headers = self._prepare_headers()
            res = AsyncTaskResponse(
                self._data,
                meta=self._data.get("meta", None),
                status_code=self._status_code,
                headers=headers,
            )

            return res
        else:
            err_msg = self._data.get("message") or self._data.get("error")
            error_logger.debug(err_msg)
            raise HTTPInterServiceRequestException(
                error=err_msg,
                status_code=self._status_code,
                code=self._data.get("code"),
                meta=self._data.get("meta", None),
            )

    def _prepare_headers(self):
        final_headers = {}
        if self._headers and self._response_headers_list:
            for key in self._response_headers_list:
                final_headers[key] = self._headers[key]
            return final_headers

        return final_headers


class SearchAPIResponseParser(BaseApiResponseParser):
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
            error_logger.debug(self._data["errors"])
            raise HTTPInterServiceRequestException(
                error=self._data["errors"],
                status_code=self._data["status_code"],
                meta=self._data.get("meta", None),
            )


class OrderServiceApiResponseParser:
    def __init__(self, data, status_code, headers, response_headers_list):
        self._data = data
        self._status_code = status_code
        self._headers = headers
        self._response_headers_list = response_headers_list
    def parse(self):
        if self._data.get("is_success", None):
            headers = self._prepare_headers()
            res = AsyncTaskResponse(
                self._data["data"],
                meta=self._data.get("meta", None),
                status_code=self._data["status_code"],
                headers=headers,
            )
            return res
        else:
            err_msg = self._data.get("message") or self._data.get("error")
            error_logger.debug(err_msg)
            raise HTTPInterServiceRequestException(
                error=err_msg,
                status_code=self._status_code,
                code=self._data.get("code"),
                meta=self._data.get("meta", None),
            )
    def _prepare_headers(self):
        final_headers = {}
        if self._headers and self._response_headers_list:
            for key in self._response_headers_list:
                final_headers[key] = self._headers[key]
            return final_headers
        return final_headers