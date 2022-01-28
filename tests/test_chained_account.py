from typing import List

import pytest
from eth_utils import is_checksum_address
from hexbytes import HexBytes
from click.testing import CliRunner
from chained_accounts.base import ChainedAccount, find_accounts
from chained_accounts.exceptions import AccountLockedError
import random
from chained_accounts.cli import main
from chained_accounts.base import CHAINED_ACCOUNTS_HOME

pkey = HexBytes("0x7a28b5ba57c53603b0b07b56bba752f7784bf506fa95edc395f5cf6c7514fe9d")
PASSWORD = "foo"


def random_name() -> str:
    """Generate a random account name."""
    return "temp" + str(random.randint(100000, 999999))


@pytest.fixture
def test_accounts() -> List[ChainedAccount]:  # type: ignore
    """Create some test accounts"""

    a1 = ChainedAccount.import_key(random_name(), chains=[1, 4], key=pkey, password=PASSWORD)
    a2 = ChainedAccount.import_key(random_name(), chains=[2], key=pkey, password=PASSWORD)
    a3 = ChainedAccount.import_key(random_name(), chains=[1, 3], key=pkey, password=PASSWORD)

    yield [a1, a2, a3]

    # Cleanup test accounts
    a1.delete()
    a2.delete()
    a3.delete()


def test_new_evm_account(test_accounts):
    runner = CliRunner()

    # New accounts are locked
    assert not test_accounts[0].is_unlocked
    assert 1 in test_accounts[0].chains
    assert 4 in test_accounts[0].chains

    # Test loading by name
    account_copy = ChainedAccount.get(test_accounts[0].name)
    assert 1 in account_copy.chains
    assert 4 in account_copy.chains
    assert account_copy.address == test_accounts[0].address
    assert is_checksum_address(account_copy.address)

    # Some properties are not available on locked accounts
    with pytest.raises(AccountLockedError):
        print(test_accounts[0].key)

    # Unlock accounts
    test_accounts[0].unlock(PASSWORD)
    test_accounts[1].unlock(PASSWORD)

    # Verify private keys (including CLI)
    assert test_accounts[0].key == test_accounts[1].key
    result = runner.invoke(main, ["key", test_accounts[0].name, "-p", PASSWORD])
    assert pkey.hex() in result.stdout

    # Lock account and verify
    test_accounts[0].lock()
    assert not test_accounts[0].is_unlocked

    # Create a new account object by name
    t1 = ChainedAccount.get(test_accounts[0].name)
    assert isinstance(t1, ChainedAccount)

    # Search account
    result = find_accounts(address="0x008aeeda4d805471df9b2a5b0f38a0c3bcba786b")
    assert len(result) == 3
    result = runner.invoke(main, ["find", "--address", "0x008aeeda4d805471df9b2a5b0f38a0c3bcba786b"])
    assert "Found 3 accounts" in result.stdout

    results = find_accounts(name=test_accounts[2].name)
    assert len(results) == 1
    result = runner.invoke(main, ["find", "--name", test_accounts[2].name])
    assert "Found 1 accounts" in result.stdout

    results = find_accounts(chain_id=1)
    assert len(results) >= 2

    # Find with no filters should return all accounts
    result = find_accounts()
    assert len(result) > 0


def test_datadir() -> List[ChainedAccount]:  # type: ignore
    """Create some test accounts"""

    datadir = CHAINED_ACCOUNTS_HOME / "test"
    datadir.mkdir(exist_ok=False)

    a1 = ChainedAccount.import_key(random_name(), chains=[1, 4], key=pkey, password=PASSWORD, datadir=datadir)
    a2 = ChainedAccount.import_key(random_name(), chains=[2], key=pkey, password=PASSWORD, datadir=datadir)

    accounts = find_accounts(datadir=datadir)
    assert len(accounts) == 2

    a1b = ChainedAccount.get(name=a1.name, datadir=datadir)
    assert a1b.name == a1.name

    # Cleanup test accounts
    a1.delete()
    a2.delete()
    datadir.rmdir()
