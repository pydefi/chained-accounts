"""Chained account/key management

This module is intended to provide a higher degree of security than storing private keys in clear text.
Use at your own risk.
"""

import getpass
import json
from pathlib import Path

from eth_typing import HexAddress, AnyAddress
from eth_utils import to_normalized_address
from chained_accounts.exceptions import AccountLockedError, ConfirmPasswordError
from eth_account import Account
from eth_account.signers.local import LocalAccount

from hexbytes import HexBytes

_homedir: Path | None = None


def get_homedir() -> Path:
    """Return the home directory used for the keystore, creating it if needed."""
    global _homedir
    if _homedir is None:
        _homedir = (Path.home() / ".chained_accounts").resolve()
    if not _homedir.is_dir():
        _homedir.mkdir(parents=True)
    return _homedir


def set_homedir(path: Path | None) -> None:
    """Override the keystore home directory (or reset to default with None)."""
    global _homedir
    _homedir = path


def ask_for_password(name: str) -> str:
    password1 = getpass.getpass(f"Enter encryption password for {name}: ")
    password2 = getpass.getpass("Confirm password: ")
    if password2 != password1:
        raise ConfirmPasswordError(f"Account: {name}")
    password = password1

    return password


class ChainedAccount:
    """Chained Account

    The ChainedAccount class provides access to a keystore for ethereum accounts, where each account is
    associated with one or more EVM chains.

    ChainedAccount objects default to a locked state, with the private key remaining encrypted.
    The `decrypt()` method must be called prior to accessing the key attribute, otherwise an exception
    will be raised.

    Attributes:
        name:
            User-specified account name (no spaces).
        chains:
            List of applicable EVM chain IDs for this account (see www.chainlist.org).
        is_unlocked:
            Returns true if the account is unlocked (key is exposed!).
        key:
            Returns the private key if the account is unlocked, otherwise an exception is raised.
        keyfile:
            Returns the path to the stored keyfile
    """

    _chains: list[int]
    _account_json: dict[str, object]

    def __init__(self, name: str):
        """Get an account from the keystore

        Accounts must first be added to the keystore using `ChainedAccount.add()`

        Args:
            name: Unique account name
        """

        self.name: str = name
        self._local_account: LocalAccount | None = None
        self._chains = []
        try:
            self._load()
        except FileNotFoundError:
            self._account_json = {}

    def __repr__(self) -> str:
        return f"ChainedAccount('{self.name}')"

    @classmethod
    def get(cls, name: str) -> "ChainedAccount":
        """Get an account from the keystore"""
        return cls(name)

    @classmethod
    def add(
        cls,
        name: str,
        chains: int | list[int],
        key: bytes,
        password: str | None = None,
    ) -> "ChainedAccount":
        """Add a new ChainedAccount to the keystore.

        Args:
            name:
                Account name
            chains:
                List of applicable EVM chain IDs for this account (see www.chainlist.org).
            key:
                Private Key for the account.  User will be prompted for password if not provided.
            password:
                Password used to encrypt the keystore

        Returns:
            A new ChainedAccount
        """

        names = list_names()
        if name in names:
            raise ValueError(f"Account {name} already exists")

        self = cls(name=name)

        if isinstance(chains, int):
            chains = [chains]

        self._chains = chains

        if password is None:
            try:
                password = ask_for_password(name)
            except ConfirmPasswordError:
                print("Passwords do not match. Try again.")
                password = ask_for_password(name)

        keystore_json = Account.encrypt(key, password)

        self._account_json = {"chains": chains, "keystore_json": keystore_json}

        self._store()

        return self

    def unlock(self, password: str | None = None) -> None:
        """Decrypt keystore data.

        Args:
            password: Used to decrypt the keyfile data
        """
        if self.is_unlocked:
            return

        if password is None:
            password = getpass.getpass(f"Enter password for {self.name} account: ")

        key = Account.decrypt(self._account_json["keystore_json"], password)
        self._local_account = Account.from_key(key)

    def lock(self) -> None:
        """Lock account"""
        self._local_account = None

    @property
    def chains(self) -> list[int]:

        if not self._chains:
            self._chains = self._account_json["chains"]

        return self._chains

    @property
    def is_unlocked(self) -> bool:
        """"""
        return self._local_account is not None

    @property
    def key(self) -> HexBytes:
        if self.is_unlocked:
            assert self._local_account is not None
            return HexBytes(self._local_account.key)
        else:
            raise AccountLockedError(f"{self.name} ChainedAccount must be unlocked to access the private key.")

    @property
    def address(self) -> HexAddress:
        return to_normalized_address(self._account_json["keystore_json"]["address"])

    @property
    def local_account(self) -> LocalAccount:
        if self.is_unlocked:
            assert self._local_account is not None
            return self._local_account
        else:
            raise AccountLockedError(f"{self.name} LocalAccount cannot be accessed when ChainedAccount is locked.")

    # --------------------------------------------------------------------------------
    # File access methods
    # --------------------------------------------------------------------------------
    @property
    def keyfile(self) -> Path:
        """Returns the path to the locally stored keyfile"""
        return get_homedir() / f"{self.name}.json"

    def _load(self) -> None:
        """Load the account from disk."""
        if not self.keyfile.exists():
            raise FileNotFoundError(f"Could not load keyfile: {self.keyfile}")

        with open(self.keyfile, "r") as f:
            self._account_json = json.load(f)

    def _store(self) -> None:
        """Store the encrypted account to disk."""
        if self.keyfile.exists():
            raise FileExistsError(f"Keyfile already exists: {self.keyfile}")

        with open(self.keyfile, "w") as f:
            json.dump(self._account_json, f, indent=2)

    def delete(self):
        if self.keyfile.exists():
            self.keyfile.unlink()


def list_names():
    """Get a list of all account names"""
    names = [f.stem for f in get_homedir().iterdir()]

    return names


def find_accounts(
    name: str | None = None,
    chain_id: int | None = None,
    address: AnyAddress | str | bytes | None = None,
) -> list["ChainedAccount"]:
    """Search for matching accounts.

    If no arguments are provided, all accounts will be returned.

    Args:
        name: search by account name
        chain_id: search for accounts with matching chain_id
        address: search for accounts with matching address

    Returns:
        List of matching accounts
    """

    accounts = []
    for acc_name in list_names():
        account = ChainedAccount(acc_name)
        if name is not None:
            if name != account.name:
                continue
        if chain_id is not None:
            if chain_id not in account.chains:
                continue
        if address is not None:
            normalized_address = to_normalized_address(address)
            if normalized_address.lower() != account.address.lower():
                continue

        accounts.append(account)

    return accounts
