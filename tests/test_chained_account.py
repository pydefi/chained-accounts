import pytest
from hexbytes import HexBytes
from click.testing import CliRunner
from chained_accounts.base import ChainedAccount, find_accounts
from chained_accounts.exceptions import AccountLockedError
from chained_accounts.cli import main

pkey = HexBytes("0x7a28b5ba57c53603b0b07b56bba752f7784bf506fa95edc395f5cf6c7514fe9d")
PASSWORD = "foo"


@pytest.fixture
def test_accounts() -> list[ChainedAccount]:
    """Create some test accounts"""
    a1 = ChainedAccount.add("acct-one", chains=[1, 4], key=pkey, password=PASSWORD)
    a2 = ChainedAccount.add("acct-two", chains=[2], key=pkey, password=PASSWORD)
    a3 = ChainedAccount.add("acct-three", chains=[1, 3], key=pkey, password=PASSWORD)

    return [a1, a2, a3]


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

    # Some properties are not available on locked accounts
    with pytest.raises(AccountLockedError):
        _ = test_accounts[0].key

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


def test_duplicate_name_raises():
    """Adding an account with an existing name raises ValueError."""
    ChainedAccount.add("dupe-test", chains=[1], key=pkey, password=PASSWORD)
    with pytest.raises(ValueError, match="already exists"):
        ChainedAccount.add("dupe-test", chains=[2], key=pkey, password=PASSWORD)


def test_delete_removes_keyfile():
    """delete() removes keyfile; double-delete doesn't error."""
    acc = ChainedAccount.add("del-test", chains=[1], key=pkey, password=PASSWORD)
    assert acc.keyfile.exists()
    acc.delete()
    assert not acc.keyfile.exists()
    # second delete is a no-op
    acc.delete()
