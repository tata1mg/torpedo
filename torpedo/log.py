import logging
from enum import Enum
import json
from collections import OrderedDict
from urllib.parse import urlparse

import aiotask_context as context
from pythonjsonlogger import jsonlogger

from .common_utils import ServiceAttribute
from sanic.http import Http


class LogType(Enum):
    ACCESS_LOG = 'access'
    CUSTOM_LOG = 'custom'
    BACKGROUND_CUSTOM_LOG = 'background'
    EXTERNAL_CALL_LOG = 'external'


class CustomTimeLoggingFormatter(jsonlogger.JsonFormatter):
    def __init__(self, *args, **kwargs):
        super(CustomTimeLoggingFormatter, self).__init__(*args, **kwargs)
        self.datefmt = "%Y-%m-%dT%H:%M:%S"
        self.rename_fields = {
            "levelname": "loglevel",
            "asctime": "timestamp"
        }
        self._skip_fields.update(
            {
                "elasticapm_labels": "elasticapm_labels",
                "elasticapm_service_name": "elasticapm_service_name",
                "elasticapm_transaction_id": "elasticapm_transaction_id",
                "elasticapm_trace_id": "elasticapm_trace_id",
                "elasticapm_span_id": "elasticapm_span_id",
                "elasticapm_event_dataset": "elasticapm_event_dataset",
                "elasticapm_service_environment": "elasticapm_service_environment"
            }
        )

    def format(self, record):
        """Formats a log record and serializes to json"""
        message_dict = {}
        if isinstance(record.msg, dict):
            record.message = json.dumps(record.msg)
        else:
            record.message = record.getMessage()

        # record.message can't be more than 100KB in size
        # There are approximately 2000 chars in 100KB
        if len(record.message) > 2000:
            record.message = record.message[:2000] + '.....'

        # only format time if needed
        if "asctime" in self._required_fields:
            record.asctime = self.formatTime(record, self.datefmt)

        # Display formatted exception, but allow overriding it in the
        # user-supplied dict.

        if record.exc_info and not message_dict.get("exc_info"):
            message_dict["exception_type"] = record.exc_info[0].__name__
            message_dict["exc_info"] = self.formatException(record.exc_info)
        if not message_dict.get("exc_info") and record.exc_text:
            message_dict["exc_info"] = record.exc_text
        # Display formatted record of stack frames
        # default format is a string returned from :func:`traceback.print_stack`
        try:
            if record.stack_info and not message_dict.get("stack_info"):
                message_dict["stack_info"] = self.formatStack(record.stack_info)
        except AttributeError:
            # Python2.7 doesn't have stack_info.
            pass
        try:
            log_record = OrderedDict()
        except NameError:
            log_record = {}
        self.add_fields(log_record, record, message_dict)
        log_record = self.process_log_record(log_record)
        if log_record.get("request"):
            request = log_record.get("request")
            log_record["method"] = request.split(" ")[0]
            log_record["url"] = urlparse(request.split(" ")[1]).path
            log_record["params"] = urlparse(request.split(" ")[1]).query

        log_record['traceback'] = log_record.pop('exc_info', None)
        log_record.pop("name", "")
        return self.serialize_log_record(log_record)


def patch_logging(config):

    """
    We are patching the standard logging to make sure -
    1) Each log record is a json log record
    2) Log record is consist of pre-defined set of keys only
    2) Each log record has all the pre-defined mandatory keys in it
    3) Put a limit on the log message length/size
    """

    # Don't patch if the app is running in DEBUG mode
    if config.get('DEBUG'):
        return

    log_message_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    ################################
    # Set propagate=False for Sanic loggers
    ################################
    import sanic
    for _sanic_handler in sanic.log.LOGGING_CONFIG_DEFAULTS['loggers'].values():
        _sanic_handler['propagate'] = False

    ################################
    # Patch LogRecordFactor of the logging module to include mandatory log parameters
    ################################
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)

        try:
            record.request_id = context.get('X-REQUEST-ID')
        except Exception as e:
            record.request_id = '-'

        # define logtype
        logger_name = record.name
        if logger_name == 'sanic.access':
            record.logtype = LogType.ACCESS_LOG.value
        elif logger_name == 'aiohttp.external':
            record.logtype = LogType.EXTERNAL_CALL_LOG.value
        elif record.request_id is None or record.request_id == '-':
            record.logtype = LogType.BACKGROUND_CUSTOM_LOG.value
        else:
            record.logtype = LogType.CUSTOM_LOG.value

        record.service_name = ServiceAttribute.name
        record.branchname = ServiceAttribute.branch_name
        record.current_tag = ServiceAttribute.current_tag
        record.host = '{}:{}'.format(ServiceAttribute.host, ServiceAttribute.port)

        # TODO put a check on length of record.message. If the length/size is more than the specified limit, truncate the message

        # log record version
        record.version = 'v2'
        return record

    logging.setLogRecordFactory(record_factory)

    ################################
    # Patch Sanic access log writer to include customer access log parameters
    ################################

    def log_response_custom(self) -> None:
        """
        Helper method provided to enable the logging of responses in case if
        the :attr:`HttpProtocol.access_log` is enabled.
        """
        req, res = self.request, self.response
        extra = {
            "status_code": getattr(res, "status", 0),
            "bytes_sent": getattr(
                self, "response_bytes_left", getattr(self, "response_size", -1)
            ),
            "uri": "",
            "user_agent": "",
            "http_method": "",
            "response_time": "",
            "source_ip": "-",
            "referer": "-"
        }
        if req is not None:
            extra['uri'] = req.path
            extra['http_method'] = req.method
            extra['user_agent'] = context.get("X-USER-AGENT")
            extra['response_time'] = context.get("response_time")

        logging.getLogger('sanic.access').info("", extra=extra)

    Http.log_response = log_response_custom

    ################################
    # Patch lastResort handler of the logging module - this is used a default handler for loggers with no handlers
    ################################

    fmt = CustomTimeLoggingFormatter(log_message_format)
    logging.lastResort.setFormatter(fmt)

    ################################
    # Make sure whenever a new handler is created CustomTimeLoggingFormatter is attached to it as formatter.
    # Instead of patching the logging.Handler.__init__ we have patched the the logging._addHandlerRef method because
    # logging._addHandlerRef is always called when a new handler is instantiated and it's relatively each to
    # patch this method
    ################################

    def _add_handler_ref_patched(handler):
        """
        Add a handler to the internal cleanup list using a weak reference.
        """
        from logging import _acquireLock, weakref, _removeHandlerRef, _handlerList, _releaseLock
        _acquireLock()
        try:
            fmt = CustomTimeLoggingFormatter(log_message_format)
            handler.setFormatter(fmt)
            _handlerList.append(weakref.ref(handler, _removeHandlerRef))
        finally:
            _releaseLock()

    logging._addHandlerRef = _add_handler_ref_patched

    ################################
    # All the handlers must have the CustomTimeLoggingFormatter as formatter.
    # So patch the logging.Handler.setFormatter method to ignore the setFormat operation
    ################################

    def _set_formatter_patched(self, fmt):
        """
        Set the formatter for this handler.
        """
        if not isinstance(fmt, CustomTimeLoggingFormatter):
            return
        self.formatter = fmt

    logging.Handler.setFormatter = _set_formatter_patched

    ################################
    # Update formatter in existing handlers
    ################################
    for weak_ref_handler in logging._handlerList:
        handler= weak_ref_handler()
        fmt = CustomTimeLoggingFormatter(log_message_format)
        handler.setFormatter(fmt)

