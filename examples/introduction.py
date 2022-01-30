from chained_accounts import ChainedAccount, find_accounts

# Adding accounts to the keystore

key1 = "0x57fe7105302229455bcfd58a8b531b532d7a2bb3b50e1026afa455cd332bf706"
ChainedAccount.import_key("my-eth-acct", [1, 4], key1, password="foo")

key2 = "0x7a3d4adc3b6fb4520893e9b486b67a730e0d879a421342f788dc3dc273543267"
ChainedAccount.import_key("my-matic-acct", 137, key2, password="bar")

# Getting accounts from the keystore
acc = find_accounts(chain_id=1)[0]
print(acc)
print(f"Address: {acc.address}")
print(f"Chains: {acc.chains}")

# Getting the private key
acc = ChainedAccount.get("my-eth-acct")
acc.unlock("foo")
print(f"Private key: {acc.key.hex()}")

# Cleanup example accounts
ChainedAccount("my-eth-acct").delete()
ChainedAccount("my-matic-acct").delete()
