"""EVM account/key management

This module is intended to provide a higher degree of security than storing private keys in clear text.
Use at your own risk.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Union, Optional, List, Dict, Any

from eth_typing import HexAddress, AnyAddress
from eth_utils import to_normalized_address
from chained_accounts import ConfirmPasswordError, AccountLockedError
from eth_account import Account
from eth_account.signers.local import LocalAccount

import getpass

from hexbytes import HexBytes


def default_homedir() -> Path:
    """Returns the default home directory used to store encrypted key files.

    If the directory does not exist, it will be created.

    Returns:
        pathlib.Path : Path to home directory
    """
    homedir = Path.home() / (".chained_accountss")
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


class EvmAccount:
    """EVM Account

    An EVM account is used to specify an account address, its private key, and the EVM chains on which it can be used.

    New EvmAccounts are stored on-disk locally in encrypted format using the `eth_account` package.

    The object defaults to a locked state, with the private key remaining encrypted.
    The `decrypt()` method must be called prior to accessing the private_key attribute, otherwise an exception
    will be raised.

    Attributes:
        name:
            User-specified account identifier.
        chain_ids:
            List of applicable EVM chains for this EVM account.
        unlocked:
            Returns true if the account is unlocked (private_key is exposed!).
        private_key:
            Returns the private key if the EvmAccount is unlocked, otherwise an exception is raised.
        keyfile:
            Returns the path to the stored keyfile
    """

    _chain_ids: List[int]
    _account_json: Dict[str, Any]

    def __init__(self, name: str):
        """Loads an existing EVM Account from disk

        New accounts must first be creating using `EvmAccount.new()`

        Args:
            name: User-specified account name
        """

        self.name: str = name
        self._local_account: Optional[LocalAccount] = None
        self._chain_ids = []
        try:
            self._load()
        except FileNotFoundError:
            self._account_json = {}

    def __repr__(self) -> str:
        return f"EvmAccount(name={self.name})"

    @classmethod
    def new(
        cls,
        name: str,
        *,
        chain_ids: Union[int, List[int]],
        private_key: bytes,
        password: Optional[str] = None,
    ) -> EvmAccount:
        """Create a new EVM account and an encrypted keystore on disk.

        Args:
            name:
                User-specified account name
            chain_ids:
                List of applicable EVM chains for this EVM account.
            private_key:
                Private Key for the account.  User will be prompted for password if not provided.
            password:
                Password used to encrypt the keystore

        Returns:
            A new EVM account
        """

        account_names = list_account_names()
        if name in account_names:
            raise Exception(f"EVM Account {name} already exists ")

        self = cls(name=name)

        if isinstance(chain_ids, int):
            chain_ids = [chain_ids]

        self._chain_ids = chain_ids

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

        keystore_json = Account.encrypt(private_key, password)

        self._account_json = {"chain_ids": chain_ids, "keystore_json": keystore_json}

        self._store()

        return self

    def unlock(self, password: Optional[str] = None) -> None:
        """Decrypt keystore data.

        Args:
            password: Used to decrypt the keyfile data
        """
        if self.unlocked:
            return

        if password is None:
            password = getpass.getpass(f"Enter password for {self.name} account: ")

        pkey = Account.decrypt(self._account_json["keystore_json"], password)
        self._local_account = Account.from_key(pkey)

    @property
    def chain_ids(self) -> List[int]:

        if not self._chain_ids:
            self._chain_ids = self._account_json["chain_ids"]

        return self._chain_ids

    @property
    def unlocked(self) -> bool:
        """"""
        return self._local_account is not None

    @property
    def private_key(self) -> HexBytes:
        if self.unlocked:
            assert self._local_account is not None
            return HexBytes(self._local_account.key)
        else:
            raise AccountLockedError(f"{self.name} EvmAccount must be unlocked to access the private key.")

    @property
    def address(self) -> HexAddress:
        return to_normalized_address(self._account_json["keystore_json"]["address"])

    @property
    def local_account(self) -> LocalAccount:
        if self.unlocked:
            assert self._local_account is not None
            return self._local_account
        else:
            raise AccountLockedError(f"{self.name} LocalAccount cannot be accessed when EvmAccount is locked.")

    # --------------------------------------------------------------------------------
    # File access methods
    # --------------------------------------------------------------------------------
    @property
    def keyfile(self) -> Path:
        """Returns the path to the locally stored keyfile"""
        return CHAINED_ACCOUNTS_HOME / f"{self.name}.json"

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


def list_account_names():
    """Get a list of all account names"""
    account_names = [f.stem for f in CHAINED_ACCOUNTS_HOME.iterdir()]

    return account_names


def get_account(name: str) -> EvmAccount:
    """Get account by name.

    Returns:
        The EVM account or an exception if it does not exist
    """
    return EvmAccount(name)


def find_accounts(
    name: Optional[str] = None,
    chain_id: Optional[int] = None,
    address: Optional[Union[AnyAddress, str, bytes]] = None,
) -> List[EvmAccount]:
    """Search for accounts

    Args:
        name: search by account name
        chain_id: search for accounts with matching chain_id
        address: search for accounts with matching address

    Returns:
        List of matching accounts
    """

    accounts = []
    for account_name in list_account_names():
        account = EvmAccount(account_name)
        if name is not None:
            if name != account.name:
                continue
        if chain_id is not None:
            if chain_id not in account.chain_ids:
                continue
        if address is not None:
            normalized_address = to_normalized_address(address)
            if normalized_address.lower() != account.address.lower():
                continue

        accounts.append(account)

    return accounts
