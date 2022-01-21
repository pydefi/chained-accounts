# Chained Accounts

A framework to help applications and users manage multiple ethereum accounts on multiple chains.

Each `ChainedAccount`:

- has a user-friendly name
- can be associated with one or more EVM chains.
- is encrypted in a local keystore using the [`eth_keyfile`](https://github.com/ethereum/eth-keyfile) package.

Applications can easily access the keystore and search for accounts by name, EVM chain, and address.

## Installation

    pip install chained_accounts

## Usage

All `ChainedAccount` features are available through Python or the Command Line Interface (CLI).

### Adding a new account

The following example demonstrates adding two accounts to the keystore.  
The first account is for use on either ethereum mainnet or Rinkeby testnet.
The second account is for use on Polygon mainnet.
For a list of valid chain identifiers, see www.chainlist.org.


```python
from chained_accounts import ChainedAccount

key = '0x57fe7105302229455bcfd58a8b531b532d7a2bb3b50e1026afa455cd332bf706'
ChainedAccount.add('my-eth-acct', chains=[1, 4], key=key, password='foo')

key = '0x7a3d4adc3b6fb4520893e9b486b67a730e0d879a421342f788dc3dc273543267'
ChainedAccount.add('my-matic-acct', chains=137, key=key, password='bar')
```

or, from the CLI:

    >> chained add my-eth-acct 0x57fe7105302229455bcfd58a8b531b532d7a2bb3b50e1026afa455cd332bf706 1 4
    Enter encryption password for my-eth-acct: 
    Confirm password:
    Added new account my-eth-acct (address= 0xcd19cf65af3a3aea1f44a7cb0257fc7455f245f0) for use on chains (1, 4)

    >> chained add my-matic-acct 0x7a3d4adc3b6fb4520893e9b486b67a730e0d879a421342f788dc3dc273543267 137
    Enter encryption password for my-matic-acct: 
    Confirm password: 
    Added new account my-matic-acct (address= 0xc1b6c5d803c45b8d1097d07df0c816157db6f00c) for use on chains (137,)

### Getting accounts from the keystore

Accounts can be accessed by `name`, or can be found by searching the keystore using `find_accounts()`. 
The following example demonstrates how an application can search for user accounts by EVM chain.

```python
ca1 = find_accounts(chain_id=1)[0]
print(f"Address: {ca1.address}")
print(f"Chains: {ca1.chains}")
```

```pycon
ChainedAccount('my-eth-acct')
Address: 0xcd19cf65af3a3aea1f44a7cb0257fc7455f245f0
Chains: [1, 4]
```

Or, from the command line:

    > chained find
    Found 2 accounts.
    Account name: my-eth-acct, address: 0xcd19cf65af3a3aea1f44a7cb0257fc7455f245f0, chain IDs: [1, 4]
    Account name: my-matic-acct, address: 0xc1b6c5d803c45b8d1097d07df0c816157db6f00c, chain IDs: [137]

### Accessing private keys 

Note that the `ChainedAccount`s private key remains encrypted until they are unlocked with a password.

```python
assert ca1.locked
```



## Development

### Developer Mode Installation

    pip install -e .
    pip install -r dev-requirements.txt

### Running tests

    pytest

### Code checks

All code should pass the following checks prior to submitting.

    mypy
    black src tests
    flake8



