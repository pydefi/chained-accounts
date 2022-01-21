import click
import chained_accounts
from chained_accounts.base import ChainedAccount, find_accounts
import getpass
from typing import List
from hexbytes import HexBytes


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--version", is_flag=True, help="Display chained_accounts version and exit.")
def main(ctx, version) -> None:
    """Main chained command line interface"""
    ctx.ensure_object(dict)
    if version:
        print(f"Version: {chained_accounts.__version__}")
        return

    if ctx.invoked_subcommand is None:
        print(ctx.command.get_help(ctx))


@main.command()
@click.argument("uid", type=str)
@click.argument("private_key", type=str)
@click.argument("chain_ids", type=int, nargs=-1)
def add(uid: str, private_key: str, chain_ids: List[int]) -> None:
    """Add an account.

    Adds an ethereum account for use by an application on one or more EVM chains.
    UID (unique account ID) is any convenient string used to identify the account.
    The PRIVATE_KEY should be provided in hexadecimal format, beginning with 0x.
    CHAIN_IDS is a list of the chains on which applications may use this account.
    """

    test_account = ChainedAccount(uid)
    if test_account.keyfile.exists():
        click.echo(f"Account {uid} already exists.")
        return

    account = ChainedAccount.add(uid, private_key=HexBytes(private_key), chain_ids=chain_ids)

    click.echo(f"Added new account {uid} (address= {account.address}) for use on chains {account.chain_ids}")


@main.command()
@click.option("--uid", type=str)
@click.option("--address", type=str)
@click.option("--chain_id", type=int)
def find(uid, address, chain_id):
    """Search the keystore for accounts.

    Each option is used as a filter when searching the keystore.
    If no options are provided, all accounts will be returned.
    """

    accounts = find_accounts(uid=uid, address=address, chain_id=chain_id)
    click.echo(f"Found {len(accounts)} accounts.")
    for account in accounts:
        click.echo(f"Account uid: {account.uid}, address: {account.address}, chain IDs: {account.chain_ids}")


@main.command()
@click.argument("uid", type=str)
@click.option("-p", "--password", type=str)
def key(uid, password):
    """Get the private key for an account.

    UID is the account id used to create the account.
    User will be prompted for the password if it is not provided through the command line option.
    """

    account = ChainedAccount(uid)
    if not account.keyfile.exists():
        click.echo(f"Account {uid} does not exist.")
        return

    try:
        if not password:
            password = getpass.getpass(f"Enter password for {uid} keyfile: ")
        acc = ChainedAccount(uid)
        acc.unlock(password)
        click.echo(f"Private key: {acc.private_key.hex()}")
    except ValueError:
        click.echo("Invalid Password")


@main.command()
@click.argument("uid", type=str)
def delete(uid):
    """Delete an account from the keystore.

    UID is the account id used to create the account.
    """
    account = ChainedAccount(uid)
    if not account.keyfile.exists():
        click.echo(f"Account {uid} does not exist.")
        return

    account.delete()


if __name__ == "__main__":
    main()
