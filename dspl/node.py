import logging

import click

from .core import cli, DSPLContext


@cli.group(help='Manage nodes and systems')
def node():
    pass


@node.command(help="Run a shell command")
@click.argument('command')
@click.option('-p', '--parallel', is_flag=True, help="Execute in parallel and save results in logs")
@click.pass_obj
def cmd(ctx: DSPLContext, command, parallel=False):
    if parallel:
        ctx.run_parallel(command, save_result=True)
    else:
        ctx.run(command)


@node.command(help="Update system packages")
@click.option('-u', '--upgrade', is_flag=True, help="Upgrade packages")
@click.option('-d', '--dist-upgrade', is_flag=True, help="Dist-upgrade unused packages")
@click.option('-r', '--autoremove', is_flag=True, help="Auto remove unused packages")
@click.pass_obj
def update(ctx: DSPLContext, upgrade: bool, dist_upgrade: bool, autoremove: bool):
    commands = ["apt-get update"]

    if upgrade:
        commands.append("apt-get upgrade -y")

    elif dist_upgrade:
        commands.append("apt-get dist-upgrade -y")

    if autoremove:
        commands.append("apt-get autoremove -y")

    ctx.run_parallel(commands, sudo=True, save_result=True, warn=True)


@node.command(help="Check if reboot is required")
@click.pass_obj
def check_reboot(ctx: DSPLContext):
    logging.info("Reading reboot required file from nodes")
    result = ctx.exists('/var/run/reboot-required')
    for n, e in result.items():
        m = "[Reboot Required]" if e else ""
        print(f"{n:8} - {m}")


@node.command(help="Reboot the nodes if required")
@click.option('-f', '--force', help="Force reboot, even if not required")
@click.pass_obj
def reboot(ctx: DSPLContext, force: bool = False):
    logging.info("Reading reboot required file from nodes")
    result = ctx.exists('/var/run/reboot-required')

    for n, e in result.items():
        if e or force:
            print(f"Rebooting {n}")
            ctx.connection(n).run("sudo shutdown --reboot 0")
        else:
            print("Reboot not required in node {n}")

#
# @node.command(help="Update sudoer privileges")
# @click.pass_obj
# def sudoer_no_passwd(ctx: DSPLContext):
#     content = "%sudo ALL=(ALL) NOPASSWD:ALL\n"
#
#     contents = {n: content for n in ctx.nodes}
#     dspl_sudoer_file = '/etc/sudoers.d/01-dspl'
#
#     ctx.write_content(dspl_sudoer_file, contents)
#     ctx.run(f"sudo chmod 440 {dspl_sudoer_file}")
