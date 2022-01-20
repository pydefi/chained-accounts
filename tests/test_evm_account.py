from typing import List

import pytest
from hexbytes import HexBytes

from chained_accounts.base import EvmAccount, AccountLockedError, get_account, find_accounts
import random

pkey = HexBytes("0x7a28b5ba57c53603b0b07b56bba752f7784bf506fa95edc395f5cf6c7514fe9d")
PASSWORD = "foo"


def random_name() -> str:
    """Generate a random account name."""
    return "temp" + str(random.randint(100000, 999999))


@pytest.fixture
def test_accounts() -> List[EvmAccount]:  # type: ignore
    """Create some test accounts"""

    a1 = EvmAccount.new(random_name(), private_key=pkey, chain_ids=[1, 4], password=PASSWORD)
    a2 = EvmAccount.new(random_name(), private_key=pkey, chain_ids=[2], password=PASSWORD)
    a3 = EvmAccount.new(random_name(), private_key=pkey, chain_ids=[1, 3], password=PASSWORD)

    yield [a1, a2, a3]

    # Cleanup test accounts
    a1.delete()
    a2.delete()
    a3.delete()


def test_new_evm_account(test_accounts):
    assert not test_accounts[0].unlocked
    assert 1 in test_accounts[0].chain_ids
    assert 4 in test_accounts[0].chain_ids

    # Test loading by name
    account_copy = EvmAccount(test_accounts[0].name)
    assert 1 in account_copy.chain_ids
    assert 4 in account_copy.chain_ids
    assert account_copy.address == test_accounts[0].address
    print(account_copy.address)

    with pytest.raises(AccountLockedError):
        print(test_accounts[0].private_key)

    test_accounts[0].unlock(PASSWORD)
    test_accounts[1].unlock(PASSWORD)

    assert test_accounts[0].private_key == test_accounts[1].private_key

    t1 = get_account(test_accounts[0].name)
    assert isinstance(t1, EvmAccount)

    results = find_accounts(address="0x008aeeda4d805471df9b2a5b0f38a0c3bcba786b")
    assert len(results) == 3

    results = find_accounts(name=test_accounts[2].name)
    assert len(results) == 1
    print(results)

    results = find_accounts(chain_id=1)
    assert len(results) == 2
