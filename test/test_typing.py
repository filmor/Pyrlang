import asyncio
from typing import TYPE_CHECKING, Any, assert_type
from unittest.mock import AsyncMock, Mock

import pytest
from term import Pid, Reference

from pyrlang.dist_proto.base_dist_protocol import (
    CONTROL_TERM_DEMONITOR_P,
    BaseDistProtocol,
)
from pyrlang.dist_proto.distribution import ErlangDistribution
from pyrlang.dist_proto.epmd_client import EPMDClient
from pyrlang.errors import EPMDClientError, ProcessNotFoundError
from pyrlang.gen.decorators import async_wrapper_factory, call, cast, info
from pyrlang.gen.server import GenServer, GenServerInterface
from pyrlang.node import Node
from pyrlang.process import Process

if TYPE_CHECKING:

    class TypedServer(GenServer):
        @call(1, lambda msg: True)
        def sync_handler(self, msg: str) -> int:
            return len(msg)

        @cast(1, lambda msg: True)
        async def async_handler(self, msg: str) -> int:
            return len(msg)

    async def check_types(node: Node, server: TypedServer, pid: Pid) -> None:
        assert_type(node.where_is(pid), Pid)
        assert_type(node.where_is_process(pid), Process | None)
        assert_type(server.get_node(), Node)
        assert_type(await server.sync_handler("hello"), int)
        assert_type(await server.async_handler("hello"), int)
        assert_type(await async_wrapper_factory(len)("hello"), int)


@pytest.mark.parametrize("decorator", [call, cast, info])
@pytest.mark.parametrize("is_async", [False, True])
def test_handler_wrappers_preserve_results(decorator: Any, is_async: bool) -> None:
    def sync_handler(msg: str) -> int:
        return len(msg)

    async def async_handler(msg: str) -> int:
        return len(msg)

    handler = decorator(1, lambda msg: True)(
        async_handler if is_async else sync_handler
    )
    assert asyncio.run(handler("hello")) == 5
    assert handler._gen_order == 1
    assert handler._gen_pattern.match("hello")


def test_remote_demonitor_removes_monitor_and_sends_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node = object.__new__(Node)
    node.node_name_ = "local@host"
    node.is_exiting_ = False
    node.reg_names_ = {}
    origin = Pid(node.node_name_, 0, 0, 0)
    target = Pid("remote@host", 0, 0, 0)
    ref = Reference.create(node.node_name_, 0)
    process = object.__new__(Process)
    process._monitors = {ref: target}
    process._monitored_by = {}
    node.processes_ = {origin: process}
    protocol = BaseDistProtocol(node.node_name_)
    node.dist_nodes_ = {target.node_name_: protocol}
    send_control = Mock()
    monkeypatch.setattr(protocol, "_control_message", send_control)

    assert asyncio.run(node.demonitor_process(origin, target, ref)) is None
    assert ref not in process._monitors
    protocol._handle_one_inbox_message(protocol.inbox_.get_nowait())
    send_control.assert_called_once_with(
        (CONTROL_TERM_DEMONITOR_P, origin, target, ref), None
    )


def test_gen_server_call_awaits_demonitor() -> None:
    node = Mock(spec=Node)
    node.send = AsyncMock()
    node.demonitor_process = AsyncMock()
    caller = Mock(spec=Process)
    caller.pid_ = Pid("local@host", 0, 0, 0)
    caller.get_node.return_value = node
    caller.receive = AsyncMock(return_value="reply")
    target = Pid("remote@host", 0, 0, 0)
    interface = GenServerInterface(caller, target)

    assert asyncio.run(interface.call("request")) == "reply"
    node.demonitor_process.assert_awaited_once_with(
        caller.pid_, target, node.monitor_process.return_value
    )


def test_distribution_demonitor_is_awaited(monkeypatch: pytest.MonkeyPatch) -> None:
    protocol = BaseDistProtocol("local@host")
    node = Mock(spec=Node)
    node.demonitor_process = AsyncMock()
    monkeypatch.setattr(protocol, "get_node", lambda: node)
    origin = Pid("remote@host", 0, 0, 0)
    target = Pid("local@host", 0, 0, 0)
    ref = Reference.create("remote@host", 0)

    result = asyncio.run(
        protocol.on_passthrough_message(
            (CONTROL_TERM_DEMONITOR_P, origin, target, ref), None
        )
    )
    assert result is None
    node.demonitor_process.assert_awaited_once_with(
        origin_pid=origin, target=target, ref=ref
    )


def test_monitor_reports_missing_local_origin() -> None:
    node = object.__new__(Node)
    node.node_name_ = "local@host"
    node.reg_names_ = {}
    origin = Pid(node.node_name_, 0, 0, 0)
    target = Pid(node.node_name_, 0, 1, 0)
    node.processes_ = {target: Mock(spec=Process)}

    with pytest.raises(ProcessNotFoundError, match="Monitor origin"):
        node.monitor_process(origin, target, Reference.create(node.node_name_, 0))


def test_unconnected_epmd_close_reports_error() -> None:
    with pytest.raises(EPMDClientError, match="No writer"):
        EPMDClient().close()


def test_unstarted_distribution_server_reports_error() -> None:
    dist = ErlangDistribution("local@host")
    with pytest.raises(RuntimeError, match="has not been started"):
        asyncio.run(dist.run_dist_server())
