import pytest
from chained_accounts import base
from chained_accounts.base import set_homedir


@pytest.fixture(autouse=True)
def isolated_homedir(tmp_path):
    """Redirect the keystore to a temp directory for every test."""
    old = base._homedir
    set_homedir(tmp_path)
    yield
    set_homedir(old)
