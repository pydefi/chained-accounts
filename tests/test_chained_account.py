import random
from collections import namedtuple
from typing import Generator

import pytest
from click.testing import CliRunner
from eth_utils import is_checksum_address
from hexbytes import HexBytes

from chained_accounts.base import CHAINED_ACCOUNTS_HOME
from chained_accounts.base import ChainedAccount
from chained_accounts.base import find_accounts
from chained_accounts.cli import main
from chained_accounts.exceptions import AccountLockedError

pkey = HexBytes("0x7a28b5ba57c53603b0b07b56bba752f7784bf506fa95edc395f5cf6c7514fe9d")
PASSWORD = "foo"

ExampleData = namedtuple("ExampleData", ["keydir", "accounts"])


def random_name() -> str:
    """Generate a random account name."""
    return "temp" + str(random.randint(100000, 999999))


@pytest.fixture(scope="module")
def example_data() -> Generator:
    """Create a data directory with some test accounts"""

    print("Creating Test Data")

    keydir = CHAINED_ACCOUNTS_HOME / random_name()
    flag_file = keydir / ".keystore"

    a1 = ChainedAccount.import_key(random_name(), chains=[1, 4], key=pkey, password=PASSWORD, datadir=keydir)
    a2 = ChainedAccount.import_key(random_name(), chains=[2], key=pkey, password=PASSWORD, datadir=keydir)
    a3 = ChainedAccount.import_key(random_name(), chains=[1, 3], key=pkey, password=PASSWORD, datadir=keydir)

    print("Created Test Data")
    yield ExampleData(keydir=keydir, accounts=[a1, a2, a3])

    # Cleanup test accounts
    a1.delete()
    a2.delete()
    a3.delete()
    flag_file.unlink()

    keydir.rmdir()
    print("Cleaned up Test Data")


def test_locked_access(example_data):
    # New accounts are locked
    assert not example_data.accounts[0].is_unlocked

    # Some properties are not available on locked accounts
    with pytest.raises(AccountLockedError):
        print(example_data.accounts[0].key)

    # Unlock accounts
    example_data.accounts[0].unlock(PASSWORD)
    example_data.accounts[1].unlock(PASSWORD)

    # Verify private keys
    assert example_data.accounts[0].key == example_data.accounts[1].key

    # Lock account and verify
    example_data.accounts[0].lock()
    assert not example_data.accounts[0].is_unlocked


def test_account_find(example_data):
    runner = CliRunner()

    # Find with no filters should return all accounts
    accounts = find_accounts(datadir=example_data.keydir)
    assert len(accounts) == 3

    cli_result = runner.invoke(main, ["find", "--datadir", example_data.keydir])
    assert "Found 3 accounts" in cli_result.stdout

    # Search account
    result = find_accounts(address="0x008aeeda4d805471df9b2a5b0f38a0c3bcba786b", datadir=example_data.keydir)
    assert len(result) == 3
    cli_result = runner.invoke(
        main, ["find", "--address", "0x008aeeda4d805471df9b2a5b0f38a0c3bcba786b", "--datadir", example_data.keydir]
    )
    assert "Found 3 accounts" in cli_result.stdout

    results = find_accounts(name=example_data.accounts[2].name, datadir=example_data.keydir)
    assert len(results) == 1
    cli_result = runner.invoke(
        main, ["find", "--name", example_data.accounts[2].name, "--datadir", example_data.keydir]
    )
    assert "Found 1 accounts" in cli_result.stdout

    results = find_accounts(chain=1, datadir=example_data.keydir)
    assert len(results) >= 2


def test_locked_access_cli(example_data):
    runner = CliRunner()

    # Correct password
    cli_result = runner.invoke(
        main, ["key", example_data.accounts[0].name, "-p", PASSWORD, "--datadir", example_data.keydir]
    )
    assert pkey.hex() in cli_result.stdout

    # Invalid Password
    cli_result = runner.invoke(
        main, ["key", example_data.accounts[0].name, "-p", "bar", "--datadir", example_data.keydir]
    )
    assert "Invalid Password" in cli_result.stdout


def test_new_evm_account(example_data):

    # Test loading by name
    account_copy = ChainedAccount.get(example_data.accounts[0].name, datadir=example_data.keydir)
    assert account_copy.address == example_data.accounts[0].address
    assert is_checksum_address(account_copy.address)

    # Create a new account object by name
    t1 = ChainedAccount.get(example_data.accounts[0].name, datadir=example_data.keydir)
    assert isinstance(t1, ChainedAccount)


