from typing import List

import pytest
from hexbytes import HexBytes
from click.testing import CliRunner
from chained_accounts.base import ChainedAccount, AccountLockedError, find_accounts
import random
from chained_accounts.cli import main

pkey = HexBytes("0x7a28b5ba57c53603b0b07b56bba752f7784bf506fa95edc395f5cf6c7514fe9d")
PASSWORD = "foo"


def random_uid() -> str:
    """Generate a random account uid."""
    return "temp" + str(random.randint(100000, 999999))


@pytest.fixture
def test_accounts() -> List[ChainedAccount]:  # type: ignore
    """Create some test accounts"""

    a1 = ChainedAccount.add(random_uid(), chain_ids=[1, 4], private_key=pkey, password=PASSWORD)
    a2 = ChainedAccount.add(random_uid(), chain_ids=[2], private_key=pkey, password=PASSWORD)
    a3 = ChainedAccount.add(random_uid(), chain_ids=[1, 3], private_key=pkey, password=PASSWORD)

    yield [a1, a2, a3]

    # Cleanup test accounts
    a1.delete()
    a2.delete()
    a3.delete()


def test_new_evm_account(test_accounts):
    runner = CliRunner()

    # New accounts are locked
    assert not test_accounts[0].unlocked
    assert 1 in test_accounts[0].chain_ids
    assert 4 in test_accounts[0].chain_ids

    # Test loading by uid
    account_copy = ChainedAccount(test_accounts[0].uid)
    assert 1 in account_copy.chain_ids
    assert 4 in account_copy.chain_ids
    assert account_copy.address == test_accounts[0].address
    print(account_copy.address)

    # Some properties are not available on locked accounts
    with pytest.raises(AccountLockedError):
        print(test_accounts[0].private_key)

    # Unlock accounts
    test_accounts[0].unlock(PASSWORD)
    test_accounts[1].unlock(PASSWORD)

    # Verify private keys (including CLI)
    assert test_accounts[0].private_key == test_accounts[1].private_key
    result = runner.invoke(main, ["key", test_accounts[0].uid, "-p", PASSWORD])
    assert pkey.hex() in result.stdout

    # Lock account and verify
    test_accounts[0].lock()
    assert not test_accounts[0].unlocked

    # Create a new account objecb by uid
    t1 = ChainedAccount.get(test_accounts[0].uid)
    assert isinstance(t1, ChainedAccount)

    # Search account
    result = find_accounts(address="0x008aeeda4d805471df9b2a5b0f38a0c3bcba786b")
    assert len(result) == 3
    result = runner.invoke(main, ["find", "--address", "0x008aeeda4d805471df9b2a5b0f38a0c3bcba786b"])
    assert "Found 3 accounts" in result.stdout

    results = find_accounts(uid=test_accounts[2].uid)
    assert len(results) == 1
    result = runner.invoke(main, ["find", "--uid", test_accounts[2].uid])
    assert "Found 1 accounts" in result.stdout

    results = find_accounts(chain_id=1)
    assert len(results) == 2

    # Find with no filters should return all accounts
    result = find_accounts()
    assert len(result) == 3
