import datetime
import importlib
import inspect
import pkgutil
import random
import socket
import time
import uuid
from functools import wraps
from urllib.parse import urlparse

import os
from git import Repo

import elasticapm

from torpedo.constants import LogLevel
from . import enums
import ujson
from sanic.log import logger

from torpedo.exceptions import ForbiddenException


def get_current_time():
    return int(time.time())


def get_uuid_token():
    return str(uuid.uuid4())


def create_random_token():
    return random.randint(100000, 999999)


def json_file_to_dict(_file: str) -> dict:
    """
    convert json file data to dict

    :param str _file: file location including name

    :rtype: dict
    :return: converted json to dict
    """
    config = None
    try:
        with open(_file) as config_file:
            config = ujson.load(config_file)
    except (TypeError, FileNotFoundError, ValueError) as exception:
        print(exception)

    return config


class CONFIG:
    config = json_file_to_dict("./config.json")


def log_combined_message(title, error, level=LogLevel.ERROR.value):
    request_params = {"exception": error}
    logger_with_level_fn = getattr(logger, level)
    logger_with_level_fn(title, extra=request_params)
    combined_error = title + " " + error
    logger.info(combined_error)


def log_combined_error(title, error):
    request_params = {"exception": error}
    logger.error(title, extra=request_params)
    combined_error = title + " " + error
    logger.info(combined_error)


def log_combined_exception(title, exception):
    error = "Exception type {} , exception {}".format(type(exception), exception)
    log_combined_error(title, error)


def instrument(span_type):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with elasticapm.async_capture_span(
                name="{}.{}".format(span_type, func.__name__), span_type=span_type
            ):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


class ServiceAttribute:
    name = ""
    host = ""
    port = ""
    branch_name = ""
    current_tag = ""

    @classmethod
    def setup_attributes(cls, _app):
        cls.name = _app.name
        cls.host = socket.gethostbyname(socket.gethostname())
        cls.port = CONFIG.config.get('PORT')
        cls.branch_name, cls.current_tag = cls._get_current_working_repo()

    @classmethod
    def _get_current_working_repo(cls) -> (str, str):
        branch_name = None
        current_tag = None

        try:
            repo = Repo(os.getcwd())
            branch = repo.active_branch
            branch_name = branch.name
            tags = repo.tags
            if tags and isinstance(tags, list):
                current_tag = tags[-1].name
        except:
            pass

        return branch_name, current_tag


def set_clients_host_for_tests(path, port):
    _clients = import_submodules(path)
    for key, _client in _clients.items():
        _host = _client.__dict__.get("_host", None)
        if _host:
            _res = urlparse(_host)
            _client._host = _host.replace(
                _res.scheme + "://" + _res.netloc, "http://127.0.0.1:{}".format(port)
            )


def import_submodules(package):
    """Import all submodules of a module, recursively, including subpackages

    :param package: package (name or actual module)
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + "." + name
        _module = importlib.import_module(full_name)

        for attribute_name in dir(_module):
            attribute = getattr(_module, attribute_name)

            if inspect.isclass(attribute):
                # Add the class to this package's variables
                results[attribute_name] = attribute

        if is_pkg:
            results.update(import_submodules(full_name))
    return results


def object_to_dict(result):
    """
    Convert object to dict
    :param result: object
    :return: dict
    """
    if hasattr(result, "__dict__"):
        result = result.__dict__
    if isinstance(result, dict):
        for key, value in result.items():
            if hasattr(value, "__dict__"):
                value = value.__dict__
            result[key] = object_to_dict(value)
            if isinstance(value, dict):
                result[key] = {k: object_to_dict(v) for k, v in value.items()}
            if isinstance(value, list):
                result[key] = [object_to_dict(r) for r in value]
    if isinstance(result, list):
        result = [object_to_dict(r) for r in result]
    if isinstance(result, datetime.datetime):
        result = result.strftime("%m-%d-%Y, %H:%M:%S")
    return result


def get_platform_value(platform_value: str):
    """
    Get the Client
    :param platform_value: Platform value string
    :return: Client value
    """
    platform_value = platform_value.lower().strip() if platform_value else ""
    if "ios" in platform_value:
        return enums.Client.IOS.value
    elif "android" in platform_value and "mobile" not in platform_value:
        return enums.Client.ANDROID.value
    elif "mweb" in platform_value:
        return enums.Client.MWEB.value
    elif "mobile" in platform_value or "web" in platform_value:
        return enums.Client.WEB.value
    else:
        return enums.Client.WEB.value


def get_page_info(count: int, records: list, limit: int, offset: int):
    """
    Get page info for paginated response
    :param count: Total Count
    :param records: List of records
    :param limit: No of records
    :param offset: No of records to skip
    :return:
    """
    return {
        "total_records": count,
        "page_number": int(offset / limit),
        "page_size": limit,
        "has_more_records": count > offset + len(records),
    }


def get_user_from_header(headers):
    """
    Get user details from header
    :param headers: Headers
    :return: User details
    """
    user = None
    shared_context = headers.get("X-SHARED-CONTEXT", None)
    if shared_context:
        user = ujson.loads(shared_context).get("user_context", None)
    if user:
        return user
    else:
        raise ForbiddenException(error={"message": "Invalid Auth Headers"})

async def call_anonymous_function(function_to_call, *args, **kwargs):
    if inspect.iscoroutinefunction(function_to_call):
        return (await function_to_call(*args, **kwargs))
    else:
        return function_to_call(*args, **kwargs)