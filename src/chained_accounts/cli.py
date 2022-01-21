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
@click.argument("name", type=str)
@click.argument("private_key", type=str)
@click.argument("chain_ids", type=int, nargs=-1)
def add(name: str, private_key: str, chain_ids: List[int]) -> None:
    """Add an account.

    Adds an encrypted private_key for use by an application.  ACCOUNT_NAME is a unique name
    used to refer to the account.  The PRIVATE_KEY should be provided in hexadecimal format,
    beginning with 0x.  CHAIN_IDS is a list of the chains on which applications may use this account.
    If PASSWORD is not provided, the user will be prompted to enter a password
    """

    test_account = ChainedAccount(name)
    if test_account.keyfile.exists():
        click.echo(f"Account {name} already exists.")
        return

    account = ChainedAccount.add(name=name, private_key=HexBytes(private_key), chain_ids=chain_ids)

    click.echo(f"Added new account {name} (address= {account.address}) for use on chains {account.chain_ids}")


@main.command()
@click.option("--name", type=str)
@click.option("--address", type=str)
@click.option("--chain_id", type=int)
def find(name, address, chain_id):
    """Find accounts."""

    accounts = find_accounts(name=name, address=address, chain_id=chain_id)
    click.echo(f"Found {len(accounts)} accounts.")
    for account in accounts:
        click.echo(f"Account name: {account.name}, address: {account.address}, chain IDs: {account.chain_ids}")


@main.command()
@click.argument("name", type=str)
@click.option("-p", "--password", type=str)
def key(name, password):
    """Get the private key for an account."""

    account = ChainedAccount(name)
    if not account.keyfile.exists():
        click.echo(f"Account {name} does not exist.")
        return

    try:
        if not password:
            password = getpass.getpass(f"Enter password for {name} keyfile: ")
        acc = ChainedAccount(name)
        acc.unlock(password)
        click.echo(f"Private key: {acc.private_key.hex()}")
    except ValueError:
        click.echo("Invalid Password")


@main.command()
@click.argument("name", type=str)
def delete(name):
    """Delete an account."""

    account = ChainedAccount(name)
    if not account.keyfile.exists():
        click.echo(f"Account {name} does not exist.")
        return

    account.delete()


if __name__ == "__main__":
    main()
