import asyncio
import time

import ujson as json
from aiohttp import ClientSession, ContentTypeError, TCPConnector
from multidict import MultiDict as WraperMultiDict
from sanic.log import access_logger as logger
from yarl import URL

from .common_utils import CONFIG
from .constants import CONTENT_TYPE, HTTPMethod
from .exceptions import HTTPRequestException, HTTPRequestTimeoutException
from .handlers import send_response
from .parser import BaseHttpResponseParser

SESSION = None


class BaseHttpRequest:
    _host = ""
    _timeout = 60
    _parser = BaseHttpResponseParser
    _config = CONFIG.config

    @classmethod
    async def get_session(cls):
        global SESSION
        if SESSION is None:
            conn = TCPConnector(
                limit=(cls._config.get("CONCURRENCY_LIMIT") or 0),
                limit_per_host=(cls._config.get("CONCURRENCY_LIMIT_HOST") or 0),
            )
            SESSION = ClientSession(connector=conn)
        return SESSION

    @classmethod
    def get_request_headers(cls, headers):
        if CONTENT_TYPE not in headers:
            headers[CONTENT_TYPE] = "application/json"
        return headers

    @classmethod
    async def request(
        cls,
        method: str,
        path: str,
        data: dict = None,
        query_params: dict = None,
        timeout=None,
        headers=None,
        multipart=False,
        response_headers_list=None,
        purge_response_keys=False,
    ):
        url = cls._host + path
        url = URL(url)
        url = cls.build_query_params(url, query_params)
        headers = cls.get_request_headers(headers)

        request_params = {
            "query_params": query_params,
            "url": str(url),
            "service_name": cls._config.get("NAME", "Unknown"),
            "service_version": cls._config.get("HTTP_VERSION", "Unknown"),
        }

        if isinstance(data, dict):
            request_params["data"] = data

        if multipart:
            headers["Content-Type"] = "multipart/form-data"
        else:
            if data:
                data = json.dumps(data)

        try:
            start_time = time.time()
            session = await cls.get_session()
            async with session.request(
                method,
                str(url),
                data=data,
                headers=headers,
                timeout=cls.request_timeout(timeout),
            ) as response:
                resp_status_code = response.status
                resp_headers = response.headers
                try:
                    payload = await response.json()
                except ContentTypeError:
                    payload = await response.text()
                    payload = json.loads(payload)
                end_time = time.time()

                request_time = end_time - start_time
                request_params["process_time"] = request_time

                logger.debug("{} - {}".format(str(url), request_time * 1000))
                logger.debug(json.dumps(request_params))
        except asyncio.TimeoutError as exception:
            print(exception)
            exception_message = "Inter service request timeout error"
            request_params["api_timeout_exception"] = exception_message
            raise HTTPRequestTimeoutException({"message": exception_message})
        except Exception as exception:
            exception_message = str(exception)
            request_params["exception"] = exception_message
            raise HTTPRequestException({"message": exception_message})

        if purge_response_keys:
            payload = send_response(
                data=payload, purge_response_keys=purge_response_keys
            )
        response_data = cls.parse_response(
            payload, resp_status_code, resp_headers, response_headers_list
        )
        return response_data

    @classmethod
    def parse_response(cls, response, status_code, headers, response_headers_list):
        result = cls._parser(
            response, status_code, headers, response_headers_list
        ).parse()
        return result

    @classmethod
    def request_timeout(cls, timeout):
        response_timeout = timeout or cls._timeout
        return response_timeout

    @classmethod
    def build_query_params(cls, url, query_params):
        if query_params:
            query = WraperMultiDict(url.query)
            params = []
            for key, value in query_params.items():
                if isinstance(value, bool):
                    value = "true" if value else "false"
                if value is not None:
                    if isinstance(value, list):
                        array_key = key + "[]"
                        for val in value:
                            params.append((array_key, str(val)))
                    else:
                        params.append((key, str(value)))

            url2 = url.with_query(params)
            query.extend(url2.query)
            url = url.with_query(query)
            url = url.with_fragment(None)

        return url

    @classmethod
    async def get(
        cls,
        path: str,
        data: dict = None,
        query_params: dict = None,
        timeout=None,
        headers=None,
        multipart=False,
        response_headers_list=None,
    ):
        result = await cls.request(
            HTTPMethod.GET.value,
            path,
            data=data,
            query_params=query_params,
            timeout=timeout,
            headers=headers,
            multipart=multipart,
            response_headers_list=response_headers_list,
        )
        return result

    @classmethod
    async def post(
        cls,
        path: str,
        data: dict = None,
        query_params: dict = None,
        timeout=None,
        headers=None,
        multipart=False,
        response_headers_list=None,
    ):
        result = await cls.request(
            HTTPMethod.POST.value,
            path,
            data=data,
            query_params=query_params,
            timeout=timeout,
            headers=headers,
            multipart=multipart,
            response_headers_list=response_headers_list,
        )
        return result

    @classmethod
    async def put(
        cls,
        path: str,
        data: dict = None,
        query_params: dict = None,
        timeout=None,
        headers=None,
        multipart=False,
        response_headers_list=None,
    ):
        result = await cls.request(
            HTTPMethod.PUT.value,
            path,
            data=data,
            query_params=query_params,
            timeout=timeout,
            headers=headers,
            multipart=multipart,
            response_headers_list=response_headers_list,
        )
        return result

    @classmethod
    async def patch(
        cls,
        path: str,
        data: dict = None,
        query_params: dict = None,
        timeout=None,
        headers=None,
        multipart=False,
        response_headers_list=None,
    ):
        result = await cls.request(
            HTTPMethod.PATCH.value,
            path,
            data=data,
            query_params=query_params,
            timeout=timeout,
            headers=headers,
            multipart=multipart,
            response_headers_list=response_headers_list,
        )
        return result

    @classmethod
    async def delete(
        cls,
        path: str,
        data: dict = None,
        query_params: dict = None,
        timeout=None,
        headers=None,
        multipart=False,
        response_headers_list=None,
    ):
        result = await cls.request(
            HTTPMethod.DELETE.value,
            path,
            data=data,
            query_params=query_params,
            timeout=timeout,
            headers=headers,
            multipart=multipart,
            response_headers_list=response_headers_list,
        )
        return result
