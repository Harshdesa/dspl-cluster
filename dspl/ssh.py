import logging
import os
from typing import List, Dict

import click

from dspl import core


class SSHHost:
    def __init__(self, hostname, ip, **kwargs):
        self.hostname = hostname
        self.ip = ip
        for k, v in kwargs.items():
            setattr(self, k, v)


class SSHHosts:
    optional_attributes = [
        ('Port', 'port'),
        ('User', 'user'),
        ('IdentityFile', 'identity-file')
    ]

    def __init__(self, hosts: List[SSHHost]):
        self.hosts = hosts

    @staticmethod
    def parse(nodes: Dict[str, Dict[str, str]], user: str, default_identity: str):
        hosts = []
        for h in nodes:
            host = SSHHost(hostname=h, **nodes[h])
            if not hasattr(host, 'identity-file'):
                setattr(host, 'identity-file', default_identity)

            if not hasattr(host, 'user'):
                setattr(host, 'user', user)

            hosts.append(host)

        return SSHHosts(hosts)

    def get_attribute(self, attribute, h):
        if hasattr(h, attribute):
            return getattr(h, attribute)

        if hasattr(self, attribute):
            return getattr(self, attribute)

    def _gen_host(self, h):
        yield 'Host {}'.format(h.hostname)
        yield '  HostName {}'.format(h.ip)
        for o, i in self.optional_attributes:
            v = self.get_attribute(i, h)
            if not v:
                continue

            yield '  {} {}'.format(o, v)

    def generate_config_file(self):

        results = []
        for h in self.hosts:
            x = [l for l in self._gen_host(h)]
            results.extend(x)

            proxy_suffix = self.get_attribute('proxy-suffix', h)
            proxy = self.get_attribute('proxy', h)

            if proxy_suffix:
                # Adding separate host entry for proxy in addition to the original entry

                results.append('')
                results.append(x[0] + '-' + proxy_suffix)
                results.extend(x[1:])

            if proxy:
                results.append('  ProxyCommand ssh {} nc %h %p'.format(proxy))

            results.append('')

        return results


@core.cli.group(help="Manage SSH configurations")
def ssh():
    pass


@ssh.command(
    name='generate',
    help="Generate SSH config"
)
@click.argument('username')
@click.option('-i', '--default-identity-file', help='Default identity file', default=None)
@click.pass_obj
def generate(ctx: core.DSPLContext, username, default_identity_file):
    logging.info("Generating SSH configurations")

    hosts = SSHHosts.parse(nodes=ctx.all_nodes, user=username, default_identity=default_identity_file)
    content = os.linesep.join(hosts.generate_config_file())

    print(content)
