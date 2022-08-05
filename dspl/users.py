import logging
import os
import subprocess

import click

from . import core
import re

username_regex = re.compile(r'^[a-z][a-z0-9_-]*$')


@core.cli.group(name='users', help="Manage users in the cluster")
def users():
    pass


def check_username(username: str):
    if not username_regex.match(username):
        raise core.DSPLError("Invalid username must contain only lower case chars and number")


@users.command(
    name='add',
    help="Add a user"
)
@click.argument("username")
@click.option("-s", '--sudoer', help="Add as sudoer", is_flag=True, default=False)
@click.pass_obj
def users_add(ctx: core.DSPLContext, username: str, sudoer: bool = False):
    check_username(username)

    password_hash = read_user_password_and_hash()
    command = f'sudo useradd "{username}" --password "{password_hash}" --create-home --user-group -s /bin/bash'
    ctx.run(command)

    bash_profile = '''

if [ -d /etc/profile.d ]; then
  for i in /etc/profile.d/*.sh; do
    if [ -r $i ]; then
      . $i
    fi
  done
  unset i
fi 
'''
    bash_rc = f"/home/{username}/.bashrc"
    r = ctx.read_file(bash_rc)

    updated_contents = {}
    for node, content in r.items():
        if "if [ -d /etc/profile.d ]; then" in content:
            updated_contents[node] = content
        else:
            updated_contents[node] = content + os.linesep + bash_profile

    ctx.write_content(bash_rc, updated_contents)

    if sudoer:
        ctx.run(f"sudo usermod -aG sudo {username}")


def read_user_password_and_hash():
    logging.info("Input user password in following OpenSSL prompt")
    password_hash = subprocess.check_output(["openssl", "passwd", "-6"])
    return password_hash


@users.command(
    name='make-sudoer',
    help="Make a user sudoer"
)
@click.argument("username")
@click.pass_obj
def users_make_sudoer(ctx: core.DSPLContext, username: str):
    check_username(username)
    ctx.run(f"sudo usermod -aG sudo {username}")


@users.command(
    name='change-password',
    help="Change password of a user"
)
@click.argument("username")
@click.pass_obj
def users_change_password(ctx: core.DSPLContext, username: str):
    check_username(username)

    password_hash = read_user_password_and_hash()
    ctx.run(f'sudo usermod --password {password_hash} {username}')
