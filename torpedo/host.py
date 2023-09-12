from sanic import Sanic
from sanic.log import logger
from sanic.request import Request
from sanic.router import Router
from tortoise.contrib.sanic import register_tortoise
import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from contextlib import suppress

from .clients import CustomElasticAPM, apm_client
from .common_utils import CONFIG, ServiceAttribute, set_clients_host_for_tests
from .handlers import CustomExceptionHandler, ping
from .listeners import set_context_factory
from .log import patch_logging
from .middlewares import handle_request_id, add_start_time, add_response_time, global_headers_middleware_factory
from .wrappers import custom_json, request_params


class CustomRouter(Router):
    pass


class Host:
    _name = None
    _host = "0.0.0.0"
    _port = None
    _workers = 1
    _debug = False
    _config = {}
    _blueprint_group = None
    _db_config = None
    _handlers = []
    _swagger_config = None
    _multi_cache = False
    _listeners = []
    _custom_request_middlewares = []
    _custom_response_middlewares = []

    @classmethod
    def setup_host(cls):
        # sets up basic service level information for Sanic app to run.
        cls._name = cls._config["NAME"]
        cls._host = cls._config["HOST"]
        cls._port = cls._config["PORT"]
        cls._workers = cls._config.get("WORKERS", 2)  # number of workers to run,
        # keep <= num of cores debug would be true for local, make sure it is
        # false on staging and production. This flag also defines logging
        # in torpedo. If this flag is false then logs are written in files by
        # overriding the default logging settings.
        cls._debug = cls._config.get("DEBUG", True)

    @classmethod
    def setup_app_ctx(cls, _app):
        # a new ctx feature was added in Sanic 21.3.2 which allows setting context vars
        # for a sanic application
        _app.ctx.multi_cache = bool(cls._multi_cache)
        ServiceAttribute.setup_attributes(_app)

    @classmethod
    def get_app(cls):
        # this function will get the sanic app instance based on DEBUG mode. If debug mode
        # is True then logging won't be setup on local machine, i.e. logs will be
        # available only on console and no log writing
        # happens in files. If DEBUG is false then we setup our custom logging.
        app = Sanic(cls._name)
        CustomElasticAPM(app=app, client=apm_client)
        return app

    @classmethod
    def register_listeners(cls, _app):
        # registers custom listeners created via torpedo and custom listeners
        # set up by service.
        _app.register_listener(set_context_factory, "after_server_start")
        for _listener, _type in cls._listeners:
            _app.register_listener(_listener, _type)

    @classmethod
    def register_middlewares(cls, _app):
        # registers custom middleware created by torpedo.
        _app.register_middleware(handle_request_id, attach_to="request")
        _app.register_middleware(add_start_time, attach_to="request")
        _app.register_middleware(global_headers_middleware_factory, attach_to="request")
        _app.register_middleware(add_response_time, attach_to="response")

    @classmethod
    def register_custom_middlewares(cls, _app):
        for middleware in cls._custom_request_middlewares:
            _app.register_middleware(middleware, attach_to='request')
        for middleware in cls._custom_response_middlewares:
            _app.register_middleware(middleware, attach_to='response')

    @classmethod
    def register_exception_handler(cls, _app):
        # setup custom exception handlers
        _app.error_handler = CustomExceptionHandler()

    @classmethod
    def register_databases(cls, _app):
        # setup database(s)
        if cls._db_config:
            # give preference to the service level db config, if added.
            register_tortoise(_app, config=cls._db_config, generate_schemas=False)
        elif "POSTGRES_HOST" in _app.config:
            db_config = {
                "connections": {
                    "default": {
                        "engine": "tortoise.backends.asyncpg",
                        "credentials": {
                            "host": _app.config["POSTGRES_HOST"],
                            "port": _app.config["POSTGRES_PORT"],
                            "user": _app.config["POSTGRES_USER"],
                            "password": _app.config["POSTGRES_PASS"],
                            "database": _app.config["POSTGRES_DB"],
                            "minsize": _app.config.get("POSTGRES_POOL_MIN_SIZE", 1),
                            "maxsize": _app.config.get("POSTGRES_POOL_MAX_SIZE", 5),
                        },
                    },
                },
                "apps": {
                    cls._name: {
                        "models": ["app.models", "app.signals"],
                        "default_connection": "default",
                    },
                },
            }
            if "POSTGRES_REPLICA_HOST" in _app.config:
                db_config["connections"]["replica"] = {
                    "engine": "tortoise.backends.asyncpg",
                    "credentials": {
                        "host": _app.config["POSTGRES_REPLICA_HOST"],
                        "port": _app.config["POSTGRES_PORT"],
                        "user": _app.config["POSTGRES_USER"],
                        "password": _app.config["POSTGRES_PASS"],
                        "database": _app.config["POSTGRES_DB"],
                        "minsize": _app.config.get("POSTGRES_POOL_MIN_SIZE", 1),
                        "maxsize": _app.config.get("POSTGRES_POOL_MAX_SIZE", 5),
                    },
                }
            register_tortoise(_app, config=db_config, generate_schemas=False)
        else:
            logger.info("__setting up service without an active database connection__")

    @classmethod
    def register_app_blueprints(cls, _app):
        """
        :param _app: Sanic app instance
        :return:
        """
        # add a default health check handler
        _app.add_route(ping, "/ping")

        # setup blueprint group coming from the service side.
        _app.blueprint(cls._blueprint_group)

        # this loop does nothing significant but print all the routes present on service
        # via blueprints
        for route in _app.router.routes_all:
            logger.info("/".join(route))

    @classmethod
    def setup_dynamic_methods(cls):
        setattr(Request, "request_params", request_params)
        setattr(Request, "custom_json", custom_json)

    @classmethod
    def set_custom_request_middlewares(cls, custom_request_middlewares):
        cls._custom_request_middlewares = custom_request_middlewares

    @classmethod
    def set_custom_response_middlewares(cls, custom_response_middlewares):
        cls._custom_response_middlewares = custom_response_middlewares

    @classmethod
    def run_server(cls, _app):
        _app.run(host=cls._host, port=cls._port, debug=cls._debug, workers=cls._workers)

    @classmethod
    def run(cls):
        # setup host basic info from config file
        cls._config = CONFIG.config
        cls.setup_host()
        patch_logging(cls._config)
        cls._config["REQUEST_MAX_HEADER_SIZE"] = 16384

        # get instance of the app
        app = cls.get_app()
        # update app config from config.json from service directory
        app.update_config(cls._config)

        # Sanic app instance no longer support assigning attributes, instead use ctx
        cls.setup_app_ctx(app)

        cls.register_databases(app)

        cls.register_listeners(app)
        cls.register_middlewares(app)
        cls.register_custom_middlewares(app)

        cls.register_exception_handler(app)

        cls.register_app_blueprints(app)

        cls.setup_dynamic_methods()
        cls.setup_sentry(cls._config)

        cls.run_server(app)

    @classmethod
    def test_setup(
        cls,
        loop,
        sanic_client,
        path,
        app,
        blueprint_group,
        env="dev",
        gen_schemas=True,
        db_config=None,
    ):
        Sanic.test_mode = True
        cls._blueprint_group = blueprint_group
        Host.setup_app_ctx(app)
        if env.lower() != "stag":
            cls._register_test_db(app, gen_schemas, db_config)
        else:
            Host.register_databases(app)

        Host.register_listeners(app)
        Host.register_middlewares(app)
        Host.register_exception_handler(app)
        Host.register_app_blueprints(app)
        Host.setup_dynamic_methods()
        _cli = loop.run_until_complete(sanic_client(app))
        set_clients_host_for_tests(path, _cli.port)
        return _cli

    @classmethod
    def _register_test_db(cls, app, gen_schemas, db_config):
        if not db_config:
            db_config = {
                "connections": {
                    "default": "sqlite://:memory:",
                },
                "apps": {
                    "test": {
                        "models": ["app.models"],
                        "default_connection": "default",
                    },
                },
            }
        register_tortoise(app, config=db_config, generate_schemas=gen_schemas)

    async def _hub_exit_modified(request, **_):
        with suppress(IndexError):
            request.ctx._sentry_hub.__exit__(None, None, None)

    @classmethod
    def setup_sentry(cls, config):
        sentry_config = config.get("SENTRY", {})
        if sentry_config:
            sentry_sdk.set_tag("service_name", cls._name)
            sentry_sdk.set_tag("em", sentry_config.get("EM", "Conversion"))
            sentry_sdk.init(
                dsn=sentry_config.get("DSN"),
                integrations=[AioHttpIntegration()],
                environment=sentry_config.get("ENVIRONMENT", "Local"),
            )
            sentry_sdk.integrations.sanic._hub_exit = cls._hub_exit_modified
            logger.info("Sentry Integration Successful")
        else:
            logger.warning("Skipping Sentry Integration: Sentry Config Not Found")
