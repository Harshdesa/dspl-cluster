import logging
from typing import Dict, List

import click
from cached_property import cached_property

from . import core


class UserAuthKeys:

    def __init__(self, username: str, context: core.DSPLContext) -> None:
        self.username = username
        self.ssh_dir = f"/home/{username}/.ssh"
        self.auth_keys_file = f"{self.ssh_dir}/authorized_keys"
        self.context = context

    @cached_property
    def user_keys(self) -> Dict[str, List[str]]:
        logging.info(f"Reading user's authorized keys file: {self.auth_keys_file}")
        return {
            n: [l for l in content.split("\n") if l] if content else []
            for n, content in self.context.read_file(self.auth_keys_file).items()
        }

    def list(self):
        for node, keys in self.user_keys.items():
            core.print_banner(f"Node: {node}, User: {self.username}")

            for k in keys:
                print(k)

    def add(self, public_key_file: str):
        with open(public_key_file) as f:
            in_key = f.read().strip()

        updated_contents = {}
        for node, keys in self.user_keys.items():
            if in_key in keys:
                logging.info(f"Key exists in {node} not adding again")
            else:
                keys.append(in_key)
                updated_contents[node] = "\n".join(keys) + "\n"

        self.update_content(updated_contents)

    def delete(self, public_key_file: str):
        with open(public_key_file) as f:
            in_key = f.read().strip()

        updated_contents = {}
        for node, keys in self.user_keys.items():
            if in_key in keys:
                keys.remove(in_key)
                updated_contents[node] = "\n".join(keys) + "\n"
            else:
                logging.info(f"Key does not exist in {node}")

        self.update_content(updated_contents)

    def update_content(self, contents):
        self.context.run(
            f'sudo mkdir -p {self.ssh_dir} '
            f'&& sudo chown {self.username}:{self.username} {self.ssh_dir}'
        )
        self.context.write_content(self.auth_keys_file, contents)
        self.context.run(f'sudo chmod 644 {self.auth_keys_file}')


@core.cli.group(help='Manage SSH authorized keys')
def auth_keys():
    pass


@auth_keys.command(
    name='list',
    help='List all of a user keys in authorized_keys'
)
@click.argument('username')
@click.pass_obj
def auth_keys_list(ctx: core.DSPLContext, username: str):
    UserAuthKeys(username, ctx).list()


@auth_keys.command(
    name='add',
    help='Add a key for the user in authorized_keys'
)
@click.argument('username')
@click.argument('public_key_file')
@click.pass_obj
def auth_keys_add(ctx: core.DSPLContext, username: str, public_key_file: str):
    UserAuthKeys(username, ctx).add(public_key_file)


@auth_keys.command(
    name='delete',
    help='Delete a key from authorized_keys'
)
@click.argument('username')
@click.argument('public_key_file')
@click.pass_obj
def auth_keys_delete(ctx: core.DSPLContext, username: str, public_key_file: str):
    UserAuthKeys(username, ctx).delete(public_key_file)
