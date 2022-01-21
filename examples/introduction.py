from chained_accounts import ChainedAccount, find_accounts

# Adding accounts to the keystore

key1 = '0x57fe7105302229455bcfd58a8b531b532d7a2bb3b50e1026afa455cd332bf706'
ChainedAccount.add('my-eth-acct', [1, 4], key1, password='foo')

key2 = '0x7a3d4adc3b6fb4520893e9b486b67a730e0d879a421342f788dc3dc273543267'
ChainedAccount.add('my-matic-acct', 137, key2, password='bar')

# Getting accounts from the keystore

ca1 = find_accounts(chain_id=1)[0]
assert ca1.locked
print(ca1)
print(f"Address: {ca1.address}")
print(f"Chains: {ca1.chains}")


ca2 = ChainedAccount.get('my-matic-acct')


# Cleanup example accounts
ca1.delete()
ChainedAccount('my-matic-acct').delete()
