import uuid
import time
import aiotask_context as context

from .constants import X_REQUEST_ID, X_VISITOR_ID, X_SOURCE_IP, X_SOURCE_USER_AGENT, X_SOURCE_REFERER, \
    GLOBAL_HEADERS, X_USER_AGENT


def get_request_id_from_request(request):
    return request.headers.get(X_REQUEST_ID) or str(uuid.uuid4())


async def handle_request_id(request):
    context.set(
        X_REQUEST_ID, get_request_id_from_request(request)
    )
    context.set(X_USER_AGENT, request.headers.get("user-agent"))


async def add_start_time(request):
    context.set('request_start_time', int(time.time()*1000))


async def add_response_time(request, response):
    context.set('response_time', int(time.time() * 1000) - context.get('request_start_time'))


async def global_headers_middleware_factory(request):
    global_headers = {
        X_REQUEST_ID: get_request_id_from_request(request),
        X_VISITOR_ID: request.headers.get(X_VISITOR_ID, ''),
        X_SOURCE_IP: request.headers.get(X_SOURCE_IP, ''),
        X_SOURCE_USER_AGENT: request.headers.get(X_SOURCE_USER_AGENT, ''),
        X_SOURCE_REFERER: request.headers.get(X_SOURCE_REFERER, '')
    }
    context.set(GLOBAL_HEADERS, global_headers)
