# DSPL Cluster

Project to manage Data Security and Privacy Lab's cluster.

## Cluster Topology

Only the router/mater node is accessible from outside world.
All other nodes can be reached through

                   ----------       ---------     --------
    Internet <---> | Router | <---> | Node1 | ... | Sgx7 |
                   ----------       ---------     --------

- All network communications to internal nodes go through router node
- We use a `bind` server to solve DNS queries from internal nodes
- We use packet masquerading technique to allow internet connectivity to internal nodes.
- Do not run experiments in the Router node, might slow down/break all communication
- **Update iptables rules with extreme caution in router node**, might break access to all nodes

IP Allocations are at [data/nodes.yml](data/nodes.yml)

## Installation

Create virtualenv

    python3 -m venv venv

Install required dependencies

    . venv/bin/activate
    pip install -r requirements.txt

Install this project

    pip install -e .

**If new dependencies are added** then update the `requirements.txt` with

    pip freeze | grep -v pkg-resources | grep -v dspl  > requirements.txt

 ## Executing a command of this project

The project is organized in commands sub-commands and core command is `dspl`.
Once the `venv` is activated with `.` (aka `source`). Commands can be executed as following

    . venv/bin/activate
    dspl <cmd> <sub-cmd>

By default commands are applied to all nodes to limit use parameter `-n`

    dspl -n 'sgx2,sgx7' <cmd> <sub-cmd>

`-n` can take a node name or a group name. Nodes and groups are defined in `data/*.yml` files.

## SSH Configurations

First generate ssh configs with the following command and put the contents in `~/.ssh/config`

    dspl ssh generate <username> -i path/to/ssh-key-private

Then you will be able to run `ssh <node-name>` to connect to that node.

## Execute a shell command in all nodes

Run `ls -hal` in all the nodes in `sgx` group

    dspl -n 'sgx' node cmd 'ls -hal '

Run the same command in parallel

    dspl -n 'sgx' node cmd -p 'ls -hal'

When running in parallel the stdout doesn't make much sense, so we save the `stdout` and `stderr`
in `logs/{date_time}/{node}.{stdout|stderr}` files for each node.

Note: Running a command in parallel in too many nodes may trigger a `Exception: Error reading SSH protocol banner`
In general it means, we didn't receive a respond in a predetermined time.
With very high probability it in this case it is due to network congestion.

## Available commands

The command is built with [Click](https://click.palletsprojects.com/en/7.x/) with help messages.
Explore each parent level commands with `-h` to see available sub-commands.

    Usage: dspl [OPTIONS] COMMAND [ARGS]...

      DSPL cluster management

    Options:
      -n, --nodes TEXT  Comma separated list of nodes to execute associated
                        command

      -h, --help        Show this message and exit.

    Commands:
      auth-keys  Manage authorized keys
      node       Manage nodes and systems
      ssh        Manage SSH configurations
      users      Manage users in the cluster
