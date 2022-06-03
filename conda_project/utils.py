import os
from contextlib import contextmanager


@contextmanager
def env_variable(key, value):
    old = os.environ.get(key, None)
    os.environ[key] = value

    yield

    if old is None:
        del os.environ[key]
    else:
        os.environ[key] = old
