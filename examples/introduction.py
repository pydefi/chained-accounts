from chained_accounts import ChainedAccount

key1 = '0x57fe7105302229455bcfd58a8b531b532d7a2bb3b50e1026afa455cd332bf706'

ca1 = ChainedAccount.add('my-eth-acct', [1, 4], key1, password='foo')
print(ca1)
print(ca1.chains)
print(ca1.address)

key2 = '0x7a3d4adc3b6fb4520893e9b486b67a730e0d879a421342f788dc3dc273543267'

ca2 = ChainedAccount.add('my-matic-acct', 137, key2, password='bar')
print(ca2)

ca1.delete()
ChainedAccount('my-matic-acct').delete()
