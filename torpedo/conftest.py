import asyncio

import pytest
from pytest_sanic.utils import TestClient


@pytest.fixture(scope="session")
def loop():
    """
    Default event loop, you should only use this event loop in your tests.
    """
    loop = asyncio.get_event_loop()
    yield loop


@pytest.fixture(scope="session")
def sanic_client(loop):
    """
    Create a TestClient instance for test easy use.

    test_client(app, **kwargs)
    """
    clients = []

    async def create_client(app, **kwargs):
        client = TestClient(app, **kwargs)
        await client.start_server()
        clients.append(client)
        return client

    yield create_client

    # Clean up
    if clients:
        for client in clients:
            loop.run_until_complete(client.close())
