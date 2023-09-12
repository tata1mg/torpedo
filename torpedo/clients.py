import threading

from elasticapm import Client, async_capture_span
from elasticapm.contrib.sanic import ElasticAPM
from elasticapm.contrib.sanic.utils import make_client
from elasticapm.instrumentation import register
from elasticapm.instrumentation.packages.asyncio.aiohttp_client import \
    AioHttpClientInstrumentation
from elasticapm.instrumentation.packages.asyncio.aioredis import (
    RedisConnectionInstrumentation, _get_destination_info)
from elasticapm.instrumentation.register import _instrumentation_singletons
from elasticapm.traces import DroppedSpan, execution_context
from elasticapm.utils import (get_host_from_url, sanitize_url,
                              url_to_destination_resource)
from elasticapm.utils.disttracing import TracingOptions
from elasticapm.utils.module_import import import_string

from .common_utils import CONFIG

_lock = threading.Lock()
apm_config = CONFIG.config.get("APM")
apm_config["SERVICE_NAME"] = CONFIG.config.get("NAME", "undefined")
apm_client = Client(config=apm_config)


class CustomElasticAPM(ElasticAPM):
    def _init_app(self) -> None:
        """
        Initialize all the required middleware and other application infrastructure that will perform the necessary
        capture of the APM instrumentation artifacts
        :return: None
        """
        if not self._client:
            self._client = make_client(
                config=self._client_config,
                client_cls=self._client_cls,
                **self._client_config
            )

        if not self._skip_init_exception_handler:
            self._setup_exception_manager()

        if self._client.config.instrument and self._client.config.enabled:
            instrument()

        if not self._skip_init_middleware:
            self._setup_request_handler(entity=self._app)


class CustomAioHttpClientInstrumentation(AioHttpClientInstrumentation):
    async def call(self, module, method, wrapped, instance, args, kwargs):
        method = kwargs["method"] if "method" in kwargs else args[0]
        url = kwargs["url"] if "url" in kwargs else args[1]
        url = str(url)
        resource = url_to_destination_resource(url)
        destination = {
            "service": {"name": resource, "resource": resource, "type": "external"}
        }

        signature = " ".join([method.upper(), get_host_from_url(url)])
        sub_type = get_host_from_url(url)
        url = sanitize_url(url)
        transaction = execution_context.get_transaction()

        async with async_capture_span(
            signature,
            span_type="external",
            span_subtype=sub_type,
            extra={"http": {"url": url}, "destination": destination},
            leaf=True,
        ) as span:
            leaf_span = span
            while isinstance(leaf_span, DroppedSpan):
                leaf_span = leaf_span.parent

            parent_id = leaf_span.id if leaf_span else transaction.id
            trace_parent = transaction.trace_parent.copy_from(
                span_id=parent_id, trace_options=TracingOptions(recorded=True)
            )
            headers = kwargs.get("headers") or {}
            self._set_disttracing_headers(headers, trace_parent, transaction)
            kwargs["headers"] = headers
            response = await wrapped(*args, **kwargs)
            if response:
                if span.context:
                    span.context["http"]["status_code"] = response.status
                span.set_success() if response.status < 400 else span.set_failure()  # pylint: disable=W0106
            return response


class CustomRedisConnectionInstrumentation(RedisConnectionInstrumentation):
    def call(self, module, method, wrapped, instance, args, kwargs):
        wrapped_name = self.get_wrapped_name(wrapped, instance, method)
        context = None
        func_name = args[0].decode("utf-8") if isinstance(args[0], bytes) else args[0]
        wrapped_name = "{}.{}".format(wrapped_name, func_name)
        try:
            if args and len(args) > 1:
                context = {
                    "db": {
                        "type": "query",
                        "statement": "{} {}".format(func_name, args[1]),
                    }
                }
        except:
            pass
        span = execution_context.get_span()
        if span and span.subtype == "aioredis":
            span.context["destination"] = _get_destination_info(instance)
        with async_capture_span(
            wrapped_name,
            span_type="db",
            span_subtype="redis",
            span_action="query",
            leaf=True,
            extra=context,
        ) as span:
            return wrapped(*args, **kwargs)


def instrument():
    """
    Instruments all registered methods/functions with a wrapper
    """
    with _lock:
        for obj in register.get_instrumentation_objects():
            custom = False
            if isinstance(obj, AioHttpClientInstrumentation):
                obj = "torpedo.clients.CustomAioHttpClientInstrumentation"
                custom = True
            elif isinstance(obj, RedisConnectionInstrumentation):
                obj = "torpedo.clients.CustomRedisConnectionInstrumentation"
                custom = True
            if custom:
                cls = import_string(obj)
                _instrumentation_singletons[obj] = cls()
                obj = _instrumentation_singletons[obj]
            obj.instrument()
