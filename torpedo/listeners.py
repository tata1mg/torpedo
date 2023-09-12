import aiotask_context as context

from .exceptions import BadRequestException, JsonDecodeException


async def set_context_factory(_app, loop):
    loop.set_task_factory(context.task_factory)


def before_send(event, hint):
    if "exc_info" in hint:
        exc_type, exc_value, traceback = hint["exc_info"]
        if exc_type in [BadRequestException, JsonDecodeException]:
            return None
    return event
