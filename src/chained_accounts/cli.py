import click
import chained_accounts
from chained_accounts.base import EvmAccount, list_account_names
import getpass
from typing import List
from hexbytes import HexBytes


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--version", is_flag=True, help="Display chained_accounts version and exit.")
def main(ctx, version) -> None:
    """Main evmacc command line interface"""
    ctx.ensure_object(dict)
    if version:
        print(f"Version: {chained_accounts.__version__}")
        return

    if ctx.invoked_subcommand is None:
        print(ctx.command.get_help(ctx))


@main.command()
@click.argument("account_name", type=str)
@click.argument("private_key", type=str)
@click.argument("chain_ids", type=int, nargs=-1)
def add(account_name: str, private_key: str, chain_ids: List[int]) -> None:
    """Add an account.

    Adds an encrypted private_key for use by an application.  ACCOUNT_NAME is a unique name
    used to refer to the account.  The PRIVATE_KEY should be provided in hexadecimal format,
    beginning with 0x.  CHAIN_IDS is a list of the chains on which applications may use this account.
    If PASSWORD is not provided, the user will be prompted to enter a password
    """

    test_account = EvmAccount(account_name)
    if test_account.keyfile.exists():
        click.echo(f"Account {account_name} already exists.")
        return

    account = EvmAccount.new(name=account_name, private_key=HexBytes(private_key), chain_ids=chain_ids)

    click.echo(f"Added new account {account_name} (address= {account.address}) for use on chains {account.chain_ids}")


@main.command()
def all():
    """List all account names."""
    names = list_account_names()
    print(f"Found {len(names)} accounts.")
    for name in names:
        click.echo(f"  {name}")


@main.command()
@click.argument("account_name", type=str)
def get_key(account_name):
    """Get the private key for an account."""

    account = EvmAccount(account_name)
    if not account.keyfile.exists():
        click.echo(f"Account {account_name} does not exist.")
        return

    try:
        password = getpass.getpass(f"Enter password for {account_name} keyfile: ")
        acc = EvmAccount(account_name)
        acc.unlock(password)
        click.echo(f"Private key: {acc.private_key.hex()}")
    except ValueError:
        click.echo("Invalid Password")


@main.command()
@click.argument("account_name", type=str)
def delete(account_name):
    """Delete an account."""

    account = EvmAccount(account_name)
    if not account.keyfile.exists():
        click.echo(f"Account {account_name} does not exist.")
        return

    account.delete()


if __name__ == "__main__":
    main()
