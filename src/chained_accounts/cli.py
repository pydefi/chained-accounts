import collections
import getpass
from pathlib import Path
from typing import List
from typing import Optional

import click
from hexbytes import HexBytes

import chained_accounts
from chained_accounts.base import CHAINED_ACCOUNTS_HOME
from chained_accounts.base import ChainedAccount
from chained_accounts.base import find_accounts
from chained_accounts.base import is_datadir


class OrderedGroup(click.Group):
    """Helper for maintaining order of commands"""

    def __init__(self, name=None, commands=None, **attrs):
        super(OrderedGroup, self).__init__(name, commands, **attrs)
        #: the registered subcommands by their exported names.
        self.commands = commands or collections.OrderedDict()

    def list_commands(self, ctx):
        return self.commands


""" Shared Options and Arguments

"""
name_argument = click.argument("name", type=str)
name_option = click.option("--name", type=str, help="Account name")
address_option = click.option("--address", type=str, help="Account address (hex string)")
chain_option = click.option("--chain", type=int, help="EVM CHain ID (see www.chainlist.org)")
chains_argument = click.argument("chains", type=int, nargs=-1)
key_argument = click.argument("key", type=str)
datadir_option = click.option(
    "--datadir",
    help=f"Data directory for the keystore. default={CHAINED_ACCOUNTS_HOME}",
    type=click.Path(),
    default=CHAINED_ACCOUNTS_HOME,
)


def validate_datadir(datadir: str) -> Optional[Path]:
    """Parse and validate the datadir argument

    Args:
        datadir: path to datadir

    Returns:
        datadir as Path object or None if invalid
    """
    keypath = Path(datadir).resolve().absolute()
    if not is_datadir(keypath):
        click.echo(f"Invalid data directory: {keypath}.")
        return None

    return keypath


@click.group(invoke_without_command=True, cls=OrderedGroup)
@click.option("--version", is_flag=True, help="Display chained_accounts version and exit.")
@click.pass_context
def main(ctx, version) -> None:
    """Main chained command line interface"""

    if version:
        print(f"Version: {chained_accounts.__version__}")
        return

    if ctx.invoked_subcommand is None:
        print(ctx.command.get_help(ctx))


@click.command()
@datadir_option
def list_command(datadir: str):
    """Print a summary of existing accounts."""

    keypath = validate_datadir(datadir)
    if not keypath:
        return

    accounts = find_accounts(datadir=keypath)
    click.echo(f"Found {len(accounts)} accounts in {keypath}")
    for account in accounts:
        click.echo(f"Account {account.name} | {account.address} | chains {account.chains}")


@click.command()
def new_command():
    """Create a new account."""
    click.echo("New accounts not yet supported.")


@click.command()
@name_argument
@datadir_option
def update_command(name, datadir):
    """Update an existing account."""

    datadir = validate_datadir(datadir)
    if not datadir:
        return

    acc = ChainedAccount(name, datadir=datadir)
    if not acc.keyfile.exists():
        click.echo(f"Account {name} does not exist.")
        return

    # Unlock the account
    try:
        password = getpass.getpass(f"Enter password for {name}: ")
        acc.unlock(password)
    except ValueError:
        click.echo("Invalid Password")
        return

    # Get a new password
    password1 = getpass.getpass(f"Enter new password for {name}: ")
    password2 = getpass.getpass("Confirm password: ")
    if password2 != password1:
        click.echo("Passwords do not match.")
        return
    password = password1


@click.command()
@name_argument
@key_argument
@chains_argument
@datadir_option
def import_command(name: str, key: str, chains: List[int], datadir: str) -> None:
    """Import a private key into a new account.

    Adds an ethereum account for use by an application on one or more EVM chains.
    NAME is used to uniquely identify the account in the keystore.
    The private KEY should be provided in hexadecimal format, beginning with 0x.
    CHAINS is a list of the chains on which applications may use this account.
    """

    keypath = validate_datadir(datadir)
    if not keypath:
        return

    account = ChainedAccount(name, datadir=keypath)
    if account.keyfile.exists():
        click.echo(f"Account {name} already exists.")
        return

    account = ChainedAccount.import_key(name, key=HexBytes(key), chains=chains, datadir=keypath)

    click.echo(f"Added new account {name} (address= {account.address}) for use on chains {account.chains}")


@click.command()
@name_option
@address_option
@chain_option
@datadir_option
def find_command(name, address, chain, datadir):
    """Search the keystore for accounts.

    Each option is used as a filter when searching the keystore.
    If no options are provided, all accounts will be returned.
    """
    datadir = validate_datadir(datadir)
    if not datadir:
        return

    accounts = find_accounts(name=name, address=address, chain=chain, datadir=datadir)
    click.echo(f"Found {len(accounts)} accounts.")
    for account in accounts:
        click.echo(f"Account {account.name} | {account.address} | chains {account.chains}")


@click.command()
@name_argument
@click.option("-p", "--password", type=str)
@datadir_option
def key_command(name, password, datadir):
    """Get the private key for an account.

    NAME is the account name used to create the account.
    User will be prompted for the password if it is not provided through the command line option.
    """
    datadir = validate_datadir(datadir)
    if not datadir:
        return

    acc = ChainedAccount(name, datadir=datadir)
    if not acc.keyfile.exists():
        click.echo(f"Account {name} does not exist.")
        return

    try:
        if not password:
            password = getpass.getpass(f"Enter password for {name} keyfile: ")
        acc.unlock(password)
        click.echo(f"Private key: {acc.key.hex()}")
    except ValueError:
        click.echo("Invalid Password")


@click.command()
@name_argument
@datadir_option
def delete_command(name, datadir):
    """Delete an account from the keystore.

    NAME is the account name used to create the account.
    """
    datadir = validate_datadir(datadir)
    if not datadir:
        return
    account = ChainedAccount(name, datadir=datadir)
    if not account.keyfile.exists():
        click.echo(f"Account {name} does not exist.")
        return

    account.delete()


main.add_command(list_command, "list")
main.add_command(update_command, "update")
main.add_command(import_command, "import")
main.add_command(new_command, "new")
main.add_command(delete_command, "delete")
main.add_command(key_command, "key")
main.add_command(find_command, "find")

if __name__ == "__main__":
    main()
