"""Chained account/key management

This module is intended to provide a higher degree of security than storing private keys in clear text.
Use at your own risk.
"""

from __future__ import annotations

import getpass
import json
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import AnyAddress
from eth_typing import HexAddress
from eth_utils import to_checksum_address
from eth_utils import to_normalized_address
from hexbytes import HexBytes

from chained_accounts.exceptions import AccountLockedError
from chained_accounts.exceptions import ConfirmPasswordError


def default_homedir() -> Path:
    """Returns the default home directory used for the keystore.

    If the directory does not exist, it will be created.

    Returns:
        pathlib.Path : Path to home directory
    """
    homedir = Path.home() / (".chained_accounts")
    homedir = homedir.resolve().absolute()
    if not homedir.is_dir():
        homedir.mkdir()

    return homedir


CHAINED_ACCOUNTS_HOME = default_homedir()

if not CHAINED_ACCOUNTS_HOME.exists():
    CHAINED_ACCOUNTS_HOME.mkdir()


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

    _chains: List[int]
    _account_json: Dict[str, Any]
    _datadir: Path

    def __init__(self, name: str, datadir: Union[str, Path] = CHAINED_ACCOUNTS_HOME):
        """Get an account from the keystore

        Accounts must first be added to the keystore using `ChainedAccount.add()`

        Args:
            name:
                Unique account name
            datadir:
                Data directory for the keystore

        """

        self.name: str = name
        self._local_account: Optional[LocalAccount] = None
        self._chains = []

        if not isinstance(datadir, Path):
            datadir = Path(datadir).resolve().absolute()
        self._datadir = datadir

        try:
            self._load()
        except FileNotFoundError:
            self._account_json = {}

    def __repr__(self) -> str:
        return f"ChainedAccount('{self.name}')"

    @classmethod
    def get(cls, name: str, datadir: Union[str, Path] = CHAINED_ACCOUNTS_HOME):
        """Get an account from the keystore

        Args:
            datadir: Data directory for the keystore
            name: Unique account name
        """
        return cls(name, datadir=datadir)

    @classmethod
    def import_key(
        cls,
        name: str,
        chains: Union[int, List[int]],
        key: bytes,
        password: Optional[str] = None,
        datadir: Union[str, Path] = CHAINED_ACCOUNTS_HOME,
    ) -> ChainedAccount:
        """Import a private key into a new ChainedAccount.

        Args:
            name:
                Account name
            chains:
                List of applicable EVM chain IDs for this account (see www.chainlist.org).
            key:
                Private Key for the account.  User will be prompted for password if not provided.
            password:
                Password used to encrypt the keystore
            datadir:
                Data directory for the keystore

        Returns:
            A new ChainedAccount
        """

        names = list_names(datadir=datadir)
        if name in names:
            raise Exception(f"Account {name} already exists ")

        self = cls(name=name, datadir=datadir)

        if isinstance(chains, int):
            chains = [chains]

        self._chains = chains

        if password is None:
            try:
                password = ask_for_password(name)
            except ConfirmPasswordError:
                print("Passwords do not match. Try again.")
                password = ask_for_password(name)

        if password is None:
            password1 = getpass.getpass(f"Enter encryption password for {name}: ")
            password2 = getpass.getpass("Confirm password: ")
            if password2 != password1:
                raise ConfirmPasswordError(f"Account: {name}")
            password = password1

        keystore_json = Account.encrypt(key, password)

        # Make sure that address is a checksum address:
        keystore_json["address"] = to_checksum_address(keystore_json["address"])

        self._account_json = {"chains": chains, "keystore_json": keystore_json}

        self._store()

        return self

    def unlock(self, password: Optional[str] = None) -> None:
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
    def chains(self) -> List[int]:

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
        return to_checksum_address(self._account_json["keystore_json"]["address"])

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
        return self._datadir / f"{self.name}.json"

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
        if self.keyfile.exists:
            self.keyfile.unlink()


def list_names(datadir: Union[str, Path] = CHAINED_ACCOUNTS_HOME):
    """Get a list of all account names

    Args:
        datadir: Data directory for the keystore
    """
    if not isinstance(datadir, Path):
        datadir = Path(datadir).resolve().absolute()

    names = [f.stem for f in datadir.iterdir()]

    return names


def find_accounts(
    datadir: Union[str, Path] = CHAINED_ACCOUNTS_HOME,
    name: Optional[str] = None,
    chain_id: Optional[int] = None,
    address: Optional[Union[AnyAddress, str, bytes]] = None,
) -> List[ChainedAccount]:
    """Search for matching accounts.

    If no arguments are provided, all accounts will be returned.

    Args:
        name: search by account name
        chain_id: search for accounts with matching chain_id
        address: search for accounts with matching address
        datadir: Data directory for the keystore

    Returns:
        List of matching accounts
    """
    if not isinstance(datadir, Path):
        datadir = Path(datadir).resolve().absolute()

    accounts = []
    for acc_name in list_names(datadir):
        account = ChainedAccount(acc_name, datadir=datadir)
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
