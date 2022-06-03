import os

from conda_project.utils import env_variable


def test_env_var_context():
    foo = '_conda_project_foo'
    assert foo not in os.environ

    with env_variable(foo, 'bar'):
        assert os.getenv(foo) == 'bar'

    assert foo not in os.environ


def test_replace_env_var_context():
    foo = '_conda_project_foo'
    os.environ[foo] = 'bar'

    with env_variable(foo, 'baz'):
        assert os.getenv(foo) == 'baz'

    assert os.getenv(foo) == 'bar'
