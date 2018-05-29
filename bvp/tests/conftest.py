import pytest

from bvp.app import create as create_app
from bvp.tests.utils import login, logout


@pytest.fixture(scope="session")
def app():
    # TODO: maybe get the environment identifier from a env var? We could test any local & configured env if we want.
    test_app = create_app(env="testing")
    return test_app


@pytest.fixture()
def use_auth(client):
    """
    Login an asset owner and log him out afterwards.
    This requires certain populated data of course, so there might come a redesign here.
    """
    login(client, "wind@seita.nl", "wind")

    yield ()

    def teardown():
        logout(client)
