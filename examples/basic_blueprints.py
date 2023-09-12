from sanic import Blueprint
from sanic.response import json

from torpedo import Host

bp1 = Blueprint('blueprint1', version='v4')
bp2 = Blueprint('blueprint2', version='v4')


@bp1.route('/hello', methods=['GET'])
async def hello(request):
    return json({'hello': 'world'}, status=200)


@bp2.route('/world', methods=['GET'])
async def world(request):
    return json({'hello': 'world'}, status=200)


if __name__ == '__main__':
    config = {
        "NAME": "basic_blueprint",
        "HOST": "0.0.0.0",
        "PORT": 6581,
        "DEBUG": True
        }

    Host._name = config['NAME']
    Host._host = config['HOST']
    Host._port = config['PORT']
    Host._workers = config.get('WORKER', 2)
    Host._debug = config['DEBUG']
    Host._config = config

    # register combined blueprint group here
    Host._handlers = [bp1, bp2]

    Host.run()
