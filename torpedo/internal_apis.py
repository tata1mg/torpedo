from sanic import Blueprint

from typing import Optional, Union


class InternalApiBlueprint(Blueprint):

    def __init__(
            self,
            name: str = None,
            host: Optional[str] = None,
            version: Optional[Union[int, str, float]] = None,
            strict_slashes: Optional[bool] = None,
            version_prefix: str = "/v",
    ):
        url_prefix = '/__onemg-internal__'
        super().__init__(
            name=name, url_prefix=url_prefix, host=host, version=version, strict_slashes=strict_slashes,
            version_prefix=version_prefix
        )