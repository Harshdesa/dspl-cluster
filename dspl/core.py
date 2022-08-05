import logging
import os
from datetime import datetime
from io import BytesIO, StringIO
from typing import List, Dict, Union

import click
import coloredlogs
import yaml
from fabric2 import Connection, Result, ThreadingGroup
from fabric2.exceptions import GroupException
import uuid

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

logging_format = '[%(asctime)s] %(levelname)s: %(message)s'
coloredlogs.install(level='INFO', logger=logging.getLogger(), fmt=logging_format)

logging.getLogger('paramiko.transport').setLevel(logging.WARN)
logging.getLogger('pssh.clients.native.single').setLevel(logging.WARN)


def relative_path(*args):
    return os.path.realpath(os.path.join(os.path.dirname(__file__), '..', *args))


def make_dirs(dir_path):
    if not os.path.exists(dir_path):
        logging.info("Creating directory: {}".format(dir_path))
        os.makedirs(dir_path)


def print_banner(s):
    b = '-' * min(len(s), 100)
    print(b)
    print(s)
    print(b)


class DSPLError(click.ClickException):

    def __init__(self, message, exit_code=-1):
        super().__init__(message)
        self.exit_code = exit_code

    def show(self, file=None):
        if file:
            super().show(file)
            return

        logging.error(self.message)


class DSPLContext:

    def __init__(self) -> None:
        self.all_nodes = {}  # type: Dict[str, Dict[str, str]]
        self.all_groups = {}  # type: Dict[str, List[str]]

        # Name of the selected nodes with `-n` arguments
        self.nodes = []  # type: List[str]
        self._conns = {}  # type: Dict[str, Connection]

    def connection(self, node: str) -> Connection:
        if node not in self._conns:
            self._conns[node] = Connection(node)

        return self._conns[node]

    def close(self):
        for n in self._conns:
            self._conns[n].close()

    def run(self, cmd, warn=True):
        for n in self.nodes:
            logging.info(f"Running command `{cmd}` in {n}")
            self.connection(n).run(cmd, warn=warn)

    @staticmethod
    def join_commands(cmd: Union[str, List[str]], sudo=False):
        if isinstance(cmd, str):
            return f"sudo {cmd}" if sudo else cmd

        cmd_with_sudo = [f"sudo {c}" for c in cmd] if sudo else cmd
        return " && ".join(cmd_with_sudo)

    def run_parallel(self, cmd: Union[str, List[str]], sudo=False, warn=True, save_result=False):
        for n in self.nodes:
            self.connection(n)

        log_dir = relative_path('logs', datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))

        logging.info(f"Running commands in {self.nodes}")
        group = ThreadingGroup.from_connections(self._conns.values())
        cmd_str = self.join_commands(cmd, sudo)

        try:
            # We enforce failure later
            result = group.run(cmd_str, warn=True)
            self.save_results(save_result, warn, log_dir, result)
        except GroupException as r:
            logging.info("Exception occurred")
            self.save_results(save_result, warn, log_dir, r.result)

    def save_results(self, save_result, warn, log_dir, result):
        if save_result:
            logging.info(f"Saving logs in {log_dir}")
            make_dirs(log_dir)

        self.save_outputs(save_result, log_dir, result.succeeded)
        self.save_outputs(save_result, log_dir, result.failed)

        if len(result.failed) > 0 and not warn:
            raise DSPLError(f'Command execution failed in {len(result.failed)} hosts')

    @staticmethod
    def save_outputs(save_result, log_dir, result_dict):
        for c, r in result_dict.items():
            if not isinstance(r, Result):
                logging.info(f"Host {c.original_host} returned: {r}")
                continue

            logging.info(f"Host {c.original_host} exit code: {r.exited}")

            if save_result:
                with open(os.path.join(log_dir, f'{c.original_host}.stdout'), 'w') as f:
                    f.write(r.stdout)

                with open(os.path.join(log_dir, f'{c.original_host}.stderr'), 'w') as f:
                    f.write(r.stderr)

    def exists(self, remote_path: str, sudo=False) -> Dict[str, bool]:
        results = {}
        cmd = f"test -e {remote_path}"

        if sudo:
            cmd = f"sudo {cmd}"

        for n in self.nodes:
            r = self.connection(n).run(cmd, warn=True)
            results[n] = r.exited == 0

        return results

    def read_file(self, remote_path: str, sudo: bool = False) -> Dict[str, str]:
        results = {}
        for n in self.nodes:
            try:
                with BytesIO() as content_stream:
                    self.connection(n).get(remote=remote_path, local=content_stream)
                    content_stream.seek(0)

                    results[n] = content_stream.read().decode('utf-8')
            except FileNotFoundError:
                logging.error(f"File not found in {n}")
                results[n] = None

        return results

    def write_content(self, remote_path: str, contents: Dict[str, str]):
        remote_local_path = '/tmp/' + str(uuid.uuid4())

        for n, content in contents.items():
            logging.info(f"Writing content in {n}:{remote_path}")
            with StringIO(content) as s:
                self.connection(n).put(local=s, remote=remote_local_path)

            self.connection(n).sudo(f"cat {remote_local_path} | sudo tee {remote_path} && rm {remote_local_path}")


@click.group(name='dspl', help="DSPL cluster management", context_settings=CONTEXT_SETTINGS)
@click.option(
    '-n', '--nodes', help="Comma separated list of nodes to execute associated command", envvar='NODES', default=None
)
@click.pass_context
def cli(ctx: click.Context, nodes=None):
    d = relative_path('data')
    context = DSPLContext()

    for filename in sorted(os.listdir(d)):
        if not filename.endswith('.yml'):
            continue

        p = os.path.join(d, filename)

        with open(p) as f:
            data = yaml.safe_load(f)
            if not data:
                continue

        if 'Nodes' in data:
            context.all_nodes.update(data['Nodes'])

        if 'Groups' in data:
            context.all_groups.update(data['Groups'])

    if nodes:
        for n in nodes.split(','):
            if n in context.all_nodes and n not in context.nodes:
                context.nodes.append(n)
            elif n in context.all_groups:
                context.nodes.extend([gn for gn in context.all_groups[n] if gn not in context.nodes])
            else:
                raise DSPLError(f"Node information not found: {n}")

    if context.nodes:
        for n in context.nodes:
            if n not in context.all_nodes:
                raise DSPLError(f"Node information not found: {n}")
    else:
        # No node selected, so select all
        context.nodes.extend(context.all_nodes.keys())

    ctx.obj = context

    def _close():
        ctx.obj.close()

    ctx.call_on_close(_close)
