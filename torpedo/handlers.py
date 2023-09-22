from sanic.app import Sanic
from sanic.exceptions import (Forbidden, MethodNotSupported, NotFound,
                              PayloadTooLarge, RequestTimeout, SanicException,
                              ServerError, ServiceUnavailable, Unauthorized)
from sanic.handlers import ErrorHandler
from sanic.log import error_logger
from sanic.response import json
from tortoise.exceptions import (BaseORMException, ConfigurationError,
                                 DBConnectionError, DoesNotExist, FieldError,
                                 IncompleteInstanceError, IntegrityError,
                                 MultipleObjectsReturned, NoValuesFetched,
                                 OperationalError, ParamsError,
                                 TransactionManagementError, ValidationError)

from .clients import apm_client
from .common_utils import ServiceAttribute
from .constants import STATUS_CODE_4XX, STATUS_CODE_MAPPING, HTTPStatusCodes
from .exceptions import (BadRequestException, ForbiddenException,
                         HTTPInterServiceRequestException, JsonDecodeException,
                         NotFoundException)


def send_response(
    data=None,
    status_code=HTTPStatusCodes.SUCCESS.value,
    meta=None,
    body: dict = None,
    headers=None,
    purge_response_keys=False,
):
    """
    :param data: final response data
    :param status_code: success status code, default is 200
    :param body: Optional: Response body dict in v4 format.
    :param headers: Optional : Response headers to be sent to clients.
    :param purge_response_keys: Optional : Converts response into dict
    :return {'is_success': True, 'data': data, 'status_code': status_code}
    :param meta results
    """
    if body is not None:
        return json(body=body, status=body["status_code"])

    status_code = STATUS_CODE_MAPPING.get(status_code) or status_code
    data = {"data": data, "is_success": True, "status_code": status_code}
    if meta:
        data["meta"] = meta
    if purge_response_keys:
        return data
    return json(body=data, status=status_code, headers=headers)


def send_response_contracts(response):
    """
    :param response: success / failure response from contract of 1mgmodels
    :return sanic json
    """
    return json(body=response, status=response["status_code"])


def get_error_body_response(error: str, status_code, meta=None, error_id=None):
    """
    error will be dict like object
    error = {'message': 'an error occured', 'errors': [{'message': 'user not found'}]}
    """
    errors = list()
    error_content = None
    status_code = STATUS_CODE_MAPPING.get(status_code) or status_code

    if error_id:
        error_content = Sanic.get_app().ctx.error_content.get(error_id)
    errors.append(error_content if error_content else {"message": error})

    _error = None
    if type(error) is dict:
        _error = error
    else:
        _error = {"message": error, "errors": errors}

    error_result = {"is_success": False, "status_code": status_code, "error": _error}
    if meta:
        error_result["meta"] = meta
    return json(body=error_result, status=status_code)


async def ping(request):
    return json({"ping": "pong"}, status=HTTPStatusCodes.SUCCESS.value)


class CustomExceptionHandler(ErrorHandler):
    def default(self, request, exception):
        response = None
        if isinstance(exception, (MethodNotSupported, NotFound)):
            error_logger.error(
                "Handled exception {}, for method {}".format(
                    exception.__class__.__name__, request.endpoint
                )
            )
            apm_client.capture_exception()
            response = get_error_body_response(
                exception.args[0],
                exception.status_code,
                error_id=getattr(exception, "error_id", None),
            )
        elif isinstance(
            exception,
            (SanicException, Unauthorized, Forbidden, RequestTimeout, PayloadTooLarge),
        ):
            error_logger.error(
                "Handled exception {}, for method {}".format(
                    exception.__class__.__name__, request.endpoint
                )
            )
            apm_client.capture_exception()
            response = get_error_body_response(
                exception.args[0],
                exception.status_code,
                error_id=getattr(exception, "error_id", None),
            )
        elif isinstance(exception, (BadRequestException, JsonDecodeException)):
            error_logger.info(
                "Handled exception {}, for method {}".format(
                    exception.__class__.__name__, request.endpoint
                )
            )
            response = get_error_body_response(
                exception.error,
                getattr(exception, "status_code") or HTTPStatusCodes.BAD_REQUEST.value,
                error_id=getattr(exception, "error_id", None),
            )
        elif isinstance(exception, HTTPInterServiceRequestException):
            _msg = "Inter Service exception {}, for method {}".format(
                exception.__class__.__name__, request.endpoint
            )
            if exception.status_code in STATUS_CODE_4XX:
                error_logger.info(_msg)
            else:
                error_logger.error(_msg)
                apm_client.capture_exception()

            response = get_error_body_response(
                exception.error,
                exception.status_code,
                exception.meta,
                error_id=getattr(exception, "error_id", None),
            )

        elif isinstance(exception, (NotFoundException)):
            error_logger.info(
                "Handled exception {}, for method {}".format(
                    exception.__class__.__name__, request.endpoint
                )
            )
            response = get_error_body_response(
                exception.error,
                getattr(exception, "status_code") or HTTPStatusCodes.NOT_FOUND.value,
                error_id=getattr(exception, "error_id", None),
            )
        elif isinstance(
            exception,
            (
                FieldError,
                ParamsError,
                TransactionManagementError,
                OperationalError,
                IntegrityError,
                NoValuesFetched,
                MultipleObjectsReturned,
                DoesNotExist,
                IncompleteInstanceError,
                ValidationError,
            ),
        ):
            error_logger.info(
                "Handled exception {}, for method {}".format(
                    exception.__class__.__name__, request.endpoint
                )
            )
            response = get_error_body_response(
                str(exception), status_code=HTTPStatusCodes.BAD_REQUEST.value
            )
        elif isinstance(
            exception, (BaseORMException, ConfigurationError, DBConnectionError)
        ):
            error_logger.info(
                "Handled exception {}, for method {}".format(
                    exception.__class__.__name__, request.endpoint
                )
            )
            response = get_error_body_response(
                str(exception), status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR.value
            )
        elif isinstance(exception, (Exception, ServerError, ServiceUnavailable)):
            error_logger.error(
                "Unhandled exception {} for method: {}".format(
                    exception.__class__.__name__, request.endpoint
                )
            )
            apm_client.capture_exception()
            response = get_error_body_response(
                "Something went wrong", HTTPStatusCodes.INTERNAL_SERVER_ERROR.value
            )
            # d = {
            #     "exception_type": exception.__class__.__name__,
            #     "method_name": request.endpoint,
            # }
            error_logger.exception(str(exception))
        elif isinstance(exception, (ForbiddenException)):
            error_logger.info(
                "Handled exception {}, for method {}".format(
                    exception.__class__.__name__, request.endpoint
                )
            )
            apm_client.capture_exception()
            response = get_error_body_response(
                exception.error,
                getattr(exception, "status_code") or HTTPStatusCodes.FORBIDDEN.value,
                error_id=getattr(exception, "error_id", None),
            )

        return response
