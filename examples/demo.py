from chained_accounts import ChainedAccount, find_accounts

key1 = "0x57fe7105302229455bcfd58a8b531b532d7a2bb3b50e1026afa455cd332bf706"
ChainedAccount.import_key("my-eth-acct", [1, 4], key1, password="foo")

acc = find_accounts(chain_id=1)[0]
print(f"Address: {acc.address}")
print(f"Chains: {acc.chains}")

acc.unlock("foo")
print(f"Private key: {acc.key.hex()}")
