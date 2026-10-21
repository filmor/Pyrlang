# Pyrlang - Erlang node in Python

This is a drop-in Erlang node implementation in Python 3, implementing
a network Erlang node protocol. It was designed to allow interoperation between
existing Python projects and BEAM languages: Erlang, Elixir, Gleam, Luaerl,
LFE, Clojerl and such.

With just a few lines of startup code your Python program becomes an Erlang
network node, participating in the Erlang cluster.

## Features

*   Erlang distribution protocol for Erlang versions 19 to 25
*   Registry of Python 'processes', which have an Erlang-compatible process
    identifier and an optional registered name
*   Send and receive messages locally and remotely by pid or name
*   Can link and monitor Erlang from Python and Python from Erlang
*   `net_adm` pings supported
*   RPC calls to Python (Erlang `rpc:call`). Exceptions are propagated
    from Python back to Erlang;
*   `pyrlang.gen.server.GenServer` descendant from `pyrlang.process.Process`
    allows accepting generic calls mapped to Python class members

## Documentation

Browse at https://pyrlang.github.io/Pyrlang/

Or build your own with `uv run sphinx-build -b html docs-src/source docs`.

## Installing

### From PyPI

```console
uv pip install pyrlang
```

### Local from Sources

Clone [Pyrlang](https://github.com/Pyrlang/Pyrlang), then run `uv sync`
in the project directory. This installs Pyrlang in editable mode, its
`pyrlang-term` dependency directly from GitHub, and the development tools.

Run Python commands with `uv run python` and tests with `uv run pytest`.
For a runtime-only environment, use `uv sync --no-dev`.

To work on [Term](https://github.com/Pyrlang/Term) alongside Pyrlang, clone it
and install it into the project environment with `uv pip install -e ../Term`.

## Support & Questions

For those times when you absolutely need assistance and email is too slow, here's a Discord channel: https://discord.gg/pWWe7Wx and there is a Slack channel `#pyrlang` on https://erlanger.slack.com/
