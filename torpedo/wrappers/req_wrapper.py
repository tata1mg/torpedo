from sanic.request import Request as req

from ..exceptions import JsonDecodeException


class Request(req):
    pass


def request_params(self):
    """
    function to get all query params and match_info params as query params
    :return: a dictionary of query params
    """
    params = {}
    for key, value in self.args.items():
        modified_key = key.replace("[]", "")
        if "[]" in key:
            params[modified_key] = value
        else:
            params[key] = value[0]

    for key, value in self.match_info.items():
        params[key] = value
    return params


def custom_json(self, *args, **kwargs):
    """Return BODY as JSON."""
    data = self.json
    if data is None:
        raise JsonDecodeException("Invalid Request")
    return data
