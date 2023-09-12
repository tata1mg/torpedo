from enum import Enum

X_HEADERS = "X-HEADERS"
X_SHARED_CONTEXT = "X-SHARED-CONTEXT"

X_REQUEST_ID = 'X-REQUEST-ID'
X_USER_AGENT = 'X-USER-AGENT'
X_VISITOR_ID = 'X-VISITOR-ID'
X_SOURCE_IP = 'X-SOURCE-IP'
X_SOURCE_USER_AGENT = 'X-SOURCE-USER-AGENT'
X_SOURCE_REFERER = 'X-SOURCE-REFERER'
X_SERVICE_NAME = 'X-SERVICE-NAME'
X_SERVICE_VERSION = 'X-SERVICE-VERSION'
CONTENT_TYPE = 'Content-Type'

GLOBAL_HEADERS = 'global_headers'


class Constant(Enum):
    DEFAULT_LIMIT = 100
    DEFAULT_OFFSET = 0


class HTTPStatusCodes(Enum):
    SUCCESS = 200
    BAD_REQUEST = 400
    NOT_FOUND = 404
    FORBIDDEN = 403
    UNAUTHORIZED = 401
    MOVED_TEMPORARILY = 302
    INTERNAL_SERVER_ERROR = 500
    REQUEST_TIMEOUT = 408


class HTTPMethod(Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"


STATUS_CODE_MAPPING = {404: 400, 403: 401, 405: 400}
STATUS_CODE_4XX = {400, 404, 401, 403}


class ListenerEventTypes(Enum):
    AFTER_SERVER_START = "after_server_start"
    BEFORE_SERVER_START = "before_server_start"
    BEFORE_SERVER_STOP = "before_server_stop"
    AFTER_SERVER_STOP = "after_server_stop"


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
